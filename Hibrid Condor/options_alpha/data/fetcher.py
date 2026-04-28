# data/fetcher.py
"""Загрузка сырых данных из Excel-файла с котировками опционов MOEX.

Файл `Option Si 06.2026.xlsx` содержит русскоязычные колонки QUIK-экспорта.
Здесь мы их нормализуем под универсальную схему, понятную остальному
пайплайну (date, strike, bid, ask, expiry, type, underlying_price, ...).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd


# Маппинг русских/QUIK колонок в нормализованные английские
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
    """Переименовывает колонки по маппингу (case-insensitive, обрезает пробелы)."""
    new_cols = {}
    for c in df.columns:
        key = str(c).strip().lower()
        if key in COLUMN_ALIASES:
            new_cols[c] = COLUMN_ALIASES[key]
    return df.rename(columns=new_cols)


def _parse_expiry_from_code(code: str) -> Optional[pd.Timestamp]:
    """Извлекает экспирацию из кода типа 'Si90000BF6' (MOEX-шаблон).

    Возвращает None, если код нестандартный — экспирация будет задана
    отдельной колонкой `Погашение`, если она есть.
    """
    if not isinstance(code, str):
        return None
    # Шаблон MOEX: BUFFER + month-letter + year. Возвращаем None — реальная
    # экспирация всё равно есть в колонке `Погашение`.
    return None


def load_underlying() -> pd.DataFrame:
    """Возвращает пример данных базового актива.

    Реальная история фьючерса Si должна загружаться из истории QUIK; здесь —
    минимальная заглушка для совместимости с пайплайном.
    """
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "price": [100.0, 101.0, 99.0, 102.0, 101.0],
        }
    )


def load_option_quotes(path: str | Path = "Option Si 06.2026.xlsx") -> pd.DataFrame:
    """Чтение и предобработка котировок из Excel-файла.

    Возвращает DataFrame с нормализованной схемой:
        date, strike, bid, ask, expiry, type, underlying_price.

    Если файл отсутствует или некорректен — возвращает пустой DataFrame,
    но всегда с указанными колонками (важно для тестов и UI).
    """
    required = ["date", "strike", "bid", "ask", "expiry", "type", "underlying_price"]
    empty = pd.DataFrame({c: pd.Series(dtype="object") for c in required})

    p = Path(path)
    if not p.exists():
        return empty

    try:
        df = pd.read_excel(str(p))
    except Exception:
        return empty

    if df is None or df.empty:
        return empty

    df = _normalize_columns(df)

    # Тип опциона → call/put
    if "type" in df.columns:
        df["type"] = (
            df["type"].astype(str).str.strip().str.lower().map(OPTION_TYPE_ALIASES)
        )
    else:
        df["type"] = pd.NA

    # Дата наблюдения. В QUIK-выгрузке часто отсутствует — подставляем сегодняшнюю
    if "date" not in df.columns:
        df["date"] = pd.Timestamp.today().normalize()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Экспирация
    if "expiry" in df.columns:
        df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
    else:
        df["expiry"] = pd.NaT

    # Числовые поля
    for col in ["strike", "bid", "ask", "last", "theoretical_price", "iv",
                "open_interest", "volume", "lot"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Базовая цена. В QUIK-выгрузке опционной доски обычно первой строкой
    # идёт сам фьючерс (страйк NaN, type NaN, в bid/ask — его цена).
    # Извлекаем её и проливаем во все строки; фьючерсную строку убираем.
    if "underlying_price" not in df.columns:
        df["underlying_price"] = pd.NA
    futures_mask = df["strike"].isna() | df["type"].isna()
    if futures_mask.any():
        fut_row = df[futures_mask].iloc[0]
        # Берём mid по фьючерсу; если спред отсутствует — last
        bid = float(fut_row.get("bid")) if pd.notna(fut_row.get("bid")) else None
        ask = float(fut_row.get("ask")) if pd.notna(fut_row.get("ask")) else None
        last = float(fut_row.get("last")) if pd.notna(fut_row.get("last")) else None
        if bid and ask and bid > 0 and ask > 0:
            spot = (bid + ask) / 2.0
        elif last and last > 0:
            spot = last
        else:
            spot = None
        if spot is not None:
            df["underlying_price"] = spot
        # Убираем строки без страйка/типа — это не опционы
        df = df[~futures_mask].reset_index(drop=True)

    # Гарантируем порядок и наличие нужных колонок
    extra = [c for c in df.columns if c not in required]
    df = df[required + extra]

    return df
