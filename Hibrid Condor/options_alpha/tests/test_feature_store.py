import unittest
import pandas as pd

from models.feature_store import build_features


class TestFeatureStore(unittest.TestCase):
    def _make_options(self, days_to_expiry: int):
        obs_date = pd.Timestamp('2024-01-01')
        expiry = obs_date + pd.Timedelta(days=days_to_expiry)
        return pd.DataFrame({
            'date': [obs_date],
            'strike': [100.0],
            'bid': [5.0],
            'ask': [5.2],
            'expiry': [expiry],
            'type': ['call'],
            'underlying_price': [100.0],
            'open_interest': [500],
            'volume': [120],
        })

    def test_build_features_columns(self):
        underlying = pd.DataFrame({'date': pd.to_datetime(['2024-01-01']), 'price': [100.0]})
        options = self._make_options(180)
        features = build_features(underlying, options)

        expected = {
            'fair_value', 'mid', 'mispricing', 'predicted_edge', 'side',
            'delta', 'gamma', 'vega', 'theta', 'rho',
            'early_exercise_premium', 'moneyness', 'iv_rank',
            'days_to_expiry', 'bid_ask_spread_pct', 'open_interest', 'daily_volume',
            'signal_confidence', 'signal_regime',
        }
        self.assertTrue(expected.issubset(set(features.columns)))
        self.assertGreater(len(features), 0)

        for col in ['fair_value', 'delta', 'gamma', 'vega', 'theta']:
            self.assertFalse(features[col].isna().any(), f'Column {col} contains NaN')

    def test_T_uses_days_to_expiry(self):
        """Главный фикс: T = days_to_expiry/365, а не хардкод 0.5.
        Опцион с большим сроком должен иметь более высокую справедливую цену."""
        underlying = pd.DataFrame({'date': pd.to_datetime(['2024-01-01']), 'price': [100.0]})
        short = build_features(underlying, self._make_options(30))
        long = build_features(underlying, self._make_options(365))

        self.assertEqual(int(short['days_to_expiry'].iloc[0]), 30)
        self.assertEqual(int(long['days_to_expiry'].iloc[0]), 365)
        # Длинный опцион дороже короткого (для одного и того же ATM call)
        self.assertGreater(long['fair_value'].iloc[0], short['fair_value'].iloc[0])

    def test_filters_invalid_rows(self):
        """Невалидные котировки должны отфильтровываться."""
        obs_date = pd.Timestamp('2024-01-01')
        expiry = obs_date + pd.Timedelta(days=90)
        bad = pd.DataFrame({
            'date': [obs_date, obs_date],
            'strike': [100.0, 100.0],
            'bid': [0.0, 5.0],         # первая строка — невалидная
            'ask': [5.0, 4.0],         # вторая — ask < bid
            'expiry': [expiry, expiry],
            'type': ['call', 'call'],
            'underlying_price': [100.0, 100.0],
        })
        features = build_features(pd.DataFrame(), bad)
        self.assertEqual(len(features), 0)

    def test_side_aware_edge(self):
        """edge учитывает сторону сделки: для положительного mispricing — buy edge с учётом ask."""
        underlying = pd.DataFrame({'date': pd.to_datetime(['2024-01-01']), 'price': [100.0]})
        options = self._make_options(180)
        features = build_features(underlying, options)
        row = features.iloc[0]
        if row['fair_value'] > row['ask']:
            self.assertEqual(row['side'], 'buy')
            self.assertAlmostEqual(row['predicted_edge'], row['fair_value'] - row['ask'], places=6)
        elif row['fair_value'] < row['bid']:
            self.assertEqual(row['side'], 'sell')
        else:
            self.assertEqual(row['side'], 'neutral')


if __name__ == '__main__':
    unittest.main()
