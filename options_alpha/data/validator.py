# data/validator.py
"""Проверка входных данных."""
import pandas as pd
def sanity_check_pricing(df: pd.DataFrame) -> None:
    """Проверка, что bid <= ask (если колонки присутствуют)."""
    if "bid" in df.columns and "ask" in df.columns:
        if ((df["bid"] > df["ask"]).any()):
            raise ValueError("validator: bid should never exceed ask")
 
def sanity_check_greeks(df: pd.DataFrame) -> None:
    """Минимальная проверка диапазонов греков (необязательно сейчас)."""
    pass  # future validation can be added