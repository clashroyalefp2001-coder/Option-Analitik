import unittest
import pandas as pd
from models.feature_store import build_features

class TestFeatureStore(unittest.TestCase):
    def test_build_features_columns(self):
        # Mock underlying
        underlying = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01']),
            'price': [100.0]
        })
        # Mock options
        options = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01']),
            'strike': [100],
            'bid': [5.0],
            'ask': [5.2],
            'expiry': ['2024-06-20'],
            'type': ['call'],
            'underlying_price': [100.0]
        })
        # Build features
        features = build_features(underlying, options)
        # Check expected columns exist
        expected = {'fair_value', 'mispricing', 'bid_ask_adjusted_edge',
                    'delta', 'gamma', 'vega', 'theta', 'moneyness',
                    'iv_rank', 'days_to_expiry', 'bid_ask_spread_pct',
                    'open_interest', 'daily_volume'}
        self.assertTrue(expected.issubset(set(features.columns)))
        # Check no NaN in critical columns
        for col in ['fair_value', 'delta', 'gamma', 'vega', 'theta']:
            self.assertFalse(features[col].isna().any(), f'Column {col} contains NaN')
        # Check at least one row
        self.assertGreater(len(features), 0)

if __name__ == '__main__':
    unittest.main()
