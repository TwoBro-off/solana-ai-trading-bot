"""
Module: multi_strategy_simulator.py
Description: Simulation multi-wallet et multi-stratégie en parallèle.
Chaque stratégie simule l'achat de tous les tokens non scam, sur un ou plusieurs wallets virtuels.
"""
import asyncio
from typing import List, Dict, Any, Callable
from trading.trading_strategies import STRATEGY_REGISTRY
from backtesting.backtesting_engine import BacktestingEngine

class MultiStrategySimulator:
    def __init__(self, wallets: List[str], strategies: List[str], token_list: List[Dict[str, Any]],
                 backtest_config: Dict[str, Any], blockchain: str = "solana"):
        """
        wallets: liste d'identifiants de wallets virtuels (simulation)
        strategies: liste de noms de stratégies (doivent être dans STRATEGY_REGISTRY)
        token_list: liste des tokens à simuler (tous sauf scam)
        backtest_config: config commune à tous les backtests
        """
        self.wallets = wallets
        self.blockchain = blockchain  # Ajout pour multi-blockchain
        self.strategies = strategies
        self.token_list = token_list
        self.backtest_config = backtest_config

    async def run_all(self) -> Dict[str, Any]:
        """
        Lance la simulation pour chaque (wallet, stratégie) en parallèle.
        Retourne un dict { (wallet, stratégie): résultats }
        """
        tasks = []
        for wallet in self.wallets:
            for strat_name in self.strategies:
                tasks.append(self._run_one(wallet, strat_name))
        results = await asyncio.gather(*tasks)
        return {f"{r['wallet']}|{r['strategy']}": r for r in results}

    async def _run_one(self, wallet: str, strat_name: str) -> Dict[str, Any]:
        strategy_class = STRATEGY_REGISTRY[strat_name]
        # On simule l'achat de tous les tokens non scam
        tokens_to_buy = [t for t in self.token_list if not t.get('is_scam', False)]
        engine = BacktestingEngine(strategy=strategy_class(),
                                   tokens=tokens_to_buy,
                                   wallet=wallet,
                                   **self.backtest_config)
        performance, trades = await engine.run_async()
        return {
            'wallet': wallet,
            'strategy': strat_name,
            'performance': performance,
            'trades': trades
        }
