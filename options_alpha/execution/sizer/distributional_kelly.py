import numpy as np
from typing import Dict, Any, List, Optional

def distributional_kelly(
    returns: np.ndarray,
    confidence: float = 0.95,
    f_grid: Optional[np.ndarray] = None,
    tail_penalty: str = "cvar"
) -> float:
    """Monte Carlo Kelly optimization with tail penalty.
    
    Maximizes expected log wealth: argmax_f E[log(1 + f * returns)]
    with optional tail penalty for risk reduction.
    """
    if f_grid is None:
        f_grid = np.linspace(0, 0.10, 100)
    
    returns = np.asarray(returns)
    if len(returns) == 0:
        return 0.0
    
    best_f = 0.0
    best_utility = -np.inf
    
    for f in f_grid:
        utilities = _compute_utility(returns, f, tail_penalty, confidence)
        if utilities["expected_utility"] > best_utility:
            best_utility = utilities["expected_utility"]
            best_f = f
    
    return float(best_f)


def _compute_utility(returns: np.ndarray, f: float, penalty: str, confidence: float) -> Dict[str, float]:
    """Compute utility with optional tail penalty."""
    wealth = 1 + f * returns
    log_wealth = np.log(np.clip(wealth, 1e-9, None))
    expected_utility = np.mean(log_wealth)
    
    if penalty == "cvar":
        var_idx = int(len(returns) * (1 - confidence))
        sorted_returns = np.sort(returns)
        cvar = np.mean(sorted_returns[:max(var_idx, 1)])
        penalty_factor = 1 - abs(cvar) / (np.std(returns) + 1e-9)
        expected_utility *= max(penalty_factor, 0.5)
    elif penalty == "gap":
        gap = np.max(returns) - np.min(returns)
        expected_utility -= 0.01 * gap
    
    return {"expected_utility": float(expected_utility)}


def _generate_synthetic_returns(win_rate: float, mean_win: float, mean_loss: float, n: int = 1000) -> np.ndarray:
    """Generate synthetic returns from Kelly stats for distributional optimization.
    
    Simulates a mix of winning and losing returns based on observed statistics.
    Returns centered on zero with appropriate scale to represent profit/loss fractions.
    """
    n_wins = int(n * win_rate)
    n_losses = n - n_wins
    
    # Generate positive returns (wins) and negative returns (losses)
    # using appropriate scale, centered around mean values
    win_returns = np.random.lognormal(np.log(mean_win + 1e-9), 0.6, n_wins) if n_wins > 0 else np.array([])
    loss_returns = -np.random.lognormal(np.log(abs(mean_loss) + 1e-9), 0.6, n_losses) if n_losses > 0 else np.array([])
    
    returns = np.concatenate([win_returns, loss_returns])
    np.random.shuffle(returns)
    return returns


def calibrate_from_trades(trades_df, pnl_column: str = "pnl") -> Dict[str, float]:
    """Calibrate Kelly from historical trade PnLs."""
    returns = trades_df[pnl_column].values
    if len(returns) == 0:
        return {"kelly_f": 0.0, "cvar_95": 0.0}
    
    cvar_95 = float(np.percentile(returns, 5))
    kelly_f = distributional_kelly(returns)
    
    return {"kelly_f": kelly_f, "cvar_95": cvar_95}
