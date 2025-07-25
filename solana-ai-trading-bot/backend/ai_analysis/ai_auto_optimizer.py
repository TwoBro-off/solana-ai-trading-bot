import json
import time
import asyncio
import threading
from loguru import logger


class AIAutoOptimizer:
    def set_param(self, key: str, value, target: str = "decision_module"):
        """
        Permet à Gemini ou tout module IA de modifier dynamiquement un paramètre du bot.
        Par défaut, cible le DecisionModule, mais peut cibler d'autres modules si besoin.
        Usage : ai_optimizer.set_param('buy_amount_sol', 0.5)
        """
        target_obj = getattr(self, target, None)
        if target_obj and hasattr(target_obj, key):
            setattr(target_obj, key, value)
            logger.info(f"[AI] Paramètre '{key}' de '{target}' mis à jour dynamiquement à {value}")
        elif hasattr(self, key):
            setattr(self, key, value)
            logger.info(f"[AI] Paramètre '{key}' de 'ai_auto_optimizer' mis à jour dynamiquement à {value}")
        else:
            logger.warning(f"[AI] Tentative de modification d'un paramètre inconnu : {key} sur {target}")
    async def start_vacation_mode_async(self, days=7):
        """Active le mode vacances : simulation forcée, autoamélioration continue, export quotidien (async)."""
        self.vacation_mode = True
        self.simulation_only = True
        logger.warning(json.dumps({"event": "vacation_mode_start", "mode": "simulation", "duration_days": days, "ts": time.time()}))
        for day in range(int(days)):
            logger.info(f"[AI Optimizer] Début du jour {day+1} de simulation continue.")
            day_start = time.time()
            while time.time() - day_start < 86400:
                self.analyze_and_adjust()
                self.advanced_analysis()
                if self.detect_overfitting():
                    self.send_alert("Sur-optimisation détectée pendant vacances !")
                await asyncio.sleep(self.interval)
            self.export_history_csv(f"ai_optimizer_history_day{day+1}.csv")
            self.export_history_json(f"ai_optimizer_history_day{day+1}.json")
            logger.info(f"[AI Optimizer] Résumé jour {day+1} : profit={self.real_profit:.4f}, winrate={self.winrate:.2%}, drawdown={self.drawdown:.4f}")
        logger.warning(json.dumps({"event": "vacation_mode_end", "mode": "simulation", "ts": time.time()}))
        self.vacation_mode = False
        self.simulation_only = False

    def start_vacation_mode(self, days=7):
        """Lance la version asynchrone dans l'event loop globale (pour compat FastAPI)."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.start_vacation_mode_async(days=days))

    async def start_real_mode_async(self, days=1):
        """Active le trading réel pour la durée spécifiée, puis repasse en simulation (async)."""
        self.simulation_only = False
        self.vacation_mode = False
        logger.warning(json.dumps({"event": "real_mode_start", "mode": "real", "duration_days": days, "ts": time.time()}))
        await asyncio.sleep(days * 86400)
        self.simulation_only = True
        logger.warning(json.dumps({"event": "real_mode_end", "mode": "simulation", "ts": time.time()}))

    def start_real_mode(self, days=1):
        """Lance la version asynchrone dans l'event loop globale (pour compat FastAPI)."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.start_real_mode_async(days=days))
    def export_history_csv(self, filename="ai_optimizer_history.csv"):
        import csv
        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["timestamp", "profit", "buy_amount_sol", "sell_multiplier", "winrate", "drawdown", "volatility"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in self.param_history:
                    writer.writerow({k: row.get(k, "") for k in fieldnames})
            logger.info(f"[AI Optimizer] Historique exporté en CSV : {filename}")
        except Exception as e:
            logger.error(f"[AI Optimizer] Erreur export CSV : {e}")

    def export_history_json(self, filename="ai_optimizer_history.json"):
        import json
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.param_history, f, ensure_ascii=False, indent=2)
            logger.info(f"[AI Optimizer] Historique exporté en JSON : {filename}")
        except Exception as e:
            logger.error(f"[AI Optimizer] Erreur export JSON : {e}")

    def detect_overfitting(self, window=30):
        """Détecte une sur-optimisation (overfitting) sur les derniers N points."""
        if len(self.param_history) < window:
            return False
        recent = self.param_history[-window:]
        profits = [r["profit"] for r in recent]
        mean_profit = sum(profits) / len(profits)
        std_profit = (sum((p - mean_profit) ** 2 for p in profits) / len(profits)) ** 0.5
        if std_profit < 0.01 and mean_profit < 0.05:
            logger.warning("[AI Optimizer] Sur-optimisation détectée : profits trop stables/faibles.")
            return True
        return False

    def send_alert(self, message, method="log"):
        """Envoie une alerte (log, email, discord, etc)."""
        logger.warning(f"[AI Optimizer][ALERTE] {message}")
        # TODO : Intégrer email/discord webhook si besoin

    def advanced_analysis(self):
        """Mode analyse avancée : détecte patterns, cycles, et propose des suggestions IA."""
        if len(self.param_history) < 10:
            return
        import numpy as np
        profits = np.array([h["profit"] for h in self.param_history])
        winrates = np.array([h["winrate"] for h in self.param_history])
        # Détection de cycles simples (FFT)
        fft = np.fft.fft(profits)
        dominant_freq = np.argmax(np.abs(fft[1:len(fft)//2])) + 1
        if dominant_freq > 0:
            logger.info(f"[AI Optimizer] Cycle détecté dans les profits (fréquence dominante : {dominant_freq})")
        # Suggestion IA simple
        if np.mean(winrates[-5:]) > 0.8:
            logger.info("[AI Optimizer] Suggestion : augmenter légèrement le risque, winrate élevé.")
        elif np.mean(winrates[-5:]) < 0.3:
            logger.info("[AI Optimizer] Suggestion : réduire le risque, winrate faible.")
    """
    Optimiseur IA avancé : surveille les logs, ajuste dynamiquement les paramètres du bot (buy_amount, sell_multiplier, risk),
    détecte drawdown, winrate, volatilité, et notifie les hooks (dashboard, alertes, etc).
    """
    def __init__(self, decision_module, simulation_log='simulation_trades.log', real_log='real_trades.log', interval=60):
        self.decision_module = decision_module
        self.simulation_log = simulation_log
        self.real_log = real_log
        self.interval = interval  # en secondes
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
        self.param_file = "ai_optimizer_params.json"
        self._load_best_params()

    def analyze_and_adjust(self):
        """
        Analyse les logs, ajuste dynamiquement les paramètres, mémorise les meilleurs, rollback si besoin, auto-tuning, freeze si profit stable.
        """
        import random
        sim_trades = self._read_log(self.simulation_log)
        real_trades = self._read_log(self.real_log)
        self.sim_profit = self._compute_profit(sim_trades)
        self.real_profit = self._compute_profit(real_trades)
        self.winrate, self.avg_profit, self.volatility = self._compute_stats(real_trades)
        self.drawdown = self._compute_drawdown(real_trades)
        self.max_drawdown = max(self.max_drawdown, self.drawdown)
        logger.info(f"[AI Optimizer] Profit simulation: {self.sim_profit:.4f} | Profit réel: {self.real_profit:.4f} | Winrate: {self.winrate:.2%} | Volatilité: {self.volatility:.4f} | Drawdown: {self.drawdown:.4f}")

        # Mémorise les meilleurs paramètres et sauvegarde sur disque
        if self.real_profit > self.best_profit:
            self.best_profit = self.real_profit
            self.best_params = {
                "buy_amount_sol": self.decision_module.buy_amount_sol,
                "sell_multiplier": self.decision_module.sell_multiplier
            }
            self._save_best_params()
            logger.info(f"[AI Optimizer] Nouveaux meilleurs paramètres sauvegardés.")
        # Historique des paramètres
        self.param_history.append({
            "profit": self.real_profit,
            "buy_amount_sol": self.decision_module.buy_amount_sol,
            "sell_multiplier": self.decision_module.sell_multiplier,
            "winrate": self.winrate,
            "drawdown": self.drawdown,
            "volatility": self.volatility,
            "timestamp": time.time()
        })

        # Freeze si profit stable et drawdown faible
        if not self.freeze and self.winrate > 0.7 and self.drawdown < 0.1 and self.real_profit > 0.5:
            self.freeze = True
            logger.info(f"[AI Optimizer] Profit stable détecté, freeze de l'autoamélioration.")
        if self.freeze and (self.winrate < 0.6 or self.drawdown > 0.15 or self.real_profit < self.best_profit * 0.8):
            self.freeze = False
            logger.warning(f"[AI Optimizer] Fin du freeze, reprise de l'autoamélioration.")

        if not self.freeze:
            # Exploration multi-profils (grid search léger)
            if random.random() < 0.15:
                old_profile = self.current_profile
                self.current_profile = (self.current_profile + 1) % len(self.strategy_profiles)
                prof = self.strategy_profiles[self.current_profile]
                self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * prof["buy_factor"])
                self.decision_module.sell_multiplier = min(2.5, max(1.0, self.decision_module.sell_multiplier + prof["sell_add"]))
                logger.info(f"[AI Optimizer] Switch profil stratégie: {self.strategy_profiles[old_profile]['name']} -> {prof['name']}")
            # Ajustement dynamique classique
            if self.drawdown > 0.2:
                self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * 0.8)
                self.decision_module.sell_multiplier = min(2.5, self.decision_module.sell_multiplier + 0.1)
                logger.warning(f"[AI Optimizer] Drawdown élevé détecté, réduction du risque.")
            elif self.winrate < 0.4:
                self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * 0.9)
                logger.warning(f"[AI Optimizer] Winrate faible, ajustement buy_amount_sol.")
            elif self.winrate > 0.7 and self.avg_profit > 0:
                self.decision_module.buy_amount_sol = min(2.0, self.decision_module.buy_amount_sol * 1.1)
                logger.info(f"[AI Optimizer] Winrate élevé, augmentation buy_amount_sol.")
            # Auto-tuning : mutation aléatoire légère
            if random.random() < 0.1:
                old = self.decision_module.buy_amount_sol
                self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * random.uniform(0.95, 1.05))
                logger.info(f"[AI Optimizer] Mutation auto-tuning buy_amount_sol: {old:.4f} -> {self.decision_module.buy_amount_sol:.4f}")
        # Analyse de corrélation (exemple simple)
        if len(self.param_history) > 20:
            from statistics import correlation, mean
            try:
                profits = [h["profit"] for h in self.param_history[-20:]]
                buy_amounts = [h["buy_amount_sol"] for h in self.param_history[-20:]]
                corr = correlation(profits, buy_amounts)
                logger.info(f"[AI Optimizer] Corrélation profit/buy_amount_sol (20 derniers): {corr:.2f}")
            except Exception:
                pass
    def _save_best_params(self):
        try:
            with open(self.param_file, "w", encoding="utf-8") as f:
                json.dump({"best_params": self.best_params, "best_profit": self.best_profit}, f)
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
            pass
        # Rollback si performance chute
        if self.best_params and self.real_profit < self.best_profit * 0.5 and not self.freeze:
            self.decision_module.buy_amount_sol = self.best_params["buy_amount_sol"]
            self.decision_module.sell_multiplier = self.best_params["sell_multiplier"]
            self.rollback_count += 1
            logger.error(f"[AI Optimizer] Rollback vers meilleurs paramètres (rollback n°{self.rollback_count})")

        if self.real_profit < self.last_profit:
            self.loss_streak += 1
            self.win_streak = 0
        elif self.real_profit > self.last_profit:
            self.win_streak += 1
            self.loss_streak = 0
        if self.loss_streak >= 3 and not self.freeze:
            self.decision_module.buy_amount_sol = max(0.01, self.decision_module.buy_amount_sol * 0.7)
            self.decision_module.sell_multiplier = min(2.5, self.decision_module.sell_multiplier + 0.2)
            logger.error(f"[AI Optimizer] Pertes consécutives, passage en mode recovery.")
        self.last_profit = self.real_profit
        # Notifier les hooks (dashboard, alertes, etc)
        for hook in self.hooks:
            try:
                hook.on_ai_adjustment({
                    "profit": self.real_profit,
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

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False

    def _run(self):
        logger.info("[AI Optimizer] Démarrage de l'optimisation automatique continue.")
        while self.running:
            self.analyze_and_adjust()
            time.sleep(self.interval)

    def on_new_trade(self, trade_entry, simulation=True):
        """
        À appeler à chaque nouveau trade (vente) pour déclencher l’analyse et l’ajustement immédiat.
        """
        self.log_trade(trade_entry, simulation=simulation)
        self.analyze_and_adjust()
        # Notifier les hooks en temps réel
        for hook in self.hooks:
            try:
                hook.on_new_trade(trade_entry)
            except Exception as e:
                logger.warning(f"[AI Optimizer] Hook error: {e}")

# Exemple d'intégration (à placer dans main.py ou backend)
# from trading.decision_module import DecisionModule
# from ai_analysis.ai_auto_optimizer import AIAutoOptimizer
# decision_module = DecisionModule(...)
# ai_optimizer = AIAutoOptimizer(decision_module)
# ai_optimizer.start()
