# execution/sizer/kelly.py
"""Position sizing based on fractional Kelly."""


def fractional_kelly(edge, win_rate, loss_rate, avg_win, avg_loss, budget, kelly_frac=0.25):
    """
    edge: expected profit per trade (can be negative)
    win_rate: probability of win
    loss_rate: probability of loss (1 - win_rate)
    avg_win: average winning trade return
    avg_loss: average losing trade return (positive number)
    budget: total capital allocated for this position
    kelly_frac: fraction of full Kelly (0.25 = 25% of Kelly)

    Returns: dollar amount to invest.
    """
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    # Full Kelly: f* = (win_rate / avg_loss) - (loss_rate / avg_win)
    # But we use edge-based: f* = edge / (avg_win**2) if edge>0 else 0
    if edge <= 0:
        return 0.0
    # Simplified: use edge as expected return, and assume risk (variance) as avg_loss**2
    variance = avg_loss ** 2
    if variance == 0:
        return 0.0
    full_kelly = edge / variance
    # Apply fractional Kelly
    f = full_kelly * kelly_frac
    # Cap at budget
    return min(f * budget, budget)
