import numpy as np
from typing import Dict, Tuple

def bayesian_adjust(
    sample_stat: float,
    sample_size: int,
    prior_mean: float = 0.55,
    prior_var: float = 0.10,
    min_samples: int = 30
) -> Tuple[float, float]:
    """Apply Bayesian shrinkage to sample statistics.
    
    Returns (adjusted_stat, uncertainty) where uncertainty is posterior variance.
    Uses conjugate normal-normal model.
    """
    if sample_size < min_samples:
        # Heavy shrinkage toward prior
        weight = sample_size / min_samples
        adjusted = weight * sample_stat + (1 - weight) * prior_mean
        uncertainty = prior_var
    else:
        # Standard Bayesian update
        sample_var = _estimate_sample_variance(sample_stat, sample_size)
        posterior_precision = 1/prior_var + sample_size/sample_var
        posterior_mean = (prior_mean/prior_var + sample_size*sample_stat/sample_var) / posterior_precision
        posterior_var = 1 / posterior_precision
        
        adjusted = posterior_mean
        uncertainty = posterior_var
    
    return adjusted, uncertainty


def _estimate_sample_variance(stat: float, n: int) -> float:
    """Estimate variance of sample statistic."""
    # Assume binomial-like variance for win_rate
    if 0 <= stat <= 1:
        return stat * (1 - stat) / max(n, 1)
    else:
        return 0.1 / max(n, 1)


def adjust_stats_with_bayesian(
    stats: Dict[str, any],
    sample_key: str = "sample_size",
    stat_keys: list = ["win_rate", "avg_win", "avg_loss"]
) -> Dict[str, any]:
    """Apply Bayesian adjustment to multiple stats."""
    adjusted = {}
    sample_size = stats.get(sample_key, 0)
    
    for key in stat_keys:
        if key in stats:
            val, _ = bayesian_adjust(
                stats[key],
                sample_size,
                prior_mean=0.55 if key == "win_rate" else 0.02,
                prior_var=0.05 if key == "win_rate" else 0.01
            )
            adjusted[key] = val
        else:
            adjusted[key] = stats.get(key, 0.0)
    
    adjusted[sample_key] = sample_size
    return adjusted