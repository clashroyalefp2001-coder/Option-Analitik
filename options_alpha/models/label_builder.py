import numpy as np
import pandas as pd

class MarketLabelBuilder:
    def __init__(
        self,
        horizon: int = 5,
        direction_threshold: float = 0.005
    ):
        self.horizon = horizon
        self.direction_threshold = direction_threshold

    def build_return_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        df["future_return"] = df["close"].shift(-self.horizon) / df["close"] - 1
        
        df["direction_class"] = 0
        df.loc[df["future_return"] > self.direction_threshold, "direction_class"] = 1
        df.loc[df["future_return"] < -self.direction_threshold, "direction_class"] = -1
        return df

    def build_regime_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        ma_fast = df["close"].rolling(10).mean()
        ma_slow = df["close"].rolling(50).mean()
        volatility = df["close"].pct_change().rolling(20).std() * np.sqrt(252)
        
        df["regime_class"] = "mean-revert"
        
        df.loc[(ma_fast > ma_slow) & (df["close"] > ma_fast), "regime_class"] = "bull_trend"
        df.loc[(ma_fast < ma_slow) & (df["close"] < ma_fast), "regime_class"] = "bear_trend"
        
        vol_q20 = volatility.rolling(100, min_periods=20).quantile(0.2)
        df.loc[volatility < vol_q20, "regime_class"] = "compression"
        
        vol_q80 = volatility.rolling(100, min_periods=20).quantile(0.8)
        df.loc[(volatility > vol_q80) & (df["close"] < ma_slow), "regime_class"] = "panic"
        
        compression_yesterday = (volatility.shift(1) < vol_q20.shift(1))
        df.loc[compression_yesterday & (df["close"].pct_change().abs() > 0.02), "regime_class"] = "breakout"
        
        return df

    def build_volatility_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        def _get_future_vol(x):
            if len(x) < self.horizon: return np.nan
            log_rets = np.log(x / x.shift(1)).dropna()
            if len(log_rets) == 0: return np.nan
            return log_rets.std() * np.sqrt(252)

        future_vol = df["close"].rolling(self.horizon).apply(_get_future_vol, raw=False).shift(-self.horizon)
        df["future_realized_vol"] = future_vol
        df["future_rv"] = future_vol
        return df

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df = self.build_return_labels(df)
        df = self.build_regime_labels(df)
        df = self.build_volatility_labels(df)
        
        df["future_min"] = df["low"].rolling(self.horizon).min().shift(-self.horizon)
        df["tail_down"] = (df["future_min"] / df["close"] - 1 < -0.02).astype(int)
        
        return df
