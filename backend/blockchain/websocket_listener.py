import asyncio
import websockets
import json
import re # Added for regex in _extract_mint_address
import base64
from .rpc_client import call_solana_rpc
from loguru import logger
from ..database.db import DatabaseManager, Token, Creator
from .creator_tracker import CreatorTracker
from .transaction_analyzer import TransactionAnalyzer
from .linked_account_detector import LinkedAccountDetector
from .creator_monitor import CreatorMonitor
from .real_time_analyzer import RealTimeAnalyzer
from .cache_manager import BlockchainCache

class WebSocketListener:
    def __init__(self, websocket_url: str, database_url: str, rpc_url: str):
        self.websocket_url = websocket_url
        self.connection = None
        self.listening_task = None
        self.db_manager = DatabaseManager(database_url)
        self.cache_manager = BlockchainCache(maxsize=10000, ttl=300)  # Cache plus grand pour l'analyse en temps réel
        self.creator_tracker = CreatorTracker(database_url, rpc_url)
        self.transaction_analyzer = TransactionAnalyzer(database_url, rpc_url)
        self.linked_account_detector = LinkedAccountDetector(database_url)
        self.creator_monitor = CreatorMonitor(database_url, rpc_url)
        self.real_time_analyzer = RealTimeAnalyzer(database_url, rpc_url, self.cache_manager)
        self.decision_module = None # Sera injecté par BotManager
        
    async def start(self):
        """Démarrage de toutes les surveillances."""
        if self.listening_task is None or self.listening_task.done():
            # Passer self.decision_module ici
            self.listening_task = asyncio.create_task(self._listen_for_notifications(self.decision_module))
            logger.info("WebSocket listening task started.")

        await self.creator_monitor.start_monitoring()
        await self.real_time_analyzer.start_analysis()

    def stop(self):
        """Arrête la tâche d'écoute WebSocket."""
        if self.listening_task and not self.listening_task.done():
            self.listening_task.cancel()
            logger.info("WebSocket listening task cancelled.")

    def _extract_mint_address(self, log_line: str) -> Optional[str]:
        """
        Extrait l'adresse du mint d'une ligne de log 'initializeMint'.
        """
        match = re.search(r'InitializeMint\s*:\s*(?P<mint_address>[1-9A-HJ-NP-Za-km-z]{32,44})', log_line)
        if match:
            return match.group('mint_address')
        # Fallback pour d'autres formats de log possibles
        parts = log_line.split()
        if "initializeMint" in parts:
            try:
                # Souvent, l'adresse du mint suit directement
                mint_index = parts.index("initializeMint") + 1
                if mint_index < len(parts):
                    potential_mint = parts[mint_index]
                    if 32 <= len(potential_mint) <= 44 and all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in potential_mint):
                        return potential_mint
            except ValueError:
                pass
        return None

    async def _listen_for_notifications(self, decision_module=None):
        logger.info(f"Connecting to WebSocket: {self.websocket_url}")
        while True:
            try:
                async with websockets.connect(self.websocket_url, ping_interval=10, ping_timeout=30) as ws:
                    self.connection = ws
                    logger.info("WebSocket connected. Subscribing to SPL Token program logs.")
                    
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "logsSubscribe",
                        "params": [
                            {"mentions": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]},
                            {"commitment": "processed"}
                        ]
                    }))
                    
                    await ws.recv() # Attendre la confirmation de l'abonnement
                    logger.success("Successfully subscribed to SPL Token program logs.")

                    async for message in ws:
                        event_start = asyncio.get_event_loop().time()
                        data = json.loads(message)
                        if 'params' in data and 'result' in data['params'] and 'value' in data['params']['result']:
                            value = data['params']['result']['value']
                            if 'logs' in value:
                                for log_line in value['logs']:
                                    if "initializeMint" in log_line:
                                        logger.info(f"InitializeMint detected: {log_line}")
                                        mint_address = self._extract_mint_address(log_line)
                                        if mint_address and decision_module:
                                            logger.success(f"New token mint found: {mint_address}. Passing to decision module.")
                                            # On ne connaît pas le prix initial ici, on le passe à 0. Le module de décision devra le récupérer.
                                            asyncio.create_task(decision_module.process_new_token_candidate(mint_address, current_price=0.0))
                                        else:
                                            logger.warning(f"Could not extract mint address from log: {log_line}")
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
                logger.error(f"WebSocket connection closed: {e}. Reconnecting in 5 seconds...")
            except asyncio.CancelledError:
                logger.info("WebSocket listener task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket listener: {e}. Reconnecting in 10 seconds...")
            
            await asyncio.sleep(5) # Délai avant de tenter une reconnexion

    async def process_new_token(self, signature):
        # Appel RPC pour récupérer la transaction et extraire le mint et le créateur
        resp = await call_solana_rpc("https://api.mainnet-beta.solana.com", "getTransaction", [signature, {"encoding": "json"}])
        if resp and resp.get("result"):
            tx = resp["result"]
            # Chercher l'instruction initializeMint
            for instr in tx["transaction"]["message"]["instructions"]:
                if instr.get("programId") == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                    data = instr.get("data")
                    if data:
                        decoded = base64.b64decode(data)
                        if len(decoded) > 0 and decoded[0] == 0:  # 0 = initializeMint
                            mint_address = instr["accounts"][0]
                            creator_address = tx["transaction"]["message"]["accountKeys"][instr["accounts"][1]]
                            logger.info(f"Mint: {mint_address}, Créateur: {creator_address}")
                            # Enregistrer dans la base de données
                            with self.db_manager.SessionLocal() as db:
                                # Créateur (logic to add/update creator in DB)
                                creator = db.query(Creator).filter_by(address=creator_address).first()
                                if not creator:
                                    creator = Creator(address=creator_address)
                                    db.add(creator)
                                    db.commit()