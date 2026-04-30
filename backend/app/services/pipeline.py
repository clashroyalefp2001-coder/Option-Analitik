"""Сервис: чтение состояния пайплайна (метрики, отчёты, конфиг) и его запуск."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from app.config import settings

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
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_equity_curve() -> list[dict[str, Any]]:
    p = settings.reports_dir / "equity_curve.csv"
    if not p.exists():
        return []
    try:
        return pd.read_csv(p).to_dict(orient="records")
    except Exception:
        return []


def read_trades() -> list[dict[str, Any]]:
    p = settings.reports_dir / "trades.csv"
    if not p.exists():
        return []
    try:
        return pd.read_csv(p).fillna("").to_dict(orient="records")
    except Exception:
        return []


def get_data_source_file() -> str:
    paths_to_try = [
        "option_export.tsv",
        "option_export.csv",
        "Option Si 06.2026.xlsx",
    ]
    for p_str in paths_to_try:
        if (settings.pipeline_root / p_str).exists():
            return p_str
    return "Файл не найден"


def get_available_instruments() -> list[str]:
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

        if df is None or df.empty or "underlying_symbol" not in df.columns:
            return []

        instruments = df["underlying_symbol"].dropna().unique().tolist()
        return sorted([str(i) for i in instruments if i])

    except Exception:
        return []

    finally:
        if sys_path_added:
            try:
                sys.path.remove(str(settings.pipeline_root))
            except ValueError:
                pass


def read_options_board(
    limit: int | None = None,
    instrument: str | None = None,
) -> list[dict[str, Any]]:
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

        if instrument and "underlying_symbol" in df.columns:
            df = df.loc[df["underlying_symbol"] == instrument].copy()

        if limit:
            df = df.head(limit)

        df = df.copy(deep=True)

        for col in df.select_dtypes(include=["datetime64[ns]"]).columns:
            df.loc[:, col] = df[col].dt.strftime("%Y-%m-%d")

        return df.fillna("").to_dict(orient="records")

    except Exception as exc:
        return [{"error": str(exc)}]

    finally:
        if sys_path_added:
            try:
                sys.path.remove(str(settings.pipeline_root))
            except ValueError:
                pass


def _classify_step(line: str) -> str | None:
    if "[1/7]" in line:
        return "data"
    if "[2/7]" in line:
        return "features"
    if "[3/7]" in line:
        return "training"
    if "[4/7]" in line:
        return "inference"
    if "[5/7]" in line:
        return "filters"
    if "[6/7]" in line:
        return "sizing"
    if "[7/7]" in line:
        return "backtest"
    return None


def _run_pipeline_blocking(
    args: list[str],
    cwd: str,
    log_file_path: Path,
    on_line=None,
) -> int:
    with log_file_path.open("w", encoding="utf-8") as log_file:
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32"
            else 0
        )

        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"

        proc = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            env=child_env,
        )

        try:
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip()

                log_file.write(line + "\n")
                log_file.flush()

                _RUN_STATE["log_tail"].append(line)
                if len(_RUN_STATE["log_tail"]) > 500:
                    _RUN_STATE["log_tail"] = _RUN_STATE["log_tail"][-500:]

                step = _classify_step(line)
                if step:
                    _RUN_STATE["step"] = step

                if on_line:
                    try:
                        on_line(line)
                    except Exception:
                        pass

        finally:
            proc.stdout.close()

        return proc.wait()


async def run_pipeline_subprocess(
    no_train: bool = False,
    on_log_line=None,
) -> int:
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
    loop = asyncio.get_running_loop() if on_log_line else None

    def _on_line(line: str) -> None:
        if not on_log_line:
            return

        if asyncio.iscoroutinefunction(on_log_line):
            asyncio.run_coroutine_threadsafe(on_log_line(line), loop)
        else:
            on_log_line(line)

    try:
        rc = await asyncio.to_thread(
            _run_pipeline_blocking,
            args,
            str(settings.pipeline_root),
            log_path,
            _on_line,
        )

        _RUN_STATE.update(
            exit_code=rc,
            running=False,
            finished_at=datetime.now().isoformat(),
            step="done" if rc == 0 else "error",
        )

        return rc

    except Exception:
        _RUN_STATE.update(
            running=False,
            finished_at=datetime.now().isoformat(),
            step="error",
            exit_code=-1,
        )
        raise


def list_training_history() -> list[dict[str, Any]]:
    history = []

    meta = read_model_meta()
    if meta:
        m = meta.get("metrics", {})

        history.append(
            {
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
            }
        )

    return history


def _file_mtime_iso(p: Path) -> str | None:
    if not p.exists():
        return None

    return datetime.fromtimestamp(
        p.stat().st_mtime
    ).isoformat(timespec="seconds")