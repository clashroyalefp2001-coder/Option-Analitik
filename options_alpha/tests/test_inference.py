import os
import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd

from models.inference import apply_model_predictions, load_model
from models.lgbm.trainer import train_model
from tests.test_trainer import _make_features  # noqa: F401  переиспользуем фикстуру


class TestInference(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_model_returns_unchanged(self):
        df = pd.DataFrame({"predicted_edge": [0.1, 0.2], "signal_confidence": [0.5, 0.5]})
        out = apply_model_predictions(df)
        # Нет модели — df возвращается как есть
        pd.testing.assert_frame_equal(out, df)

    def test_predictions_overwrite_edge(self):
        df = _make_features(n=60)
        df["predicted_edge"] = 0.0
        df["signal_confidence"] = 0.5

        train_model(df, val_ratio=0.25, save=True)
        model, features = load_model()
        self.assertIsNotNone(model)
        self.assertGreater(len(features), 0)

        out = apply_model_predictions(df)
        # predicted_edge перезаписан моделью
        self.assertFalse(np.allclose(out["predicted_edge"].values, 0.0))
        # signal_confidence в диапазоне [0.5, 1.0]
        self.assertTrue((out["signal_confidence"] >= 0.5 - 1e-9).all())
        self.assertTrue((out["signal_confidence"] <= 1.0 + 1e-9).all())

    def test_empty_df(self):
        out = apply_model_predictions(pd.DataFrame())
        self.assertTrue(out.empty)


if __name__ == "__main__":
    unittest.main()
