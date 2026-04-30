"""Настройки backend: пути, CORS, окружение."""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings

# Корень репозитория: C:\Project\Option Analitik
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_ROOT = REPO_ROOT / "options_alpha"

class Settings(BaseSettings):
    repo_root: Path = REPO_ROOT
    pipeline_root: Path = PIPELINE_ROOT
    reports_dir: Path = PIPELINE_ROOT / "reports"
    config_path: Path = PIPELINE_ROOT / "config_live.json"
    model_meta_path: Path = PIPELINE_ROOT / "models" / "lgbm" / "model_meta.json"
    metrics_path: Path = PIPELINE_ROOT / "reports" / "model_metrics.json"
    logs_dir: Path = REPO_ROOT / "backend" / "logs"
    
    # Жесткий путь к файлу с данными из QUIK
    tsv_data_path: Path = REPO_ROOT / "data" / "option_export.tsv"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
    ]

    class Config:
        env_prefix = "OA_"

settings = Settings()
settings.logs_dir.mkdir(parents=True, exist_ok=True)
(settings.repo_root / "data").mkdir(parents=True, exist_ok=True)