import os
import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd

from models.lgbm.trainer import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_target,
    train_model,
)


def _make_features(n: int = 80, seed: int = 0) -> pd.DataFrame:
    """Синтетический набор признаков, где fair_value и mid слегка различаются."""
    rng = np.random.default_rng(seed)
    underlying = 100.0 + rng.normal(0, 1, size=n)
    mid = underlying * 0.05 + rng.normal(0, 0.3, size=n) + 5.0
    fair = mid + rng.normal(0, 0.5, size=n)  # шумный mispricing
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "fair_value": fair,
        "mid": mid,
        "mispricing": fair - mid,
        "delta": rng.uniform(0.3, 0.7, n),
        "gamma": rng.uniform(0.01, 0.1, n),
        "vega": rng.uniform(0.1, 0.5, n),
        "theta": -rng.uniform(0.01, 0.05, n),
        "rho": rng.uniform(0.01, 0.1, n),
        "early_exercise_premium": rng.uniform(0, 0.05, n),
        "moneyness": rng.uniform(-0.2, 0.2, n),
        "days_to_expiry": rng.integers(10, 200, n),
        "bid_ask_spread_pct": rng.uniform(0.01, 0.05, n),
        "open_interest": rng.integers(0, 1000, n),
        "daily_volume": rng.integers(0, 500, n),
        "iv_rank": rng.uniform(0, 1, n),
    })


class TestBuildTarget(unittest.TestCase):
    def test_basic(self):
        df = pd.DataFrame({"fair_value": [10.0, 9.0], "mid": [9.5, 9.5]})
        target = build_target(df)
        self.assertAlmostEqual(target.iloc[0], 0.5)
        self.assertAlmostEqual(target.iloc[1], -0.5)

    def test_missing_columns_raises(self):
        with self.assertRaises(KeyError):
            build_target(pd.DataFrame({"fair_value": [1.0]}))


class TestTrainModel(unittest.TestCase):
    def setUp(self):
        # Изолируем модель от файловой системы проекта
        self.tmpdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_train_returns_metrics(self):
        df = _make_features(n=80)
        metrics = train_model(df, val_ratio=0.25, save=True)

        # Структура метрик
        for key in ["backend", "features", "training_loss", "validation_loss",
                    "feature_importance", "trading_samples", "train_samples", "val_samples"]:
            self.assertIn(key, metrics)

        # Backend выбран один из ожидаемых
        self.assertIn(metrics["backend"], {"lightgbm", "sklearn_gbr", "dummy_mean"})

        # MSE неотрицательный и конечный
        self.assertGreaterEqual(metrics["training_loss"], 0.0)
        self.assertGreaterEqual(metrics["validation_loss"], 0.0)
        self.assertFalse(np.isnan(metrics["validation_loss"]))

        # Сэмплы делятся хронологически 75/25
        self.assertEqual(metrics["train_samples"] + metrics["val_samples"], 80)

        # Feature importance суммируется в ~1
        total = sum(metrics["feature_importance"].values())
        self.assertAlmostEqual(total, 1.0, places=4)

        # Файлы модели созданы
        self.assertTrue(os.path.exists(os.path.join("models", "lgbm", "model.pkl")))
        self.assertTrue(os.path.exists(os.path.join("models", "lgbm", "model_meta.json")))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            train_model(pd.DataFrame(), save=False)


if __name__ == "__main__":
    unittest.main()
