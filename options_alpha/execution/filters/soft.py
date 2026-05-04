# execution/filters/soft.py
def apply_soft_filters(df, risk_cfg):
    """Сортировка и мягкая фильтрация по уверенности и edge."""
    if df.empty: return df
    res = df.copy()
    
    min_edge = risk_cfg.get("min_edge", 0.0)
    res = res[res["predicted_edge"] > min_edge]
    
    # Сортируем по убыванию edge
    res = res.sort_values("predicted_edge", ascending=False)
    
    return res
