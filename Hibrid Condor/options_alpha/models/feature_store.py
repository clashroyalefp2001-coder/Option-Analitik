# models/feature_store.py
"""Формирование признаков из pricing и данных."""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from pricing.binomial import price_american
from config import DEFAULT_SIGMA, DEFAULT_R, DEFAULT_DIVIDEND


def _safe_float(x, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _compute_iv_rank(group: pd.Series, window: int = 252) -> pd.Series:
    """IV rank в скользящем окне: позиция текущей IV в её историческом диапазоне.

    Если истории недостаточно — возвращает 0.5 (нейтральное значение).
    """
    rank = pd.Series(0.5, index=group.index, dtype=float)
    for i in range(len(group)):
        start = max(0, i - window + 1)
        sub = group.iloc[start : i + 1]
        if len(sub) < 5:
            continue
        lo, hi = sub.min(), sub.max()
        if hi - lo < 1e-9:
            continue
        rank.iloc[i] = float((group.iloc[i] - lo) / (hi - lo))
    return rank


def build_features(
    underlying: pd.DataFrame,
    options: pd.DataFrame,
    sigma: float = DEFAULT_SIGMA,
    risk_free_rate: float = DEFAULT_R,
    dividend: float = DEFAULT_DIVIDEND,
) -> pd.DataFrame:
    """Создаёт DataFrame с признаками для каждой опционной серии.

    Главные правки относительно прошлой версии:
    - T рассчитывается из реального days_to_expiry (а не хардкодится 0.5)
    - IV rank считается через скользящее окно по mid-price, а не хардкодится
    - Нет print-спама в продакшене (только при пустых результатах)
    """
    if options is None or options.empty:
        return pd.DataFrame()

    rows = []
    for _, row in options.iterrows():
        underlying_price = _safe_float(row.get("underlying_price", row.get("price")))
        strike = _safe_float(row.get("strike"))
        bid_val = _safe_float(row.get("bid"))
        ask_val = _safe_float(row.get("ask"))
        option_type = str(row.get("type", "call")).lower()

        if underlying_price <= 0 or strike <= 0:
            continue
        if bid_val <= 0 or ask_val <= 0 or ask_val < bid_val:
            continue

        mid = (bid_val + ask_val) / 2.0
        if mid <= 0:
            continue

        # Реальный days_to_expiry
        try:
            expiry_date = pd.to_datetime(row.get("expiry"))
            obs_date = pd.to_datetime(row.get("date"))
            if pd.isna(expiry_date) or pd.isna(obs_date):
                days_to_expiry = 30
            else:
                days_to_expiry = max(1, (expiry_date - obs_date).days)
        except Exception:
            days_to_expiry = 30

        T = days_to_expiry / 365.0  # ← главный фикс: правильный T, а не 0.5

        fair = price_american(
            S=underlying_price,
            K=strike,
            T=T,
            r=risk_free_rate,
            sigma=sigma,
            dividend=dividend,
            option_type=option_type,
        )

        mispricing = fair["fair_value"] - mid
        # Edge с учётом стороны сделки и спреда
        if fair["fair_value"] > ask_val:
            # Покупаем по ask, продаём по fair
            edge = fair["fair_value"] - ask_val
            side = "buy"
        elif fair["fair_value"] < bid_val:
            # Шортим по bid, откупаем по fair
            edge = bid_val - fair["fair_value"]
            side = "sell"
        else:
            edge = 0.0
            side = "neutral"

        try:
            moneyness = math.log(underlying_price / strike)
        except ValueError:
            moneyness = 0.0

        bid_ask_spread_pct = (ask_val - bid_val) / mid if mid > 0 else 0.0

        rows.append(
            {
                "date": row.get("date"),
                "expiry": row.get("expiry"),
                "strike": strike,
                "type": option_type,
                "underlying_price": underlying_price,
                "bid": bid_val,
                "ask": ask_val,
                "mid": mid,
                "fair_value": fair["fair_value"],
                "mispricing": mispricing,
                "predicted_edge": edge,  # будет перезаписан моделью при инференсе
                "side": side,
                "delta": fair["delta"],
                "gamma": fair["gamma"],
                "vega": fair["vega"],
                "theta": fair["theta"],
                "rho": fair["rho"],
                "early_exercise_premium": fair["early_exercise_premium"],
                "moneyness": moneyness,
                "days_to_expiry": days_to_expiry,
                "bid_ask_spread_pct": bid_ask_spread_pct,
                "open_interest": _safe_float(row.get("open_interest", 0)),
                "daily_volume": _safe_float(row.get("volume", 0)),
                # Плейсхолдеры — заполняются на этапе обучения / инференса
                "iv_rank": 0.5,
                "iv_skew": 0.0,
                "iv_curvature": 0.0,
                "signal_confidence": 0.5,
                "signal_regime": "normal",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Считаем IV rank в скользящем окне по mid (proxy для IV)
    if "mid" in df.columns and len(df) >= 5:
        df["iv_rank"] = _compute_iv_rank(df["mid"])

    return df
