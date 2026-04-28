# data/fetcher.py
"""Загрузка сырых данных из Excel-файла с котировками."""
import pandas as pd
from pathlib import Path
from pandas.errors import ParserError

def load_underlying() -> pd.DataFrame:
    """Возвращает пример данных базового актива."""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5, freq="D"),
        "price": [100, 101, 99, 102, 101]
    })

def load_option_quotes() -> pd.DataFrame:
    """Чтение и предобработка онлайн‑котировок из Excel‑файла.
    Ожидаются минимум столбцы: date, strike, bid, ask, expiry, type, underlying_price.
    Если файл отсутствует – возвращается пустой DataFrame.
    """
    try:
        path = Path("Option Si 06.2026.xlsx")
        if not path.exists():
            raise FileNotFoundError("Файл Option Si 06.2026.xlsx не найден")
        df = pd.read_excel(str(path))
        
        # Приведение дат, переведём всё к строковому типу, где нужно
        df = df.convert_dtypes()
        
        # Оставляем только нужные колонки
        required = {"date", "strike", "bid", "ask", "expiry", "type", "underlying_price"}
        cols = [c for c in df.columns if c.lower() in required]
        df = df[cols]

        # Приводим даты к типу datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        if "expiry" in df.columns:
            df["expiry"] = pd.to_datetime(df["expiry"])
        
        return df
    except Exception as exc:
        print(f"[load_option_quotes] Ошибка чтения Excel: {exc}")
        return pd.DataFrame()
