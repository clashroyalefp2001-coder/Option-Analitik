import unittest
import pandas as pd
import math
from pricing.binomial import price_american
from config import DEFAULT_SIGMA, DEFAULT_R, DEFAULT_DIVIDEND

class TestPricing(unittest.TestCase):
    def test_call_option(self):
        res = price_american(S=100, K=100, T=1.0, r=0.05, sigma=0.2, dividend=0.0, option_type='call')
        self.assertGreaterEqual(res['fair_value'], 0.0)
        self.assertIn('delta', res)
        self.assertIn('gamma', res)
        self.assertIn('vega', res)
        self.assertIn('theta', res)
        self.assertIn('rho', res)
        self.assertIn('early_exercise_premium', res)
        self.assertAlmostEqual(res['moneyness'], math.log(100/100), places=5)

    def test_call_vs_put(self):
        call = price_american(S=100, K=100, T=0.5, r=0.05, sigma=0.2, dividend=0.0, option_type='call')
        put = price_american(S=100, K=100, T=1.0, r=0.05, sigma=0.2, dividend=0.0, option_type='put')
        # At-the-money forward call price should be higher than put price
        self.assertGreater(call['fair_value'], put['fair_value'])

if __name__ == '__main__':
    unittest.main()