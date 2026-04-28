# execution/filters/hard.py
"""Hard фильтры ликвидности и торговых ограничений."""


def apply_hard_filters(df, config):
    """
    Отбрасывает ряды, нарушающие базовые лимиты.
    Ожидает колонки: bid_ask_spread_pct, open_interest, daily_volume, days_to_expiry.
    """
    df = df.copy()
    mask = (
        (df["bid_ask_spread_pct"] <= config["max_spread_pct"]) &
        (df["open_interest"] >= config["min_open_interest"]) &
        (df["daily_volume"] >= config["min_daily_volume"]) &
        (df["days_to_expiry"] >= config["min_days_to_expiry"])
    )
    return df[mask].copy()
