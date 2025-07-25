import numpy as np
import time

class VolatilityAnalyzer:
    def __init__(self, window_size=10, min_volume=5):
        self.price_history = {}
        self.volume_history = {}
        self.last_update = {}
        self.window_size = window_size
        self.min_volume = min_volume

    def update(self, token, price, volume):
        # Historique des prix
        if token not in self.price_history:
            self.price_history[token] = []
        self.price_history[token].append(price)
        self.price_history[token] = self.price_history[token][-self.window_size:]
        # Historique des volumes
        if token not in self.volume_history:
            self.volume_history[token] = []
        self.volume_history[token].append(volume)
        self.volume_history[token] = self.volume_history[token][-self.window_size:]
        # Timestamp
        self.last_update[token] = time.time()

    def get_volatility(self, token):
        prices = self.price_history.get(token, [])
        if len(prices) < 2:
            return 0
        return float(np.std(prices) / np.mean(prices)) if np.mean(prices) > 0 else 0

    def get_avg_volume(self, token):
        volumes = self.volume_history.get(token, [])
        if not volumes:
            return 0
        return float(np.mean(volumes))

    def is_high_volatility(self, token, vol_threshold=0.05, volume_threshold=None):
        if volume_threshold is None:
            volume_threshold = self.min_volume
        return self.get_volatility(token) > vol_threshold and self.get_avg_volume(token) > volume_threshold

    def get_top_tokens(self, top_n=5, vol_threshold=0.05):
        scores = {
            t: self.get_volatility(t) for t in self.price_history
            if self.is_high_volatility(t, vol_threshold)
        }
        return sorted(scores, key=scores.get, reverse=True)[:top_n]
