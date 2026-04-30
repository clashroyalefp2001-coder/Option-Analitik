# strategies/base.py
class BaseStrategy:
    """Abstract base class for all strategy implementations."""
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError