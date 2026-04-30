# execution/exits/rules.py
"""Exit rules for positions."""


def should_exit(position, current, config):
    """
    position: dict with keys: entry_price, size, entry_date, side, ...
    current: dict with keys: price, date, signal (optional), tp_pct, sl_pct
    config: dict with time_exit_max_days, tp_pct, sl_pct

    Returns: "close" / "hold"
    """
    # 1) Time exit
    from datetime import datetime
    if "entry_date" in position:
        days_held = (current["date"] - position["entry_date"]).days
        if days_held >= config.get("time_exit_max_days", 30):
            return "close"
    # 2) Take profit
    if position["side"] == "long":
        if current["price"] >= position["entry_price"] * (1 + config.get("tp_pct", 0.05)):
            return "close"
        if current["price"] <= position["entry_price"] * (1 - config.get("sl_pct", 0.02)):
            return "close"
    else:
        if current["price"] <= position["entry_price"] * (1 - config.get("tp_pct", 0.05)):
            return "close"
        if current["price"] >= position["entry_price"] * (1 + config.get("sl_pct", 0.02)):
            return "close"
    # 3) Signal flip exit (if signal exists and disagrees with position side)
    if "signal" in current:
        if position["side"] == "long" and current["signal"] == "SELL":
            return "close"
        if position["side"] == "short" and current["signal"] == "BUY":
            return "close"
    return "hold"
