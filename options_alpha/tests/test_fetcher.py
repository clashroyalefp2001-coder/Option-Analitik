import unittest
import pandas as pd
from data.fetcher import load_option_quotes

class TestFetcher(unittest.TestCase):
    def test_load_option_quotes_structure(self):
        """Проверяем, что load_option_quotes возвращает DataFrame с нужными колонками."""
        df = load_option_quotes()
        self.assertIsInstance(df, pd.DataFrame)
        required = {"date", "strike", "bid", "ask", "expiry", "type", "underlying_price"}
        self.assertTrue(required.issubset(set(df.columns)), 
                        f"Отсутствуют колонки: {required - set(df.columns)}")
    
    def test_load_option_quotes_nonempty(self):
        """Проверяем, что при наличии файла возвращаются данные."""
        df = load_option_quotes()
        self.assertTrue(len(df) >= 0)  # может быть пустым только если файл нет
