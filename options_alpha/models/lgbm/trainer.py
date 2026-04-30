# models/lgbm/trainer.py
"""Полноценный пайплайн обучения модели предсказания edge.

Что делает:
  1) Принимает DataFrame признаков из feature_store.build_features
  2) Строит таргет (mispricing — справедливое отклонение от mid)
  3) Делит данные хронологически на train/val
  4) Обучает регрессор (LightGBM, если доступен; иначе sklearn GBR; иначе DummyMean)
  5) Сохраняет модель + метаданные (список фичей, метрики, важность)
  6) Возвращает все метрики единым словарём для UI / отчёта
"""

from __future__ import annotations

import json
import math
import os
import pickle
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# Список признаков, которые модель использует на инференсе.
# Должен быть стабильным — при изменении нужно переобучать модель.
FEATURE_COLUMNS: List[str] = [
    "fair_value",
    "mid",
    "mispricing",
    "delta",
    "gamma",
    "vega",
    "theta",
    "rho",
    "early_exercise_premium",
    "moneyness",
    "days_to_expiry",
    "bid_ask_spread_pct",
    "open_interest",
    "daily_volume",
    "iv_rank",
]

TARGET_COLUMN = "target_edge"

MODEL_DIR = os.path.join("models", "lgbm")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
META_PATH = os.path.join(MODEL_DIR, "model_meta.json")


def build_target(df: pd.DataFrame) -> pd.Series:
    """Целевая переменная: насколько fair_value отклоняется от mid.

    Положительное значение → опцион недооценён (имеет смысл покупать).
    Отрицательное → переоценён (имеет смысл шортить или избегать).

    На реальных данных рекомендуется заменить на forward-return (PnL через N
    дней), но для этого нужны исторические серии котировок. Mispricing —
    рабочий прокси для MVP и обеспечивает обучаемый сигнал.
    """
    if "fair_value" not in df.columns or "mid" not in df.columns:
        raise KeyError("DataFrame должен содержать колонки 'fair_value' и 'mid'")
    return (df["fair_value"] - df["mid"]).astype(float)


def _split_chronological(
    df: pd.DataFrame, val_ratio: float = 0.2
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Хронологический train/val split. Если есть колонка 'date' —
    сортируем по ней; иначе считаем DataFrame уже упорядоченным."""
    if "date" in df.columns:
        df = df.sort_values("date", kind="stable").reset_index(drop=True)
    n = len(df)
    n_val = max(1, int(n * val_ratio))
    return df.iloc[: n - n_val].copy(), df.iloc[n - n_val :].copy()


def _build_model():
    """Возвращает (model, backend_name).

    Приоритет: LightGBM → sklearn GradientBoostingRegressor → DummyMean.
    """
    # 1. LightGBM
    try:
        import lightgbm as lgb  # type: ignore

        model = lgb.LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=5,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            verbose=-1,
        )
        return model, "lightgbm"
    except Exception:
        pass

    # 2. sklearn GBR
    try:
        from sklearn.ensemble import GradientBoostingRegressor

        model = GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.05, max_depth=3, random_state=42
        )
        return model, "sklearn_gbr"
    except Exception:
        pass

    # 3. Final fallback
    class DummyMean:
        def fit(self, X, y):
            self.mean_ = float(np.mean(y)) if len(y) else 0.0
            return self

        def predict(self, X):
            return np.full(len(X), self.mean_, dtype=float)

    return DummyMean(), "dummy_mean"


def _safe_metric(fn, *args, **kwargs) -> float:
    try:
        return float(fn(*args, **kwargs))
    except Exception:
        return 0.0


def _direction_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Метрики качества предсказания знака edge (классификация направления)."""
    try:
        from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
    except Exception:
        return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0}

    yt = (y_true > 0).astype(int)
    yp_bin = (y_pred > 0).astype(int)
    metrics = {
        "precision": _safe_metric(precision_score, yt, yp_bin, zero_division=0),
        "recall": _safe_metric(recall_score, yt, yp_bin, zero_division=0),
        "f1_score": _safe_metric(f1_score, yt, yp_bin, zero_division=0),
    }
    # ROC-AUC требует обоих классов
    if len(np.unique(yt)) == 2:
        metrics["roc_auc"] = _safe_metric(roc_auc_score, yt, y_pred)
    else:
        metrics["roc_auc"] = 0.0
    return metrics


def _feature_importance(model, features: List[str]) -> Dict[str, float]:
    """Извлекает feature importance, нормализованную в сумму = 1.0."""
    raw = None
    if hasattr(model, "feature_importances_"):
        raw = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        raw = np.abs(np.asarray(model.coef_, dtype=float)).ravel()

    if raw is None or raw.sum() == 0:
        # Равномерное распределение для DummyMean
        equal = 1.0 / len(features)
        return {f: equal for f in features}

    raw = raw[: len(features)]
    total = raw.sum()
    return {features[i]: float(raw[i] / total) for i in range(len(features))}


def train_model(
    features_df: pd.DataFrame,
    val_ratio: float = 0.2,
    save: bool = True,
) -> dict:
    if features_df is None or features_df.empty:
        raise ValueError("features_df пуст — нечего обучать")

    df = features_df.copy(deep=True) # Исключает Chained assignment
    df[TARGET_COLUMN] = build_target(df)

    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    if len(available) < 3:
        raise ValueError(f"Слишком мало признаков: {available}")

    df = df.dropna(subset=available + [TARGET_COLUMN])
    if len(df) < 10:
        raise ValueError(f"Слишком мало строк: {len(df)}")

    train_df, val_df = _split_chronological(df, val_ratio=val_ratio)

    # УБРАЛИ конвертацию через .values! Сохраняем как DataFrame
    X_train = train_df[available].astype(float)
    y_train = train_df[TARGET_COLUMN].values
    X_val = val_df[available].astype(float)
    y_val = val_df[TARGET_COLUMN].values

    model, backend = _build_model()

    import time
    t0 = time.perf_counter()
    model.fit(X_train, y_train)
    training_time = time.perf_counter() - t0

    pred_train = model.predict(X_train)
    pred_val = model.predict(X_val) if len(X_val) > 0 else np.array([])

    train_mse = _safe_metric(lambda: float(np.mean((pred_train - y_train) ** 2)))
    val_mse = (_safe_metric(lambda: float(np.mean((pred_val - y_val) ** 2))) if len(pred_val) > 0 else 0.0)

    direction = _direction_metrics(y_val, pred_val) if len(pred_val) > 0 else {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0}
    importance = _feature_importance(model, available)

    metrics = {
        "backend": backend,
        "features": available,
        "training_loss": train_mse,
        "validation_loss": val_mse,
        "training_accuracy": 0.0,
        "validation_accuracy": 0.0,
        "feature_importance": importance,
        "roc_auc": direction["roc_auc"],
        "precision": direction["precision"],
        "recall": direction["recall"],
        "f1_score": direction["f1_score"],
        "trading_samples": int(len(df)),
        "train_samples": int(len(train_df)),
        "val_samples": int(len(val_df)),
        "epochs": int(getattr(model, "n_estimators", 1)),
        "training_time": float(training_time),
    }

    if save:
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({"model": model, "features": available}, f)
        import json
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump({"backend": backend, "features": available, "metrics": metrics}, f, indent=2, ensure_ascii=False)

    return metrics


# Совместимость со старым API
def train_lgbm(X: pd.DataFrame, y: pd.Series):
    """Старый интерфейс. Сохраняем для существующего кода/тестов."""
    model, _ = _build_model()
    model.fit(np.asarray(X, dtype=float), np.asarray(y, dtype=float))
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "features": list(X.columns)}, f)
    return model, MODEL_PATH
