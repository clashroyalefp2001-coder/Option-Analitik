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


    def test_theoretical_price_used_as_mid(self):
        """Если theoretical_price есть и > 0 — она используется как mid (вместо bid/ask)."""
        obs_date = pd.Timestamp('2024-01-01')
        expiry = obs_date + pd.Timedelta(days=180)
        options = pd.DataFrame({
            'date': [obs_date],
            'strike': [100.0],
            'bid': [5.0],
            'ask': [5.2],
            'theoretical_price': [7.5],   # расходится с (bid+ask)/2 = 5.1
            'expiry': [expiry],
            'type': ['call'],
            'underlying_price': [100.0],
        })
        features = build_features(pd.DataFrame(), options)
        self.assertEqual(len(features), 1)
        self.assertAlmostEqual(features['mid'].iloc[0], 7.5, places=6)
        self.assertEqual(features['mid_source'].iloc[0], 'theoretical')

    def test_falls_back_to_bid_ask_when_no_theoretical(self):
        """Без theoretical_price — старая логика через (bid+ask)/2."""
        obs_date = pd.Timestamp('2024-01-01')
        expiry = obs_date + pd.Timedelta(days=180)
        options = pd.DataFrame({
            'date': [obs_date],
            'strike': [100.0],
            'bid': [5.0],
            'ask': [5.2],
            'expiry': [expiry],
            'type': ['call'],
            'underlying_price': [100.0],
        })
        features = build_features(pd.DataFrame(), options)
        self.assertEqual(len(features), 1)
        self.assertAlmostEqual(features['mid'].iloc[0], 5.1, places=6)
        self.assertEqual(features['mid_source'].iloc[0], 'bid_ask')

    def test_no_quotes_but_theoretical_still_works(self):
        """Нет bid/ask, но есть theoretical_price — строка не выкидывается."""
        obs_date = pd.Timestamp('2024-01-01')
        expiry = obs_date + pd.Timedelta(days=180)
        options = pd.DataFrame({
            'date': [obs_date],
            'strike': [100.0],
            'bid': [0.0],
            'ask': [0.0],
            'theoretical_price': [6.0],
            'expiry': [expiry],
            'type': ['call'],
            'underlying_price': [100.0],
        })
        features = build_features(pd.DataFrame(), options)
        self.assertEqual(len(features), 1)
        self.assertEqual(features['mid_source'].iloc[0], 'theoretical')
        # bid_ask_spread_pct = 0, потому что стакана нет
        self.assertEqual(features['bid_ask_spread_pct'].iloc[0], 0.0)

    def test_multiple_expirations_have_different_T(self):
        """Разные экспирации в одном файле — каждая считается со своим days_to_expiry."""
        obs_date = pd.Timestamp('2024-01-01')
        options = pd.DataFrame({
            'date': [obs_date, obs_date, obs_date],
            'strike': [100.0, 100.0, 100.0],
            'bid': [5.0, 5.0, 5.0],
            'ask': [5.2, 5.2, 5.2],
            'expiry': [
                obs_date + pd.Timedelta(days=7),
                obs_date + pd.Timedelta(days=30),
                obs_date + pd.Timedelta(days=180),
            ],
            'type': ['call', 'call', 'call'],
            'underlying_price': [100.0, 100.0, 100.0],
        })
        features = build_features(pd.DataFrame(), options).sort_values('days_to_expiry').reset_index(drop=True)
        self.assertEqual(len(features), 3)
        self.assertEqual(list(features['days_to_expiry']), [7, 30, 180])
        # Более дальняя экспирация — больше справедливая цена для ATM call
        self.assertLess(features['fair_value'].iloc[0], features['fair_value'].iloc[2])


if __name__ == '__main__':
    unittest.main()
