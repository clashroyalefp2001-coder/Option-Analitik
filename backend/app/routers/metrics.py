"""Эндпоинты метрик и состояния модели."""
from fastapi import APIRouter

from app.services.pipeline import read_metrics, read_model_meta

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics")
def metrics() -> dict:
    m = read_metrics()
    meta = read_model_meta()
    backend = meta.get("backend", m.get("backend", "unknown"))
    features = meta.get("features", [])
    importance = m.get("feature_importance") or meta.get("metrics", {}).get(
        "feature_importance", {}
    )
    return {
        "kpi": {
            "sharpe_ratio": m.get("sharpe_ratio", 0.0),
            "max_drawdown": m.get("max_drawdown", 0.0),
            "total_return": m.get("total_return", 0.0),
            "hit_rate": m.get("hit_rate", 0.0),
            "cagr": m.get("cagr", 0.0),
            "calmar": m.get("calmar", 0.0),
        },
        "model": {
            "backend": backend,
            "f1_score": m.get("f1_score", 0.0),
            "precision": m.get("precision", 0.0),
            "recall": m.get("recall", 0.0),
            "roc_auc": m.get("roc_auc", 0.0),
            "training_loss": m.get("training_loss", 0.0),
            "validation_loss": m.get("validation_loss", 0.0),
            "trading_samples": m.get("trading_samples", 0),
            "train_samples": m.get("train_samples", 0),
            "val_samples": m.get("val_samples", 0),
            "training_time": m.get("training_time", 0.0),
            "features": features,
            "feature_importance": importance,
        },
        "timestamp": m.get("timestamp"),
    }
