# data/quik_fetcher.py
"""Загрузка данных из QUIK или CSV."""

from __future__ import annotations
import os
import pandas as pd
import numpy as np

def load_underlying() -> pd.DataFrame:
    """Загрузка цен базового актива."""
    path = os.path.join("data", "underlying_prices.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    
    raise FileNotFoundError(f"Underlying prices file not found: {path}. Synthetic data disabled.")

def load_option_quotes() -> pd.DataFrame:
    """Загрузка котировок опционов."""
    # Try multiple possible paths for flexibility
    possible_paths = [
        os.path.join("data", "option_export.tsv"),
        os.path.join("..", "data", "option_export.tsv"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "option_export.tsv")),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return pd.read_csv(path, sep='\t')
    
    raise FileNotFoundError(f"Options quotes file not found in any of: {possible_paths}. Synthetic data disabled.")


# --- MOEX Market Data Fetcher ---

def fetch_moex_market_data(
    symbol: str, 
    start_date: str, 
    end_date: str, 
    interval: str = "1d",
    cache: bool = True,
    is_production: bool = True
) -> pd.DataFrame:
    """Интегрированный загрузчик данных MOEX с кэшированием."""
    import asyncio
    import sys
    import logging
    
    log = logging.getLogger("moex_fetcher")
    
    cache_dir = "data/raw/market"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{symbol}_{start_date}_{end_date}_{interval}.csv")
    
    # 1. Кэш
    if cache and os.path.exists(cache_file):
        df = pd.read_csv(cache_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        log.info(f"Loaded {len(df)} rows from cache: {cache_file}")
        return df
    
    # 2. Загрузка через MoexHistoryFetcher (из backend сервиса)
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    try:
        from backend.app.services.moex_history_fetcher import MoexHistoryFetcher
        fetcher = MoexHistoryFetcher()
        
        # Запуск асинхронного кода в синхронном контексте
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        
        df = loop.run_until_complete(fetcher.fetch_history(
            engine="futures", market="forts", security=symbol,
            start_date=start_date, end_date=end_date
        ))
        
        if df is not None and not df.empty:
            # Форматирование
            mapping = {'TRADEDATE': 'timestamp', 'OPEN': 'open', 'HIGH': 'high', 
                       'LOW': 'low', 'CLOSE': 'close', 'VOLCUR': 'volume', 'OPENPOSITION': 'open_interest'}
            df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # --- ВАЛИДАЦИЯ (PHASE 1 Rules) ---
            # Правило 1: Сортировка по времени
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            # Правило 2: Отсутствие дубликатов времени (no_duplicate_timestamps)
            if df['timestamp'].duplicated().any():
                log.warning("Found duplicated timestamps! Dropping duplicates.")
                df = df.drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
            
            # Правило 3: Отсутствие заглядывания в будущее (no_future_leakage)
            today = pd.Timestamp.today().normalize()
            if (df['timestamp'] > today).any():
                log.warning("Future timestamps detected! Filtering out.")
                df = df[df['timestamp'] <= today].reset_index(drop=True)
                
            # Правило 4: Проверка длины данных
            if len(df) < 1000:
                log.warning(f"Data length validation failed: fetched {len(df)} rows, expected >= 1000.")
                
            # Удаление текстовых колонок, чтобы не сломать LGBM
            for col in df.columns:
                if col != "timestamp" and df[col].dtype == "object":
                    df = df.drop(columns=[col])

            log.info(f"Successfully fetched and validated {len(df)} rows for {symbol}.")
            
            if cache:
                df.to_csv(cache_file, index=False)
            return df
            
    except Exception as e:
        log.error(f"MOEX fetch error: {e}")
        raise RuntimeError(f"DataFetchError: MOEX fetch failed and synthetic fallback is disabled: {e}")
