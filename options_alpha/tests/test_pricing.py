import math
import unittest

from pricing.binomial import price_american


class TestPricing(unittest.TestCase):
    def test_call_basic(self):
        res = price_american(S=100, K=100, T=0.5, r=0.05, sigma=0.2, dividend=0.0, option_type='call')
        # Все ключевые поля присутствуют
        for key in ['fair_value', 'delta', 'gamma', 'vega',
                    'theta', 'rho', 'early_exercise_premium', 'moneyness']:
            self.assertIn(key, res)
        # ATM call с T=0.5, sigma=0.20 ≈ 6.6
        self.assertAlmostEqual(res['fair_value'], 6.6, delta=0.5)
        # Delta ATM call ≈ 0.55–0.65
        self.assertGreater(res['delta'], 0.45)
        self.assertLess(res['delta'], 0.7)
        # Gamma положительная
        self.assertGreater(res['gamma'], 0.0)
        # American премия неотрицательна
        self.assertGreaterEqual(res['early_exercise_premium'], -1e-6)

    def test_call_vs_put_parity_signs(self):
        call = price_american(S=100, K=100, T=0.5, r=0.05, sigma=0.2, dividend=0.0, option_type='call')
        put = price_american(S=100, K=100, T=0.5, r=0.05, sigma=0.2, dividend=0.0, option_type='put')
        # Delta call > 0, delta put < 0
        self.assertGreater(call['delta'], 0)
        self.assertLess(put['delta'], 0)
        # Theta обычно отрицательная для long-опциона
        self.assertLess(call['theta'], 0)

    def test_T_actually_matters(self):
        """Главный фикс: T не должен быть захардкоден. Разные T → разные fair values."""
        short = price_american(S=100, K=100, T=0.05, r=0.05, sigma=0.2, dividend=0.0, option_type='call')
        long = price_american(S=100, K=100, T=1.0, r=0.05, sigma=0.2, dividend=0.0, option_type='call')
        self.assertGreater(long['fair_value'], short['fair_value'])
        # Long opcion имеет более высокую vega
        self.assertGreater(long['vega'], short['vega'])

    def test_moneyness(self):
        res = price_american(S=110, K=100, T=0.5, r=0.05, sigma=0.2, dividend=0.0, option_type='call')
        self.assertAlmostEqual(res['moneyness'], math.log(110/100), places=5)


if __name__ == '__main__':
    unittest.main()
