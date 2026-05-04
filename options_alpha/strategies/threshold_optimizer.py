import numpy as np
import warnings

class ThresholdOptimizer:
    """Простой оптимизатор порога, выбирающий порог максимизирующий Sharpe/EV.
    """

    def __init__(self, grid_start=0.45, grid_stop=0.90, grid_step=0.01):
        self.threshold_grid = np.arange(grid_start, grid_stop, grid_step)

    def _score(self, threshold: float, probs: np.ndarray, pnl_proxy: np.ndarray) -> float:
        """Вычисляет показатель Sharpe для данного порога.
        Предполагается, что сигнал положителен, если prob>threshold.
        """
        signals = np.where(probs > threshold, 1, -1)
        # Эффективные прибыли по сигналу
        pnl = signals * pnl_proxy
        mean_pnl = np.mean(pnl)
        std_pnl = np.std(pnl) if np.std(pnl) != 0 else 1e-9
        sharpe = mean_pnl / std_pnl
        return sharpe

    def fit(self, probs: np.ndarray, labels: np.ndarray, pnl_proxy: np.ndarray) -> float:
        """Ищет порог, максимизирующий Sharpe с учётом pnl_proxy.
        labels не используется в настоящей реализации.
        """
        best_thr = None
        best_score = -np.inf
        for thr in self.threshold_grid:
            try:
                score = self._score(thr, probs, pnl_proxy)
            except Exception:
                score = -np.inf
            if score > best_score:
                best_score = score
                best_thr = thr
        return float(best_thr) if best_thr is not None else float(0.5)
