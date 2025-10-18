from loguru import logger
import asyncio
import os
import json
import random
import time
import aiohttp
from solders.pubkey import Pubkey as PublicKey
from typing import Dict, List, Optional, Any

# --- Configuration des chemins ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

class DecisionModule:
    """
    Module de décision pour le trading automatique (simulation/réel).
    Gère le capital, la logique d'achat/vente, les logs, et l'intégration IA.
    """
    def __init__(self, bot_manager: Any, order_executor: Any, buy_amount_sol: float, sell_multiplier: float, trailing_stop_percent: float, simulation_mode: bool = False):
        self.bot_manager = bot_manager
        self.buy_amount_sol = buy_amount_sol
        self.sell_multiplier = sell_multiplier
        self.trailing_stop_percent = trailing_stop_percent
        self.simulation_mode = simulation_mode
        self.simulation_results: List[dict] = []
        self.held_tokens: Dict[str, dict] = {} # {mint_address: {buy_price: float, buy_amount: float}}
        self.capital: float = 0.0
        self.available_capital: float = 0.0
        self.ia_hooks: List[Any] = [] # Pour brancher des modules IA/optimisation
        self.honeypot_cache = {} # Cache pour les vérifications honeypot
        self.order_executor = order_executor
        self.gemini_analyzer = None # Sera injecté plus tard
    def set_realtime_analyzer(self, analyzer):
        """
        Permet d'enregistrer l'analyseur temps réel pour notifier les achats/ventes.
        """
        self.realtime_analyzer = analyzer
    def set_param(self, key: str, value):
        """
        Permet à un module IA (ex: Gemini) de modifier dynamiquement un paramètre du DecisionModule.
        Usage : decision_module.set_param('buy_amount_sol', 0.5)
        """
        if hasattr(self, key):
            setattr(self, key, value)
            logger.info(f"[AI] Paramètre '{key}' mis à jour dynamiquement à {value}")
        else:
            logger.warning(f"[AI] Tentative de modification d'un paramètre inconnu : {key}")
    async def sell_all_tokens(self):
        """
        Force la vente de tous les tokens actuellement détenus (utile pour garantir la liquidité et la sortie rapide).
        """
        for token_mint_address in list(self.held_tokens.keys()):
            try:
                logger.info(f"[FORCED SELL] Selling all of {token_mint_address} (manual or end-of-session)")
                # _execute_sale retourne maintenant le prix de vente réel
                sell_price = await self._execute_sale(token_mint_address)
                self.record_real_trade({
                    "token": token_mint_address,
                    "price": sell_price if sell_price else self.held_tokens.get(token_mint_address, {}).get("buy_price", 0),
                    "action": "sell",
                    "timestamp": asyncio.get_event_loop().time(),
                    "forced": True
                })
            except Exception as e:
                logger.error(f"Erreur lors de la vente forcée de {token_mint_address} : {e}")

    def log_trade(self, entry: dict, simulation: bool = True) -> None:
        """
        Enregistre chaque trade dans un fichier log distinct selon le mode (simulation ou réel).
        """
        log_file = os.path.join(LOGS_DIR, "simulation_trades.log") if simulation else os.path.join(LOGS_DIR, "real_trades.log")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture du log trade : {e}")

    def enable_real_time_simulation(self) -> None:
        """Active le mode simulation en temps réel (aucun argent réel utilisé)."""
        self.simulation_mode = True
        self.simulation_results = []
        logger.info("Mode simulation activé (aucun trade réel ne sera effectué).")

    def record_simulation_trade(self, entry: dict) -> None:
        """
        Ajoute un trade simulé à la liste et au fichier log de simulation.
        """
        self.simulation_results.append(entry)
        self.log_trade(entry, simulation=True)

    def record_real_trade(self, entry: dict) -> None:
        """
        Ajoute un trade réel au fichier log dédié.
        """
        self.log_trade(entry, simulation=False)

    def get_simulation_profit_loss(self) -> float:
        """Calcule le profit/perte total de la simulation."""
        profit = 0.0
        buy_prices = {}
        for entry in self.simulation_results:
            if entry["action"] == "buy":
                buy_prices[entry["token"]] = entry["price"]
            elif entry["action"] == "sell" and entry["token"] in buy_prices:
                profit += entry["price"] - buy_prices[entry["token"]]
        return profit

    def set_gemini_analyzer(self, analyzer):
        """Injecte l'analyseur Gemini pour les fonctionnalités IA."""
        self.gemini_analyzer = analyzer

    def set_initial_capital(self, amount: float) -> None:
        """
        Définit le capital de départ à investir (modifié via l'interface).
        """
        self.capital = float(amount)
        self.available_capital = float(amount)
        logger.info(f"Capital initial défini à {amount} SOL")

    def get_available_capital(self) -> float:
        """
        Retourne le capital disponible pour investissement.
        """
        return self.available_capital

    async def process_new_token_candidate(self, token_mint_address: str, current_price: float) -> None:
        """
        Analyse et achat d'un nouveau token en moins de 500ms (toutes vérifications parallélisées).
        """
        start_time = time.time()
        logger.info(f"[FAST BUY] Analyse et achat de {token_mint_address} à {current_price} SOL")
        is_exploration_phase = (time.time() - self.bot_manager.start_time) < 3600 if self.bot_manager.start_time else False
        try:
            # En mode démo/simulation, on simule l'achat de nombreux tokens pour tester la charge.
            if self.simulation_mode:
                # Pour test/démo : toujours acheter en simulation, ignorer la phase d'exploitation
                logger.info(f"[SIMULATION] Achat simulé de {token_mint_address}")
                self.bot_manager.log_activity(f"Achat simulé: {token_mint_address}", "INFO")

                # Enregistre le trade simulé
                simulated_buy_entry = {
                    "token": token_mint_address,
                    "price": current_price,
                    "action": "buy",
                    "timestamp": time.time()
                }
                self.record_simulation_trade(simulated_buy_entry)

                # Ajoute le token aux positions détenues pour la simulation de vente
                self.held_tokens[token_mint_address] = {
                    "buy_price": current_price,
                    "buy_amount": self.buy_amount_sol,
                    "creator_wallets": [], # Pas besoin de détecter en simulation
                    "buy_timestamp": time.time()
                }
                # Correction: Lancer la surveillance même en simulation
                if hasattr(self, 'realtime_analyzer') and self.realtime_analyzer:
                    await self.realtime_analyzer.start_monitoring_token(token_mint_address)
                return

            # --- Logique de trading en mode réel ---
            creator_wallets = await self._detect_creator_wallets(token_mint_address)

            # Phase d'Exploitation : après 1h, on ne trade que les créateurs de confiance.
            if not is_exploration_phase:
                is_trusted_creator = any(creator in self.successful_creator_cache for creator in creator_wallets)
                if not is_trusted_creator:
                    logger.info(f"[EXPLOITATION] Token {token_mint_address} ignoré. Créateur non trouvé dans le cache de confiance.")
                    self.bot_manager.log_activity(f"Ignoré (créateur non fiable): {token_mint_address}", "DEBUG")
                    return
                
                # Si le créateur est de confiance, on achète directement sans autres vérifications.
                logger.success(f"[EXPLOITATION - TRUSTED BUY] Achat du token {token_mint_address} (créateur de confiance).")
                self.bot_manager.log_activity(
                    f"Achat (créateur de confiance): {token_mint_address}", "SUCCESS"
                )
                success = await self.order_executor.execute_buy(token_mint_address, self.buy_amount_sol)
                if success:
                    self.held_tokens[token_mint_address] = {
                        "buy_price": current_price,
                        "buy_amount": self.buy_amount_sol,
                        "creator_wallets": creator_wallets,
                        "buy_timestamp": time.time()
                    }
                    if hasattr(self, 'realtime_analyzer'):
                        await self.realtime_analyzer.start_monitoring_token(token_mint_address)
                return # Fin du traitement pour cet achat.

            # Parallélisation des vérifications
            tasks = [
                self._check_token_honeypot_and_taxes(token_mint_address),
                self._check_token_liquidity(token_mint_address, min_sol=5),
                self._check_token_sellable(token_mint_address)
            ]
            honeypot_info, has_liquidity, is_sellable = await asyncio.gather(*tasks)

            # Vérification du solde TrustWallet
            wallet_status = await self.order_executor.get_wallet_status()
            sol_balance = wallet_status.get("balance_sol", 0)
            montant_total = self.buy_amount_sol + 0.001 # Frais de transaction estimés
            if not wallet_status.get("balance_ok") or sol_balance < montant_total:
                logger.error(f"Solde insuffisant ({sol_balance:.4f} SOL) pour acheter {self.buy_amount_sol} SOL de {token_mint_address}. Achat annulé.")
                self.bot_manager.log_activity(f"Solde insuffisant ({sol_balance:.4f} SOL) pour {token_mint_address}", "ERROR")
                return
            # Vérification du capital disponible géré par le bot
            if self.available_capital < self.buy_amount_sol:
                logger.error(f"Capital disponible insuffisant ({self.available_capital:.4f} SOL) pour acheter {self.buy_amount_sol} SOL de {token_mint_address}. Achat annulé.")
                self.bot_manager.log_activity(f"Capital insuffisant ({self.available_capital:.4f} SOL) pour {token_mint_address}", "ERROR")
                return

            # Vérifications synchrones
            if token_mint_address in self.held_tokens:
                logger.info(f"Already holding {token_mint_address}, skipping buy.")
                self.bot_manager.log_activity(f"Déjà détenu: {token_mint_address}", "DEBUG")
                return
            if honeypot_info.get("is_honeypot"):
                logger.error(f"Token {token_mint_address} détecté comme honeypot. Achat annulé.")
                self.bot_manager.log_activity(f"Honeypot détecté: {token_mint_address}", "ERROR")
                return
            taxes = honeypot_info.get("taxes", {})
            if taxes and (taxes.get("buy", 0) > 0.15 or taxes.get("sell", 0) > 0.15):
                tax_msg = f"Taxes élevées (A: {taxes.get('buy', 0):.1%}, V: {taxes.get('sell', 0):.1%})"
                logger.error(f"Token {token_mint_address} a des {tax_msg}. Achat annulé.")
                self.bot_manager.log_activity(f"{tax_msg} pour {token_mint_address}", "ERROR")
                return
            marketcap = honeypot_info.get("marketcap", 0)
            if marketcap and marketcap > 50000: # Plafond de 50k$ pour cibler les micro-caps
                logger.error(f"Token {token_mint_address} a un market cap trop élevé ({marketcap}$), potentiel de x2 rapide plus faible. Achat annulé.")
                self.bot_manager.log_activity(f"Marketcap > 50k$ ({marketcap:,.0f}$) pour {token_mint_address}", "ERROR")
                return
            if honeypot_info.get("antiBot", False) or honeypot_info.get("antiBotDetected", False):
                logger.error(f"Token {token_mint_address} détecté comme anti-bot. Achat annulé.")
                self.bot_manager.log_activity(f"Anti-bot détecté: {token_mint_address}", "ERROR")
                return
            if not has_liquidity:
                logger.error(f"Token {token_mint_address} a une liquidité trop faible (<5 SOL) sur Jupiter. Achat annulé.")
                self.bot_manager.log_activity(f"Liquidité < 5 SOL: {token_mint_address}", "ERROR")
                return
            if not is_sellable:
                logger.error(f"Token {token_mint_address} non revendable (pas de pool ou de route DEX trouvée). Achat annulé.")
                self.bot_manager.log_activity(f"Non revendable: {token_mint_address}", "ERROR")
                return
            # Achat immédiat
            if is_exploration_phase:
                logger.info(f"[EXPLORATION] Achat de {self.buy_amount_sol} SOL de {token_mint_address} après passage des filtres de sécurité.")
                self.bot_manager.log_activity(f"Achat (Exploration): {token_mint_address}", "INFO")
            else:
                # This branch is for exploitation phase, but it's already handled by the trusted creator logic.
                # This part of the code will likely not be hit in exploitation phase unless the logic changes.
                logger.info(f"[EXPLOITATION] Achat de {self.buy_amount_sol} SOL de {token_mint_address} (créateur de confiance).")
            success = await self.order_executor.execute_buy(token_mint_address, self.buy_amount_sol)
            if success:
                self.held_tokens[token_mint_address] = {
                    "buy_price": current_price,
                    "buy_amount": self.buy_amount_sol,
                    "creator_wallets": creator_wallets,
                    "buy_timestamp": time.time() # Enregistre le timestamp de l'achat
                }
                logger.success(f"Successfully bought {token_mint_address}. Tracking for sale. Creator wallets: {creator_wallets}")
                self.bot_manager.log_activity(f"Achat exécuté: {token_mint_address}", "SUCCESS")
                if hasattr(self, 'realtime_analyzer') and self.realtime_analyzer:
                    await self.realtime_analyzer.start_monitoring_token(token_mint_address)
                self.record_real_trade({
                    "token": token_mint_address,
                    "price": current_price,
                    "action": "buy",
                    "timestamp": time.time()
                })
            else:
                self.bot_manager.log_activity(f"Échec de la transaction d'achat: {token_mint_address}", "ERROR")
                logger.error(f"Failed to buy {token_mint_address}.")

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            logger.info(f"[FAST BUY] Latence totale analyse+achat: {latency_ms:.1f} ms")
            if latency_ms > 500:
                logger.warning(f"[FAST BUY] Latence supérieure à 500ms ! Optimisation requise.")

        except Exception as e:
            logger.error(f"Erreur inattendue dans process_new_token_candidate pour {token_mint_address} : {e}")
    async def _check_token_honeypot_and_taxes(self, token_mint_address: str) -> dict:
        """
        Détecte si le token est un honeypot, récupère les taxes, le market cap et anti-bot.
        Retourne un dict {"is_honeypot": bool, "taxes": {"buy": float, "sell": float}, "marketcap": float, "antiBot": bool}
        """
        # Vérification du cache
        cache_entry = self.honeypot_cache.get(token_mint_address)
        if cache_entry and (time.time() - cache_entry['timestamp']) < 300: # Cache de 5 minutes
            logger.info(f"Honeypot check for {token_mint_address} from cache.")
            return cache_entry['data']

        result = {"is_honeypot": False, "taxes": {}, "marketcap": 0, "antiBot": False}
        try:
            url = f"https://honeypot.is/api/v1/solana/{token_mint_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("honeypotResult") or data.get("isHoneypot"):
                            logger.warning(f"Honeypot détecté pour {token_mint_address} : {data}")
                            result["is_honeypot"] = True
                        taxes = data.get("taxes", {})
                        result["taxes"] = taxes
                        # Market cap
                        if "marketcap" in data:
                            result["marketcap"] = data["marketcap"]
                        elif "marketCap" in data:
                            result["marketcap"] = data["marketCap"]
                        # Anti-bot
                        if data.get("antiBot") or data.get("antiBotDetected"):
                            result["antiBot"] = True
                    else:
                        logger.warning(f"API honeypot.is non disponible pour {token_mint_address} (status {resp.status})")
        except Exception as e:
            logger.error(f"Erreur lors de la détection honeypot/taxes/marketcap/antibot pour {token_mint_address} : {e}")
        
        # Mise en cache du résultat
        self.honeypot_cache[token_mint_address] = {
            'timestamp': time.time(),
            'data': result
        }
        return result

    async def _check_token_liquidity(self, token_mint_address: str, min_sol: float = 5) -> bool:
        """
        Vérifie la liquidité du token sur Jupiter (min_sol en SOL). Retourne True si la liquidité est suffisante.
        """
        try:
            sol_mint = "So11111111111111111111111111111111111111112"
            params = {
                "inputMint": sol_mint,
                "outputMint": token_mint_address,
                "amount": int(min_sol * 1e9),
                "slippageBps": 50
            }
            async with aiohttp.ClientSession() as session:
                async with session.get("https://quote-api.jup.ag/v6/quote", params=params) as resp:
                    data = await resp.json()
                    # Jupiter v6 quote response has outAmount at the root
                    out_amount = data.get("outAmount", "0")
                    if int(out_amount) > 0:
                        logger.info(f"Liquidité suffisante pour {token_mint_address} sur Jupiter.")
                        return True
                    logger.warning(f"Liquidité insuffisante pour {token_mint_address} sur Jupiter.")
                    return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de liquidité Jupiter pour {token_mint_address} : {e}")
            return False

    async def _check_token_sellable(self, token_mint_address: str) -> bool:
        """
        Vérifie si le token est revendable (présence d'une route DEX réelle via Jupiter).
        Retourne True si revendable, False sinon.
        """
        try:
            # SOL mint address (input) sur Solana mainnet
            sol_mint = "So11111111111111111111111111111111111111112"
            params = {
                "inputMint": token_mint_address,
                "outputMint": sol_mint,
                "amount": int(0.1 * 1e9),  # Vérifie la liquidité pour 0.1 token (ajuste si besoin)
                "slippageBps": 50
            }
            async with aiohttp.ClientSession() as session:
                async with session.get("https://quote-api.jup.ag/v6/quote", params=params) as resp:
                    data = await resp.json()
                    # Jupiter v6 quote response has outAmount at the root
                    if data and data.get("outAmount", "0") != "0":
                        logger.info(f"Token {token_mint_address} revendable : route DEX trouvée via Jupiter.")
                        return True
                    else:
                        logger.error(f"Token {token_mint_address} NON revendable : aucune route DEX trouvée via Jupiter.")
                        return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification revendabilité du token {token_mint_address} : {e}")
            return False
    async def _detect_creator_wallets(self, token_mint_address: str):
        """Détecte le wallet du créateur en analysant les premières transactions du token."""
        try:
            # Cette méthode est une simplification. Une analyse robuste nécessite un indexeur.
            # On cherche les signatures pour l'adresse du mint.
            signatures_resp = await self.order_executor.async_client.get_signatures_for_address(PublicKey.from_string(token_mint_address), limit=10, commitment="confirmed")
            signatures = signatures_resp.value
            if not signatures:
                return []

            # On prend la plus ancienne transaction (la dernière de la liste)
            last_tx_sig = signatures[-1].signature
            tx_details_resp = await self.order_executor.async_client.get_transaction(last_tx_sig, encoding="json", max_supported_transaction_version=0)
            tx_details = tx_details_resp.value
            
            if tx_details and tx_details.transaction:
                # Le payeur de la transaction de création est souvent le créateur.
                creator_wallet = tx_details.transaction.message.account_keys[0]
                logger.info(f"Créateur potentiel détecté pour {token_mint_address}: {creator_wallet}")
                return [str(creator_wallet)]
        except Exception as e:
            logger.error(f"Erreur lors de la détection du créateur pour {token_mint_address}: {e}")
        return []

    async def evaluate_held_tokens_for_sale(self, token_mint_address: str, current_price: float, whale_selling: bool = False) -> None:
        """
        Évalue si un token détenu doit être vendu (simulation enrichie : slippage, spread, latence, erreurs, logs IA).
        """
        try:
            if token_mint_address in self.held_tokens:
                buy_price = self.held_tokens[token_mint_address]["buy_price"]
                profit_multiplier = current_price / buy_price
                creator_wallets = self.held_tokens[token_mint_address].get("creator_wallets", [])
                
                # PRIORITÉ : Take profit automatique
                if profit_multiplier >= self.sell_multiplier:
                    logger.info(f"[TAKE PROFIT] Selling {token_mint_address}: Price reached x{self.sell_multiplier} (x{profit_multiplier:.2f}). Vente immédiate.")
                    self.bot_manager.log_activity(
                        f"Vente (Take Profit x{profit_multiplier:.2f}): {token_mint_address}", "SUCCESS"
                    )
                    await self._execute_sale(token_mint_address)

                    # Logique d'ajout au cache créateur en mode simulation
                    if self.simulation_mode: # Cette condition est déjà dans _execute_sale, mais on la garde pour la logique spécifique au créateur
                        buy_timestamp = self.held_tokens[token_mint_address].get("buy_timestamp", 0)
                        trade_duration = time.time() - buy_timestamp
                        # Si x2 en moins d'une heure (3600s)
                        if trade_duration < 3600:
                            creators = self.held_tokens[token_mint_address].get("creator_wallets", [])
                            for creator in creators:
                                if creator not in self.successful_creator_cache:
                                    logger.success(f"[CREATOR CACHE] Ajout du créateur performant {creator} au cache.")
                                    self.successful_creator_cache.add(creator)
                                    self._save_creator_cache()
                                    # Demander à Gemini de trouver des wallets associés
                                    if self.gemini_analyzer:
                                        logger.info(f"Lancement de l'analyse IA pour trouver les wallets associés à {creator}...")
                                        asyncio.create_task(self.gemini_analyzer.find_associated_creator_wallets(creator))


                    return

                # Trailing Stop Loss
                trailing_stop_percent = getattr(self, 'trailing_stop_percent', 0.15)  # 15% par défaut
                if 'max_price' not in self.held_tokens[token_mint_address]:
                    self.held_tokens[token_mint_address]['max_price'] = buy_price
                
                if current_price > self.held_tokens[token_mint_address]['max_price']:
                    self.held_tokens[token_mint_address]['max_price'] = current_price
                
                max_price = self.held_tokens[token_mint_address]['max_price']
                if current_price < max_price * (1 - trailing_stop_percent):
                    logger.warning(f"[TRAILING STOP] Selling {token_mint_address}: Price dropped >{int(trailing_stop_percent*100)}% from max ({current_price:.4f} < {max_price:.4f}). Vente automatique.")
                    self.bot_manager.log_activity(
                        f"Vente (Trailing Stop >{int(trailing_stop_percent*100)}%): {token_mint_address}", "WARNING"
                    )
                    await self._execute_sale(token_mint_address)
                    return

                logger.info(f"Evaluating {token_mint_address}: Buy Price={buy_price:.6f}, Current Price={current_price:.6f}, Max Price: {max_price:.6f}, Multiplier={profit_multiplier:.2f}x")

                # Détection avancée des signaux de dump (volume, créateur, liquidité)
                # Note: _creator_wallet_selling est coûteux, à utiliser avec parcimonie
                if whale_selling or await self._creator_wallet_selling(token_mint_address, creator_wallets):
                    logger.warning(f"[DUMP SIGNAL] Selling {token_mint_address}: Dump ou activité suspecte détectée.")
                    await self._execute_sale(token_mint_address)
                    return
                logger.info(f"No sale conditions met for {token_mint_address}.")
            else:
                logger.debug(f"Not holding {token_mint_address}, skipping sale evaluation.")
        except Exception as e:
            logger.error(f"Erreur evaluate_held_tokens_for_sale : {e}")
    async def _creator_wallet_selling(self, token_mint_address: str, creator_wallets: list) -> bool:
        """Détecte si un des wallets du créateur a récemment vendu le token."""
        if not creator_wallets:
            return False

        async def check_wallet(wallet):
            try:
                signatures_resp = await self.order_executor.async_client.get_signatures_for_address(PublicKey.from_string(wallet), limit=5)
                signatures = signatures_resp.value
                for sig_info in signatures:
                    tx_details_resp = await self.order_executor.async_client.get_transaction(sig_info.signature, encoding="json", max_supported_transaction_version=0)
                    tx_details = tx_details_resp.value
                    # Simplification: on regarde si le token apparait dans les balances post-transaction
                    if tx_details and tx_details.meta and any(token_mint_address in str(account.mint) for account in tx_details.meta.post_token_balances):
                         logger.warning(f"Activité de vente potentielle du créateur {wallet} pour le token {token_mint_address}.")
                         return True
            except Exception as e:
                logger.error(f"Erreur lors de la vérification de vente du créateur {wallet}: {e}")
            return False

        tasks = [check_wallet(wallet) for wallet in creator_wallets]
        results = await asyncio.gather(*tasks)
        
        if any(results):
            return True
        return False

    def _log_completed_trade(self, token_mint_address: str, sell_price: float):
        """
        Enregistre un trade complété (achat + vente) dans un log dédié pour l'analyse IA.
        """
        buy_info = self.held_tokens.get(token_mint_address, {})
        if not buy_info:
            return

        buy_price = buy_info.get("buy_price", 0)
        buy_timestamp = buy_info.get("buy_timestamp", 0)
        sell_timestamp = time.time()
        
        completed_trade_entry = {
            "token": token_mint_address,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "buy_timestamp": buy_timestamp,
            "sell_timestamp": sell_timestamp,
            "duration_seconds": sell_timestamp - buy_timestamp,
            "profit_per_token": sell_price - buy_price,
            "profit_multiplier": sell_price / buy_price if buy_price > 0 else 0,
            "creator_wallets": buy_info.get("creator_wallets", [])
        }

        with open(os.path.join(LOGS_DIR, "completed_trades.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps(completed_trade_entry, ensure_ascii=False) + "\n")
        logger.info(f"Trade complété pour {token_mint_address} enregistré pour analyse IA.")

    async def _execute_sale(self, token_mint_address: str) -> Optional[float]:
        """Exécute la vente d'un token détenu (tout le montant)."""
        try:
            if self.simulation_mode:
                # Logique de vente pour la SIMULATION
                logger.info(f"[SIMULATION] Selling {token_mint_address}")
                # En simulation, le prix de vente est déterminé par la condition qui a déclenché la vente
                # (ex: take profit, trailing stop). Pour simplifier, on simule ici avec le multiplicateur de take-profit.
                # Pour l'instant, on simule avec le multiplicateur de take-profit.
                current_price = self.held_tokens[token_mint_address]['buy_price'] * self.sell_multiplier
                simulated_sell_entry = {
                    "token": token_mint_address,
                    "price": current_price,
                    "action": "sell",
                    "timestamp": time.time()
                }
                self.record_simulation_trade(simulated_sell_entry)
                del self.held_tokens[token_mint_address] # Important: retirer le token des positions
                return current_price

            else:
                # Logique de vente pour le mode RÉEL
                logger.info(f"Attempting to sell all of {token_mint_address}")
                amount = self.held_tokens[token_mint_address]["buy_amount"]
                # execute_sell retourne maintenant les données de la vente
                success_data = await self.order_executor.execute_sell(token_mint_address, amount)
                
                if success_data and success_data.get("success"):
                    logger.success(f"Successfully sold {token_mint_address}.")
                    # Utiliser le prix de vente réel retourné par l'executor
                    sell_price = success_data.get("sell_price_sol", self.held_tokens.get(token_mint_address, {}).get("buy_price", 0))
                    
                    # Enregistrer le trade complet pour l'analyse IA
                    self._log_completed_trade(token_mint_address, sell_price)

                    self.record_real_trade({
                        "token": token_mint_address,
                        "price": sell_price,
                        "action": "sell",
                        "timestamp": time.time()
                    })

                    for hook in self.ia_hooks:
                        try:
                            hook.on_trade("sell", token_mint_address, sell_price) 
                        except Exception as e:
                            logger.warning(f"Erreur hook IA après vente : {e}")
                    
                    if hasattr(self, 'realtime_analyzer') and self.realtime_analyzer:
                        await self.realtime_analyzer.stop_monitoring_token(token_mint_address)

                    del self.held_tokens[token_mint_address]
                    return sell_price
                else:
                    logger.error(f"Failed to sell {token_mint_address}.")
                    return None
        except Exception as e:
            logger.error(f"Erreur _execute_sale : {e}")
        return None