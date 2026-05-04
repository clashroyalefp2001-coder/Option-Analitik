import os
import numpy as np
import pandas as pd
import joblib

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
        joblib.dump({"model": self.model, "features": self.features}, path)

    def load(self, path: str):
        if os.path.exists(path):
            data = joblib.load(path)
            self.model = data["model"]
            self.features = data["features"]
            self.is_trained = True
