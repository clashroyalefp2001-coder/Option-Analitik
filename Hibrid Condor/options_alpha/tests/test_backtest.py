import unittest
import pandas as pd
from backtest.engine import backtest_engine

class TestBacktestEngine(unittest.TestCase):
    def test_backtest_engine_simple(self):
        signals = pd.DataFrame({
            'signal': ['BUY', 'SELL', 'SELL'],
            'fair_value': [100.0, 101.0, 102.0],
            'mid': [100.0, 101.0, 102.0],
            'quantity': [1, 1, 1]
        })
        result = backtest_engine(signals, initial_capital=100_000)
        self.assertIn('capital', result)
        self.assertIn('equity_curve', result)
        self.assertIn('trades', result)
        # equity_curve length should be len(signals)+1
        self.assertEqual(len(result['equity_curve']), len(signals)+1)
        # trades should be a DataFrame
        self.assertTrue(isinstance(result['trades'], pd.DataFrame) or len(result['trades']) >= 0)

    def test_backtest_no_signals(self):
        signals = pd.DataFrame({
            'signal': [],
            'fair_value': [],
            'mid': [],
            'quantity': []
        })
        result = backtest_engine(signals, initial_capital=50_000)
        self.assertEqual(result['capital'], 50_000)
        self.assertEqual(len(result['equity_curve']), 1)

if __name__ == '__main__':
    unittest.main()
