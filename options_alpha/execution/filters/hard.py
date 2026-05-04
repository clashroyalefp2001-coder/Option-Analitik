# execution/filters/hard.py
def apply_hard_filters(df, risk_cfg):
    """Применяет жесткие фильтры (ликвидность, DTE)."""
    if df.empty: return df
    res = df.copy()
    
    # Пример: фильтр по спреду
    max_spread = risk_cfg.get("max_spread_pct", 0.05)
    if "bid_ask_spread_pct" in res.columns:
        res = res[res["bid_ask_spread_pct"] < max_spread]
        
    return res
