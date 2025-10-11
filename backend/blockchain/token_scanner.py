import asyncio
from loguru import logger
from ..blockchain.rpc_client import call_solana_rpc, get_token_supply, get_token_holders
from ..blockchain.cache_manager import BlockchainCache, TokenAnalyzer
import base64
import json
from typing import Dict, Any, Optional

class TokenScanner:
    def __init__(self, rpc_url: str, gemini_analyzer, reputation_db_manager, reputation_threshold: float):
        self.rpc_url = rpc_url
        self.gemini_analyzer = gemini_analyzer
        self.reputation_db_manager = reputation_db_manager
        self.reputation_threshold = reputation_threshold
        self.decision_module = None # Will be set by BotManager
        self._scanning_task = None
        self.known_mints = set()
        self.cache_manager = BlockchainCache(maxsize=1000, ttl=60)
        self.token_analyzer = TokenAnalyzer(rpc_url, self.cache_manager)

    async def _scan_for_new_tokens(self):
        import time
        logger.info("Scanning for new tokens (latence optimisée)...")
        start = time.time()
        try:
            slot_resp = await call_solana_rpc(self.rpc_url, "getSlot", [])
            current_slot = slot_resp.get("result")
            if not hasattr(self, "last_scanned_slot"):
                self.last_scanned_slot = current_slot - 5
            # Batch scan des slots
            slots_to_scan = list(range(self.last_scanned_slot + 1, current_slot + 1))
            for slot in slots_to_scan:
                block_resp = await call_solana_rpc(self.rpc_url, "getBlock", [slot, {"encoding": "json", "transactionDetails": "full", "rewards": False}])
                if not block_resp or not block_resp.get("result"):
                    continue
                block = block_resp["result"]
                transactions = block.get("transactions", [])
                for tx in transactions:
                    for instr in tx["transaction"]["message"]["instructions"]:
                        if instr.get("programId") == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                            data = instr.get("data")
                            if data:
                                try:
                                    decoded = base64.b64decode(data)
                                    if len(decoded) > 0 and decoded[0] == 0:
                                        mint_address = instr["accounts"][0]
                                        if mint_address not in self.known_mints:
                                            logger.info(f"Nouveau token détecté : {mint_address} (slot {slot})")
                                            await self.analyze_and_decide(mint_address)
                                            self.known_mints.add(mint_address)
                                except Exception as e:
                                    logger.warning(f"Erreur décodage instruction : {e}")
            self.last_scanned_slot = current_slot
            latency = (time.time() - start) * 1000
            logger.info(f"Scan batch slots latence: {latency:.1f}ms pour {len(slots_to_scan)} slots.")
        except Exception as e:
            logger.error(f"Erreur lors du scan des nouveaux tokens : {e}")

    async def analyze_and_decide(self, token_mint_address: str) -> bool:
        """Analyse complète d'un token potentiel."""
        logger.info(f"Analyzing token: {token_mint_address}")

        try:
            # Analyse approfondie avec le TokenAnalyzer
            full_analysis = await self.token_analyzer.analyze_token(token_mint_address)
            
            # Vérification de la réputation
            reputation_entry = self.reputation_db_manager.get_entry(token_mint_address)
            if reputation_entry and reputation_entry.score_de_confiance < self.reputation_threshold:
                logger.warning(f"Token {token_mint_address} rejected due to low reputation score ({reputation_entry.score_de_confiance}).")
                return False
            
            # Analyse des métriques de liquidité
            liquidity = full_analysis.get("liquidity", {})
            if not self._is_sufficient_liquidity(liquidity):
                logger.warning(f"Token {token_mint_address} rejected: insufficient liquidity")
                return False
            
            # Analyse du volume
            volume = full_analysis.get("volume", {})
            if not self._is_sufficient_volume(volume):
                logger.warning(f"Token {token_mint_address} rejected: insufficient volume")
                return False
            
            # Analyse avec Gemini AI
            risk_score = await self.gemini_analyzer.analyze_token(full_analysis)
            logger.info(f"Token {token_mint_address} AI risk score: {risk_score}")
            
            if risk_score < self.reputation_threshold:
                logger.warning(f"Token {token_mint_address} rejected: AI risk score too low")
                return False
            
            logger.info(f"Token {token_mint_address} passed all analysis filters. Ready for decision module.")
            # Pass to decision module for potential buy
            if self.decision_module:
                await self.decision_module.process_new_token_candidate(token_mint_address, current_price=0.0) # current_price needs to be fetched

            return True
            
        except Exception as e:
            logger.error(f"Error analyzing token {token_mint_address}: {e}")
            return False
    
    def _is_sufficient_liquidity(self, liquidity: Dict[str, Any]) -> bool:
        """Vérifie si la liquidité est suffisante."""
        # Implémenter la logique de vérification de la liquidité
        return True
    
    def _is_sufficient_volume(self, volume: Dict[str, Any]) -> bool:
        """Vérifie si le volume de trading est suffisant."""
        # Implémenter la logique de vérification du volume
        return True

    async def start_scanning(self, interval: int = 5):
        if self._scanning_task is None or self._scanning_task.done():
            self._scanning_task = asyncio.create_task(self._scanning_loop(interval))
            logger.info(f"Token scanner started with interval: {interval} seconds.")

    async def _scanning_loop(self, interval: int):
        while True:
            try:
                await self._scan_for_new_tokens()
            except Exception as e:
                logger.error(f"Error during token scanning: {e}")
            await asyncio.sleep(interval)

    async def stop_scanning(self):
        if self._scanning_task:
            self._scanning_task.cancel()
            try:
                await self._scanning_task
            except asyncio.CancelledError:
                logger.info("Token scanning task cancelled.")