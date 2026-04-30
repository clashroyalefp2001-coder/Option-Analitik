"""Загрузка сырых данных (Excel) с котировками опционов MOEX.
Из него мы также используем словарь маппингов для TSV."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import pandas as pd

COLUMN_ALIASES = {
    "страйк": "strike",
    "strike": "strike",
    "спрос": "bid",
    "bid": "bid",
    "предл.": "ask",
    "предложение": "ask",
    "ask": "ask",
    "погашение": "expiry",
    "expiry": "expiry",
    "expiration": "expiry",
    "тип опциона": "type",
    "тип": "type",
    "type": "type",
    "баз.актив": "underlying_symbol",
    "базовый актив": "underlying_symbol",
    "underlying": "underlying_symbol",
    "цена послед.": "last",
    "последняя": "last",
    "last": "last",
    "теор. цена": "theoretical_price",
    "теор.цена": "theoretical_price",
    "theoretical price": "theoretical_price",
    "волатильность": "iv",
    "iv": "iv",
    "implied volatility": "iv",
    "лот": "lot",
    "шаг цены": "tick_value",
    "open interest": "open_interest",
    "открытый интерес": "open_interest",
    "объём": "volume",
    "объем": "volume",
    "volume": "volume",
    "date": "date",
    "дата": "date",
}

OPTION_TYPE_ALIASES = {
    "call": "call",
    "колл": "call",
    "c": "call",
    "к": "call",
    "put": "put",
    "пут": "put",
    "p": "put",
    "п": "put",
}

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = {}
    for c in df.columns:
        key = str(c).strip().lower()
        if key in COLUMN_ALIASES:
            new_cols[c] = COLUMN_ALIASES[key]
    return df.rename(columns=new_cols)

def load_underlying() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "price": [100.0, 101.0, 99.0, 102.0, 101.0],
        }
    )

def load_option_quotes(path: str | Path = None) -> pd.DataFrame:
    """Чтение и предобработка котировок из CSV/TSV/Excel-файла."""
    required = [
        "date", "strike", "bid", "ask", "last", "expiry", 
        "type", "underlying_price", "underlying_symbol"
    ]
    empty = pd.DataFrame({c: pd.Series(dtype="object") for c in required})

    if path is None:
        # Автопоиск нужного файла с экспортом
        candidates = ["data/option_export.tsv", "data/option_export.csv", "Option Si 06.2026.xlsx"]
        for cand in candidates:
            if Path(cand).exists():
                path = cand
                break
        if path is None:
            return empty

    p = Path(path)
    if not p.exists():
        return empty

    try:
        if p.suffix.lower() == '.csv':
            df = pd.read_csv(str(p), sep=';', encoding='cp1251', on_bad_lines='skip')
        elif p.suffix.lower() == '.tsv':
            df = pd.read_csv(str(p), sep='\t', encoding='cp1251', on_bad_lines='skip')
        else:
            df = pd.read_excel(str(p))
    except Exception:
        return empty

    if df is None or df.empty:
        return empty

    df = _normalize_columns(df).copy()

    if "type" in df.columns:
        df.loc[:, "type"] = df["type"].astype(str).str.strip().str.lower().map(OPTION_TYPE_ALIASES)
    else:
        df.loc[:, "type"] = pd.NA

    if "date" not in df.columns:
        df.loc[:, "date"] = pd.Timestamp.today().normalize()
    df.loc[:, "date"] = pd.to_datetime(df["date"], errors="coerce")

    if "expiry" in df.columns:
        df.loc[:, "expiry"] = pd.to_datetime(df["expiry"], errors="coerce", dayfirst=True)
    else:
        df.loc[:, "expiry"] = pd.NaT

    for col in ["strike", "bid", "ask", "last", "theoretical_price", "iv", "open_interest", "volume", "lot"]:
        if col in df.columns:
            if df[col].dtype == object:
                # На случай строк с запятыми из квика (русская локализация)
                df.loc[:, col] = df[col].astype(str).str.replace(",", ".", regex=False)
            df.loc[:, col] = pd.to_numeric(df[col], errors="coerce")

    if "underlying_price" not in df.columns:
        df.loc[:, "underlying_price"] = pd.NA

    futures_mask = df["strike"].isna() | df["type"].isna()
    if futures_mask.any():
        fut_row = df[futures_mask].iloc[0]
        bid = float(fut_row.get("bid")) if pd.notna(fut_row.get("bid")) else None
        ask = float(fut_row.get("ask")) if pd.notna(fut_row.get("ask")) else None
        last_val = float(fut_row.get("last")) if pd.notna(fut_row.get("last")) else None
        
        spot = None
        if bid and ask and bid > 0 and ask > 0:
            spot = (bid + ask) / 2.0
        elif last_val and last_val > 0:
            spot = last_val
            
        if spot is not None:
            df.loc[:, "underlying_price"] = spot
            
        df = df.loc[~futures_mask].reset_index(drop=True).copy()

    extra = [c for c in df.columns if c not in required]
    
    # САМОЕ ВАЖНОЕ: обязательно .copy() при срезе, чтобы отвязать таблицу от исходной!
    return df[required + extra].copy()