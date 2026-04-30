# tests/test_data.py
import unittest
import pandas as pd
from data.fetcher import load_underlying, load_option_quotes
from data.cleaner import deduplicate, check_nulls, align_dates
from data.validator import sanity_check_pricing, sanity_check_greeks

class TestDataFetcher(unittest.TestCase):
    def test_load_underlying(self):
        df = load_underlying()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn('date', df.columns)
        self.assertIn('price', df.columns)

    def test_load_option_quotes(self):
        df = load_option_quotes()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn('strike', df.columns)
        self.assertIn('bid', df.columns)
        self.assertIn('ask', df.columns)

class TestDataCleaner(unittest.TestCase):
    def test_deduplicate(self):
        df = pd.DataFrame({'a': [1, 1, 2], 'b': [3, 3, 4]})
        dedup = deduplicate(df)
        self.assertEqual(len(dedup), 2)

    def test_check_nulls_fail(self):
        df = pd.DataFrame({'price': [1, None, 3]})
        with self.assertRaises(ValueError):
            check_nulls(df, 'test')

class TestDataValidator(unittest.TestCase):
    def test_sanity_check_pricing_ok(self):
        df = pd.DataFrame({'bid': [1.0, 2.0], 'ask': [1.1, 2.1]})
        try:
            sanity_check_pricing(df)
        except ValueError:
            self.fail('sanity_check_pricing raised unexpectedly')

    def test_sanity_check_pricing_fail(self):
        df = pd.DataFrame({'bid': [2.0], 'ask': [1.0]})
        with self.assertRaises(ValueError):
            sanity_check_pricing(df)

if __name__ == '__main__':
    unittest.main()
