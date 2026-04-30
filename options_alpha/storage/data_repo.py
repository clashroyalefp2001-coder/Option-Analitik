# storage/data_repo.py
"""Persistence layer for features using Parquet when possible."""
import os
import pandas as pd

def save_parquet(df: pd.DataFrame, path: str) -> None:
    """
    Save DataFrame to disk in Parquet format.
    Falls back to CSV if pyarrow/fastparquet not available.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        # Try to write Parquet
        df.to_parquet(path, index=False)
    except Exception:
        # Fallback to CSV
        df.to_csv(path, index=False)
