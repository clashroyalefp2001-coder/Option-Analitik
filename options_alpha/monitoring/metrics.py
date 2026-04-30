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
