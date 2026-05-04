import pandas as pd
import numpy as np
from typing import List, Dict, Any

class EVRanker:
    """Utility class for evaluating and ranking candidate option strategies
    based on expected value (EV) and risk metrics.
    """

    def __init__(self, pnl_proxy: pd.Series | List[float]):
        self.pnl_proxy = np.array(pnl_proxy)

    def compute_expected_payoff(self, candidate: Dict[str, Any]) -> float:
        """Estimate expected payoff using candidate's implied payout.
        Placeholder: use average pnl_proxy as proxy.
        """
        return float(np.mean(self.pnl_proxy))

    def compute_max_loss(self, candidate: Dict[str, Any]) -> float:
        """Maximum possible loss for the candidate.
        Placeholder: use negative of min pnl_proxy.
        """
        return float(-np.min(self.pnl_proxy))

    def compute_margin_efficiency(self, candidate: Dict[str, Any]) -> float:
        """Margin efficiency = expected payoff / required margin.
        Placeholder: assume margin = 1.0 for all candidates.
        """
        exp = self.compute_expected_payoff(candidate)
        margin = candidate.get("margin_required", 1.0)
        return exp / margin if margin != 0 else 0.0

    def compute_tail_penalty(self, candidate: Dict[str, Any], tail_quantile: float = 0.05) -> float:
        """Penalty based on tail losses (e.g., CVaR at tail_quantile).
        Placeholder: use quantile of pnl_proxy.
        """
        tail_loss = np.percentile(self.pnl_proxy, tail_quantile * 100)
        return float(abs(tail_loss))

    def rank_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank candidates by a composite score.
        Score = EV * margin_efficiency - tail_penalty
        Returns candidates sorted descending by score.
        """
        scored = []
        for cand in candidates:
            ev = self.compute_expected_payoff(cand)
            me = self.compute_margin_efficiency(cand)
            tp = self.compute_tail_penalty(cand)
            score = ev * me - tp
            scored.append((score, cand))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [cand for _, cand in scored]
