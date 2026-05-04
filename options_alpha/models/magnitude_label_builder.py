import numpy as np
import pandas as pd

class MagnitudeLabelBuilder:
    def __init__(self, horizon: int = 5):
        self.horizon = horizon

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        df["future_abs_return"] = (df["close"].shift(-self.horizon) / df["close"] - 1).abs()
        return df.dropna()
