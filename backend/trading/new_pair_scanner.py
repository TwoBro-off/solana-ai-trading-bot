import asyncio
import json
import base58
import websockets
import traceback
from loguru import logger
from solders.pubkey import Pubkey
from solders.signature import Signature
from solana.exceptions import SolanaRpcException

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
                # Stratégie de détection plus ciblée : on écoute la création de comptes de token
                "params": [
                    {"mentions": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]}, # SPL Token Program
                    {"commitment": "finalized"} # On attend la finalisation pour être sûr
                ]
            }))
            # Le premier message est la confirmation d'abonnement. On l'attend et on le valide.
            subscription_response = await ws.recv()
            sub_data = json.loads(subscription_response)
            if 'result' in sub_data and isinstance(sub_data['result'], int):
                logger.success(f"WebSocket connected and subscribed with ID: {sub_data['result']}")
            else:
                logger.error(f"Failed to get a valid subscription ID from WebSocket. Response: {sub_data}")
                return

            # Maintenant que l'abonnement est confirmé, on écoute les vrais messages de log.
            async for message in ws:
                data = json.loads(message)

                # On extrait les logs et la signature directement, sans validation stricte
                value = data.get("params", {}).get("result", {}).get("value", {})
                if not isinstance(value, dict):
                    continue

                # Si ce n'est pas une notification de logs, on passe
                if data.get("method") != "logsNotification":
                    continue

                # Log the first message we receive to understand its structure
                if not hasattr(self, '_logged_first_message'):
                    logger.info(f"First message structure: {json.dumps(data)[:2000]}")
                    self._logged_first_message = True

                signature = None
                logs = []
                if isinstance(value, dict):
                    signature = value.get("signature")
                    # logs peut être sous forme de liste ou autre; on protège
                    raw_logs = value.get("logs")
                    if isinstance(raw_logs, list):
                        logs = raw_logs
                    elif isinstance(raw_logs, str):
                        # Parfois c'est chaîne; on peut essayer de splitlines
                        logs = raw_logs.splitlines()

                # On cherche le log spécifique à la création d'un nouveau compte de token
                if any("Instruction: InitializeAccount" in log for log in logs):
                    if signature:
                        logger.info(f"Potential new pair detected in transaction: {signature}. Analyzing...")
                        # Pass the raw signature string to the processor to avoid solders parsing issues
                        asyncio.create_task(self.process_new_pool(signature))

    async def process_new_pool(self, signature: str):
        """Analyse la transaction pour extraire les informations de la nouvelle pool."""
        try:
            client = self.decision_module.order_executor.async_client
            # Récupérer les détails de la transaction
            # The RPC client expects a solders.Signature object. Convert safely from the base58 string.
            try:
                sig_obj = Signature.from_string(signature)
            except Exception as e:
                logger.warning(f"Invalid signature format received, skipping: {signature} ({e})")
                return
            try:
                tx_resp = await client.get_transaction(sig_obj, encoding="jsonParsed", max_supported_transaction_version=0)
            except SolanaRpcException as e:
                logger.warning(f"Solana RPC rate limit reached (429 Too Many Requests): {e}. Waiting 2 seconds before retry.")
                await asyncio.sleep(2)
                return
            if not tx_resp or not getattr(tx_resp, 'value', None) or not getattr(tx_resp.value, 'transaction', None):
                logger.error(f"Could not retrieve transaction details for signature {signature}")
                return
            tx = tx_resp.value.transaction
            instructions = tx.message.instructions

            # Pré-filtrage : si le programme Raydium n'est même pas mentionné, on ignore la transaction.
            # C'est une optimisation cruciale pour éviter d'analyser des milliers de transactions non pertinentes.
            if not any(str(acc) == RAYDIUM_LP_V4 for acc in tx.message.account_keys):
                logger.debug(f"Skipping transaction {signature} as it does not involve Raydium LP V4 program.")
                return

            # Analyser les instructions pour trouver la création de pool
            # L'instruction 'initialize2' est celle qui nous intéresse.
            # Le discriminant pour 'initialize2' est b'\xd8\x1c\x8e#\x84\x96\xe9\x9b'
            initialize2_discriminant = b'\xd8\x1c\x8e#\x84\x96\xe9\x9b'
            for ix in instructions:
                # ix.data est maintenant une chaîne base58, il faut la décoder en bytes
                ix_data_bytes = base58.b58decode(ix.data)

                if ix.program_id == Pubkey.from_string(RAYDIUM_LP_V4) and ix_data_bytes.startswith(initialize2_discriminant):
                    accounts = ix.accounts
                    token0_mint = str(accounts[8])
                    token1_mint = str(accounts[9])

                    # Identifier le nouveau token et le token de base (SOL)
                    if token0_mint == SOL_MINT:
                        new_token_mint = token1_mint
                    elif token1_mint == SOL_MINT:
                        new_token_mint = token0_mint
                    else:
                        logger.debug(f"Skipping non-SOL pair: {token0_mint} / {token1_mint}")
                        return

                    # Found a new SOL pair -> handle it and exit
                    logger.info(f"New token identified: {new_token_mint}. Passing to Decision Module for analysis.")
                    self.decision_module.bot_manager.log_activity(f"Nouveau token détecté: {new_token_mint}", "INFO")
                    await self.decision_module.process_new_token_candidate(new_token_mint, current_price=0.0)
                    return
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error processing new pool for signature {signature}: {e}\n{tb}")
