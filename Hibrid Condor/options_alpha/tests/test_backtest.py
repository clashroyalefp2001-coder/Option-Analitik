import unittest
import numpy as np
import pandas as pd

from backtest.engine import (
    BacktestEngine,
    OptionBacktestEngine,
    backtest_engine,
)


class TestBacktestEngine(unittest.TestCase):
    """Старый движок (legacy) — оставлен для обратной совместимости."""

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
        self.assertEqual(len(result['equity_curve']), len(signals) + 1)
        self.assertTrue(
            isinstance(result['trades'], pd.DataFrame) or len(result['trades']) >= 0
        )

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


class TestOptionBacktestEngine(unittest.TestCase):
    """Реалистичный опционный бэктест."""

    def _make_signals(self, n=3):
        # Базовый набор: ATM call с DTE=30
        return pd.DataFrame({
            'underlying_price': [100.0] * n,
            'strike': [100.0] * n,
            'type': ['call'] * n,
            'fair_value': [3.0] * n,
            'mid': [3.0] * n,
            'days_to_expiry': [30] * n,
            'side': ['buy'] * n,
            'predicted_edge': [0.5] * n,
        })

    def test_initialization_defaults(self):
        eng = OptionBacktestEngine()
        self.assertEqual(eng.initial_capital, 1_000_000)
        self.assertEqual(eng.equity_curve, [1_000_000])
        self.assertEqual(eng.trades, [])

    def test_run_with_no_signals(self):
        eng = OptionBacktestEngine(n_simulations=10)
        eng.run(pd.DataFrame(), pd.Series([], dtype=float))
        self.assertEqual(eng.equity_curve, [1_000_000])
        self.assertEqual(len(eng.trades), 0)

    def test_run_produces_trades_and_equity_curve(self):
        signals = self._make_signals(2)
        sizes = pd.Series([1.0, 1.0])
        eng = OptionBacktestEngine(
            n_simulations=20,
            seed=123,
            realized_vol=0.25,
        )
        eng.run(signals, sizes)
        # 30 дней DTE → equity curve длиной 31
        self.assertEqual(len(eng.equity_curve), 31)
        self.assertEqual(len(eng.trades), 2)
        # Trades содержит ожидаемые поля
        for trade in eng.trades:
            self.assertIn('pnl', trade)
            self.assertIn('exit_reason', trade)
            self.assertIn('win_rate_sim', trade)
            self.assertIn('days_held', trade)
            # win_rate_sim в [0, 1]
            self.assertGreaterEqual(trade['win_rate_sim'], 0.0)
            self.assertLessEqual(trade['win_rate_sim'], 1.0)

    def test_pnl_is_not_zero_for_realistic_case(self):
        """Главный регрессионный тест: P&L не должен быть нулевым.

        Старый движок давал pnl=0 (entry=exit). Новый движок — реальный P&L
        от движения базового актива.
        """
        signals = self._make_signals(1)
        sizes = pd.Series([1.0])
        eng = OptionBacktestEngine(
            n_simulations=50,
            seed=7,
            realized_vol=0.25,
            stop_loss_pct=None,
            take_profit_pct=None,
        )
        eng.run(signals, sizes)
        trade = eng.trades[0]
        # P&L не должен быть точно нулём; даже при ATM на экспирации
        # с n_simulations=50 ожидаем некоторую дисперсию.
        self.assertNotEqual(trade['pnl'], 0.0)
        # Equity curve не плоская
        eq = np.array(eng.equity_curve)
        self.assertGreater(np.std(eq), 0.0)

    def test_stop_loss_triggers_exit(self):
        """С агрессивным стоп-лоссом часть сделок должна выходить раньше."""
        signals = self._make_signals(1)
        sizes = pd.Series([1.0])
        eng = OptionBacktestEngine(
            n_simulations=100,
            seed=42,
            realized_vol=0.5,  # высокая волатильность
            stop_loss_pct=0.1,  # очень узкий SL = 10% от цены входа
            take_profit_pct=10.0,  # эффективно отключён
        )
        eng.run(signals, sizes)
        trade = eng.trades[0]
        # При высокой волатильности и узком SL средняя длительность
        # удержания должна быть меньше DTE
        self.assertLess(trade['days_held'], 30)

    def test_hit_rate_in_valid_range(self):
        """Hit rate должен быть в (0, 1) для разумной выборки."""
        signals = self._make_signals(5)
        sizes = pd.Series([1.0] * 5)
        eng = OptionBacktestEngine(
            n_simulations=50,
            seed=99,
            realized_vol=0.3,
        )
        eng.run(signals, sizes)
        trades_df = pd.DataFrame(eng.trades)
        if not trades_df.empty:
            wins = (trades_df['pnl'] > 0).sum()
            hit_rate = wins / len(trades_df)
            self.assertGreaterEqual(hit_rate, 0.0)
            self.assertLessEqual(hit_rate, 1.0)

    def test_buy_and_sell_sides_handled(self):
        """Поддержка обеих сторон: buy и sell."""
        signals = pd.DataFrame({
            'underlying_price': [100.0, 100.0],
            'strike': [100.0, 105.0],
            'type': ['call', 'put'],
            'fair_value': [3.0, 4.0],
            'days_to_expiry': [20, 20],
            'side': ['buy', 'sell'],
            'predicted_edge': [0.5, 0.3],
        })
        sizes = pd.Series([1.0, 1.0])
        eng = OptionBacktestEngine(n_simulations=20, seed=11)
        eng.run(signals, sizes)
        self.assertEqual(len(eng.trades), 2)
        self.assertEqual(eng.trades[0]['side'], 'buy')
        self.assertEqual(eng.trades[1]['side'], 'sell')

    def test_zero_size_skips_trade(self):
        """Сделки с нулевым размером пропускаются."""
        signals = self._make_signals(2)
        sizes = pd.Series([0.0, 1.0])
        eng = OptionBacktestEngine(n_simulations=10, seed=5)
        eng.run(signals, sizes)
        self.assertEqual(len(eng.trades), 1)

    def test_zero_dte_skips_trade(self):
        """Сделки с DTE=0 пропускаются (нечего симулировать)."""
        signals = self._make_signals(1)
        signals.loc[0, 'days_to_expiry'] = 0
        sizes = pd.Series([1.0])
        eng = OptionBacktestEngine(n_simulations=10, seed=5)
        eng.run(signals, sizes)
        self.assertEqual(len(eng.trades), 0)

    def test_reproducibility_with_seed(self):
        """С одинаковым seed результаты должны совпадать."""
        signals = self._make_signals(2)
        sizes = pd.Series([1.0, 1.0])

        eng1 = OptionBacktestEngine(n_simulations=20, seed=2024)
        eng1.run(signals, sizes)

        eng2 = OptionBacktestEngine(n_simulations=20, seed=2024)
        eng2.run(signals, sizes)

        for t1, t2 in zip(eng1.trades, eng2.trades):
            self.assertAlmostEqual(t1['pnl'], t2['pnl'], places=6)


if __name__ == '__main__':
    unittest.main()
