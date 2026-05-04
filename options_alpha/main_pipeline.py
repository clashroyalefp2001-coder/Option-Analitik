#!/usr/bin/env python3
"""Options Trading Alpha Engine — main dispatcher."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

import pandas as pd

# Настройки pandas / warnings
pd.options.mode.copy_on_write = False
pd.options.mode.chained_assignment = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _load_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logging.warning("Не удалось прочитать %s: %s", path, exc)
        return {}


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def run_pipeline(
    config_path: str = "config_live.json",
    train_model: bool = True,
    open_report: bool = False,
    audit: bool = False,
) -> int:
    """Dispatch to appropriate pipeline based on config."""
    log = logging.getLogger("pipeline")
    log.info("=== Options Trading Alpha Engine ===")
    log.info("Старт: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    config = _load_config(config_path)
    if config:
        log.info("Конфиг загружен: %s", config_path)
    else:
        log.info("Конфиг не найден — используем значения по умолчанию")

    risk_cfg = config.get("RISK_CONFIG", {})
    pipeline_mode = config.get("pipeline_mode")
    
    if pipeline_mode == "forecast":
        log.info("--- Switching to FORECAST pipeline mode ---")
        from pipelines.forecast_pipeline import ForecastPipeline
        pipeline = ForecastPipeline()
        result = pipeline.run(config)
        return result.status

    elif pipeline_mode == "live":
        log.info("--- Switching to LIVE pipeline mode ---")
        from pipelines.live_pipeline import LivePipeline
        pipeline = LivePipeline(config_path)
        result = pipeline.run()
        return result["status"]

    elif pipeline_mode == "legacy":
        log.info("--- Switching to LEGACY pipeline mode ---")
        from pipelines.legacy_pipeline import run_legacy_pipeline
        return run_legacy_pipeline(config, risk_cfg)["status"]

    else:
        raise ValueError(
            f"Invalid pipeline_mode: {pipeline_mode!r}. "
            f"Must be one of: 'forecast', 'live', 'legacy'. "
            f"Config path: {config_path}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Options Alpha Engine pipeline")
    parser.add_argument("--config", default="config_live.json")
    parser.add_argument("--no-train", action="store_true", help="Не переобучать модель")
    parser.add_argument("--open-report", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--audit", action="store_true", help="Запустить аудит устойчивости")
    
    args = parser.parse_args()
    _setup_logging(args.log_level)
    
    return run_pipeline(
        config_path=args.config,
        train_model=not args.no_train,
        open_report=args.open_report,
        audit=args.audit,
    )


if __name__ == "__main__":
    sys.exit(main())
