from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
auto_validation = True
router = APIRouter()
@router.post("/api/trustwallet-validation")
async def set_trustwallet_validation(request: Request):
    data = await request.json()
    global auto_validation
    auto_validation = data.get("auto_validation", True)
    return JSONResponse({"auto_validation": auto_validation})
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter()

sessions = {}

@router.websocket("/ws/trustwallet")
async def trustwallet_connect(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    sessions[session_id] = websocket
    logger.info(f"Nouvelle session TrustWalletConnect v2 : {session_id}")
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Message TrustWallet reçu : {data}")
            if data.startswith("BUY_REQUEST:"):
                _, payload = data.split(":", 1)
                mint_address, amount = payload.split(",")
                tx = {
                    "type": "buy",
                    "mint_address": mint_address,
                    "amount": amount
                }
                if auto_validation:
                    logger.info(f"Validation automatique de l'achat {tx}")
                    await websocket.send_text(f"SIGNED:{tx}")
                else:
                    logger.info(f"Validation manuelle requise pour l'achat {tx}")
                    await websocket.send_text(f"SIGN_REQUEST:{tx}")
            else:
                await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        logger.info(f"Session TrustWalletConnect v2 terminée : {session_id}")
        del sessions[session_id]
