import numpy as np
import pandas as pd

def build_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Применяет набор трансформаций к сырым рыночным данным (БА).
    Гарантирует отсутствие ликажа (leakage).
    """
    df = df.copy()
    
    date_col = next((c for c in df.columns if c.lower() in ["timestamp", "date", "datetime"]), "timestamp")
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).reset_index(drop=True)

    for h in [1, 3, 5, 10]:
        df[f"ret_{h}"] = df["close"].pct_change(h)
    
    df["mom_5"] = df["close"] / df["close"].shift(5) - 1
    df["mom_20"] = df["close"] / df["close"].shift(20) - 1

    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["ma_dist"] = (df["close"] - df["ma_20"]) / df["ma_20"]
    
    def _get_slope(x):
        if len(x) < 10: return np.nan
        return (x.iloc[-1] - x.iloc[0]) / 10
    
    df["trend_slope_10"] = df["close"].rolling(10).apply(_get_slope, raw=False)

    rets = df["close"].pct_change()
    for h in [5, 10, 20]:
        df[f"rv_{h}"] = rets.rolling(h).std() * np.sqrt(252)
            
    prev_close = df["close"].shift(1)
    tr = np.maximum(df["high"] - df["low"], 
                    np.maximum(np.abs(df["high"] - prev_close), 
                               np.abs(df["low"] - prev_close)))
    df["atr_14"] = tr.rolling(14).mean()
    df["range_pct"] = (df["high"] - df["low"]) / df["close"]

    if "volume" in df.columns:
        df["volume_ma"] = df["volume"].rolling(20).mean()
        df["volume_std"] = df["volume"].rolling(20).std().replace(0, np.nan)
        df["volume_z"] = (df["volume"] - df["volume_ma"]) / df["volume_std"]
        df["volume_z"] = df["volume_z"].fillna(0)
        df = df.drop(columns=["volume_ma", "volume_std"])
        
    if "open_interest" in df.columns:
        df["oi_change"] = df["open_interest"].pct_change()
        if "volume" in df.columns:
            df["vol_oi_ratio"] = df["volume"] / df["open_interest"].replace(0, np.nan)

    df["dow"] = df[date_col].dt.dayofweek
    df["month"] = df[date_col].dt.month
    df["is_month_end"] = df[date_col].dt.is_month_end.astype(int)

    return df.dropna().reset_index(drop=True)
