# monitoring/metrics.py
"""Вычисление KPI и метрик качества модели"""

import pandas as pd
from typing import Dict, Any, Optional
import numpy as np

def compute_kpis(equity_curve, trades) -> Dict[str, Any]:
    """Вычисление ключевых метрик из equity curve и списка сделок."""
    # Преобразование equity_curve в Series
    if not isinstance(equity_curve, pd.Series):
        equity_curve = pd.Series(equity_curve or [1_000_000])

    if equity_curve.empty:
        equity_curve = pd.Series([1_000_000])

    # Total return
    total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0] if len(equity_curve) > 1 else 0.0

    # Sharpe ratio
    if len(equity_curve) >= 2:
        returns = equity_curve.pct_change().dropna()
        std_ret = returns.std()
        sharpe_ratio = (returns.mean() / std_ret) * (252 ** 0.5) if std_ret > 0 else 0.0
    else:
        sharpe_ratio = 0.0

    # Max drawdown
    if len(equity_curve) > 1:
        running_max = equity_curve.cummax()
        drawdowns = (equity_curve - running_max) / running_max * 100
        max_drawdown = drawdowns.min() if len(drawdowns) > 0 else 0.0
    else:
        max_drawdown = 0.0

    # Hit rate
    if isinstance(trades, pd.DataFrame):
        trades_df = trades
    elif isinstance(trades, dict):
        trades_df = pd.DataFrame(trades)
    else:
        trades_df = pd.DataFrame()

    if trades_df.empty:
        hit_rate = 0.0
    else:
        profitable = (trades_df["pnl"] > 0).sum() if "pnl" in trades_df.columns else 0
        hit_rate = float(profitable / len(trades_df)) if len(trades_df) > 0 else 0.0

    return {
        "sharpe_ratio": round(float(sharpe_ratio), 4),
        "max_drawdown": round(float(max_drawdown), 4),
        "total_return": round(float(total_return), 4),
        "hit_rate": round(float(hit_rate), 4),
        "drift": 0.0
    }


class ModelMetrics:
    """Класс для хранения и вычисления метрик модели"""
    
    def __init__(self):
        self.training_loss: list = []
        self.validation_loss: list = []
        self.training_accuracy: list = []
        self.validation_accuracy: list = []
        self.feature_importance: Dict[str, float] = {}
        self.roc_auc: float = 0.0
        self.precision: float = 0.0
        self.recall: float = 0.0
        self.f1_score: float = 0.0
        self.sharpe_ratio: float = 0.0
        self.trading_samples: int = 0
        self.epochs: int = 0
        self.training_time: float = 0.0
        
    def update_training_metrics(self, train_loss: float, val_loss: float, 
                                train_acc: float = 0.0, val_acc: float = 0.0):
        """Обновить метрики обучения"""
        self.training_loss.append(train_loss)
        self.validation_loss.append(val_loss)
        if train_acc > 0:
            self.training_accuracy.append(train_acc)
        if val_acc > 0:
            self.validation_accuracy.append(val_acc)
    
    def set_feature_importance(self, importance_dict: Dict[str, float]):
        """Установить важность признаков"""
        self.feature_importance = importance_dict
    
    def set_classification_metrics(self, precision: float, recall: float, 
                                   f1_score: float, roc_auc: float):
        """Установить метрики классификации"""
        self.precision = precision
        self.recall = recall
        self.f1_score = f1_score
        self.roc_auc = roc_auc
    
    def set_trading_metrics(self, sharpe_ratio: float, samples: int, epochs: int, training_time: float):
        """Установить торговые метрики"""
        self.sharpe_ratio = sharpe_ratio
        self.trading_samples = samples
        self.epochs = epochs
        self.training_time = training_time
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Получить все метрики"""
        return {
            "training_loss": self.training_loss[-1] if self.training_loss else 0.0,
            "validation_loss": self.validation_loss[-1] if self.validation_loss else 0.0,
            "training_accuracy": self.training_accuracy[-1] if self.training_accuracy else 0.0,
            "validation_accuracy": self.validation_accuracy[-1] if self.validation_accuracy else 0.0,
            "feature_importance": self.feature_importance,
            "roc_auc": self.roc_auc,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "sharpe_ratio": self.sharpe_ratio,
            "trading_samples": self.trading_samples,
            "epochs": self.epochs,
            "training_time": self.training_time
        }
    
    def get_loss_history(self) -> tuple:
        """Получить историю потерь для графика"""
        return (self.training_loss, self.validation_loss)
    
    def get_accuracy_history(self) -> tuple:
        """Получить историю точности для графика"""
        return (self.training_accuracy, self.validation_accuracy)
    
    def get_feature_importance_sorted(self) -> list:
        """Получить важность признаков, отсортированную по убыванию"""
        return sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)


class ForecastDiagnosticsReport:
    """Генерация отчетов по качеству прогнозов и сигналам."""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        
    def generate_probability_histogram(self, raw_probs: np.ndarray, calibrated_probs: np.ndarray):
        """Сохраняет гистограмму вероятностей."""
        df = pd.DataFrame({
            "bear_raw": raw_probs[:, 0], "neutral_raw": raw_probs[:, 1], "bull_raw": raw_probs[:, 2],
            "bear_cal": calibrated_probs[:, 0], "neutral_cal": calibrated_probs[:, 1], "bull_cal": calibrated_probs[:, 2]
        })
        df.to_csv(f"{self.output_dir}/probability_histogram.csv", index=False)
        
    def generate_class_distribution(self, y_true: np.ndarray, y_pred: np.ndarray):
        """Сохраняет распределение классов."""
        df = pd.DataFrame({"y_true": y_true, "y_pred": y_pred})
        dist_df = df.apply(pd.Series.value_counts).fillna(0)
        dist_df.to_csv(f"{self.output_dir}/class_distribution.csv")
        
    def generate_calibration_curve(self, y_true: np.ndarray, probs: np.ndarray, n_bins: int = 10):
        """Сохраняет данные для кривой калибровки."""
        from sklearn.calibration import calibration_curve
        results = []
        for c in range(probs.shape[1]):
            y_bin = (y_true == c).astype(int)
            prob_true, prob_pred = calibration_curve(y_bin, probs[:, c], n_bins=n_bins, strategy='uniform')
            for pt, pp in zip(prob_true, prob_pred):
                results.append({"class": c, "prob_true": pt, "prob_pred": pp})
        pd.DataFrame(results).to_csv(f"{self.output_dir}/calibration_curve.csv", index=False)
        
    def generate_psi_drift(self, expected: np.ndarray, actual: np.ndarray, buckets: int = 10):
        """Population Stability Index."""
        def get_psi(e_col, a_col, bins):
            e_pct = np.histogram(e_col, bins=bins)[0] / len(e_col)
            a_pct = np.histogram(a_col, bins=bins)[0] / len(a_col)
            e_pct = np.maximum(e_pct, 0.0001)
            a_pct = np.maximum(a_pct, 0.0001)
            return np.sum((e_pct - a_pct) * np.log(e_pct / a_pct))

        bins = np.linspace(min(np.min(expected), np.min(actual)), max(np.max(expected), np.max(actual)), buckets + 1)
        psi_val = get_psi(expected, actual, bins)
        pd.DataFrame([{"psi": psi_val}]).to_csv(f"{self.output_dir}/psi_drift.csv", index=False)

    def generate_feature_drift(self, df_train: pd.DataFrame, df_live: pd.DataFrame):
        """Feature drift (train vs live distributions)."""
        drift_stats = []
        for col in df_train.columns:
            if col in df_live.columns and pd.api.types.is_numeric_dtype(df_train[col]):
                mean_train = df_train[col].mean()
                mean_live = df_live[col].mean()
                std_train = df_train[col].std()
                drift = np.abs(mean_train - mean_live) / (std_train + 1e-9)
                drift_stats.append({"feature": col, "drift_score": drift, "mean_train": mean_train, "mean_live": mean_live})
        
        pd.DataFrame(drift_stats).to_csv(f"{self.output_dir}/feature_drift.csv", index=False)

    def generate_signal_attribution(self, trades_df: pd.DataFrame):
        """PnL by strategy type, PnL by regime."""
        if trades_df.empty: return
        
        if "strategy_instance" in trades_df.columns and "pnl" in trades_df.columns:
            pnl_by_strat = trades_df.groupby("strategy_instance")["pnl"].sum().reset_index()
            pnl_by_strat.to_csv(f"{self.output_dir}/pnl_by_strategy.csv", index=False)
            
        if "regime_class" in trades_df.columns and "pnl" in trades_df.columns:
            pnl_by_regime = trades_df.groupby("regime_class")["pnl"].sum().reset_index()
            pnl_by_regime.to_csv(f"{self.output_dir}/pnl_by_regime.csv", index=False)

    def generate_feature_importance(self, model, feature_names: list):
        """Сохраняет важность признаков."""
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            df = pd.DataFrame({"feature": feature_names, "importance": importances})
            df = df.sort_values("importance", ascending=False)
            df.to_csv(f"{self.output_dir}/feature_importance.csv", index=False)
            
    def generate_signal_rejection_stats(self, stats: dict):
        """Сохраняет статистику отклонения сигналов."""
        pd.DataFrame([stats]).to_csv(f"{self.output_dir}/signal_rejection_stats.csv", index=False)

