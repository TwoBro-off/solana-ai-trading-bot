"""
Module: grid_search_optimizer.py
Description: Automated multi-parameter backtesting (grid search, auto-optimization) for AlphaStriker strategies.
"""
import itertools
import random
import csv
import copy
from backtesting.backtesting_engine import BacktestingEngine
from typing import Dict, Any, List, Callable, Optional, Union
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer, Categorical
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False

class GridSearchOptimizer:
    def __init__(self, strategy_class: Callable, param_grid: Dict[str, List[Any]],
                 backtest_config: Dict[str, Any],
                blockchain: str = "solana",
                 auto_optimize: bool = True,
                 early_stop_loss: Optional[float] = -0.5,
                 search_mode: str = "grid",
                 n_iter: int = 50,
                 monitor_callback: Optional[Callable[[int, Dict[str, Any]], None]] = None,
                 multi_metric: Union[str, List[str]] = "total_profit",
                 global_patience: int = 20,
                 export_csv_path: Optional[str] = None,
                 export_html_path: Optional[str] = None):
        """
        :param strategy_class: Classe de stratégie à optimiser
        :param param_grid: Dictionnaire {param: [valeurs]}
        :param backtest_config: Config du backtest (symboles, période, etc.)
        :param auto_optimize: Active l'auto-optimisation (zoom adaptatif)
        :param early_stop_loss: Arrêt anticipé si perte < ce seuil (ex: -0.5 = -50%)
        :param search_mode: "grid" ou "random"
        :param n_iter: Nombre d'itérations pour le random search
        :param monitor_callback: Fonction appelée à chaque essai (pour logs/monitoring)
        :param multi_metric: Critère(s) d'optimisation (str ou liste de str)
        :param global_patience: Arrêt si pas de progrès après X essais
        :param export_csv_path: Chemin d'export CSV (optionnel)
        """
        self.strategy_class = strategy_class
        self.blockchain = blockchain  # Ajout pour multi-blockchain
        self.param_grid = param_grid
        self.backtest_config = backtest_config
        self.auto_optimize = auto_optimize
        self.early_stop_loss = early_stop_loss
        self.search_mode = search_mode
        self.n_iter = n_iter
        self.monitor_callback = monitor_callback
        self.multi_metric = multi_metric if isinstance(multi_metric, list) else [multi_metric]
        self.global_patience = global_patience
        self.export_csv_path = export_csv_path
        self.export_html_path = export_html_path

    def run(self) -> List[Dict[str, Any]]:
        """
        Lance le grid search, random search, bayesian search (si dispo), et auto-optimisation si activée.
        Retourne une liste de résultats détaillés.
        """
        if self.search_mode == "random":
            results = self._random_search(self.param_grid, self.n_iter)
        elif self.search_mode == "bayesian" and SKOPT_AVAILABLE:
            results = self._bayesian_search(self.param_grid, self.n_iter)
        else:
            results = self._grid_search(self.param_grid)
        if self.auto_optimize and results:
            best = results[0]['params']
            refined_grid = self._refine_grid(best)
            if refined_grid:
                if self.search_mode == "random":
                    refined_results = self._random_search(refined_grid, max(10, self.n_iter // 3))
                elif self.search_mode == "bayesian" and SKOPT_AVAILABLE:
                    refined_results = self._bayesian_search(refined_grid, max(10, self.n_iter // 3))
                else:
                    refined_results = self._grid_search(refined_grid)
                results += refined_results
                results = self._sort_results(results)
        if self.export_csv_path:
            self._export_csv(results)
        if self.export_html_path:
            self._export_html(results)
        return results
    def _bayesian_search(self, param_grid: Dict[str, List[Any]], n_iter: int) -> List[Dict[str, Any]]:
        if not SKOPT_AVAILABLE:
            raise ImportError("scikit-optimize (skopt) n'est pas installé")
        # Construction de l'espace de recherche
        space = []
        keys = list(param_grid.keys())
        for k in keys:
            vals = param_grid[k]
            if all(isinstance(v, int) for v in vals):
                space.append(Integer(min(vals), max(vals), name=k))
            elif all(isinstance(v, float) for v in vals):
                space.append(Real(min(vals), max(vals), name=k))
            else:
                space.append(Categorical(vals, name=k))

        results = []
        tried = set()
        no_improve = 0
        best_score = None

        def objective(x):
            params = dict(zip(keys, x))
            frozen = tuple(sorted(params.items()))
            if frozen in tried:
                return 1e6  # Penalise déjà testé
            tried.add(frozen)
            res = self._run_one(params)
            if res:
                results.append(res)
                score = -res['performance'].get(self.multi_metric[0], 0)
                nonlocal best_score, no_improve
                if best_score is None or score < best_score:
                    best_score = score
                    no_improve = 0
                else:
                    no_improve += 1
                if self.monitor_callback:
                    self.monitor_callback(len(results), res)
                if self.global_patience and no_improve >= self.global_patience:
                    raise StopIteration("Arrêt anticipé bayésien")
                return score
            return 1e6

        try:
            gp_minimize(objective, space, n_calls=n_iter, random_state=42, verbose=False)
        except StopIteration:
            pass
        return self._sort_results(results)
    def _export_html(self, results: List[Dict[str, Any]]):
        if not results or not self.export_html_path:
            return
        html = ["<html><head><meta charset='utf-8'><title>Résultats Backtesting</title></head><body>"]
        html.append("<h2>Résultats du backtesting multi-paramètres</h2>")
        html.append("<table border='1' cellpadding='4' style='border-collapse:collapse;'>")
        header = list(results[0]['params'].keys()) + list(results[0]['performance'].keys())
        html.append("<tr>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>")
        for r in results:
            row = list(r['params'].values()) + list(r['performance'].values())
            html.append("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>")
        html.append("</table></body></html>")
        with open(self.export_html_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(html))

    def _sort_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Tri multi-métrique (par défaut: total_profit décroissant)
        def sort_key(r):
            return tuple(-r['performance'].get(m, 0) for m in self.multi_metric)
        return sorted(results, key=sort_key)

    def _grid_search(self, param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        results = []
        no_improve = 0
        best_score = None
        for i, combo in enumerate(itertools.product(*values)):
            params = dict(zip(keys, combo))
            res = self._run_one(params)
            if res:
                results.append(res)
                score = res['performance'].get(self.multi_metric[0], 0)
                if best_score is None or score > best_score:
                    best_score = score
                    no_improve = 0
                else:
                    no_improve += 1
                if self.monitor_callback:
                    self.monitor_callback(i, res)
                if self.global_patience and no_improve >= self.global_patience:
                    break
        return self._sort_results(results)

    def _random_search(self, param_grid: Dict[str, List[Any]], n_iter: int) -> List[Dict[str, Any]]:
        keys = list(param_grid.keys())
        results = []
        no_improve = 0
        best_score = None
        for i in range(n_iter):
            combo = [random.choice(param_grid[k]) for k in keys]
            params = dict(zip(keys, combo))
            res = self._run_one(params)
            if res:
                results.append(res)
                score = res['performance'].get(self.multi_metric[0], 0)
                if best_score is None or score > best_score:
                    best_score = score
                    no_improve = 0
                else:
                    no_improve += 1
                if self.monitor_callback:
                    self.monitor_callback(i, res)
                if self.global_patience and no_improve >= self.global_patience:
                    break
        return self._sort_results(results)

    def _run_one(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        strategy = self.strategy_class(**params)
        engine = BacktestingEngine(strategy=strategy, **self.backtest_config)
        performance, trades = engine.run(early_stop=self.early_stop_loss)
        if self.early_stop_loss is not None and performance.get('total_profit', 0) < self.early_stop_loss:
            return None
        return {
            'params': copy.deepcopy(params),
            'performance': {
                'total_profit': performance.get('total_profit'),
                'max_drawdown': performance.get('max_drawdown'),
                'win_rate': performance.get('win_rate'),
                'sharpe_ratio': performance.get('sharpe_ratio'),
                'trades_count': len(trades),
            },
            'trades': trades
        }

    def _refine_grid(self, best_params: Dict[str, Any]) -> Optional[Dict[str, List[Any]]]:
        refined = {}
        for k, v in best_params.items():
            if isinstance(v, (int, float)):
                step = abs(v) * 0.1 if v != 0 else 1
                refined[k] = [v - step, v, v + step]
            else:
                refined[k] = [v]
        if all(len(vals) == 1 for vals in refined.values()):
            return None
        return refined

    def _export_csv(self, results: List[Dict[str, Any]]):
        if not results or not self.export_csv_path:
            return
        with open(self.export_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = list(results[0]['params'].keys()) + list(results[0]['performance'].keys())
            writer.writerow(header)
            for r in results:
                row = list(r['params'].values()) + list(r['performance'].values())
                writer.writerow(row)

    @staticmethod
    def best_params(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {}
        return results[0]['params']
