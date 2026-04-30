# data/cleaner.py
"""Очистка и подготовка данных."""
import pandas as pd

def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Удаляет дубликаты."""
    return df.drop_duplicates()

def check_nulls(df: pd.DataFrame, label: str) -> None:
    """Проверка на пропуски."""
    if df.isnull().values.any():
        raise ValueError(f"cleaner: null values found in {label}")

def align_dates(underlying: pd.DataFrame, options: pd.DataFrame) -> pd.DataFrame:
    """Объединяет данные базового актива и опционов по дате."""
    # Ensure both have 'date' column
    if 'date' not in underlying.columns:
        underlying.loc[:, 'date'] = pd.Timestamp.now().normalize()
    if 'date' not in options.columns:
        options.loc[:, 'date'] = pd.Timestamp.now().normalize()
    return pd.merge(underlying, options, on="date", how="inner")
