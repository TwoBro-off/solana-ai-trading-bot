# --- API : Créer un fichier via Gemini (OpenRouter) ---
class CreateFileRequest(BaseModel):
    file: str
    content: str

@app.post("/api/gemini-create-file", dependencies=[Depends(get_current_user)])
async def gemini_create_file(req: CreateFileRequest = Body(...)):
    """
    Permet à Gemini de créer un nouveau fichier dans le projet (hors fichiers critiques/secrets).
    """
    try:
        forbidden = [".env", "env", "secrets", "private_key", "wallet", "node_modules", "venv", "__pycache__", "requirements.txt", "main.py"]
        if any(x in req.file.lower() for x in forbidden):
            return JSONResponse(status_code=403, content={"error": "Création de ce fichier interdite."})
        # Crée le dossier si besoin
        import os
        os.makedirs(os.path.dirname(req.file), exist_ok=True)
        with open(req.file, "w", encoding="utf-8") as f:
            f.write(req.content)
        logger.info(f"[GeminiCreateFile] Fichier créé : {req.file}")
        return {"status": "ok", "message": f"Fichier créé : {req.file}"}
    except Exception as e:
        logger.error(f"Erreur GeminiCreateFile : {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur GeminiCreateFile: {e}"})
# --- API : Appliquer un patch proposé par Gemini (OpenRouter) ---
class ApplyPatchRequest(BaseModel):
    file: str
    patch: str  # Le patch à appliquer (diff unifié ou remplacement complet)

@app.post("/api/gemini-apply-patch", dependencies=[Depends(get_current_user)])
async def gemini_apply_patch(req: ApplyPatchRequest = Body(...)):
    """
    Applique un patch proposé par Gemini sur un fichier du projet (hors secrets/env).
    L'utilisateur doit valider le patch avant application.
    """
    try:
        forbidden = [".env", "env", "secrets", "private_key", "wallet", "node_modules", "venv", "__pycache__"]
        if any(x in req.file.lower() for x in forbidden):
            return JSONResponse(status_code=403, content={"error": "Modification de ce fichier interdite."})
        # Pour simplifier, on remplace le contenu du fichier par le patch (texte complet)
        with open(req.file, "w", encoding="utf-8") as f:
            f.write(req.patch)
        logger.info(f"[GeminiPatch] Patch appliqué sur {req.file}")
        return {"status": "ok", "message": f"Patch appliqué sur {req.file}"}
    except Exception as e:
        logger.error(f"Erreur GeminiApplyPatch : {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur GeminiApplyPatch: {e}"})
from fastapi import Body
import inspect
# --- API : Chat Gemini (OpenRouter) pour modification du bot ---
class GeminiChatRequest(BaseModel):
    message: str
    file: Optional[str] = None  # Chemin du fichier à exposer à l'IA (optionnel)

@app.post("/api/gemini-chat", dependencies=[Depends(get_current_user)])
async def gemini_chat(req: GeminiChatRequest = Body(...)):
    """
    Permet à l'utilisateur de discuter avec Gemini (OpenRouter) et de demander des modifications du bot.
    Si 'file' est fourni, le code source du fichier est inclus dans le prompt pour l'IA.
    L'IA peut proposer un patch ou une explication, et l'utilisateur valide avant application.
    """
    try:
        prompt = req.message
        code_snippet = None
        if req.file:
            # Autoriser l'accès à tous les fichiers du projet sauf secrets/env
            forbidden = [".env", "env", "secrets", "private_key", "wallet", "node_modules", "venv", "__pycache__"]
            if any(x in req.file.lower() for x in forbidden):
                code_snippet = "[Accès refusé à ce fichier critique ou sensible]"
            else:
                try:
                    with open(req.file, "r", encoding="utf-8") as f:
                        code_snippet = f.read()
                except Exception as e:
                    code_snippet = f"[Erreur lecture fichier: {e}]"
        full_prompt = prompt
        if code_snippet:
            full_prompt += f"\n\nVoici le code source demandé :\n\n" + code_snippet[:8000]  # Limite taille
        # Appel OpenRouter (Gemini, GPT, etc.)
        headers = {
            "Authorization": f"Bearer {gemini_analyzer.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": gemini_analyzer.model,
            "messages": [
                {"role": "system", "content": "Tu es un assistant IA pour le développement Python FastAPI/React. Propose des modifications de code sous forme de patchs clairs, ou explique comment modifier le bot. Ne propose jamais d'action dangereuse ou de fuite de clé."},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 512,
            "temperature": 0.2
        }
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30) as resp:
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"]
        logger.info(f"[GeminiChat] Question: {prompt}\nRéponse: {reply[:200]}...")
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Erreur GeminiChat : {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur GeminiChat: {e}"})
from .ai_analysis.ai_auto_optimizer import AIAutoOptimizer
ai_optimizer = None
async def get_rpc_latency(rpc_url: str) -> float:
    """Stub: Returns a fake RPC latency for now (ms)."""
    return 42.0

async def get_solana_balance(rpc_url: str, private_key: str) -> float:
    """Stub: Returns a fake SOL balance for now."""
    return 100.0
import os
def get_bot_mode_and_status():
    # Détecte le mode actif et un message d’état
    mode = 'inconnu'
    msg = ''
    if ai_optimizer:
        if getattr(ai_optimizer, 'vacation_mode', False):
            mode = 'vacances'
            msg = 'Optimisation IA intensive (simulation) en cours.'
        elif getattr(ai_optimizer, 'simulation_only', True):
            mode = 'simulation'
            msg = 'Le bot tourne en simulation.'
        else:
            mode = 'réel'
            msg = 'Le bot trade en vrai argent.'
    return mode, msg
    class RealModeRequest(BaseModel):
        days: int = 0
        hours: int = 0

    @app.post("/api/ai/start_real_mode", dependencies=[Depends(get_current_user)])
    async def start_real_mode(real: RealModeRequest):
        """Active le trading réel pour la durée spécifiée, puis repasse en simulation."""
        try:
            total_days = float(real.days) + float(real.hours) / 24.0
            if total_days <= 0:
                return JSONResponse(status_code=400, content={"error": "Durée invalide"})
            optimizer = get_ai_optimizer()
            optimizer.start_real_mode(days=total_days)
            return {"status": "ok", "message": f"Trading réel activé pour {total_days:.2f} jours."}
        except Exception as e:
            logger.error(f"Erreur start_real_mode : {e}")
            return JSONResponse(status_code=500, content={"error": "Erreur lors de l'activation du mode réel"})
from .ai_analysis.ai_auto_optimizer import AIAutoOptimizer
ai_optimizer = None
def get_ai_optimizer():
    global ai_optimizer
    if ai_optimizer is None:
        if decision_module is None:
            initialize_trading_modules()
        ai_optimizer = AIAutoOptimizer(decision_module)
    return ai_optimizer
    # --- API : démarrer le mode vacances (simulation/auto-optimisation pendant X jours/heures) ---
    class VacationRequest(BaseModel):
        days: int = 0
        hours: int = 0

    @app.post("/api/ai/start_vacation_mode", dependencies=[Depends(get_current_user)])
    async def start_vacation_mode(vacation: VacationRequest):
        """Active le mode vacances (simulation/auto-optimisation) pour la durée spécifiée."""
        try:
            total_days = float(vacation.days) + float(vacation.hours) / 24.0
            if total_days <= 0:
                return JSONResponse(status_code=400, content={"error": "Durée invalide"})
            optimizer = get_ai_optimizer()
            optimizer.start_vacation_mode(days=total_days)
            logger.info(f"Mode vacances lancé pour {total_days:.2f} jours.")
            return {"status": "ok", "message": f"Mode vacances lancé pour {total_days:.2f} jours."}
        except Exception as e:
            logger.error(f"Erreur start_vacation_mode : {e}")
            return JSONResponse(status_code=500, content={"error": "Erreur lors de l'activation du mode vacances"})
import os
import asyncio
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Optional
import logging

from .config.settings import initiate_settings
from .blockchain.token_scanner import TokenScanner
from .blockchain.websocket_listener import WebSocketListener
from .trading.decision_module import DecisionModule
from utils.solana_utils import get_trustwallet_balance
from .ai_analysis.gemini_analyzer import GeminiAnalyzer
from .ai_analysis.reputation_db_manager import ReputationDBManager
from .utils.logger import setup_logging
from .auth.auth import authenticate_user, create_access_token, get_current_user

load_dotenv()

settings = initiate_settings()
logger = setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)

# Contrôle des paramètres essentiels
if not settings.GEMINI_API_KEY or not settings.PRIVATE_KEY or not settings.WALLET_ADDRESS:
    logger.critical("Configuration manquante : GEMINI_API_KEY, PRIVATE_KEY ou WALLET_ADDRESS.")
    raise RuntimeError("Veuillez renseigner la clé API Gemini et votre compte TrustWallet (PRIVATE_KEY, WALLET_ADDRESS) dans le fichier .env avant de lancer le bot.")

app = FastAPI(
    title="API du Bot de Trading IA Solana",
    description="API pour l'analyse de tokens Solana en temps réel et l'automatisation du trading.",
    version="1.0.0",
)

app.mount("/", StaticFiles(directory="backend/static", html=True), name="static")

reputation_db_manager = ReputationDBManager(settings.DATABASE_URL)
gemini_analyzer = GeminiAnalyzer(settings.GEMINI_API_KEY, reputation_db_manager)
token_scanner = TokenScanner(
    settings.SOLANA_RPC_URL,
    gemini_analyzer,
    reputation_db_manager,
    settings.REPUTATION_SCORE_THRESHOLD
)
websocket_listener = WebSocketListener(settings.SOLANA_WEBSOCKET_URL)
order_executor = None
decision_module = None

def initialize_trading_modules():
    global order_executor, decision_module
    from .trading.order_executor import OrderExecutor
    order_executor = OrderExecutor(
        settings.SOLANA_RPC_URL,
        settings.SOLANA_PRIVATE_KEY
    )
    decision_module = DecisionModule(
        order_executor,
        settings.BUY_AMOUNT_SOL,
        settings.SELL_MULTIPLIER
    )
    global ai_optimizer
    from .ai_analysis.ai_auto_optimizer import AIAutoOptimizer
    ai_optimizer = AIAutoOptimizer(decision_module)
# --- API : Profits cumulés (simulation + réel) ---
@app.get("/api/profits", summary="Obtenir le profit total en simulation et en réel", dependencies=[Depends(get_current_user)])
async def get_total_profits():
    """Retourne le profit total (simulation et réel) depuis le lancement du bot."""
    try:
        if ai_optimizer is None:
            return JSONResponse(status_code=500, content={"error": "AI optimizer non initialisé"})
        # Rafraîchir les profits à partir des logs
        ai_optimizer.analyze_and_adjust()
        return {
            "profit_simulation": round(getattr(ai_optimizer, "sim_profit", 0.0), 6),
            "profit_reel": round(getattr(ai_optimizer, "real_profit", 0.0), 6)
        }
    except Exception as e:
        logger.error(f"Erreur récupération profits : {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors de la récupération des profits"})
initialize_trading_modules()

@app.on_event("startup")
async def startup_event():
    """Démarrage de l'application : connexion BDD, lancement des tâches asynchrones."""
    logger.info("Starting up application...")
    try:
        await reputation_db_manager.connect()
        asyncio.create_task(token_scanner.start_scanning(settings.TOKEN_SCAN_INTERVAL))
        asyncio.create_task(websocket_listener.start_listening(decision_module))
        asyncio.create_task(log_rpc_latency())
        logger.info("Application startup complete.")
    except Exception as e:
        logger.critical(f"Erreur au démarrage : {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Arrêt propre de l'application."""
    logger.info("Shutting down application...")
    try:
        await websocket_listener.stop_listening()
        await reputation_db_manager.disconnect()
        logger.info("Application shutdown complete.")
    except Exception as e:
        logger.error(f"Erreur à l'arrêt : {e}")

async def log_rpc_latency():
    """Tâche asynchrone pour loguer la latence RPC."""
    while True:
        try:
            latency = await get_rpc_latency(settings.SOLANA_RPC_URL)
            logger.info(f"RPC Latency: {latency:.2f} ms")
        except Exception as e:
            logger.warning(f"Erreur lors du check de latence RPC : {e}")
        await asyncio.sleep(settings.RPC_LATENCY_CHECK_INTERVAL)

@app.post("/token", summary="Créer un jeton d'accès pour l'interface web")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """Génère un token JWT pour l'authentification web."""
    user = authenticate_user(settings.WEB_USERNAME, settings.WEB_PASSWORD, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Tentative de connexion échouée pour l'utilisateur : {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"Token généré pour l'utilisateur : {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/dashboard", dependencies=[Depends(get_current_user)])
async def get_dashboard_data() -> dict:
    """Retourne les données du dashboard (solde, mode, message, P&L, tokens détenus)."""
    try:
        balance = await get_solana_balance(settings.SOLANA_RPC_URL, settings.SOLANA_PRIVATE_KEY)
        mode, msg = get_bot_mode_and_status()
        return {
            "solana_balance": balance,
            "mode": mode,
            "status_message": msg,
            "profits_losses": "N/A",
            "held_tokens": []
        }
    except Exception as e:
        logger.error(f"Erreur dashboard : {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors de la récupération du dashboard"})
# --- API : logs récents (30 dernières lignes simulation + réel) ---
@app.get("/api/logs/recent", dependencies=[Depends(get_current_user)])
async def get_recent_logs():
    def tail(filename, n=30):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.readlines()[-n:]
        except Exception:
            return []
    logs = tail('simulation_trades.log', 15) + tail('real_trades.log', 15)
    logs = [l.strip() for l in logs if l.strip()]
    return {"logs": logs[-30:]}

class ApiKeyUpdate(BaseModel):
    """Modèle pour la mise à jour de la clé API Gemini."""
    gemini_api_key: str

@app.post("/api/gemini-api-key", dependencies=[Depends(get_current_user)])
async def update_gemini_api_key(key_update: ApiKeyUpdate):
    """Met à jour la clé API Gemini utilisée par l'analyseur."""
    try:
        gemini_analyzer.update_api_key(key_update.gemini_api_key)
        logger.info("Clé API Gemini mise à jour via l'API.")
        return {"message": "Clé API Gemini mise à jour avec succès"}
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la clé Gemini : {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors de la mise à jour de la clé Gemini"})

class ReputationEntry(BaseModel):
    """Modèle pour l'ajout manuel d'une entrée de réputation."""
    wallet_id: str
    ip_publique: Optional[str] = None
    tags: List[str] = []
    comportement: Optional[str] = None
    score_de_confiance: float = Field(..., ge=0.0, le=1.0)

@app.post("/api/manual-reputation-entry", summary="Ajouter manuellement une entrée à la base de données de réputation", dependencies=[Depends(get_current_user)])
async def manual_reputation_entry(entry: ReputationEntry):
    """Ajoute une entrée manuelle à la base de données de réputation."""
    try:
        tags_str = ', '.join(entry.tags) if entry.tags else None
        reputation_db_manager.add_entry(entry.wallet_id, entry.ip_publique, tags_str, entry.comportement, entry.score_de_confiance)
        logger.info(f"Entrée de réputation ajoutée pour {entry.wallet_id}")
        return {"message": "Entrée ajoutée à la base de données de réputation"}
    except Exception as e:
        logger.error(f"Erreur ajout réputation : {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors de l'ajout de la réputation"})

@app.get("/api/reputation-db", summary="Obtenir les entrées de la base de données de réputation", dependencies=[Depends(get_current_user)])
async def get_reputation_db_entries():
    """Retourne toutes les entrées de la base de données de réputation."""
    try:
        return reputation_db_manager.get_all_entries()
    except Exception as e:
        logger.error(f"Erreur récupération BDD réputation : {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors de la récupération de la base de données de réputation"})

@app.get("/api/test-mode", summary="Activer/Désactiver le mode test", dependencies=[Depends(get_current_user)])
async def toggle_test_mode():
    """Active ou désactive le mode test (placeholder)."""
    # TODO: Implémenter la logique réelle de test mode
    logger.info("Test mode toggled (placeholder)")
    return {"message": "Mode test activé/désactivé (fonctionnalité à implémenter)"}

@app.post("/api/decision/set_initial_capital")
async def set_initial_capital(request: Request):
    """Définit le capital initial à investir (vérifie le solde TrustWallet)."""
    try:
        data = await request.json()
        amount = data.get("amount")
        if amount is None:
            return JSONResponse(status_code=400, content={"error": "amount required"})
        trustwallet_address = getattr(decision_module, 'trustwallet_address', None)
        if not trustwallet_address:
            return JSONResponse(status_code=400, content={"error": "Adresse TrustWallet non configurée"})
        sol_balance = await get_trustwallet_balance(trustwallet_address)
        if float(amount) > sol_balance:
            return JSONResponse(status_code=400, content={"error": f"Solde insuffisant sur TrustWallet ({sol_balance:.2f} SOL)"})
        decision_module.set_initial_capital(amount)
        logger.info(f"Capital initial défini à {amount} SOL")
        return {"status": "ok", "capital": amount}
    except Exception as e:
        logger.error(f"Erreur set_initial_capital : {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors de la définition du capital initial"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)