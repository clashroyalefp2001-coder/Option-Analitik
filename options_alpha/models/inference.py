from __future__ import annotations
import os
import pickle
from typing import Optional
import numpy as np
import pandas as pd
from models.lgbm.trainer import MODEL_PATH

def load_model(path: str = MODEL_PATH):
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        if isinstance(payload, dict) and "model" in payload:
            return payload["model"], payload.get("features", [])
        return payload, None
    except Exception:
        return None, None

def apply_model_predictions(features_df: pd.DataFrame) -> pd.DataFrame:
    if features_df is None or features_df.empty:
        return features_df

    model, features = load_model()
    if model is None:
        return features_df

    df = features_df.copy(deep=True)  # Явное глубокое копирование
    if not features:
        return df

    available = [c for c in features if c in df.columns]
    if len(available) != len(features):
        missing = set(features) - set(available)
        raise KeyError(f"В признаках отсутствуют ожидаемые колонки: {missing}")

    # Передаем pandas DataFrame, а не numpy array (.values удалено)
    X = df[available].astype(float)
    try:
        preds = np.asarray(model.predict(X), dtype=float)
    except Exception:
        return df

    df["predicted_edge"] = preds

    abs_preds = np.abs(preds)
    if abs_preds.max() > 0:
        confidence = abs_preds / abs_preds.max()
        df["signal_confidence"] = 0.5 + 0.5 * confidence
    else:
        df["signal_confidence"] = 0.5

    return df