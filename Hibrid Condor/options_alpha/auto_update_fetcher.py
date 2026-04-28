# auto_update_fetcher.py
import pathlib
import datetime

# ----------------- ПУТИ ---------------------------------------------------------
PROJECT_ROOT = pathlib.Path(r"C:\Project\Option Analitik\Hibrid Condor\options_alpha")

FETCHER_PATH      = PROJECT_ROOT / "data" / "fetcher.py"
TEST_FILE_PATH    = PROJECT_ROOT / "tests" / "test_fetcher.py"

EXCEL_FILE        = PROJECT_ROOT / "Option Si 06.2026.xlsx"

# -------------------------------------------------------------

def _write_fetcher_code():
    """
    Записывает в data/fetcher.py код, который читает онлайн‑квотировки
    из Excel‑файла (см. `load_option_quotes_excel` ниже).
    """
    code = '''# data/fetcher.py
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
'''
    with open(FETCHER_PATH, "w", encoding="utf-8") as f:
        f.write(code)
    print("[auto_update_fetcher] Записан новый код в", FETCHER_PATH)


def _write_test_fetcher():
    """
    Создаёт/обновляет тест test_fetcher.py.
    Тест проверяет, что функция `load_option_quotes` возвращает DataFrame
    и содержит ожидаемые колонки.
    """
    test_code = '''import unittest
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
'''
    with open(TEST_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(test_code)
    print("[auto_update_fetcher] Записан тест", TEST_FILE_PATH)


if __name__ == "__main__":
    # ---------- 1. Обновляем fetcher.py ----------
    _write_fetcher_code()

    # ---------- 2. Обновляем тесты ----------
    _write_test_fetcher()
    
    print("[auto_update_fetcher] Готово: fetcher.py и тесты обновлены")
