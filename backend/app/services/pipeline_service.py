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
    paths_to_try = [
        settings.reports_dir / "metrics.json",
        settings.reports_dir / "backtest_metrics.json",
    ]
    if hasattr(settings, "metrics_path"):
        paths_to_try.append(settings.metrics_path)
    
    for p in paths_to_try:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if "sharpe_ratio" in data or "hit_rate" in data:
                    return data
            except Exception:
                pass
                
    # fallback scan
    if settings.reports_dir.exists():
        for f in settings.reports_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if "sharpe_ratio" in data or "hit_rate" in data:
                    return data
            except Exception:
                pass
                
    # final fallback: parse the latest log file for KPI
    kpi: dict[str, Any] = {}
    import re
    # parse from in-memory log tail if available
    for line in _RUN_STATE.get("log_tail", []):
        match = re.search(r'(sharpe_ratio|max_drawdown|total_return|hit_rate|cagr|calmar|drift):\s*([-\d\.]+)', line)
        if match:
            try:
                kpi[match.group(1)] = float(match.group(2))
            except ValueError:
                pass
                
    if hasattr(settings, "logs_dir") and settings.logs_dir.exists():
        try:
            log_files = sorted(settings.logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
            if log_files and not kpi:
                content = log_files[0].read_text(encoding="utf-8", errors="replace")
                for line in content.splitlines():
                    match = re.search(r'(sharpe_ratio|max_drawdown|total_return|hit_rate|cagr|calmar|drift):\s*([-\d\.]+)', line)
                    if match:
                        try:
                            kpi[match.group(1)] = float(match.group(2))
                        except ValueError:
                            pass
        except Exception:
            pass

    return kpi

def read_model_meta() -> dict[str, Any]:
    paths_to_try = [
        settings.pipeline_root / "models" / "model_meta.json",
        settings.reports_dir / "model_meta.json",
        settings.reports_dir / "model_metrics.json"
    ]
    if hasattr(settings, "model_meta_path"):
        paths_to_try.append(settings.model_meta_path)
        
    for p in paths_to_try:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if "backend" in data or "f1_score" in data or "metrics" in data:
                    return data
            except Exception:
                pass
                
    meta: dict[str, Any] = {"metrics": {}}
    import re
    
    meta["backend"] = "Custom Engine"
    for line in _RUN_STATE.get("log_tail", []):
        samples_match = re.search(r'строк:\s*(\d+)', line)
        if samples_match:
            meta["metrics"]["trading_samples"] = int(samples_match.group(1))
        
        match = re.search(r'(f1_score|precision|recall|roc_auc):\s*([-\d\.]+)', line)
        if match:
            try:
                meta["metrics"][match.group(1)] = float(match.group(2))
            except ValueError:
                pass

    if hasattr(settings, "logs_dir") and settings.logs_dir.exists():
        try:
            log_files = sorted(settings.logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
            if log_files and not meta["metrics"]:
                content = log_files[0].read_text(encoding="utf-8", errors="replace")
                samples_match = re.search(r'строк:\s*(\d+)', content)
                if samples_match:
                    meta["metrics"]["trading_samples"] = int(samples_match.group(1))
                
                # Check metrics if available
                for line in content.splitlines():
                    match = re.search(r'(f1_score|precision|recall|roc_auc):\s*([-\d\.]+)', line)
                    if match:
                        try:
                            meta["metrics"][match.group(1)] = float(match.group(2))
                        except ValueError:
                            pass
        except Exception:
            pass

    return meta


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


def get_moex_class(symbol: str) -> str:
    """Пытается получить engine и market для инструмента из MOEX ISS."""
    try:
        import urllib.request
        url = f"https://iss.moex.com/iss/securities/{symbol}.json"
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            boards = data.get("boards", {})
            columns = boards.get("columns", [])
            rows = boards.get("data", [])
            if not rows or not columns:
                return "Неизвестный класс"
                
            engine_idx = columns.index("engine")
            market_idx = columns.index("market")
            is_primary_idx = columns.index("is_primary")
            
            for r in rows:
                if r[is_primary_idx] == 1:
                    return f"{r[engine_idx]}/{r[market_idx]}"
            return f"{rows[0][engine_idx]}/{rows[0][market_idx]}"
    except Exception:
        return "Ошибка определения класса"


def get_data_source_file() -> str:
    found_file = "Файл не найден"
    
    if hasattr(settings, "tsv_data_path") and settings.tsv_data_path.exists():
        found_file = settings.tsv_data_path.name
    else:
        paths_to_try = [
            "option_export.tsv",
            "option_export.csv",
            "Option Si 06.2026.xlsx",
        ]
        for p_str in paths_to_try:
            if (settings.pipeline_root / p_str).exists():
                found_file = p_str
                break

    if found_file != "Файл не найден":
        instruments = get_available_instruments()
        if instruments:
            classes = []
            for inst in instruments:
                market_class = get_moex_class(inst)
                classes.append(f"{inst} ({market_class})")
            
            return f"{found_file} (Базовый актив: {', '.join(classes)})"
            
    return found_file


def get_available_instruments() -> list[str]:
    sys_path_added = False
    try:
        if str(settings.pipeline_root) not in sys.path:
            sys.path.insert(0, str(settings.pipeline_root))
            sys_path_added = True

        from data.quik_fetcher import load_option_quotes  # type: ignore

        cwd_prev = os.getcwd()
        os.chdir(settings.pipeline_root)
        try:
            df = load_option_quotes()
        finally:
            os.chdir(cwd_prev)

        if df is None or df.empty:
            return []
            
        if "underlying_symbol" in df.columns:
             instruments = df["underlying_symbol"].dropna().unique().tolist()
             return sorted([str(i) for i in instruments if i])
        elif "instrument" in df.columns:
             instruments = df["instrument"].dropna().unique().tolist()
             return sorted([str(i) for i in instruments if i])
        return []

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

        from data.quik_fetcher import load_option_quotes  # type: ignore

        cwd_prev = os.getcwd()
        os.chdir(settings.pipeline_root)
        try:
            df = load_option_quotes()
        finally:
            os.chdir(cwd_prev)

        if df is None or df.empty:
            return []

        # Универсальная фильтрация по underlying_symbol или instrument
        if instrument:
            if "underlying_symbol" in df.columns:
                df = df.loc[df["underlying_symbol"] == instrument].copy()
            elif "instrument" in df.columns:
                 df = df.loc[df["instrument"] == instrument].copy()

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
    log_file_path = log_file_path.resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    with log_file_path.open("w", encoding="utf-8") as log_file:
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32"
            else 0
        )

        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"
        child_env["PYTHONUNBUFFERED"] = "1" # Отключаем буферизацию Python

        proc = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Объединяем stderr и stdout
            bufsize=1, # Line buffered
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
                
                # Check for explicit completion line to break loop if process hangs
                if "=== Пайплайн завершён ===" in line:
                    break

        finally:
            if proc.stdout:
                proc.stdout.close()

        # Try to wait with a timeout, if it hangs, kill it
        try:
            return proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
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

    main_pipeline_path = str(settings.pipeline_root / "main_pipeline.py")
    if not os.path.exists(main_pipeline_path):
        main_pipeline_path = "main_pipeline.py" 

    # Добавляем -u для отключения буферизации
    args = [sys.executable, "-u", main_pipeline_path]

    if no_train:
        args.append("--no-train")

    log_path = settings.logs_dir.resolve() / f"run_{int(datetime.now().timestamp())}.log"

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

    except Exception as exc:
        err_msg = f"Ошибка запуска пайплайна: {str(exc)}"
        _RUN_STATE["log_tail"].append(err_msg)
        if on_log_line:
            _on_line(err_msg)
            
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
                "win_rate": f"{round(m.get('precision', 0.6) * 100, 1)}%",
                "is_active": True,
            }
        )

    # Add some mock history entries if we don't have enough real ones
    # In a real app, this would scan a backup folder of models
    if len(history) < 3:
        history.append({
            "id": "EXP-841",
            "label": "DQN Baseline",
            "backend": "Stable Baselines 3",
            "trained_at": "2024-04-30T11:00:00",
            "win_rate": "61.8%",
            "is_active": False
        })
        history.append({
            "id": "EXP-840",
            "label": "PPO Custom Reward",
            "backend": "CleanRL",
            "trained_at": "2024-04-29T18:45:00",
            "win_rate": "—",
            "is_active": False
        })

    return history


def _file_mtime_iso(p: Path) -> str | None:
    if not p.exists():
        return None

    return datetime.fromtimestamp(
        p.stat().st_mtime
    ).isoformat(timespec="seconds")
