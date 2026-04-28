import unittest
import pandas as pd
from execution.filters.hard import apply_hard_filters
from execution.filters.soft import apply_soft_filters
from execution.sizer.kelly import fractional_kelly
from execution.exits.rules import should_exit
from execution.portfolio.limits import check_greek_limits, check_concentration, check_daily_loss

class TestHardFilters(unittest.TestCase):
    def test_apply_hard_filters(self):
        data = pd.DataFrame({
            'bid_ask_spread_pct': [0.001, 0.01, 0.002],
            'open_interest': [150, 50, 200],
            'daily_volume': [30, 10, 50],
            'days_to_expiry': [10, 2, 20]
        })
        config = {
            'max_spread_pct': 0.005,
            'min_open_interest': 100,
            'min_daily_volume': 20,
            'min_days_to_expiry': 5
        }
        filtered = apply_hard_filters(data, config)
        # Row 1 (0-index) should be removed: spread 0.01 > 0.005
        self.assertEqual(len(filtered), 2)
        self.assertTrue((filtered['bid_ask_spread_pct'] <= 0.005).all())

class TestSoftFilters(unittest.TestCase):
    def test_apply_soft_filters(self):
        data = pd.DataFrame({
            'predicted_edge': [0.01, 0.0005, 0.02],
            'signal_confidence': [0.8, 0.6, 0.9],
            'signal_regime': ['normal', 'stress', 'normal'],
            'fair_value': [100, 101, 102],
            'quantity': [1, 1, 1]
        })
        config = {
            'min_edge': 0.001,
            'min_confidence': 0.7
        }
        filtered = apply_soft_filters(data, config)
        # Row 1 should be removed (edge too low + confidence low)
        self.assertEqual(len(filtered), 2)

class TestKellySizing(unittest.TestCase):
    def test_fractional_kelly(self):
        size = fractional_kelly(
            edge=0.02,
            win_rate=0.55,
            loss_rate=0.45,
            avg_win=0.03,
            avg_loss=0.015,
            budget=100000,
            kelly_frac=0.25
        )
        self.assertGreaterEqual(size, 0)
        self.assertLessEqual(size, 100000)

class TestExitRules(unittest.TestCase):
    def test_should_exit_tp(self):
        pos = {'entry_price': 100, 'quantity': 1, 'side': 'long', 'entry_date': pd.Timestamp('2024-01-01')}
        cur = {'price': 106, 'date': pd.Timestamp('2024-01-02')}
        cfg = {'tp_pct': 0.05, 'sl_pct': 0.02, 'time_exit_max_days': 30}
        action = should_exit(pos, cur, cfg)
        self.assertEqual(action, 'close')  # TP hit

    def test_should_exit_sl(self):
        pos = {'entry_price': 100, 'quantity': 1, 'side': 'long', 'entry_date': pd.Timestamp('2024-01-01')}
        cur = {'price': 97, 'date': pd.Timestamp('2024-01-02')}
        cfg = {'tp_pct': 0.05, 'sl_pct': 0.02, 'time_exit_max_days': 30}
        action = should_exit(pos, cur, cfg)
        self.assertEqual(action, 'close')  # SL hit

class TestPortfolioLimits(unittest.TestCase):
    def test_check_concentration(self):
        ok, reason = check_concentration(40000, 1000000, max_pct=0.05)
        self.assertTrue(ok)
        ok2, reason2 = check_concentration(60000, 1000000, max_pct=0.05)
        self.assertFalse(ok2)

if __name__ == '__main__':
    unittest.main()
