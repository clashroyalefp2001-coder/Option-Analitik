import os
from pathlib import Path

class Settings:
    def __init__(self):
        # Определение базовых путей
        # config.py находится в /backend/app/config.py
        self.app_dir = Path(__file__).resolve().parent      # /backend/app
        self.backend_dir = self.app_dir.parent             # /backend
        self.root_dir = self.backend_dir.parent           # / (корень проекта)
        
        # options_alpha лежит в корне проекта
        self.pipeline_root = self.root_dir / "options_alpha"
        
        # Директории для отчетов и логов внутри options_alpha
        self.reports_dir = self.pipeline_root / "reports"
        self.logs_dir = self.pipeline_root / "logs"
        self.models_dir = self.pipeline_root / "models"
        
        # Пути к файлам конфигурации и метаданных
        self.config_path = self.pipeline_root / "config.json"
        self.metrics_path = self.reports_dir / "metrics.json"
        self.model_meta_path = self.models_dir / "model_meta.json"
        
        # Путь к данным (опционально)
        self.tsv_data_path = self.pipeline_root / "option_export.tsv"
        
        # Создание папок, если их нет
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()
