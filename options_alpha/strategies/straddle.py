# strategies/straddle.py
import pandas as pd
from .base import BaseStrategy

class StraddleStrategy(BaseStrategy):
    """Buy ATM Call + Buy ATM Put (synthetic straddle) with fair‑value logic."""
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.DataFrame(index=df.index)
        signals["mid"] = df["mid"]
        signals["fair_value"] = df["fair_value"]
        # Example rule: if fair_value is significantly above mid → BUY call side,
        # if significantly below mid → BUY put side (we mark as SELL to open short put).
        # For a neutral MVP we just flag a "straddle" position.
        signals["signal"] = "NEUTRAL"
        mask = signals["fair_value"] > signals["mid"] * 1.005
        signals.loc[mask, "signal"] = "BUY_CALL"
        signals.loc[~mask & (signals["fair_value"] < signals["mid"] * 0.995), "signal"] = "BUY_PUT"
        return signals[["signal"]]