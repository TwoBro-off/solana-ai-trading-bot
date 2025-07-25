
from loguru import logger
import asyncio
from typing import Dict, List, Optional, Any


class DecisionModule:
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
                await self._execute_sale(token_mint_address)
                self.record_real_trade({
                    "token": token_mint_address,
                    "price": self.held_tokens.get(token_mint_address, {}).get("buy_price", 0),
                    "action": "sell",
                    "timestamp": asyncio.get_event_loop().time(),
                    "forced": True
                })
            except Exception as e:
                logger.error(f"Erreur lors de la vente forcée de {token_mint_address} : {e}")

    """
    Module de décision pour le trading automatique (simulation/réel).
    Gère le capital, la logique d'achat/vente, les logs, et l'intégration IA.
    """

    def log_trade(self, entry: dict, simulation: bool = True) -> None:
        """
        Enregistre chaque trade dans un fichier log distinct selon le mode (simulation ou réel).
        """
        import json
        log_file = "simulation_trades.log" if simulation else "real_trades.log"
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

    def export_simulation_report_for_gemini(self, filename: str = "simulation_gemini.json") -> None:
        """Export des résultats de simulation pour analyse Gemini."""
        import json
        report = {
            "results": self.simulation_results,
            "profit_loss": self.get_simulation_profit_loss(),
            "parameters": {
                "buy_amount_sol": self.buy_amount_sol,
                "sell_multiplier": self.sell_multiplier
            }
        }
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"Rapport simulation exporté pour Gemini : {filename}")
        except Exception as e:
            logger.error(f"Erreur export rapport Gemini : {e}")
    def __init__(self, order_executor: Any, buy_amount_sol: float, sell_multiplier: float, simulation_mode: bool = False):
        """
        Initialise le module de décision.
        order_executor : module d'exécution des ordres (buy/sell)
        buy_amount_sol : montant à investir par trade
        sell_multiplier : multiplicateur de take profit
        simulation_mode : True pour la simulation, False pour le réel
        """
        self.order_executor = order_executor
        self.buy_amount_sol = buy_amount_sol
        self.sell_multiplier = sell_multiplier
        self.simulation_mode = simulation_mode
        self.simulation_results: List[dict] = []
        self.held_tokens: Dict[str, dict] = {} # {mint_address: {buy_price: float, buy_amount: float}}
        self.capital: float = 0.0
        self.available_capital: float = 0.0
        self.ia_hooks: List[Any] = [] # Pour brancher des modules IA/optimisation

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

    def update_after_trade(self, profit_or_loss: float) -> None:
        """
        Met à jour le capital disponible après chaque trade (réinvestissement automatique des gains).
        """
        self.available_capital += profit_or_loss
        if self.available_capital < 0:
            self.available_capital = 0
        logger.info(f"Capital mis à jour après trade : {self.available_capital} SOL")

    def get_next_investment_amount(self) -> float:
        """
        Calcule le montant à investir pour le prochain trade (100% du capital disponible).
        """
        return self.available_capital

    async def process_new_token_candidate(self, token_mint_address: str, current_price: float) -> None:
        """
        Analyse un nouveau token candidat et décide d'acheter ou non (simulation enrichie : slippage, spread, latence, erreurs, logs IA).
        """
        import random, time
        logger.info(f"Decision module received new token candidate: {token_mint_address} at price {current_price}")
        try:
            will_double = await self._predict_x2_in_10min(token_mint_address, current_price)
            if not will_double:
                logger.warning(f"Token {token_mint_address} ne devrait pas atteindre x2 dans les 10min, achat annulé.")
                return
            if self.simulation_mode:
                # Simulation avancée : slippage, spread, latence, frais, erreurs
                slippage = random.uniform(0.001, 0.01)  # 0.1% à 1%
                spread = random.uniform(0.0005, 0.003)  # 0.05% à 0.3%
                fee = 0.002  # 0.2% de frais
                latency = random.uniform(0.005, 0.02)  # 5ms à 20ms (ultra-fast simulation)
                fail_chance = 0.01  # 1% d'échec simulé
                await asyncio.sleep(latency)
                if random.random() < fail_chance:
                    logger.error(f"[SIMULATION] Echec d'achat simulé pour {token_mint_address}")
                    return
                effective_price = current_price * (1 + slippage + spread + fee)
                result = {
                    "token": token_mint_address,
                    "price": effective_price,
                    "action": "buy",
                    "timestamp": asyncio.get_event_loop().time(),
                    "sim_slippage": slippage,
                    "sim_spread": spread,
                    "sim_fee": fee,
                    "sim_latency": latency,
                    "sim_type": "buy"
                }
                self.simulation_results.append(result)
                self.log_trade(result, simulation=True)
                logger.info(f"Simulation avancée: buy logged for {token_mint_address} (slippage={slippage:.4f}, spread={spread:.4f}, fee={fee:.4f}, latency={latency:.3f}s)")
                return
            if token_mint_address in self.held_tokens:
                logger.info(f"Already holding {token_mint_address}, skipping buy.")
                return
            # Not held, proceed with buy checks
            # Vérification du solde minimum avant achat
            try:
                from utils.solana_utils import get_trustwallet_balance
                trustwallet_address = getattr(self, 'trustwallet_address', None)
                if not trustwallet_address:
                    logger.error("Adresse TrustWallet non configurée. Achat annulé.")
                    return
                sol_balance = await get_trustwallet_balance(trustwallet_address)
                montant_total = self.buy_amount_sol + 0.01  # 0.01 SOL de marge pour les frais
                if sol_balance < montant_total:
                    logger.error(f"Solde insuffisant ({sol_balance:.4f} SOL) pour acheter {self.buy_amount_sol} SOL de {token_mint_address}. Achat annulé.")
                    return
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du solde TrustWallet : {e}")
                return
            # Détection honeypot, taxes élevées, market cap, anti-bot AVANT l'achat
            honeypot_info = await self._check_token_honeypot_and_taxes(token_mint_address)
            if honeypot_info.get("is_honeypot"):
                logger.error(f"Token {token_mint_address} détecté comme honeypot. Achat annulé.")
                return
            taxes = honeypot_info.get("taxes", {})
            if taxes and (taxes.get("buy", 0) > 0.15 or taxes.get("sell", 0) > 0.15):
                logger.error(f"Token {token_mint_address} a des taxes élevées (buy: {taxes.get('buy', 0):.2%}, sell: {taxes.get('sell', 0):.2%}). Achat annulé.")
                return
            # Vérification du market cap (via honeypot.is ou heuristique)
            marketcap = honeypot_info.get("marketcap", 0)
            if marketcap and marketcap < 10000:
                logger.error(f"Token {token_mint_address} a un market cap trop faible ({marketcap}$). Achat annulé.")
                return
            # Détection anti-bot (via honeypot.is ou heuristique)
            if honeypot_info.get("antiBot", False) or honeypot_info.get("antiBotDetected", False):
                logger.error(f"Token {token_mint_address} détecté comme anti-bot. Achat annulé.")
                return
            # Vérification de la liquidité sur Jupiter (min 5 SOL)
            has_liquidity = await self._check_token_liquidity(token_mint_address, min_sol=5)
            if not has_liquidity:
                logger.error(f"Token {token_mint_address} a une liquidité trop faible (<5 SOL) sur Jupiter. Achat annulé.")
                return
            # Prédiction x2 en 20 minutes AVANT l'achat
            will_double = await self._predict_x2_in_20min(token_mint_address, current_price)
            if not will_double:
                logger.error(f"Token {token_mint_address} ne devrait PAS faire x2 dans les 20min après achat. Achat annulé.")
                return
            # Vérification revendabilité : check pool/route DEX (Jupiter) AVANT l'achat
            is_sellable = await self._check_token_sellable(token_mint_address)
            if not is_sellable:
                logger.error(f"Token {token_mint_address} non revendable (pas de pool ou de route DEX trouvée). Achat annulé.")
                return
            # All checks passed, execute buy
            logger.info(f"Attempting to buy {self.buy_amount_sol} SOL worth of {token_mint_address}")
            success = await self.order_executor.execute_buy(token_mint_address, self.buy_amount_sol)
            if success:
                creator_wallets = await self._detect_creator_wallets(token_mint_address)
                self.held_tokens[token_mint_address] = {
                    "buy_price": current_price,
                    "buy_amount": self.buy_amount_sol,
                    "creator_wallets": creator_wallets
                }
                logger.success(f"Successfully bought {token_mint_address}. Tracking for sale. Creator wallets: {creator_wallets}")
                # Notifier l'analyseur temps réel de commencer la surveillance de ce token
                if hasattr(self, 'realtime_analyzer') and self.realtime_analyzer:
                    await self.realtime_analyzer.start_monitoring_token(token_mint_address)
                # Hook IA/logs après achat réel
                self.record_real_trade({
                    "token": token_mint_address,
                    "price": current_price,
                    "action": "buy",
                    "timestamp": asyncio.get_event_loop().time()
                })
                for hook in self.ia_hooks:
                    try:
                        hook.on_trade("buy", token_mint_address, current_price)
                    except Exception as e:
                        logger.warning(f"Erreur hook IA après achat : {e}")
    async def notify_token_sold(self, token_mint_address: str):
        """
        À appeler après la vente d'un token pour arrêter la surveillance blockchain.
        """
        if hasattr(self, 'realtime_analyzer') and self.realtime_analyzer:
            await self.realtime_analyzer.stop_monitoring_token(token_mint_address)
            else:
                logger.error(f"Failed to buy {token_mint_address}.")
        except Exception as e:
            logger.error(f"Erreur inattendue dans process_new_token_candidate pour {token_mint_address} : {e}")
            return
    async def _check_token_honeypot_and_taxes(self, token_mint_address: str) -> dict:
        """
        Détecte si le token est un honeypot, récupère les taxes, le market cap et anti-bot.
        Retourne un dict {"is_honeypot": bool, "taxes": {"buy": float, "sell": float}, "marketcap": float, "antiBot": bool}
        """
        result = {"is_honeypot": False, "taxes": {}, "marketcap": 0, "antiBot": False}
        try:
            import aiohttp
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
        return result

    async def _check_token_liquidity(self, token_mint_address: str, min_sol: float = 5) -> bool:
        """
        Vérifie la liquidité du token sur Jupiter (min_sol en SOL). Retourne True si la liquidité est suffisante.
        """
        try:
            import aiohttp
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
                    routes = data.get("data", [])
                    if routes:
                        out_amount = routes[0].get("outAmount", 0)
                        if out_amount and int(out_amount) > 0:
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
            import aiohttp
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
                    routes = data.get("data", [])
                    if routes:
                        logger.info(f"Token {token_mint_address} revendable : route DEX trouvée via Jupiter.")
                        return True
                    else:
                        logger.error(f"Token {token_mint_address} NON revendable : aucune route DEX trouvée via Jupiter.")
                        return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification revendabilité du token {token_mint_address} : {e}")
            return False
    async def _predict_x2_in_20min(self, token_mint_address: str, current_price: float) -> bool:
        """
        Prédit si le token peut atteindre x2 dans les 20min après achat (analyse historique, heuristique, IA, etc).
        Retourne True si la proba est suffisante, False sinon.
        """
        import random, time, asyncio
        start = time.time()
        score = 0.5
        try:
            if hasattr(self, 'db_manager'):
                db = self.db_manager
                similar_tokens = db.get_tokens_with_x2_in_20min(token_mint_address)
                if similar_tokens:
                    score += 0.4
                else:
                    score -= 0.2
        except Exception as e:
            logger.warning(f"Erreur accès base de données pour la prédiction: {e}")
        # Heuristique simple : nom, supply, holders, blacklist
        if "good" in token_mint_address.lower():
            score += 0.2
        if "scam" in token_mint_address.lower() or "bad" in token_mint_address.lower():
            score -= 0.2
        # Ajout d'un bruit pseudo-aléatoire
        score += (random.random() - 0.5) * 0.1
        score = max(0.0, min(1.0, score))
        elapsed = (time.time() - start) * 1000
        logger.info(f"Prédiction x2 en 20min pour {token_mint_address}: score={score:.2f} (calculé en {elapsed:.1f}ms)")
        if elapsed > 800:
            logger.warning(f"Prédiction trop lente: {elapsed:.1f}ms")
        return score > 0.5
    async def _detect_creator_wallets(self, token_mint_address: str):
        """Détecte tous les comptes liés au créateur du token (via graphe, signatures, transferts, pools)."""
        # À remplacer par une vraie détection blockchain
        # Ici, on simule avec une liste factice
        return [f"wallet_{token_mint_address}_1", f"wallet_{token_mint_address}_2"]

    async def evaluate_held_tokens_for_sale(self, token_mint_address: str, current_price: float, whale_selling: bool = False) -> None:
        """
        Évalue si un token détenu doit être vendu (simulation enrichie : slippage, spread, latence, erreurs, logs IA).
        """
        import random
        try:
            if self.simulation_mode:
                slippage = random.uniform(0.001, 0.01)
                spread = random.uniform(0.0005, 0.003)
                fee = 0.002
                latency = random.uniform(0.005, 0.02)  # 5ms à 20ms (ultra-fast simulation)
                fail_chance = 0.01
                await asyncio.sleep(latency)
                if random.random() < fail_chance:
                    logger.error(f"[SIMULATION] Echec de vente simulé pour {token_mint_address}")
                    return
                effective_price = current_price * (1 - slippage - spread - fee)
                result = {
                    "token": token_mint_address,
                    "price": effective_price,
                    "action": "sell",
                    "whale_selling": whale_selling,
                    "timestamp": asyncio.get_event_loop().time(),
                    "sim_slippage": slippage,
                    "sim_spread": spread,
                    "sim_fee": fee,
                    "sim_latency": latency,
                    "sim_type": "sell"
                }
                self.simulation_results.append(result)
                self.log_trade(result, simulation=True)
                logger.info(f"Simulation avancée: sell logged for {token_mint_address} (slippage={slippage:.4f}, spread={spread:.4f}, fee={fee:.4f}, latency={latency:.3f}s)")
                return
            if token_mint_address in self.held_tokens:
                buy_price = self.held_tokens[token_mint_address]["buy_price"]
                profit_multiplier = current_price / buy_price
                creator_wallets = self.held_tokens[token_mint_address].get("creator_wallets", [])
                logger.info(f"Evaluating {token_mint_address}: Buy Price={buy_price}, Current Price={current_price}, Multiplier={profit_multiplier:.2f}")
                # Trailing stop : stop loss dynamique après achat
                trailing_stop_percent = getattr(self, 'trailing_stop_percent', 0.15) # 15% par défaut
                if 'max_price' not in self.held_tokens[token_mint_address]:
                    self.held_tokens[token_mint_address]['max_price'] = buy_price
                # Met à jour le plus haut atteint
                if current_price > self.held_tokens[token_mint_address]['max_price']:
                    self.held_tokens[token_mint_address]['max_price'] = current_price
                # Si le prix redescend de plus de trailing_stop_percent depuis le plus haut, vente
                max_price = self.held_tokens[token_mint_address]['max_price']
                if current_price < max_price * (1 - trailing_stop_percent):
                    logger.warning(f"[TRAILING STOP] Selling {token_mint_address}: Price dropped >{int(trailing_stop_percent*100)}% from max ({current_price:.4f} < {max_price:.4f}). Vente automatique.")
                    await self._execute_sale(token_mint_address)
                    # Hook IA/logs après vente réelle
                    self.record_real_trade({
                        "token": token_mint_address,
                        "price": current_price,
                        "action": "sell",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    for hook in self.ia_hooks:
                        try:
                            hook.on_trade("sell", token_mint_address, current_price)
                        except Exception as e:
                            logger.warning(f"Erreur hook IA après vente : {e}")
                    return
                # PRIORITÉ : Take profit automatique à x2
                if profit_multiplier >= self.sell_multiplier:
                    logger.info(f"[TAKE PROFIT] Selling {token_mint_address}: Price reached x{self.sell_multiplier} (x{profit_multiplier:.2f}). Vente immédiate.")
                    await self._execute_sale(token_mint_address)
                    return
                # STOP LOSS : vente immédiate si le prix passe sous le prix d'achat
                if profit_multiplier < 1.0:
                    logger.warning(f"[STOP LOSS] Selling {token_mint_address}: Price dropped below buy price (x{profit_multiplier:.2f} < x1.0). Vente automatique pour éviter toute perte.")
                    await self._execute_sale(token_mint_address)
                    return
                # Détection avancée des signaux de dump (volume, créateur, liquidité)
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
        """Détecte si un wallet du créateur est en train de vendre ou retirer de la liquidité."""
        # À remplacer par une vraie détection blockchain
        # Ici, on simule avec une probabilité
        import random
        return random.random() > 0.7
    def export_simulation_report(self, filename: str = "simulation_report.csv") -> None:
        """Exporte le rapport de simulation au format CSV."""
        import csv
        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["token", "price", "action", "whale_selling", "timestamp"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in self.simulation_results:
                    writer.writerow(row)
            logger.info(f"Rapport simulation exporté : {filename}")
        except Exception as e:
            logger.error(f"Erreur export rapport simulation : {e}")

    async def _execute_sale(self, token_mint_address: str) -> None:
        """Exécute la vente d'un token détenu (tout le montant)."""
        try:
            logger.info(f"Attempting to sell all of {token_mint_address}")
            amount = self.held_tokens[token_mint_address]["buy_amount"]
            success = await self.order_executor.execute_sell(token_mint_address, amount)
            if success:
                logger.success(f"Successfully sold {token_mint_address}.")
                del self.held_tokens[token_mint_address]
            else:
                logger.error(f"Failed to sell {token_mint_address}.")
        except Exception as e:
            logger.error(f"Erreur _execute_sale : {e}")