import asyncio
import base64
from loguru import logger
from typing import Dict, Any, Set, List
from ..database.db import DatabaseManager, Token, Creator, Transaction
from .cache_manager import BlockchainCache
from .creator_monitor import CreatorMonitor

class RealTimeAnalyzer:
    def __init__(self, database_url: str, rpc_url: str, cache_manager: BlockchainCache):
        self.db_manager = DatabaseManager(database_url)
        self.rpc_url = rpc_url
        self.cache = cache_manager
        self.creator_monitor = CreatorMonitor(database_url, rpc_url)
        self._analysis_task = None
        self.rpc_client = None # Will be set by BotManager
        self._transaction_cache: Dict[str, Dict[str, Any]] = {}
        self._suspicious_patterns: Set[str] = set()
        self._watched_tokens: Set[str] = set()  # Tokens à surveiller dynamiquement

    async def start_monitoring_token(self, token_mint_address: str):
        """
        Commence la surveillance temps réel de ce token.
        """
        self._watched_tokens.add(token_mint_address)
        logger.info(f"Surveillance temps réel activée pour le token {token_mint_address}")

    async def stop_monitoring_token(self, token_mint_address: str):
        """
        Arrête la surveillance temps réel de ce token.
        """
        self._watched_tokens.discard(token_mint_address)
        logger.info(f"Surveillance temps réel arrêtée pour le token {token_mint_address}")
        
    async def start_analysis(self):
        """Démarrage de l'analyse en temps réel."""
        if self._analysis_task is None or self._analysis_task.done():
            self._analysis_task = asyncio.create_task(self._analysis_loop())
            logger.info("Analyse en temps réel démarrée.")
            
    async def _analysis_loop(self):
        """Boucle principale d'analyse."""
        while True:
            try:
                await self._analyze_transactions()
                await self._detect_patterns()
                await self._update_suspicious_patterns()
                await asyncio.sleep(0.5)  # Analyse toutes les 0.5 secondes (ultra-rapide)
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse: {e}")
                await asyncio.sleep(2)
    
    async def _analyze_transactions(self):
        """Analyse les transactions récentes pour les tokens surveillés."""
        transactions = await self._get_recent_transactions()
        for tx in transactions:
            # Filtrer les transactions pour ne traiter que celles concernant les tokens surveillés
            mint = tx.get('mint_address') or tx.get('token_mint_address')
            if mint and mint in self._watched_tokens:
                await self._analyze_transaction(tx)
    
    async def _get_recent_transactions(self) -> List[Dict[str, Any]]:
        """Récupère les transactions récentes."""
        # This method needs to be implemented to fetch recent transactions.
        # For now, it returns an empty list.
        # It would typically involve calling a Solana RPC method like getSignaturesForAddress or getBlock.
        logger.warning("RealTimeAnalyzer._get_recent_transactions not fully implemented. Returning empty list.")
        return []
    
    async def _analyze_transaction(self, transaction: Dict[str, Any]):
        """Analyse une transaction spécifique et mesure la latence."""
        import time
        tx_id = transaction.get('signature')
        if not tx_id:
            return
        T0 = time.time()
        instructions = transaction.get('transaction', {}).get('message', {}).get('instructions', [])
        liquidity_ok = False
        honeypot_safe = True
        contract_safe = True
        holders_ok = True
        creator_wallets = set()
        for instr in instructions:
            await self._analyze_instruction(instr, tx_id)
            # Filtrage live : exemple
            if instr.get('programId') == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                mint_address = instr.get('accounts', [None])[0]
                if mint_address:
                    # Vérifie la liquidité
                    liquidity = await self.cache.get_liquidity(mint_address)
                    liquidity_ok = liquidity.get('sol', 0) >= 3.0
                    # Anti-honeypot
                    honeypot_safe = not liquidity.get('honeypot', False)
                    # Analyse smart contract
                    contract_safe = not liquidity.get('blacklisted', False)
                    # Nombre de holders
                    holders_ok = liquidity.get('holders', 0) > 50 and liquidity.get('centralization', 1.0) < 0.5
                    # Graphe de wallets liés
                    creator_wallets = await self.creator_monitor.get_linked_wallets(mint_address)
        # Stop loss dynamique
        stop_loss_triggered = False
        if liquidity_ok and honeypot_safe and contract_safe and holders_ok:
            # Simule un profit x5 pour le stop loss
            profit = transaction.get('profit', 1.0)
            if profit >= 5.0:
                stop_loss_triggered = True
        T1 = time.time()
        Tn = T1 + 0.15 # Latence cible 150ms
        if not hasattr(self, 'latency_metrics'):
            self.latency_metrics = []
        self.latency_metrics.append({
            "tx_id": tx_id,
            "T0": T0,
            "T1": T1,
            "Tn": Tn,
            "latency_ms": int((Tn-T0)*1000),
            "liquidity_ok": liquidity_ok,
            "honeypot_safe": honeypot_safe,
            "contract_safe": contract_safe,
            "holders_ok": holders_ok,
            "creator_wallets": list(creator_wallets),
            "stop_loss_triggered": stop_loss_triggered
        })
    def export_latency_metrics(self, filename: str = "latency_metrics.json"):
        import json
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.latency_metrics, f, ensure_ascii=False, indent=2)
    
    async def _analyze_instruction(self, instruction: Dict[str, Any], tx_id: str):
        """Analyse une instruction spécifique."""
        program_id = instruction.get('programId')
        if not program_id:
            return
            
        # Analyser les différents types de programmes
        if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
            await self._analyze_token_instruction(instruction, tx_id)
        elif program_id == "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin":  # Raydium
            await self._analyze_raydium_instruction(instruction, tx_id)
        elif program_id == "Orca11111111111111111111111111111111111111111":  # Orca
            await self._analyze_orca_instruction(instruction, tx_id)
    
    async def _analyze_token_instruction(self, instruction: Dict[str, Any], tx_id: str):
        """Analyse une instruction SPL Token."""
        # Détecter les actions importantes
        data = instruction.get('data')
        if data:
            try:
                decoded = base64.b64decode(data)
                if len(decoded) >= 1:
                    instruction_type = decoded[0]
                    
                    # Types d'instructions importants
                    if instruction_type == 0:  # InitializeMint
                        await self._handle_new_token(instruction, tx_id)
                    elif instruction_type == 7:  # Transfer
                        await self._handle_token_transfer(instruction, tx_id)
                    elif instruction_type == 8:  # Approve
                        await self._handle_token_approval(instruction, tx_id)
            except Exception as e:
                logger.warning(f"Erreur décodage instruction: {e}")
    
    async def _handle_new_token(self, instruction: Dict[str, Any], tx_id: str):
        """Gère la création d'un nouveau token."""
        mint_address = instruction.get('accounts', [])[0]
        if mint_address:
            logger.info(f"Nouveau token détecté: {mint_address}")
            await self.creator_monitor._update_watched_creators()
    
    async def _handle_token_transfer(self, instruction: Dict[str, Any], tx_id: str):
        """Gère les transferts de tokens et enrichit le graphe de wallets."""
        accounts = instruction.get('accounts', [])
        if len(accounts) >= 2:
            source = accounts[0]
            dest = accounts[1]
            logger.info(f"Transfert détecté: {source} -> {dest} dans tx {tx_id}")
            # Ajout au graphe de wallets liés
            self.creator_monitor.add_wallet_link(source, dest)
            # Détection de vente par wallet lié au créateur
            if dest in self._get_creator_wallets():
                logger.warning(f"Vente détectée par wallet lié au créateur: {dest}")
                await self._send_alerts()
    
    async def _handle_token_approval(self, instruction: Dict[str, Any], tx_id: str):
        """Gère les approbations de tokens et surveille les autorisations mutables."""
        accounts = instruction.get('accounts', [])
        if accounts:
            approver = accounts[0]
            approved = accounts[1] if len(accounts) > 1 else None
            logger.info(f"Approbation détectée: {approver} -> {approved} dans tx {tx_id}")
            # Vérifie si l'approbation concerne un wallet lié au créateur
            if approved and approved in self._get_creator_wallets():
                logger.warning(f"Approbation suspecte pour wallet créateur: {approved}")
                await self._send_alerts()
    def _get_creator_wallets(self) -> Set[str]:
        """Retourne l'ensemble des wallets liés au créateur actuellement surveillés."""
        if hasattr(self.creator_monitor, 'watched_wallets'):
            return set(self.creator_monitor.watched_wallets)
        return set()
    
    async def _detect_patterns(self):
        """Détection de patterns suspects."""
        # Analyser les patterns récents
        recent_patterns = await self._get_recent_patterns()
        
        # Comparer avec les patterns connus
        for pattern in recent_patterns:
            if self._is_suspicious_pattern(pattern):
                self._suspicious_patterns.add(pattern)
                logger.warning(f"Pattern suspect détecté: {pattern}")
    
    async def _get_recent_patterns(self) -> List[str]:
        """Récupère les patterns récents."""
        # À implémenter
        return []
    
    def _is_suspicious_pattern(self, pattern: str) -> bool:
        """Détermine si un pattern est suspect (ex: honeypot, rug, vente massive, etc)."""
        keywords = ['honeypot', 'rug', 'massive_sell', 'blacklist', 'centralized']
        return any(k in pattern.lower() for k in keywords)
    
    async def _update_suspicious_patterns(self):
        """Met à jour la liste des patterns suspects."""
        if self._suspicious_patterns:
            logger.info(f"Patterns suspects détectés: {len(self._suspicious_patterns)}")
            # Envoyer des alertes si nécessaire
            await self._send_alerts()
    
    async def _send_alerts(self):
        """Envoie des alertes pour les activités suspectes (ex: webhook, email, log)."""
        logger.error("ALERTE: Activité suspecte détectée sur la blockchain Solana !")
        # Ici, on peut ajouter l'envoi vers un webhook, email, ou autre système de notification
