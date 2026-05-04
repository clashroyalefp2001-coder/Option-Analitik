from __future__ import annotations
import math
import numpy as np
import pandas as pd
from typing import Any, List, Optional
from datetime import datetime

from pricing.binomial import price_american, calculate_iv
from config import DEFAULT_SIGMA, DEFAULT_R, DEFAULT_DIVIDEND


def _safe_float(x, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default

def _get_col(row: Any, aliases: List[str], default: Any = None) -> Any:
    row_keys = {str(k).lower(): k for k in row.keys()}
    for a in aliases:
        a_low = a.lower()
        if a_low in row_keys:
            return row[row_keys[a_low]]
    return default

def _compute_iv_rank_vec(group: pd.Series, window: int = 252) -> pd.Series:
    if len(group) < 10:
        return pd.Series(0.5, index=group.index)
    rolling_min = group.rolling(window, min_periods=10).min().shift(1)
    rolling_max = group.rolling(window, min_periods=10).max().shift(1)
    rank = (group - rolling_min) / (rolling_max - rolling_min)
    return rank.fillna(0.5).clip(0, 1)

def _compute_underlying_features(underlying: pd.DataFrame) -> pd.DataFrame:
    if underlying is None or underlying.empty:
        return pd.DataFrame()
    
    df = underlying.copy()
    date_col = next((c for c in df.columns if c.lower() == "date"), None)
    if date_col:
        df["date"] = pd.to_datetime(df[date_col])
        df = df.sort_values("date")
    
    price_col = next((c for c in df.columns if c.lower() in ["close", "price", "spot", "last"]), None)
    if not price_col:
        return pd.DataFrame()

    df["u_ret_1d"] = df[price_col].pct_change(1)
    df["u_ret_5d"] = df[price_col].pct_change(5)
    df["u_ret_20d"] = df[price_col].pct_change(20)
    df["u_rv_20d"] = df["u_ret_1d"].rolling(20).std() * math.sqrt(252)
    df["u_ema_20"] = df[price_col].ewm(span=20).mean()
    df["u_dist_ema_20"] = (df[price_col] / df["u_ema_20"]) - 1.0
    return df

def build_features(
    underlying: pd.DataFrame,
    options: pd.DataFrame,
    sigma: float = DEFAULT_SIGMA,
    risk_free_rate: float = DEFAULT_R,
    dividend: float = DEFAULT_DIVIDEND,
) -> pd.DataFrame:
    if options is None or options.empty:
        return pd.DataFrame()

    u_feats = _compute_underlying_features(underlying)
    u_price_col = "close" if "close" in u_feats.columns else ("price" if "price" in u_feats.columns else None)
    
    rows = []
    opts_sorted = options.copy()
    
    date_col = next((c for c in opts_sorted.columns if c.lower() == "date"), None)
    if date_col:
        opts_sorted[date_col] = pd.to_datetime(opts_sorted[date_col], errors="coerce")
        opts_sorted = opts_sorted.dropna(subset=[date_col]).sort_values(date_col)
        
        if u_price_col and "underlying_price" not in [c.lower() for c in opts_sorted.columns]:
            u_feats_sorted = u_feats.sort_values("date")
            opts_sorted = pd.merge_asof(
                opts_sorted,
                u_feats_sorted[["date", u_price_col]].rename(columns={u_price_col: "underlying_price"}),
                on="date",
                direction="backward"
            )
    
    skipped_count = 0
    for _, row in opts_sorted.iterrows():
        underlying_price = _safe_float(_get_col(row, ["underlying_price", "price", "spot", "base_price"]))
        strike = _safe_float(_get_col(row, ["strike", "k"]))
        bid_val = _safe_float(_get_col(row, ["bid", "b"]))
        ask_val = _safe_float(_get_col(row, ["ask", "a"]))
        theor_val = _safe_float(_get_col(row, ["theoretical_price", "theor_price", "fair"]))
        
        option_type = str(_get_col(row, ["type", "option_type", "cp"], "call")).lower()

        if underlying_price <= 0 or strike <= 0:
            skipped_count += 1
            continue

        has_quotes = bid_val > 0 and ask_val > 0 and ask_val >= bid_val
        
        if has_quotes:
            mid = (bid_val + ask_val) / 2.0
        else:
            mid = _safe_float(_get_col(row, ["last", "price", "mid", "valuation"])) or theor_val
            
        if mid <= 0: 
            skipped_count += 1
            continue

        try:
            obs_date = pd.to_datetime(_get_col(row, ["date"])) if date_col else datetime.now()
            expiry_date = pd.to_datetime(_get_col(row, ["expiry", "expiration"]))
            days_to_expiry = max(1, (expiry_date - obs_date).days) if not (pd.isna(expiry_date) or pd.isna(obs_date)) else 30
        except: 
            days_to_expiry = 30
        T = days_to_expiry / 365.0

        market_iv = calculate_iv(mid, underlying_price, strike, T, risk_free_rate, dividend, option_type)
        fair = price_american(S=underlying_price, K=strike, T=T, r=risk_free_rate, sigma=sigma, dividend=dividend, option_type=option_type)

        mispricing = fair["fair_value"] - mid
        edge = 0.0
        side = "neutral"
        if has_quotes:
            if fair["fair_value"] > ask_val:
                edge = fair["fair_value"] - ask_val
                side = "buy"
            elif fair["fair_value"] < bid_val:
                edge = bid_val - fair["fair_value"]
                side = "sell"
        else:
            edge = abs(mispricing)
            side = "buy" if mispricing > 0 else "sell"

        rows.append({
            "date": obs_date,
            "expiry": expiry_date,
            "strike": strike,
            "type": option_type,
            "mid": mid,
            "iv": market_iv,
            "delta": fair["delta"],
            "gamma": fair["gamma"],
            "vega": fair["vega"],
            "theta": fair["theta"],
            "moneyness": math.log(underlying_price / strike) if strike > 0 else 0,
            "days_to_expiry": days_to_expiry,
            "bid_ask_spread_pct": (ask_val - bid_val) / mid if (has_quotes and mid > 0) else 0.0,
            "predicted_edge": edge,
            "side": side,
            "underlying_price": underlying_price,
            "option_symbol": _get_col(row, ["symbol", "option_symbol", "secid"], "OPT")
        })

    if skipped_count > 0:
        import logging
        logging.getLogger("option_features").info("skipped %d rows due to missing price/strike", skipped_count)

    df = pd.DataFrame(rows)
    if df.empty: return df

    if not u_feats.empty:
        df = pd.merge(df, u_feats, on="date", how="left")
        if "u_rv_20d" in df.columns:
            df["iv_premium"] = df["iv"] / df["u_rv_20d"].replace(0, np.nan)

    def _calc_cs_features(group):
        if len(group) < 2: return group
        atm_mask = (group["moneyness"].abs() < 0.1)
        if atm_mask.any():
            atm_iv = group.loc[atm_mask, "iv"].mean()
            otm_put_mask = (group["type"] == "put") & (group["moneyness"] < -0.1)
            group["iv_skew"] = group.loc[otm_put_mask, "iv"].mean() - atm_iv if otm_put_mask.any() else 0.0
        else:
            group["iv_skew"] = 0.0
            
        st_mask = (group["days_to_expiry"] < 30)
        lt_mask = (group["days_to_expiry"] > 60)
        group["iv_ts_slope"] = group.loc[lt_mask, "iv"].mean() - group.loc[st_mask, "iv"].mean() if st_mask.any() and lt_mask.any() else 0.0
            
        return group

    if "date" in df.columns:
        df = df.groupby("date", group_keys=False).apply(_calc_cs_features)

    if "iv" in df.columns and "date" in df.columns:
        MIN_SURFACE_OPTIONS = 8
        prev_surface_iv = 0.20

        def _get_stable_surface_iv(group):
            nonlocal prev_surface_iv
            if len(group) < MIN_SURFACE_OPTIONS:
                return prev_surface_iv
            
            m_abs = group["moneyness"].abs()
            weights = np.exp(-m_abs * 10)
            valid = (group["iv"] > 0) & (group["iv"] < 5.0)
            if not valid.any() or valid.sum() < MIN_SURFACE_OPTIONS:
                return prev_surface_iv
            
            surface_iv = np.average(group.loc[valid, "iv"], weights=weights[valid])
            prev_surface_iv = surface_iv
            return surface_iv

        surface_ivs = df.groupby("date", group_keys=False).apply(_get_stable_surface_iv)
        surface_ranks = _compute_iv_rank_vec(surface_ivs)
        df["iv_rank"] = df["date"].map(surface_ranks)
    else:
        df["iv_rank"] = 0.5

    return df.fillna(0)
