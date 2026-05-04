import numpy as np
import pandas as pd

class VolatilityLabelBuilder:
    def __init__(self, horizon: int = 5):
        self.horizon = horizon

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        # Annualized Vol within horizon
        def _get_future_vol(x):
            log_rets = np.log(x / x.shift(1)).dropna()
            if len(log_rets) == 0: return np.nan
            return log_rets.std() * np.sqrt(252)

        df["future_realized_vol_h"] = df["close"].rolling(self.horizon).apply(_get_future_vol, raw=False).shift(-self.horizon)
        return df.dropna()
