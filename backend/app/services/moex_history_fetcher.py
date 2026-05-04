import asyncio
import aiohttp
import pandas as pd
from datetime import datetime

class MoexHistoryFetcher:
    """
    Асинхронный клиент для получения исторических данных с Московской Биржи (MOEX ISS).
    Позволяет скачивать историю по одной бумаге за интервал дат.
    """
    
    BASE_URL = "https://iss.moex.com"

    async def fetch_history(self, engine: str, market: str, security: str, start_date: str, end_date: str, session_id: str = None) -> pd.DataFrame:
        """
        Получить историю по одной бумаге на рынке за интервал дат.
        
        :param engine: Движок (например, 'futures' или 'stock')
        :param market: Рынок (например, 'forts' или 'shares')
        :param security: Код инструмента (например, 'SiM6')
        :param start_date: Начальная дата в формате 'YYYY-MM-DD'
        :param end_date: Конечная дата в формате 'YYYY-MM-DD'
        :param session_id: ID сессии (опционально, например '1', '2', '3')
        """
        if session_id:
            url = f"{self.BASE_URL}/iss/history/engines/{engine}/markets/{market}/sessions/{session_id}/securities/{security}.json"
        else:
            url = f"{self.BASE_URL}/iss/history/engines/{engine}/markets/{market}/securities/{security}.json"

        params = {
            "from": start_date,
            "till": end_date,
            "iss.meta": "off",
            "start": 0
        }

        all_data = []
        columns = []
        
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if "history" not in data or not data["history"]["data"]:
                        break
                        
                    if not columns:
                        columns = data["history"]["columns"]
                        
                    all_data.extend(data["history"]["data"])
                    
                    # Проверяем, есть ли еще данные (пагинация)
                    # MOEX возвращает по 100 записей за раз
                    if len(data["history"]["data"]) < 100:
                        break
                        
                    params["start"] += len(data["history"]["data"])

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data, columns=columns)
        
        # Приводим даты к datetime
        if 'TRADEDATE' in df.columns:
            df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
            
        return df

# Пример использования
if __name__ == "__main__":
    async def main():
        fetcher = MoexHistoryFetcher()
        print("Скачивание исторических данных для SiM6...")
        df = await fetcher.fetch_history(
            engine="futures",
            market="forts",
            security="SiM6",
            start_date="2024-01-01",
            end_date="2024-05-01"
        )
        print(f"Получено записей: {len(df)}")
        if not df.empty:
            print(df.head())

    asyncio.run(main())
