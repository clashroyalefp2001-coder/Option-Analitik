# models/inference.py
"""Загрузка обученной модели и применение её к признакам.

Используется в main_pipeline после build_features:
    df = apply_model_predictions(df)
"""

from __future__ import annotations

import os
import pickle
from typing import Optional

import numpy as np
import pandas as pd

from models.lgbm.trainer import MODEL_PATH


def load_model(path: str = MODEL_PATH):
    """Возвращает (model, features) или (None, None), если модели ещё нет."""
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        if isinstance(payload, dict) and "model" in payload:
            return payload["model"], payload.get("features", [])
        # Совместимость со старым форматом — голая модель
        return payload, None
    except Exception:
        return None, None


def apply_model_predictions(features_df: pd.DataFrame) -> pd.DataFrame:
    """Применяет модель к DataFrame, обновляя колонки `predicted_edge`
    и `signal_confidence`.

    Если модель отсутствует — возвращает df без изменений (predicted_edge
    остаётся аналитическим, посчитанным в feature_store).
    """
    if features_df is None or features_df.empty:
        return features_df

    model, features = load_model()
    if model is None:
        return features_df

    df = features_df.copy()
    if not features:
        # Без метаданных — нечего делать безопасно
        return df

    available = [c for c in features if c in df.columns]
    if len(available) != len(features):
        missing = set(features) - set(available)
        raise KeyError(
            f"В признаках отсутствуют колонки, ожидаемые моделью: {missing}"
        )

    X = df[available].astype(float).values
    try:
        preds = np.asarray(model.predict(X), dtype=float)
    except Exception:
        return df

    df["predicted_edge"] = preds

    # Уверенность ~ нормированная абсолютная величина предсказания
    abs_preds = np.abs(preds)
    if abs_preds.max() > 0:
        confidence = abs_preds / abs_preds.max()
        # Сжимаем в [0.5, 1.0] чтобы не отсекать всё на soft-фильтре
        df["signal_confidence"] = 0.5 + 0.5 * confidence
    else:
        df["signal_confidence"] = 0.5

    return df
