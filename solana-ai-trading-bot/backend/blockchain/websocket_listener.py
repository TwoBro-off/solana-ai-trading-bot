import asyncio
import websockets
import json
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
        
    async def start(self):
        """Démarrage de toutes les surveillances."""
        await self.start_listening()
        await self.creator_monitor.start_monitoring()
        await self.real_time_analyzer.start_analysis()

    async def _listen_for_notifications(self, decision_module=None):
        logger.info(f"Connecting to WebSocket: {self.websocket_url}")
        async with websockets.connect(self.websocket_url, ping_interval=2, close_timeout=0.5) as ws:
            self.connection = ws
            logger.info("WebSocket connected. Subscribing to program logs.")
            programs = [
                {"mentions": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]},
                {"mentions": ["9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"]},
                {"mentions": ["Orca11111111111111111111111111111111111111111"]},
            ]
            for i, program in enumerate(programs):
                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": i + 1,
                    "method": "logsSubscribe",
                    "params": [program, {"commitment": "finalized"}]
                }))
            async for message in ws:
                event_start = asyncio.get_event_loop().time()
                data = json.loads(message)
                if 'params' in data and 'result' in data['params'] and 'value' in data['params']['result']:
                    value = data['params']['result']['value']
                    if 'logs' in value:
                        for log_line in value['logs']:
                            if "initializeMint" in log_line:
                                logger.info(f"initializeMint detected: {log_line}")
                                mint_start = asyncio.get_event_loop().time()
                                mint_address = self._extract_mint_address(log_line)
                                price_resp = await call_solana_rpc(self.rpc_url, "getTokenSupply", [mint_address])
                                current_price = 0.0
                                if price_resp and 'result' in price_resp and 'value' in price_resp['result']:
                                    current_price = float(price_resp['result']['value'].get('uiAmount', 0.0))
                                if decision_module is not None:
                                    await decision_module.process_new_token_candidate(mint_address, current_price)
                                mint_latency = (asyncio.get_event_loop().time() - mint_start) * 1000
                                global_latency = (asyncio.get_event_loop().time() - event_start) * 1000
                                logger.info(f"Latence mint->achat: {mint_latency:.1f}ms | Latence totale event->achat: {global_latency:.1f}ms (objectif <600ms)")
                                signature = value.get('signature')
        slot_resp = await call_solana_rpc(self.rpc_url, "getSlot", [])
        current_slot = slot_resp.get("result")
        if not hasattr(self, "last_scanned_slot"):
            self.last_scanned_slot = current_slot - 5

        for slot in range(self.last_scanned_slot + 1, current_slot + 1):
            block_resp = await call_solana_rpc(self.rpc_url, "getBlock", [slot, {"encoding": "json", "transactionDetails": "full", "rewards": False}])
            if not block_resp or not block_resp.get("result"):
                continue
            block = block_resp["result"]
            transactions = block.get("transactions", [])
            for tx in transactions:
                for instr in tx["transaction"]["message"]["instructions"]:
                    program_id = instr.get("programId")
                    data = instr.get("data")
                    if program_id and data:
                        decoded = base64.b64decode(data)
                        instruction_type = decoded[0] if len(decoded) > 0 else None
                        if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                            await self._analyze_token_instruction(instr, tx)
                        elif program_id == "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin":
                            await self._analyze_raydium_instruction(instr, tx)
                        elif program_id == "Orca11111111111111111111111111111111111111111":
                            await self._analyze_orca_instruction(instr, tx)
        self.last_scanned_slot = current_slot
                                        mint_address = self._extract_mint_address(log_line)
                                        price_resp = await call_solana_rpc(self.rpc_url, "getTokenSupply", [mint_address])
                                        current_price = 0.0
                                        if price_resp and 'result' in price_resp and 'value' in price_resp['result']:
                                            current_price = float(price_resp['result']['value'].get('uiAmount', 0.0))
                                        if decision_module is not None:
                                            await decision_module.process_new_token_candidate(mint_address, current_price)
                                        mint_latency = (asyncio.get_event_loop().time() - mint_start) * 1000
                                        global_latency = (asyncio.get_event_loop().time() - event_start) * 1000
                                        logger.info(f"Latence mint->achat: {mint_latency:.1f}ms | Latence totale event->achat: {global_latency:.1f}ms (objectif <600ms)")
                                        signature = value.get('signature')
        slot_resp = await call_solana_rpc(self.rpc_url, "getSlot", [])
        current_slot = slot_resp.get("result")
        if not hasattr(self, "last_scanned_slot"):
            self.last_scanned_slot = current_slot - 5

        for slot in range(self.last_scanned_slot + 1, current_slot + 1):
            block_resp = await call_solana_rpc(self.rpc_url, "getBlock", [slot, {"encoding": "json", "transactionDetails": "full", "rewards": False}])
            if not block_resp or not block_resp.get("result"):
                continue
            block = block_resp["result"]
            transactions = block.get("transactions", [])
            for tx in transactions:
                for instr in tx["transaction"]["message"]["instructions"]:
                    program_id = instr.get("programId")
                    data = instr.get("data")
                    if program_id and data:
                        try:
                            decoded = base64.b64decode(data)
                            instruction_type = decoded[0] if len(decoded) > 0 else None
                            if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                                await self._analyze_token_instruction(instr, tx)
                            elif program_id == "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin":
                                await self._analyze_raydium_instruction(instr, tx)
                            elif program_id == "Orca11111111111111111111111111111111111111111":
                                await self._analyze_orca_instruction(instr, tx)
                        except Exception as e:
                            logger.warning(f"Erreur décodage instruction : {e}")
        self.last_scanned_slot = current_slot
                                logger.warning(f"Erreur décodage instruction : {e}")
            
            self.last_scanned_slot = current_slot
        except Exception as e:
            logger.error(f"Erreur lors du scan des activités : {e}")

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
                                # Créateur
                                creator = db.query(Creator).filter_by(address=creator_address).first()
                                if not creator:
                                    creator = Creator(address=creator_address)
        try:
            logger.info(f"Connecting to WebSocket: {self.websocket_url}")
            async with websockets.connect(self.websocket_url, ping_interval=5, close_timeout=1) as ws:
                self.connection = ws
                logger.info("WebSocket connected. Subscribing to program logs.")

                programs = [
                    {"mentions": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]},
                    {"mentions": ["9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"]},
                    {"mentions": ["Orca11111111111111111111111111111111111111111"]},
                ]
                for i, program in enumerate(programs):
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": i + 1,
                        "method": "logsSubscribe",
                        "params": [program, {"commitment": "finalized"}]
                    }))

                async for message in ws:
                    start = asyncio.get_event_loop().time()
                    data = json.loads(message)
                    if 'params' in data and 'result' in data['params'] and 'value' in data['params']['result']:
                        value = data['params']['result']['value']
                        if 'logs' in value:
                            for log_line in value['logs']:
                                if "initializeMint" in log_line:
                                    logger.info(f"initializeMint detected: {log_line}")
                                    # Déclenchement prioritaire du module de décision, latence globale
                                    mint_start = asyncio.get_event_loop().time()
                                    if decision_module:
                                        mint_address = self._extract_mint_address(log_line)
                                        # Récupération du prix initial via RPC ultra-rapide
                                        price_resp = await call_solana_rpc(self.rpc_url, "getTokenSupply", [mint_address])
                                        current_price = 0.0
                                        if price_resp and 'result' in price_resp and 'value' in price_resp['result']:
                                            current_price = float(price_resp['result']['value'].get('uiAmount', 0.0))
                                        await decision_module.process_new_token_candidate(mint_address, current_price)
                                        mint_latency = (asyncio.get_event_loop().time() - mint_start) * 1000
                                        logger.info(f"Latence totale création->achat: {mint_latency:.1f}ms (objectif <800ms)")
                                    logger.info(f"Nouveau token SPL détecté (log): {log_line}")
                                    signature = value.get('signature')
                                    if signature:
                                        await self.process_new_token(signature)