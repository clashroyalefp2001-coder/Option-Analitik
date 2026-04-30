# strategies/butterfly.py
import pandas as pd
from .base import BaseStrategy

class ButterflyStrategy(BaseStrategy):
    """Simple butterfly strategy (placeholder)."""
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        signals = pd.DataFrame(index=df.index)
        signals["signal"] = "NEUTRAL"
        return signals[["signal"]]