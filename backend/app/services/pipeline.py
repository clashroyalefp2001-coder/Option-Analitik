"""Сервис: чтение состояния пайплайна (метрики, отчёты, конфиг) и его запуск."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings


# Глобальное состояние асинхронного запуска
_RUN_STATE: dict[str, Any] = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "exit_code": None,
    "step": None,
    "log_tail": [],
}


def is_running() -> bool:
    return bool(_RUN_STATE["running"])


def get_run_state() -> dict[str, Any]:
    return dict(_RUN_STATE)


def read_metrics() -> dict[str, Any]:
    """Читает reports/model_metrics.json. Возвращает пустой словарь, если файла нет."""
    p = settings.metrics_path
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_model_meta() -> dict[str, Any]:
    p = settings.model_meta_path
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_config() -> dict[str, Any]:
    p = settings.config_path
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_config(payload: dict[str, Any]) -> None:
    settings.config_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def read_equity_curve() -> list[dict[str, Any]]:
    p = settings.reports_dir / "equity_curve.csv"
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p)
        return df.to_dict(orient="records")
    except Exception:
        return []


def read_trades() -> list[dict[str, Any]]:
    p = settings.reports_dir / "trades.csv"
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p)
        return df.fillna("").to_dict(orient="records")
    except Exception:
        return []


def read_options_board(limit: int | None = None) -> list[dict[str, Any]]:
    """Подгружает опционную доску через `data.fetcher.load_option_quotes`."""
    sys_path_added = False
    try:
        if str(settings.pipeline_root) not in sys.path:
            sys.path.insert(0, str(settings.pipeline_root))
            sys_path_added = True
        from data.fetcher import load_option_quotes  # type: ignore
        cwd_prev = os.getcwd()
        os.chdir(settings.pipeline_root)
        try:
            df = load_option_quotes()
        finally:
            os.chdir(cwd_prev)
        if df is None or df.empty:
            return []
        if limit:
            df = df.head(limit)
        # JSON-friendly
        df = df.copy()
        for col in df.select_dtypes(include=["datetime64[ns]"]).columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")
        return df.fillna("").to_dict(orient="records")
    except Exception as exc:
        return [{"error": str(exc)}]
    finally:
        if sys_path_added:
            try:
                sys.path.remove(str(settings.pipeline_root))
            except ValueError:
                pass


async def run_pipeline_subprocess(
    no_train: bool = False,
    on_log_line=None,
) -> int:
    """Запускает `python main_pipeline.py` в каталоге пайплайна, стримит stdout/stderr.

    on_log_line: async callback (line: str) -> None
    """
    if _RUN_STATE["running"]:
        raise RuntimeError("Пайплайн уже выполняется")

    _RUN_STATE.update(
        running=True,
        started_at=datetime.now().isoformat(timespec="seconds"),
        finished_at=None,
        exit_code=None,
        step="starting",
        log_tail=[],
    )

    args = [sys.executable, "main_pipeline.py"]
    if no_train:
        args.append("--no-train")

    log_path = settings.logs_dir / f"run_{int(datetime.now().timestamp())}.log"
    log_file = log_path.open("w", encoding="utf-8")

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(settings.pipeline_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip()
            log_file.write(line + "\n")
            log_file.flush()
            _RUN_STATE["log_tail"].append(line)
            if len(_RUN_STATE["log_tail"]) > 500:
                _RUN_STATE["log_tail"] = _RUN_STATE["log_tail"][-500:]
            # Грубое определение шага по тексту
            if "[1/7]" in line: _RUN_STATE["step"] = "data"
            elif "[2/7]" in line: _RUN_STATE["step"] = "features"
            elif "[3/7]" in line: _RUN_STATE["step"] = "training"
            elif "[4/7]" in line: _RUN_STATE["step"] = "inference"
            elif "[5/7]" in line: _RUN_STATE["step"] = "filters"
            elif "[6/7]" in line: _RUN_STATE["step"] = "sizing"
            elif "[7/7]" in line: _RUN_STATE["step"] = "backtest"
            if on_log_line:
                await on_log_line(line)

        rc = await proc.wait()
        _RUN_STATE.update(
            exit_code=rc,
            running=False,
            finished_at=datetime.now().isoformat(timespec="seconds"),
            step="done" if rc == 0 else "error",
        )
        return rc
    finally:
        log_file.close()


def list_training_history() -> list[dict[str, Any]]:
    """Чтение истории обучений из логов backend/logs/run_*.log + текущая модель."""
    history: list[dict[str, Any]] = []
    meta = read_model_meta()
    if meta:
        m = meta.get("metrics", {})
        history.append({
            "id": "current",
            "label": "Текущая модель",
            "backend": meta.get("backend", "unknown"),
            "trained_at": _file_mtime_iso(settings.model_meta_path),
            "f1_score": m.get("f1_score", 0.0),
            "precision": m.get("precision", 0.0),
            "recall": m.get("recall", 0.0),
            "roc_auc": m.get("roc_auc", 0.0),
            "training_loss": m.get("training_loss", 0.0),
            "validation_loss": m.get("validation_loss", 0.0),
            "samples": m.get("trading_samples", 0),
            "is_active": True,
        })
    return history


def _file_mtime_iso(p: Path) -> str | None:
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
