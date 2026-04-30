"""Загрузка данных из выгрузки QUIK (TSV формат)."""
import pandas as pd
from pathlib import Path
import logging

from data.fetcher import _normalize_columns, OPTION_TYPE_ALIASES

logger = logging.getLogger(__name__)

# Точный путь до файла, который делает LUA скрипт в QUIK
TSV_PATH = Path(r"C:\Project\Option Analitik\data\option_export.tsv")

def load_underlying() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5, freq="D"),
        "price": [100.0, 101.0, 99.0, 102.0, 101.0]
    })

def load_option_quotes(path: str | Path = TSV_PATH) -> pd.DataFrame:
    required = ["date", "strike", "bid", "ask", "expiry", "type", "underlying_price", "iv", "last"]
    empty = pd.DataFrame({c: pd.Series(dtype="object") for c in required})

    p = Path(path)
    if not p.exists():
        logger.error(f"Файл {p} не найден! Проверь, выгружает ли QUIK данные.")
        return empty

    try:
        # QUIK выгружает в cp1251. Разделитель \t
        df = pd.read_csv(p, sep="\t", encoding="cp1251", on_bad_lines="skip")
    except Exception as e:
        logger.error(f"Ошибка чтения TSV-файла {p}: {e}")
        return empty

    if df is None or df.empty:
        logger.error(f"Файл {p} пустой.")
        return empty

    # Очистка имен колонок от пробелов
    df.columns = df.columns.str.strip()
    
    # 1. Нормализация
    df = _normalize_columns(df).copy()

    # 2. Тип опциона
    if "type" in df.columns:
        # ИСПОЛЬЗУЕМ .loc[:, "col"] ВМЕСТО ПРЯМОГО ПРИСВАИВАНИЯ
        df.loc[:, "type"] = df["type"].astype(str).str.strip().str.lower().map(OPTION_TYPE_ALIASES)
    else:
        df.loc[:, "type"] = pd.NA

    # 3. Дата
    if "date" not in df.columns:
        df.loc[:, "date"] = pd.Timestamp.today().normalize()
    df.loc[:, "date"] = pd.to_datetime(df["date"], errors="coerce")

    # 4. Экспирация
    if "expiry" in df.columns:
         df.loc[:, "expiry"] = pd.to_datetime(df["expiry"], errors="coerce", dayfirst=True)
    else:
         df.loc[:, "expiry"] = pd.NaT

    # 5. Преобразование числовых полей
    for col in ["strike", "bid", "ask", "last", "theoretical_price", "iv", "open_interest", "volume", "lot"]:
        if col in df.columns:
            # Заменяем в строках запятые на точки для парсинга (у QUIK русская локаль: 98,5)
            if df[col].dtype == object:
                df.loc[:, col] = df[col].str.replace(",", ".", regex=False)
            df.loc[:, col] = pd.to_numeric(df[col], errors="coerce")
            
    if "underlying_price" not in df.columns:
        df.loc[:, "underlying_price"] = pd.NA

    # 6. Фьючерс
    futures_mask = df["strike"].isna() | df["type"].isna()
    if futures_mask.any():
        fut_row = df[futures_mask].iloc[0]
        bid = float(fut_row.get("bid")) if pd.notna(fut_row.get("bid")) else None
        ask = float(fut_row.get("ask")) if pd.notna(fut_row.get("ask")) else None
        last = float(fut_row.get("last")) if pd.notna(fut_row.get("last")) else None
        
        spot = None
        if bid and ask and bid > 0 and ask > 0:
            spot = (bid + ask) / 2.0
        elif last and last > 0:
            spot = last
            
        if spot is not None:
            df.loc[:, "underlying_price"] = spot
        
        # Удаляем строку фьючерса
        df = df[~futures_mask].reset_index(drop=True)

    # 7. Возвращаем с нужными колонками
    extra = [c for c in df.columns if c not in required]
    return df[required + extra]