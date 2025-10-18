import json
import time
import asyncio
import os
import threading
from loguru import logger
from typing import Optional
from .gemini_analyzer import GeminiAnalyzer


# --- Configuration des chemins ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
# Logger dédié pour les décisions structurées de l'IA
decision_logger = logger.bind(name="AIOptimizerDecisions")
decision_logger.add(os.path.join(LOGS_DIR, "ai_optimizer_decisions.log"), format="{message}", level="INFO", rotation="5 MB", serialize=True)
class AIAutoOptimizer:
    """
    Optimiseur IA avancé : surveille les logs, ajuste dynamiquement les paramètres du bot (buy_amount, sell_multiplier, risk),
    détecte drawdown, winrate, volatilité, et notifie les hooks (dashboard, alertes, etc).
    """
    def __init__(self, decision_module, interval=60):
        self.decision_module = decision_module
        self.simulation_log = os.path.join(LOGS_DIR, 'simulation_trades.log')
        self.first_run_interval = 3600  # 1 heure
        self.subsequent_interval = 1200 # 20 minutes
        self.gemini_analyzer: Optional['GeminiAnalyzer'] = None # Sera injecté
        self.running = False
        self.last_sim_len = 0
        self.last_real_len = 0
        self.hooks = []  # Pour notifier le dashboard ou d'autres modules
        self.max_drawdown = 0.0
        self.last_profit = 0.0
        self.loss_streak = 0
        self.win_streak = 0
        self.last_action = None
        self.best_params = None
        self.best_profit = float('-inf')
        self.freeze = False
        self.rollback_count = 0
        self.param_history = []
        self.strategy_profiles = [
            {"name": "conservateur", "buy_factor": 0.8, "sell_add": 0.1},
            {"name": "agressif", "buy_factor": 1.2, "sell_add": -0.05},
            {"name": "équilibré", "buy_factor": 1.0, "sell_add": 0.0}
        ]
        self.current_profile = 2  # start with équilibré
        self.param_file = os.path.join(LOGS_DIR, "ai_optimizer_params.json")
        self._load_best_params()
        self.hall_of_fame = [] # Historique des meilleurs génomes
        self.last_analysis = None # Pour stocker la dernière analyse de Gemini
        # Initialiser les valeurs pour l'API
        self.winrate = 0.0
        self.drawdown = 0.0

    def _log_decision(self, reason: str, action: str, old_params: dict, new_params: dict):
        """Enregistre une décision de manière structurée."""
        log_entry = {
            "timestamp": time.time(),
            "reason": reason,
            "action": action,
            "details": {
                "old_params": old_params,
                "new_params": new_params
            }
        }
        decision_logger.info(log_entry)


    def get_status_dict(self):
        """Retourne un dictionnaire de l'état actuel pour l'API."""
        return {
            "winrate": self.winrate,
            "max_drawdown": self.max_drawdown,
            "freeze": self.freeze,
            "rollback_count": self.rollback_count,
            "current_profile": self.current_profile,
            "is_running": self.running,
            "last_analysis": self.last_analysis,
            "decision_history": self._read_decision_log(),
            "hall_of_fame": self.hall_of_fame,
        }

    def get_history(self):
        """Retourne l'historique des paramètres et performances pour les graphiques."""
        return self.param_history

    def get_hall_of_fame(self):
        """Retourne la liste des meilleurs génomes historiques."""
        return [genome.__dict__ for genome in self.hall_of_fame]

    def get_population_status(self):
        """Retourne l'état de la population pour l'API (méthode ajoutée)."""
        # Cette méthode est un placeholder, car la logique de population a été simplifiée.
        # On retourne le champion actuel comme seule population pour la cohérence de l'UI.
        current_genome = self.best_params or {"buy_amount_sol": 0, "sell_multiplier": 0}
        current_genome['role'] = 'Champion'
        return {"population": [current_genome], "generation_count": self.rollback_count}

    def set_gemini_analyzer(self, analyzer):
        """Injecte l'analyseur Gemini pour les fonctionnalités IA."""
        self.gemini_analyzer = analyzer

    def analyze_and_adjust(self):
        """
        Analyse les logs, ajuste dynamiquement les paramètres, mémorise les meilleurs, rollback si besoin, auto-tuning, freeze si profit stable.
        """
        if not self.decision_module:
            logger.debug("[AI Optimizer] Decision module non configuré, analyse en attente.")
            return
        
        import random
        # L'analyse se base sur les trades de simulation
        sim_trades = self._read_log(self.simulation_log)
        self.sim_profit = self._compute_profit(sim_trades)
        self.winrate, self.avg_profit, self.volatility = self._compute_stats(sim_trades)
        self.drawdown = self._compute_drawdown(sim_trades)
        self.max_drawdown = max(self.max_drawdown, self.drawdown)
        logger.info(f"[AI Optimizer] Profit simulation: {self.sim_profit:.4f} | Winrate: {self.winrate:.2%} | Volatilité: {self.volatility:.4f} | Drawdown: {self.drawdown:.4f}")

        # Mémorise les meilleurs paramètres et sauvegarde sur disque
        if self.sim_profit > self.best_profit:
            self.best_profit = self.sim_profit
            self.best_params = {
                "buy_amount_sol": self.decision_module.buy_amount_sol,
                "sell_multiplier": self.decision_module.sell_multiplier
            }
            # Mettre à jour le Hall of Fame
            if self.best_params not in self.hall_of_fame:
                self.hall_of_fame.append(self.best_params)
                self.hall_of_fame.sort(key=lambda x: x.get('profit', 0), reverse=True)
                self.hall_of_fame = self.hall_of_fame[:5] # Garder les 5 meilleurs
            self._save_best_params()
            logger.info(f"[AI Optimizer] Nouveaux meilleurs paramètres sauvegardés.")
        # Historique des paramètres
        self.param_history.append({
            "profit": self.sim_profit,
            "buy_amount_sol": self.decision_module.buy_amount_sol,
            "sell_multiplier": self.decision_module.sell_multiplier,
            "winrate": self.winrate,
            "drawdown": self.drawdown,
            "volatility": self.volatility,
            "timestamp": time.time()
        })

        # Freeze si profit stable et drawdown faible
        if not self.freeze and self.winrate > 0.7 and self.drawdown < 0.1 and self.sim_profit > 0.5:
            self.freeze = True
            logger.info(f"[AI Optimizer] Profit stable détecté, freeze de l'autoamélioration.")
        if self.freeze and (self.winrate < 0.6 or self.drawdown > 0.15 or self.sim_profit < self.best_profit * 0.8):
            self.freeze = False
            logger.warning(f"[AI Optimizer] Fin du freeze, reprise de l'autoamélioration.")

        if not self.freeze:
            # Exploration multi-profils (grid search léger)
            if random.random() < 0.15:
                old_profile = self.current_profile
                self.current_profile = (self.current_profile + 1) % len(self.strategy_profiles)
                prof = self.strategy_profiles[self.current_profile]
                
                old_params = {"buy_amount_sol": self.decision_module.buy_amount_sol, "sell_multiplier": self.decision_module.sell_multiplier}
                new_buy_amount = max(0.01, self.decision_module.buy_amount_sol * prof["buy_factor"])
                new_sell_multiplier = min(2.5, max(1.0, self.decision_module.sell_multiplier + prof["sell_add"]))
                self.decision_module.buy_amount_sol = new_buy_amount
                self.decision_module.sell_multiplier = new_sell_multiplier
                new_params = {"buy_amount_sol": new_buy_amount, "sell_multiplier": new_sell_multiplier}

                logger.info(f"[AI Optimizer] Switch profil stratégie: {self.strategy_profiles[old_profile]['name']} -> {prof['name']}")
                self._log_decision(f"Exploration de stratégie: passage au profil '{prof['name']}'", "switch_profile", old_params, new_params)

            # Ajustement dynamique classique
            if self.drawdown > 0.2:
                old_params = {"buy_amount_sol": self.decision_module.buy_amount_sol, "sell_multiplier": self.decision_module.sell_multiplier}
                self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * 0.8)
                self.decision_module.sell_multiplier = min(2.5, self.decision_module.sell_multiplier + 0.1)
                new_params = {"buy_amount_sol": self.decision_module.buy_amount_sol, "sell_multiplier": self.decision_module.sell_multiplier}
                logger.warning(f"[AI Optimizer] Drawdown élevé détecté, réduction du risque.")
                self._log_decision(f"Drawdown élevé ({self.drawdown:.2%})", "reduce_risk", old_params, new_params)

            elif self.winrate < 0.4:
                old_params = {"buy_amount_sol": self.decision_module.buy_amount_sol}
                self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * 0.9)
                new_params = {"buy_amount_sol": self.decision_module.buy_amount_sol}
                logger.warning(f"[AI Optimizer] Winrate faible, ajustement buy_amount_sol.")
                self._log_decision(f"Winrate faible ({self.winrate:.2%})", "adjust_buy_amount", old_params, new_params)

            elif self.winrate > 0.7 and self.avg_profit > 0:
                old_params = {"buy_amount_sol": self.decision_module.buy_amount_sol}
                self.decision_module.buy_amount_sol = min(2.0, self.decision_module.buy_amount_sol * 1.1)
                new_params = {"buy_amount_sol": self.decision_module.buy_amount_sol}
                logger.info(f"[AI Optimizer] Winrate élevé, augmentation buy_amount_sol.")
                self._log_decision(f"Winrate élevé ({self.winrate:.2%}) et profit moyen positif", "increase_risk", old_params, new_params)

            # Auto-tuning : mutation aléatoire légère
            if random.random() < 0.1:
                old_buy = self.decision_module.buy_amount_sol
                new_buy = max(0.01, old_buy * random.uniform(0.95, 1.05))
                self.decision_module.buy_amount_sol = new_buy
                logger.info(f"[AI Optimizer] Mutation auto-tuning buy_amount_sol: {old_buy:.4f} -> {new_buy:.4f}")
                self._log_decision("Mutation aléatoire pour exploration", "auto_tune", {"buy_amount_sol": old_buy}, {"buy_amount_sol": new_buy})

        self._check_and_apply_rollback()

        # Analyse IA des trades complétés via Gemini
        if self.gemini_analyzer and self.decision_module.simulation_mode:
            completed_log_path = os.path.join(LOGS_DIR, "simulation_trades.log") # En simulation, on analyse les trades de simulation
            if os.path.exists(completed_log_path):
                # Lancer l'analyse et stocker le résultat
                async def run_analysis():
                    logger.info("[SIMULATION] Lancement de l'analyse IA des trades complétés...")
                    analysis_result = await self.gemini_analyzer.analyze_logs(log_path=completed_log_path)
                    self.last_analysis = analysis_result
                    logger.info("[SIMULATION] Analyse IA terminée.")
                asyncio.run_coroutine_threadsafe(run_analysis(), asyncio.get_event_loop())

    def _save_best_params(self):
        """Sauvegarde les meilleurs paramètres sur le disque."""
        try:
            with open(self.param_file, "w", encoding="utf-8") as f:
                json.dump({"best_params": self.best_params, "best_profit": self.best_profit}, f, indent=2)
        except Exception as e:
            logger.warning(f"[AI Optimizer] Erreur sauvegarde best_params: {e}")

    def _load_best_params(self):
        try:
            with open(self.param_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.best_params = data.get("best_params")
                self.best_profit = data.get("best_profit", float('-inf'))
                logger.info(f"[AI Optimizer] Best params chargés depuis disque.")
        except Exception:
            logger.info("[AI Optimizer] Aucun fichier de paramètres trouvé, démarrage avec les valeurs par défaut.")
            pass

    def _check_and_apply_rollback(self):
        """Vérifie si un rollback vers les meilleurs paramètres est nécessaire."""
        if self.best_params and self.sim_profit < self.best_profit * 0.5 and not self.freeze:
            old_params = {"buy_amount_sol": self.decision_module.buy_amount_sol, "sell_multiplier": self.decision_module.sell_multiplier}
            self.decision_module.buy_amount_sol = self.best_params["buy_amount_sol"]
            self.decision_module.sell_multiplier = self.best_params["sell_multiplier"]
            new_params = self.best_params
            self.rollback_count += 1
            logger.error(f"[AI Optimizer] Rollback vers meilleurs paramètres (rollback n°{self.rollback_count})")
            self._log_decision(f"Chute de performance (profit actuel {self.sim_profit:.4f} < 50% du meilleur profit {self.best_profit:.4f})", "rollback_to_best", old_params, new_params)
        if self.sim_profit < self.last_profit:
            self.loss_streak += 1
            self.win_streak = 0
        elif self.sim_profit > self.last_profit:
            self.win_streak += 1
            self.loss_streak = 0
        if self.loss_streak >= 3 and not self.freeze:
            old_params = {"buy_amount_sol": self.decision_module.buy_amount_sol, "sell_multiplier": self.decision_module.sell_multiplier}
            self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * 0.7)
            self.decision_module.sell_multiplier = min(2.5, self.decision_module.sell_multiplier + 0.2)
            new_params = {"buy_amount_sol": self.decision_module.buy_amount_sol, "sell_multiplier": self.decision_module.sell_multiplier}
            logger.error(f"[AI Optimizer] Pertes consécutives, passage en mode recovery.")
            self._log_decision(f"{self.loss_streak} pertes consécutives", "recovery_mode", old_params, new_params)
        self.last_profit = self.sim_profit
        # Notifier les hooks (dashboard, alertes, etc)
        for hook in self.hooks:
            try:
                hook.on_ai_adjustment({
                    "profit": self.sim_profit,
                    "winrate": self.winrate,
                    "drawdown": self.drawdown,
                    "volatility": self.volatility,
                    "buy_amount_sol": self.decision_module.buy_amount_sol,
                    "sell_multiplier": self.decision_module.sell_multiplier,
                    "freeze": self.freeze,
                    "rollback_count": self.rollback_count
                })
            except Exception as e:
                logger.warning(f"[AI Optimizer] Hook error: {e}")
    def _compute_stats(self, trades):
        """Calcule winrate, profit moyen, volatilité sur la série de trades."""
        wins = 0
        losses = 0
        profits = []
        buy_prices = {}
        for entry in trades:
            if entry.get('action') == 'buy':
                buy_prices[entry['token']] = entry['price']
            elif entry.get('action') == 'sell' and entry['token'] in buy_prices:
                profit = entry['price'] - buy_prices[entry['token']]
                profits.append(profit)
                if profit > 0:
                    wins += 1
                else:
                    losses += 1
        total = wins + losses
        winrate = wins / total if total > 0 else 0.0
        avg_profit = sum(profits) / len(profits) if profits else 0.0
        volatility = (sum((p - avg_profit) ** 2 for p in profits) / len(profits)) ** 0.5 if profits else 0.0
        return winrate, avg_profit, volatility

    def _compute_drawdown(self, trades):
        """Calcule le drawdown maximum sur la série de trades."""
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        buy_prices = {}
        for entry in trades:
            if entry.get('action') == 'buy':
                buy_prices[entry['token']] = entry['price']
            elif entry.get('action') == 'sell' and entry['token'] in buy_prices:
                equity += entry['price'] - buy_prices[entry['token']]
                peak = max(peak, equity)
                dd = (peak - equity) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, dd)
        return max_dd

    def _read_log(self, log_file):
        trades = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        trades.append(json.loads(line.strip()))
                    except Exception:
                        continue
        except FileNotFoundError:
            pass
        return trades

    def _compute_profit(self, trades):
        profit = 0.0
        buy_prices = {}
        for entry in trades:
            if entry.get('action') == 'buy':
                buy_prices[entry['token']] = entry['price']
            elif entry.get('action') == 'sell' and entry['token'] in buy_prices:
                profit += entry['price'] - buy_prices[entry['token']]
        return profit

    def _read_decision_log(self):
        """Lit le fichier de log des décisions de l'IA."""
        log_file = os.path.join(LOGS_DIR, "ai_optimizer_decisions.log")
        decisions = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        decisions.append(json.loads(line.strip()))
                    except Exception: continue
        except FileNotFoundError: pass
        return decisions

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False

    def _run(self):
        logger.info("[AI Optimizer] Démarrage de l'optimisation automatique continue.")
        first_run_done = False
        while self.running:
            # La boucle attend que le bot soit fonctionnel et en mode simulation
            if self.decision_module and self.decision_module.simulation_mode:
                interval = self.subsequent_interval if first_run_done else self.first_run_interval
                logger.info(f"[AI Optimizer] Bot fonctionnel en mode démo. Prochain cycle d'évolution dans {interval / 60:.1f} minutes.")
                time.sleep(interval)
                self.analyze_and_adjust()
                first_run_done = True
            else:
                # Si le bot n'est pas prêt, on vérifie plus fréquemment
                first_run_done = False # Reset if bot stops
                time.sleep(60)


# Exemple d'intégration (à placer dans main.py ou backend)
# from trading.decision_module import DecisionModule
# from ai_analysis.ai_auto_optimizer import AIAutoOptimizer
# decision_module = DecisionModule(...)
# ai_optimizer = AIAutoOptimizer(decision_module)
# ai_optimizer.start()
