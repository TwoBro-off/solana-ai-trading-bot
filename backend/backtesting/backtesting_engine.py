import datetime
from typing import List, Dict, Any
import logging

class BacktestingEngine:
    def __init__(self, strategy, historical_data: List[Dict[str, Any]]):
        self.strategy = strategy
        self.historical_data = historical_data
        self.results = []

    def run(self):
        for data_point in self.historical_data:
            action = self.strategy.evaluate(data_point)
            self.results.append({
                'timestamp': data_point.get('timestamp'),
                'action': action,
                'price': data_point.get('price'),
                'balance': self.strategy.balance
            })
        return self.results

# Example strategy stub
import math

class TrendFollowingStrategy:
    def __init__(self, initial_balance=1000, mode='advanced'):
        self.balance = initial_balance
        self.position = 0  # 0 = no position, 1 = long
        self.last_price = None
        self.prices = []
        self.ema = None
        self.macd_hist = []
        self.rsi_period = 14
        self.rsi_gains = []
        self.rsi_losses = []
        self.mode = mode  # 'advanced' ou 'basic'
        
        self.logger = logging.getLogger("TrendFollowingStrategy")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def sma(self, period):
        if len(self.prices) < period:
            return None
        return sum(self.prices[-period:]) / period

    def ema_calc(self, period):
        if len(self.prices) < period:
            return None
        k = 2 / (period + 1)
        ema = self.prices[-period]
        for price in self.prices[-period+1:]:
            ema = price * k + ema * (1 - k)
        return ema

    def rsi(self):
        if len(self.rsi_gains) < self.rsi_period:
            return None
        avg_gain = sum(self.rsi_gains[-self.rsi_period:]) / self.rsi_period
        avg_loss = sum(self.rsi_losses[-self.rsi_period:]) / self.rsi_period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def macd(self):
        ema12 = self.ema_calc(12)
        ema26 = self.ema_calc(26)
        if ema12 is None or ema26 is None:
            return None, None
        macd = ema12 - ema26
        signal = self.ema_calc(9) if len(self.macd_hist) >= 9 else None
        return macd, signal

    def bollinger_bands(self, period=20):
        if len(self.prices) < period:
            return None, None
        sma = self.sma(period)
        std = math.sqrt(sum((p - sma) ** 2 for p in self.prices[-period:]) / period)
        upper = sma + 2 * std
        lower = sma - 2 * std
        return upper, lower


    def evaluate(self, data_point):
        try:
            price = data_point['price']
            # Vérification fiabilité : ignorer tick si prix None, négatif ou aberrant
            if price is None or not isinstance(price, (int, float)) or price <= 0 or price > 1e9:
                self.logger.warning(f"[DATA] Tick ignoré : prix invalide ({price})")
                return 'hold'
            action = 'hold'
            # Optimisation : ne recalculer les indicateurs que si le prix a changé
            if self.last_price is not None and price == self.last_price:
                self.logger.debug(f"[OPTIM] Prix inchangé, aucun recalcul d'indicateur pour ce tick.")
                return 'hold'
            # Sécurité : vérifie les flags de sécurité si présents dans data_point
            liquidity_ok = data_point.get('liquidity_ok', True)
            honeypot_safe = data_point.get('honeypot_safe', True)
            contract_safe = data_point.get('contract_safe', True)
            holders_ok = data_point.get('holders_ok', True)
            can_trade = liquidity_ok and honeypot_safe and contract_safe and holders_ok
            if self.mode == 'basic':
                # Gestion multi-tokens : suivi de toutes les positions ouvertes
                if not hasattr(self, 'positions'):
                    self.positions = {}  # {token_id: {'buy_price': float, 'quantity': float}}
                if not hasattr(self, 'success_count'):
                    self.success_count = 0
                if not hasattr(self, 'fail_count'):
                    self.fail_count = 0
                if not hasattr(self, 'efficiency_score'):
                    self.efficiency_score = 1.0

                token_id = data_point.get('token_id', 'default')
                price = data_point['price']
                action = 'hold'

                # Achat si pas déjà en position et sécurité OK
                if token_id not in self.positions and can_trade:
                    self.positions[token_id] = {'buy_price': price, 'quantity': 1}
                    self.balance -= price
                    action = f'buy {token_id}'
                # Analyse continue : vente si profit optimal ou perte selon efficacité passée
                elif token_id in self.positions and can_trade:
                    buy_price = self.positions[token_id]['buy_price']
                    profit_pct = (price - buy_price) / buy_price if buy_price > 0 else 0
                    # Seuils dynamiques selon efficacité
                    profit_target = 1.0 + (self.efficiency_score - 0.5)  # x2 si efficacité 0.5, plus si >0.5
                    loss_limit = -0.2 + (0.2 * (0.5 - self.efficiency_score))  # -20% si efficacité 0.5, plus strict si <0.5
                    # Vente si profit ou perte atteint, ou prix < prix d'achat
                    if profit_pct >= profit_target or profit_pct <= loss_limit or price < buy_price:
                        self.balance += price
                        del self.positions[token_id]
                        action = f'sell {token_id} (profit {profit_pct:.2%})'
                        # Apprentissage simple
                        if profit_pct > 0:
                            self.success_count += 1
                        else:
                            self.fail_count += 1
                        total = self.success_count + self.fail_count
                        if total > 0:
                            self.efficiency_score = self.success_count / total
                else:
                    action = 'hold (blocked by security)'
                self.last_price = price

            else: # Mode avancé (indicateurs)
                # Optimisation mémoire : ne garder que les 30 derniers prix pour les indicateurs
                self.prices.append(price)
                if len(self.prices) > 30:
                    self.prices = self.prices[-30:]
                # RSI
                if self.last_price is not None:
                    change = price - self.last_price
                    self.rsi_gains.append(max(change, 0))
                    self.rsi_losses.append(abs(min(change, 0)))
                rsi = self.rsi()
                # MACD
                macd, signal = self.macd()
                if macd is not None:
                    self.macd_hist.append(macd)
                # Bollinger Bands
                upper, lower = self.bollinger_bands()
                # SMA/EMA
                sma20 = self.sma(20)
                ema20 = self.ema_calc(20)

                # Logique d'achat/vente basée sur les indicateurs
                if self.position == 0:
                    # Conditions d'achat
                    if rsi is not None and rsi < 30:
                        self.position = 1
                        self.balance -= price
                        action = 'buy (RSI)'
                    elif macd is not None and signal is not None and macd > signal:
                        self.position = 1
                        self.balance -= price
                        action = 'buy (MACD)'
                    elif sma20 is not None and price > sma20:
                        self.position = 1
                        self.balance -= price
                        action = 'buy (SMA)'
                    elif ema20 is not None and price > ema20:
                        self.position = 1
                        self.balance -= price
                        action = 'buy (EMA)'
                    elif upper is not None and price < lower:
                        self.position = 1
                        self.balance -= price
                        action = 'buy (Bollinger)'
                else:
                    # Conditions de vente
                    if rsi is not None and rsi > 70:
                        self.position = 0
                        self.balance += price
                        action = 'sell (RSI)'
                    elif macd is not None and signal is not None and macd < signal:
                        self.position = 0
                        self.balance += price
                        action = 'sell (MACD)'
                    elif sma20 is not None and price < sma20:
                        self.position = 0
                        self.balance += price
                        action = 'sell (SMA)'
                    elif ema20 is not None and price < ema20:
                        self.position = 0
                        self.balance += price
                        action = 'sell (EMA)'
                    elif upper is not None and price > upper:
                        self.position = 0
                        self.balance += price
                        action = 'sell (Bollinger)'
                self.last_price = price

            return action

        except Exception as e:
            # Log l'erreur et retourne 'error' pour ce tick
            self.logger.error(f"[Backtesting][Error] {e}")
            return 'error'

    def get_performance(self):
        # Le backtesting permet d'optimiser la stratégie avant d'investir en réel.
        # Il aide à maximiser les profits et à limiter les pertes en testant sur des données historiques.
        # Les résultats ne garantissent pas un gain futur, mais réduisent les risques liés à une mauvaise stratégie.
        if not self.results:
            return {}
        start_balance = self.results[0]['balance']
        end_balance = self.results[-1]['balance']
        profit = end_balance - start_balance
        # Ajout du score d'efficacité si disponible
        efficiency_score = getattr(self.strategy, 'efficiency_score', None)
        return {
            'start_balance': start_balance,
            'end_balance': end_balance,
            'profit': profit,
            'efficiency_score': efficiency_score
        }
