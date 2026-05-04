# models/lgbm/trainer.py
"""Полноценный пайплайн обучения модели предсказания edge.

Что делает:
  1) Принимает DataFrame признаков из feature_store.build_features
  2) Строит таргет (forward return — доходность через N шагов)
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
# Убрали fair_value, mid, mispricing для исключения прямого ликажа (т.к. таргет - доходность mid).
FEATURE_COLUMNS: List[str] = [
    # Greeks
    "delta",
    "gamma",
    "vega",
    "theta",
    # Option specific
    "moneyness",
    "days_to_expiry",
    "bid_ask_spread_pct",
    # Underlying Dynamics (Momentum)
    "u_ret_1d",
    "u_ret_5d",
    "u_ret_20d",
    "u_dist_ema_20",
    # Volatility Features
    "iv",
    "iv_rank",
    "u_rv_20d",
    "iv_premium", # IV / RV spread
    "iv_skew",    # IV Skew
    "iv_ts_slope" # Term structure slope
]

TARGET_COLUMN = "target_return"

MODEL_DIR = os.path.join("models", "lgbm")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
META_PATH = os.path.join(MODEL_DIR, "model_meta.json")


def build_target(df: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """Целевая переменная: доходность опциона через N шагов (forward return).

    Критически важный метод. Если в данных только один снапшот на контракт,
    shift(-horizon) вернёт NaN. В этом случае обучение модели на рыночных данных 
    становится невозможным без временных рядов.
    """
    if "mid" not in df.columns:
        raise KeyError("DataFrame должен содержать колонку 'mid' для расчета доходности")

    # 1. Определяем ключ группы (один и тот же контракт во времени)
    group_cols = []
    if "option_symbol" in df.columns:
        group_cols = ["option_symbol"]
    elif all(c in df.columns for c in ["strike", "type", "expiry"]):
        # Если нет уникального символа, идентифицируем по страйку/экспирации/типу
        group_cols = ["strike", "type", "expiry"]
    
    # 2. Считаем будущую цену через shift
    if group_cols:
        # Сортируем по времени внутри группы для корректного сдвига
        # Предполагаем наличие колонки 'date' или 'timestamp'
        time_col = "date" if "date" in df.columns else None
        
        if time_col:
            # Создаем временную копию для безопасного сдвига
            temp_df = df[[*group_cols, time_col, "mid"]].sort_values([*group_cols, time_col])
            future_mid = temp_df.groupby(group_cols)["mid"].shift(-horizon)
        else:
            # Если даты нет, надеемся на порядок в исходном DF
            future_mid = df.groupby(group_cols)["mid"].shift(-horizon)
    else:
        future_mid = df["mid"].shift(-horizon)
    
    # 3. Проверка на пустоту (Data Quality Check)
    valid_count = future_mid.notna().sum()
    if valid_count == 0:
        # ТЕРМИНАЛЬНАЯ ОШИБКА РЕАЛИЗМА: 
        # Если мы здесь, значит в данных на каждый контракт приходится <= horizon строк.
        # Модель не может выучить динамику рынка, т.к. нет 'будущего'.
        print(f"[build_target] WARNING: Target is 100% NaN. Horizon={horizon} is too large or data is not a timeseries.")
        # В качестве крайней меры (для отладки пайплайна) возвращаем NaN, 
        # но логгируем проблему. Модель в train_model упадет или выдаст ошибку.
        return pd.Series(np.nan, index=df.index)

    # 4. Расчет доходности
    target = (future_mid / df["mid"]) - 1.0
    
    # Регуляризация (ограничение выбросов для стабильности градиента)
    target = target.clip(-1.0, 5.0) 
    target = target.replace([np.inf, -np.inf], np.nan)
    
    return target


def generate_purged_walk_forward_splits(
    n_rows: int,
    train_size: int,
    val_size: int,
    horizon: int,
    embargo: int
) -> List[dict]:
    splits = []
    cursor = train_size

    while True:
        train_end = cursor
        val_start = train_end + embargo + horizon
        val_end = val_start + val_size

        if val_end > n_rows:
            break

        splits.append({
            "train_idx": np.arange(0, train_end),
            "val_idx": np.arange(val_start, val_end)
        })

        cursor += val_size
    return splits


def _trading_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Вычисляет специфичные для трейдинга метрики: IC, rank correlation."""
    if len(y_true) < 2 or len(np.unique(y_true)) < 2:
        return {"ic": 0.0, "rank_ic": 0.0}

    from scipy.stats import spearmanr # type: ignore
    
    # Pearson Correlation (Information Coefficient)
    try:
        ic = float(np.corrcoef(y_true, y_pred)[0, 1])
        if np.isnan(ic): ic = 0.0
    except:
        ic = 0.0
        
    # Spearman Rank Correlation (Rank IC)
    try:
        rank_ic, _ = spearmanr(y_true, y_pred)
        rank_ic = float(rank_ic)
        if np.isnan(rank_ic): rank_ic = 0.0
    except:
        rank_ic = 0.0
        
    return {
        "ic": round(ic, 4),
        "rank_ic": round(rank_ic, 4)
    }


def _build_model():
    """Возвращает (model, backend_name).

    Приоритет: LightGBM → sklearn GradientBoostingRegressor → DummyMean.
    """
    # 1. LightGBM
    try:
        import lightgbm as lgb  # type: ignore

        model = lgb.LGBMRegressor(
            n_estimators=300,
            learning_rate=0.03, # Немного уменьшили для стабильности на доходностях
            num_leaves=31,
            min_child_samples=10,
            subsample=0.8,
            colsample_bytree=0.8,
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
    """Метрики качества предсказания знака доходности (классификация направления)."""
    try:
        from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
    except Exception:
        return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0}

    # Считаем попадание в знак (будет ли доходность положительной)
    yt = (y_true > 0).astype(int)
    yp_bin = (y_pred > 0).astype(int)
    
    metrics = {
        "precision": _safe_metric(precision_score, yt, yp_bin, zero_division=0),
        "recall": _safe_metric(recall_score, yt, yp_bin, zero_division=0),
        "f1_score": _safe_metric(f1_score, yt, yp_bin, zero_division=0),
    }
    
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
        equal = 1.0 / len(features)
        return {f: equal for f in features}

    raw = raw[: len(features)]
    total = raw.sum()
    return {features[i]: float(raw[i] / total) for i in range(len(features))}


def train_model(
    features_df: pd.DataFrame,
    save: bool = True,
    horizon: int = 5,
    n_folds: int = 3,
) -> dict:
    if features_df is None or features_df.empty:
        raise ValueError("features_df пуст — нечего обучать")

    df = features_df.copy(deep=True)
    df[TARGET_COLUMN] = build_target(df, horizon=horizon)

    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    
    # Удаляем строки, где нет таргета
    df = df.dropna(subset=available + [TARGET_COLUMN])
    
    if len(df) < 50: # Увеличили порог для CV
        raise ValueError(f"Слишком мало строк для обучения с CV: {len(df)}")

    # Walk-forward CV
    n_rows = len(df)
    train_size = int(n_rows * 0.5)
    val_size = int(n_rows * 0.1)
    embargo = 5
    folds = generate_purged_walk_forward_splits(
        n_rows=n_rows,
        train_size=train_size,
        val_size=val_size,
        horizon=horizon,
        embargo=embargo
    )
    
    fold_metrics = []
    final_model = None
    
    for i, split in enumerate(folds):
        train_df = df.iloc[split["train_idx"]]
        val_df = df.iloc[split["val_idx"]]
        X_train = train_df[available].astype(float)
        y_train = train_df[TARGET_COLUMN].values
        X_val = val_df[available].astype(float)
        y_val = val_df[TARGET_COLUMN].values

        model, backend = _build_model()
        model.fit(X_train, y_train)
        
        # Предсказания на валидации
        pred_val = model.predict(X_val)
        
        # Метрики фолда
        mse = float(np.mean((pred_val - y_val) ** 2))
        dir_m = _direction_metrics(y_val, pred_val)
        trad_m = _trading_metrics(y_val, pred_val)
        
        fold_metrics.append({
            "mse": mse,
            **dir_m,
            **trad_m
        })
        
        # Сохраняем модель из самого последнего фолда (самые свежие данные)
        if i == n_folds - 1:
            final_model = model

    # Усредняем метрики по фолдам
    avg_metrics: Dict[str, Any] = {
        "validation_loss": float(np.mean([m["mse"] for m in fold_metrics])),
        "precision": float(np.mean([m["precision"] for m in fold_metrics])),
        "recall": float(np.mean([m["recall"] for m in fold_metrics])),
        "f1_score": float(np.mean([m["f1_score"] for m in fold_metrics])),
        "roc_auc": float(np.mean([m["roc_auc"] for m in fold_metrics])),
        "ic": float(np.mean([m["ic"] for m in fold_metrics])),
        "rank_ic": float(np.mean([m["rank_ic"] for m in fold_metrics])),
    }

    # Итоговое обучение на ВСЕХ данных для финальной модели (опционально, 
    # или используем последнюю модель из CV чтобы избежать look-ahead)
    # По классике walk-forward мы используем последнюю модель или переобучаем до "сегодня".
    
    importance = _feature_importance(final_model, available)
    
    metrics = {
        "backend": backend,
        "features": available,
        "training_loss": 0.0, # В CV фокусе на вал
        **avg_metrics,
        "feature_importance": importance,
        "trading_samples": int(len(df)),
    }

    if save and final_model:
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({"model": final_model, "features": available}, f)
        
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump({"backend": backend, "features": available, "metrics": metrics}, f, indent=2, ensure_ascii=False)

    return metrics


# --- Market Forecasting Logic (New Integrated Functionality) ---

class MarketForecaster:
    def __init__(self, params: dict = None):
        import lightgbm as lgb
        if params is None:
            params = {
                "n_estimators": 100,
                "learning_rate": 0.05,
                "num_leaves": 31,
                "objective": "multiclass",
                "num_class": 3,
                "random_state": 42,
                "verbose": -1
            }
        self.params = params
        self.model = lgb.LGBMClassifier(**params)
        self.is_trained = False
        self.features = []
        self.calibrator = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> dict:
        """Обучение модели с валидацией."""
        import lightgbm as lgb
        self.features = X_train.columns.tolist()
        # y_train/y_val: -1, 0, 1 -> 0, 1, 2
        y_train_shifted = y_train + 1
        y_val_shifted = y_val + 1
        
        self.model.fit(
            X_train,
            y_train_shifted,
            eval_set=[(X_val, y_val_shifted)],
            callbacks=[lgb.early_stopping(stopping_rounds=20)]
        )
        
        self.is_trained = True
        return self._compute_metrics(X_val, y_val_shifted)

    def predict_distribution(self, X: pd.DataFrame) -> dict:
        """Возвращает вероятности для каждого класса (Bear, Neutral, Bull)."""
        probs = self.model.predict_proba(X)
        if getattr(self, 'calibrator', None) is not None:
            probs = self.calibrator.transform(probs)
            
        if probs.ndim == 1 or probs.shape[0] == 1:
            p = probs[0] if probs.ndim > 1 else probs
            return {"bear_prob": p[0], "neutral_prob": p[1], "bull_prob": p[2]}
        return {
            "bear_prob": probs[:, 0],
            "neutral_prob": probs[:, 1],
            "bull_prob": probs[:, 2],
        }

    def _compute_metrics(self, X_val, y_val_shifted):
        preds = self.model.predict(X_val)
        accuracy = (preds == y_val_shifted).mean()
        importances = dict(zip(X_val.columns, self.model.feature_importances_.tolist()))
        importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))
        return {"val_accuracy": accuracy, "feature_importance": importances}

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import joblib
        joblib.dump({"model": self.model, "features": self.features}, path)

    def load(self, path: str):
        import joblib
        if os.path.exists(path):
            data = joblib.load(path)
            self.model = data["model"]
            self.features = data["features"]
            self.is_trained = True


def generate_walk_forward_splits(n_rows: int, train_size: int, val_size: int, embargo: int) -> List[Dict]:
    splits = []
    current_end = n_rows
    split_id = 0
    while current_end > train_size + val_size + embargo:
        val_end = current_end
        val_start = val_end - val_size
        train_end = val_start - embargo
        train_start = max(0, train_end - train_size)
        if train_end <= train_start: break
        splits.append({"train_idx": list(range(train_start, train_end)), "val_idx": list(range(val_start, val_end)), "split_id": split_id})
        current_end -= val_size
        split_id += 1
    return splits[::-1]

import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from dataclasses import dataclass
class ProbabilityCalibrator:
    """
    Калибратор вероятностей моделей (Platt Scaling, Isotonic Regression, Temperature Scaling).
    """
    def __init__(self, method='isotonic'):
        self.method = method
        self.calibrators = []
        self.temperature = 1.0

    def fit(self, raw_probs: np.ndarray, y_true: np.ndarray):
        from sklearn.calibration import IsotonicRegression
        from sklearn.linear_model import LogisticRegression
        n_classes = raw_probs.shape[1]
        
        if self.method == 'isotonic':
            self.calibrators = []
            for c in range(n_classes):
                ir = IsotonicRegression(out_of_bounds='clip')
                y_bin = (y_true == c).astype(float)
                ir.fit(raw_probs[:, c], y_bin)
                self.calibrators.append(ir)
                
        elif self.method == 'platt':
            self.calibrators = []
            for c in range(n_classes):
                lr = LogisticRegression(solver='lbfgs')
                y_bin = (y_true == c).astype(float)
                lr.fit(raw_probs[:, c].reshape(-1, 1), y_bin)
                self.calibrators.append(lr)
                
        elif self.method == 'temperature':
            self.temperature = 1.5
            
    def transform(self, raw_probs: np.ndarray) -> np.ndarray:
        n_classes = raw_probs.shape[1]
        calibrated = np.zeros_like(raw_probs)
        
        if getattr(self, 'calibrators', None) is None and getattr(self, 'temperature', None) is None:
            return raw_probs
            
        if self.method == 'isotonic':
            for c in range(n_classes):
                calibrated[:, c] = self.calibrators[c].transform(raw_probs[:, c])
                
        elif self.method == 'platt':
            for c in range(n_classes):
                calibrated[:, c] = self.calibrators[c].predict_proba(raw_probs[:, c].reshape(-1, 1))[:, 1]
                
        elif self.method == 'temperature':
            eps = 1e-7
            logits = np.log(np.clip(raw_probs, eps, 1 - eps))
            scaled_logits = logits / self.temperature
            exp_logits = np.exp(scaled_logits)
            calibrated = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
            return calibrated
            
        row_sums = calibrated.sum(axis=1)[:, np.newaxis]
        row_sums[row_sums == 0] = 1e-7
        calibrated = calibrated / row_sums
        return calibrated


@dataclass
class TrainingArtifact:
    model: Any
    metrics: Dict[str, float]
    fold_metrics: List[Dict[str, float]]
    features: List[str]
    calibrator: Any = None

def train_walk_forward(X: pd.DataFrame, y: pd.Series, splits: List[Dict], reports_dir: str = "reports") -> TrainingArtifact:
    import lightgbm as lgb
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, brier_score_loss, log_loss
    from monitoring.metrics import ForecastDiagnosticsReport
    import os

    os.makedirs(reports_dir, exist_ok=True)
    report_gen = ForecastDiagnosticsReport(output_dir=reports_dir)

    fold_metrics = []
    y_shifted = y + 1

    final_model = None
    final_calibrator = None
    features = X.columns.tolist()
    
    all_raw_probs = []
    all_calib_probs = []
    all_y_val = []
    all_preds = []

    for split in splits:
        model = lgb.LGBMClassifier(
            n_estimators=100, learning_rate=0.05, num_leaves=31, 
            objective="multiclass", num_class=3, random_state=42, verbose=-1
        )
        X_train, y_train = X.iloc[split["train_idx"]], y_shifted.iloc[split["train_idx"]]
        X_val, y_val = X.iloc[split["val_idx"]], y_shifted.iloc[split["val_idx"]]

        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
        )
        final_model = model

        preds = model.predict(X_val)
        raw_probs = model.predict_proba(X_val)
        
        # Fit Calibrator
        calibrator = ProbabilityCalibrator(method='isotonic')
        calibrator.fit(raw_probs, y_val.values)
        probs = calibrator.transform(raw_probs)
        final_calibrator = calibrator

        all_raw_probs.append(raw_probs)
        all_calib_probs.append(probs)
        all_y_val.append(y_val.values)
        all_preds.append(np.argmax(probs, axis=1) if probs is not None else preds)

        acc = accuracy_score(y_val, preds)
        f1 = f1_score(y_val, preds, average="macro", zero_division=0)
        prec = precision_score(y_val, preds, average="macro", zero_division=0)
        rec = recall_score(y_val, preds, average="macro", zero_division=0)
        
        try:
            ll = log_loss(y_val, probs, labels=[0, 1, 2])
        except Exception:
            ll = float('nan')

        brier = 0.0
        for c in range(3):
            y_true_c = (y_val == c).astype(int)
            if c < probs.shape[1]:
                brier += brier_score_loss(y_true_c, probs[:, c])
        brier /= 3.0
        
        # simple placeholder for calibration error 
        calib_error = np.mean(np.abs(np.max(probs, axis=1) - (preds == y_val).astype(float)))
        
        fold_metrics.append({
            "accuracy": float(acc),
            "f1_macro": float(f1),
            "precision_macro": float(prec),
            "recall_macro": float(rec),
            "logloss": float(ll) if not math.isnan(ll) else 0.0,
            "brier_score": float(brier),
            "calibration_error": float(calib_error)
        })

    if not fold_metrics:
        avg_metrics = {}
    else:
        avg_metrics = {k: float(np.mean([m[k] for m in fold_metrics])) for k in fold_metrics[0].keys()}
        
        # Generate diagnostic files
        cat_raw_probs = np.vstack(all_raw_probs)
        cat_calib_probs = np.vstack(all_calib_probs)
        cat_y_val = np.concatenate(all_y_val)
        cat_preds = np.concatenate(all_preds)
        
        report_gen.generate_probability_histogram(cat_raw_probs, cat_calib_probs)
        report_gen.generate_class_distribution(cat_y_val, cat_preds)
        report_gen.generate_calibration_curve(cat_y_val, cat_calib_probs)
        if final_model is not None:
            report_gen.generate_feature_importance(final_model, features)
    
    # Build forecaster to wrap it
    artifact = TrainingArtifact(
        model=final_model,
        metrics=avg_metrics,
        fold_metrics=fold_metrics,
        features=features,
        calibrator=final_calibrator
    )
    return artifact


def train_walk_forward_fold(X: pd.DataFrame, y: pd.Series, split: Dict) -> TrainingArtifact:
    import lightgbm as lgb
    X_train, y_train = X.iloc[split["train_idx"]], (y + 1).iloc[split["train_idx"]]
    X_val, y_val = X.iloc[split["val_idx"]], (y + 1).iloc[split["val_idx"]]

    model = lgb.LGBMClassifier(
            n_estimators=100, learning_rate=0.05, num_leaves=31, 
            objective="multiclass", num_class=3, random_state=42, verbose=-1
        )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
    )
    
    raw_probs = model.predict_proba(X_val)
    calibrator = ProbabilityCalibrator(method='isotonic')
    calibrator.fit(raw_probs, y_val.values)
    
    return TrainingArtifact(
        model=model,
        metrics={},
        fold_metrics=[],
        features=X.columns.tolist(),
        calibrator=calibrator
    )

