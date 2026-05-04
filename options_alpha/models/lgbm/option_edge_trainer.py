import pandas as pd

def validate_contract_timeseries(df: pd.DataFrame, horizon_days: int = 5):
    """Проверка целостности временных рядов контрактов."""
    
    # 1. no duplicate (symbol, timestamp)
    duplicates = df.duplicated(subset=['option_symbol', 'date']).sum()
    if duplicates > 0:
        raise ValueError(f"Found {duplicates} duplicate option_symbol+date entries")

    # 2. monotonic date per symbol, expiry constant within symbol
    for symbol, group in df.groupby('option_symbol'):
        if not group['date'].is_monotonic_increasing:
             raise ValueError(f"Dates not monotonic for {symbol}")
        
        if group['expiry'].nunique() > 1:
            raise ValueError(f"Expiry not consistent for symbol {symbol}")
            
        # 3. no horizon crossing expiry
        # Check if date + horizon_days > expiry
        expiry = group['expiry'].iloc[0]
        if (group['date'] + pd.Timedelta(days=horizon_days) > expiry).any():
             raise ValueError(f"Some records have horizons crossing expiry for {symbol}")
