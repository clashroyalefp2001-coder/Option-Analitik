import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional

class ThresholdEngine:
    def __init__(self, base_percentile: float = 80.0, min_history: int = 50, default_threshold: float = 0.60):
        self.base_percentile = base_percentile
        self.min_history = min_history
        self.default_threshold = default_threshold
        
    def compute_dynamic_threshold(
        self,
        probs_history: List[float],
        recent_hit_rate: float = 0.5,
        market_regime: str = "mean-revert"
    ) -> float:
        if len(probs_history) < self.min_history:
            return self.default_threshold
            
        base_threshold = float(np.percentile(probs_history, self.base_percentile))
        
        if recent_hit_rate > 0.6:
            base_threshold *= 0.95
        elif recent_hit_rate < 0.4:
            base_threshold *= 1.05
            
        if market_regime == "panic":
            base_threshold *= 1.1
        elif market_regime == "compression":
            base_threshold *= 0.9
            
        return float(np.clip(base_threshold, 0.4, 0.95))
