# execution/sizer/kelly.py
import numpy as np

def fractional_kelly(
    win_rate,
    avg_win,
    avg_loss,
    budget,
    kelly_frac=0.25,
    max_fstar=0.20,
    max_position_pct=0.05,
    min_avg_loss=0.10,
    max_win_rate=0.80,
    **kwargs
):
    """
    Production-grade fractional Kelly calculation with regularization and hard risk caps.
    
    Prevents sizing explosions by capping inputs and outputs.
    """
    if avg_win <= 0:
        return 0.0

    # Regularization: Noisy distributions often show unrealistic stats
    win_rate = np.clip(win_rate, 0.05, max_win_rate)
    avg_loss = max(avg_loss, min_avg_loss)

    b = avg_win / avg_loss
    q = 1.0 - win_rate

    # f* = p - q/b
    f_star = win_rate - q / b
    
    # Cap the f_star leverage (leverage is dangerous in options)
    f_star = np.clip(f_star, 0.0, max_fstar)

    # Calculate final size relative to budget
    size = budget * f_star * kelly_frac
    
    # Final hard constraint: max % of capital allowed for single position
    size = min(size, budget * max_position_pct)

    return float(size)
