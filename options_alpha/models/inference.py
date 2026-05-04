# models/inference.py
"""Применение обученной модели к новым данным."""

from __future__ import annotations
import os
import pickle
import pandas as pd
import numpy as np

MODEL_PATH = os.path.join("models", "lgbm", "model.pkl")

def apply_model_predictions(df: pd.DataFrame) -> pd.DataFrame:
    """Загружает модель и предсказывает edge."""
    if df.empty:
        return df
        
    res = df.copy()
    
    if not os.path.exists(MODEL_PATH):
        # Если модели нет, предсказываем 0 (нейтрально)
        res["predicted_edge"] = 0.0
        res["signal_confidence"] = 0.5
        return res
        
    try:
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
            model = data["model"]
            features = data["features"]
            
        # Убеждаемся, что все фичи есть
        X = res[features].astype(float)
        res["predicted_edge"] = model.predict(X)
        
        # Сигма-прокси для уверенности (confidence)
        # В реальности можно использовать predict_proba или разброс на кросс-валидации
        res["signal_confidence"] = 0.5 + np.clip(res["predicted_edge"] * 10, -0.49, 0.49)
        
    except Exception:
        res["predicted_edge"] = 0.0
        res["signal_confidence"] = 0.5
        
    return res
