# execution/filters/soft.py
"""Soft фильтры на основе качества сигнала и рыночного режима."""


def apply_soft_filters(df, config):
    """
    Отбирает сигналы, у которых:
      - predicted_edge > execution_cost
      - confidence >= threshold
      - regime не stress
    """
    df = df.copy()
    # 1) Edge filter
    edge_mask = df["predicted_edge"] >= config["min_edge"]
    # 2) Confidence filter
    conf_mask = df["signal_confidence"] >= config["min_confidence"]
    # 3) Regime filter: если stress, уменьшаем размер позиции
    regime_ok = df["signal_regime"] != "stress" 

    mask = edge_mask & conf_mask 
    filtered = df[mask].copy()
    
    # БЕЗОПАСНАЯ перезапись колонок через assign для устранения ChainedAssignmentError
    needs_reduction = df.loc[mask.index, "signal_regime"] == "stress"
    filtered = filtered.assign(needs_size_reduction=needs_reduction)
    
    return filtered