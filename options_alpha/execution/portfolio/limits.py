# execution/portfolio/limits.py
"""Portfolio-level risk limits."""


def check_greek_limits(portfolio_greeks, limits):
    """
    portfolio_greeks: dict with keys delta, gamma, vega (total portfolio)
    limits: dict with max_delta_pct, max_gamma_pct, max_vega_pct of capital
    Returns: (bool ok, str reason)
    """
    for greek, limit_key in [("delta", "max_delta_pct"), ("gamma", "max_gamma_pct"), ("vega", "max_vega_pct")]:
        if greek in portfolio_greeks and limit_key in limits:
            if abs(portfolio_greeks[greek]) > limits[limit_key]:
                return False, f"{greek} limit breached: {portfolio_greeks[greek]:.4f} > {limits[limit_key]:.4f}"
    return True, "OK"


def check_concentration(position_size, total_capital, max_pct=0.05):
    """No single position >5% of capital by default."""
    if position_size > total_capital * max_pct:
        return False, f"Concentration limit: {position_size:.2f} > {total_capital * max_pct:.2f}"
    return True, "OK"


def check_daily_loss(capital_before, capital_after, max_loss_pct=0.02):
    """Daily loss limit (2% default)."""
    loss = capital_before - capital_after
    if loss > capital_before * max_loss_pct:
        return False, f"Daily loss limit: {loss:.2f} > {capital_before * max_loss_pct:.2f}"
    return True, "OK"
