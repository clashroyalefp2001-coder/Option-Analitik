import asyncio
import aiohttp
import pandas as pd
from datetime import datetime

class MoexIssFetcher:
    """
    Асинхронный адаптер для получения онлайн-данных опционов Московской биржи (MOEX).
    Заменяет чтение из статического Excel файла `Option Si 06.2026.xlsx`.
    """
    
    # Эндпоинт для опционов (доска ROPD - фьючерсные опционы основного рынка)
    OPTIONS_URL = "https://iss.moex.com/iss/engines/futures/markets/options/boards/ROPD/securities.json"
    # Эндпоинт для базовых активов (фьючерсов, доска RFUD)
    FUTURES_URL = "https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities.json"

    def __init__(self, underlying_asset: str = "Si"):
        self.underlying_asset = underlying_asset

    async def fetch_options_board(self, session: aiohttp.ClientSession) -> pd.DataFrame:
        """
        Скачивает текущую опционную доску.
        """
        async with session.get(self.OPTIONS_URL) as response:
            data = await response.json()
            
            # Парсим блок securities
            columns = data["securities"]["columns"]
            rows = data["securities"]["data"]
            df = pd.DataFrame(rows, columns=columns)
            
            # Фильтруем только опционы на наш базовый актив (например, Si)
            # SECID для опционов на Si обычно начинается с 'Si'
            df = df[df['SECID'].str.startswith(self.underlying_asset)]
            
            # Очистка и приведение к формату Option-Analitik
            df_clean = pd.DataFrame({
                "symbol": df["SECID"],
                "type": df["OPTIONTYPE"].apply(lambda x: "call" if x == "C" else "put"),
                "strike": pd.to_numeric(df["STRIKE"]),
                "bid": pd.to_numeric(df["BID"]),
                "ask": pd.to_numeric(df["OFFER"]),
                "open_interest": pd.to_numeric(df["OPENPOSITION"]),
                "volume": pd.to_numeric(df["VOLTODAY"]),
                "implied_volatility": pd.to_numeric(df["IMPLVOL"]),
            })
            return df_clean
            
    async def fetch_underlying_price(self, session: aiohttp.ClientSession) -> float:
        """
        Получает текущую цену базового фьючерса.
        """
        async with session.get(self.FUTURES_URL) as response:
            data = await response.json()
            columns = data["securities"]["columns"]
            rows = data["securities"]["data"]
            df = pd.DataFrame(rows, columns=columns)
            
            # Ищем актуальный фьючерс (например, Si-6.26)
            si_row = df[df['SECID'].str.startswith(self.underlying_asset)].iloc[0]
            last_price = float(si_row['LAST'])
            return last_price

    async def get_live_snapshot(self) -> dict:
        """
        Основной метод оркестрации. Возвращает текущий "снимок" рынка.
        """
        async with aiohttp.ClientSession() as session:
            try:
                underlying_task = asyncio.create_task(self.fetch_underlying_price(session))
                options_task = asyncio.create_task(self.fetch_options_board(session))
                
                underlying_price, options_board = await asyncio.gather(underlying_task, options_task)
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "underlying_price": underlying_price,
                    "options_board": options_board
                }
            except Exception as e:
                print(f"Ошибка получения онлайн-данных: {e}")
                return None

# Пример использования
if __name__ == "__main__":
    fetcher = MoexIssFetcher(underlying_asset="Si")
    snapshot = asyncio.run(fetcher.get_live_snapshot())
    if snapshot:
        print(f"Цена базового актива: {snapshot['underlying_price']}")
        print(f"Количество опционов: {len(snapshot['options_board'])}")
        print(snapshot['options_board'].head())
