# execution/filters/soft.py
"""Soft фильтры на основе качества сигнала и рыночного режима."""


def apply_soft_filters(df, config):
    """
    Отбирает сигналы, у которых:
      - predicted_edge > execution_cost (уже учтено в edge, но можно усилить порогом)
      - confidence >= threshold
      - regime не stress (или уменьшить размер позиции)
    """
    df = df.copy()
    # 1) Edge filter
    edge_mask = df["predicted_edge"] >= config["min_edge"]
    # 2) Confidence filter
    conf_mask = df["signal_confidence"] >= config["min_confidence"]
    # 3) Regime filter: если stress, уменьшаем размер позиции (обрабатывается в sizer)
    # Здесь просто оставляем метку
    regime_ok = df["signal_regime"] != "stress"  # можно оставить все, а размер поправим в sizer

    mask = edge_mask & conf_mask  # regime влияет на размер, не отбор
    filtered = df[mask].copy()
    # Добавим флаг для sizer, что нужно уменьшить размер при stress
    filtered["needs_size_reduction"] = df.loc[mask.index, "signal_regime"] == "stress"
    return filtered
