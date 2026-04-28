# models/lgbm/trainer.py
"""Обучение базовой модели (работает без внешних зависимостей).
Использует sklearn, если доступен; иначе DummyRegressor / DummyMean.
Сохранение модели через pickle, чтобы избежать зависимости от joblib.
"""
import pandas as pd
import pickle
import os

def train_lgbm(X: pd.DataFrame, y: pd.Series):
    model = None
    model_path = os.path.join("models", "lgbm", "model.pkl")

    # GradientBoostingRegressor (часть sklearn, но может быть недоступен)
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
        )
        model.fit(X, y)
    except Exception:
        pass

    # Если не удалось — DummyRegressor
    if model is None:
        try:
            from sklearn.dummy import DummyRegressor
            model = DummyRegressor(strategy="mean")
            model.fit(X, y)
        except Exception:
            # Финальный fallback без sklearn
            class DummyMean:
                def fit(self, X, y):
                    self.mean_ = y.mean()
                def predict(self, X):
                    import numpy as np
                    return np.full(len(X), self.mean_, dtype=float)
            model = DummyMean()
            model.fit(X, y)

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    return model, model_path
