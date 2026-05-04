from fastapi import APIRouter
from ..services import pipeline_service as pipeline
from datetime import datetime

router = APIRouter()

@router.get("/")
def get_metrics():
    metrics = pipeline.read_metrics()
    meta = pipeline.read_model_meta()
    
    kpi = metrics.get("kpi", metrics)
    model_metrics = meta.get("metrics", meta)
    
    return {
        "status": "Active",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "kpi": {
            "sharpe_ratio": kpi.get("sharpe_ratio", 0.0),
            "max_drawdown": kpi.get("max_drawdown", 0.0),
            "hit_rate": kpi.get("hit_rate", 0.0),
            "total_return": kpi.get("total_return", 0.0),
            "cagr": kpi.get("cagr", 0.0),
            "calmar": kpi.get("calmar", 0.0),
        },
        "model": {
            "backend": meta.get("backend", "—") or model_metrics.get("backend", "—"),
            "f1_score": model_metrics.get("f1_score", 0.0),
            "precision": model_metrics.get("precision", 0.0),
            "recall": model_metrics.get("recall", 0.0),
            "roc_auc": model_metrics.get("roc_auc", 0.0),
            "trading_samples": model_metrics.get("trading_samples", 0),
            "train_samples": model_metrics.get("train_samples", 0),
            "val_samples": model_metrics.get("val_samples", 0),
        }
    }
