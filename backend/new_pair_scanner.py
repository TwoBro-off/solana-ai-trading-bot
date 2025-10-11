import asyncio
import json
import websockets
from loguru import logger
from solders.pubkey import Pubkey
from solders.rpc.responses import RpcLogsResponse, SubscriptionResult

# Raydium Liquidity Pool V4 program ID
RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
SOL_MINT = "So11111111111111111111111111111111111111112"

class NewPairScanner:
    def __init__(self, websocket_url: str, decision_module):
        self.websocket_url = websocket_url
        self.decision_module = decision_module
        self.connection = None
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            try:
                await self._listen()
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
                logger.warning(f"WebSocket connection closed: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"An unexpected error occurred in the scanner: {e}. Restarting loop in 10 seconds...")
                await asyncio.sleep(10)

    def stop(self): # Rendu synchrone pour un arrêt propre
        self.running = False
        if self.connection:
            # La fermeture de la connexion sera gérée par la sortie de la boucle `_listen`
            asyncio.create_task(self.connection.close())
        logger.info("NewPairScanner stopped.")

    async def _listen(self):
        logger.info(f"Connecting to WebSocket: {self.websocket_url}")
        async with websockets.connect(self.websocket_url) as ws:
            self.connection = ws
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [RAYDIUM_LP_V4]},
                    {"commitment": "processed"}
                ]
            }))
            # Attendre la confirmation de l'abonnement
            await ws.recv()
            logger.success("WebSocket connected and subscribed to Raydium LP logs.")

            async for message in ws:
                data = json.loads(message)
                if 'params' not in data or 'result' not in data['params']:
                    continue

                log_result = RpcLogsResponse.from_json(message).value
                if not log_result.value:
                    continue

                logs = log_result.value.logs
                if any("initialize2" in log for log in logs):
                    signature = log_result.value.signature
                    logger.success(f"New Raydium Liquidity Pool detected! Signature: {signature}")
                    asyncio.create_task(self.process_new_pool(signature))

    async def process_new_pool(self, signature):
        """Analyse la transaction pour extraire les informations de la nouvelle pool."""
        try:
            client = self.decision_module.order_executor.async_client
            tx_resp = await client.get_transaction(signature, encoding="jsonParsed", max_supported_transaction_version=0)
            if not tx_resp or not tx_resp.value or not tx_resp.value.transaction:
                logger.error(f"Could not retrieve transaction details for signature {signature}")
                return

            tx = tx_resp.value.transaction
            instructions = tx.message.instructions

            # Trouver l'instruction 'initialize2'
            for ix in instructions:
                if ix.program_id == Pubkey.from_string(RAYDIUM_LP_V4) and ix.data and "initialize2" in str(ix.data):
                    accounts = ix.accounts
                    token0_mint = str(accounts[8])
                    token1_mint = str(accounts[9])

                    # Identifier le nouveau token et le token de base (SOL)
                    if token0_mint == SOL_MINT:
                        base_token_mint, new_token_mint = token0_mint, token1_mint
                    elif token1_mint == SOL_MINT:
                        base_token_mint, new_token_mint = token1_mint, token0_mint
                    else:
                        logger.warning(f"New pair does not involve SOL: {token0_mint} / {token1_mint}. Skipping.")
                        return
                    
                    # Calculer le prix initial en analysant les changements de balance
                    pre_balances = tx.meta.pre_token_balances
                    post_balances = tx.meta.post_token_balances
                    
                    sol_change = next((bal.ui_token_amount.ui_amount for bal in post_balances if bal.mint == SOL_MINT), 0) - \
                                 next((bal.ui_token_amount.ui_amount for bal in pre_balances if bal.mint == SOL_MINT), 0)
                    
                    token_change = next((bal.ui_token_amount.ui_amount for bal in post_balances if bal.mint == new_token_mint), 0) - \
                                   next((bal.ui_token_amount.ui_amount for bal in pre_balances if bal.mint == new_token_mint), 0)

                    if base_token_mint != SOL_MINT:
                        logger.warning(f"New pair does not involve SOL: {token0_mint} / {token1_mint}")
                        return
                    if token_change > 0 and abs(sol_change) > 0:
                        initial_price = abs(sol_change) / token_change
                        logger.info(f"New token identified: {new_token_mint} at initial price: {initial_price:.12f} SOL. Passing to Decision Module.")
                        await self.decision_module.process_new_token_candidate(new_token_mint, current_price=initial_price)
                    else:
                        logger.warning(f"Could not determine initial price for {new_token_mint}. Passing with price 0.")
                        await self.decision_module.process_new_token_candidate(new_token_mint, current_price=0.0)
                    return
        except Exception as e:
            logger.error(f"Error processing new pool for signature {signature}: {e}")