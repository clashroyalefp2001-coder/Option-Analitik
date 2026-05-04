#!/usr/bin/env python3
"""Options Trading Alpha Engine — основной пайплайн."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from datetime import datetime
from typing import Any, Dict

import pandas as pd

# Настройки pandas / warnings
pd.options.mode.copy_on_write = False
pd.options.mode.chained_assignment = None

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r".*ChainedAssignmentError.*",
)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r".*Parsing dates in.*format when dayfirst.*",
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}

    try:
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


def _to_bucket(row: Dict[str, Any] | pd.Series) -> str:
    """Определяет бакет риска для сделки."""
    dte = row.get("days_to_expiry", 30)
    m = row.get("moneyness", 0)
    t = row.get("type", "call")
    
    dte_b = "short" if dte < 10 else ("med" if dte < 45 else "long")
    # ITM vs OTM
    is_itm = (m > 0.02) if t == "call" else (m < -0.02)
    is_otm = (m < -0.02) if t == "call" else (m > 0.02)
    m_b = "itm" if is_itm else ("otm" if is_otm else "atm")
    
    return f"{dte_b}_{m_b}"


def _get_empirical_stats(trades_path: str = "reports/trades.csv") -> Dict[str, Any]:
    """Загружает историческую статистику сделок для калибровки Келли по бакетам."""
    default_stats = {"win_rate": 0.55, "avg_win": 0.30, "avg_loss": 0.25, "sample_size": 0}
    try:
        if not os.path.exists(trades_path):
            return {"global": default_stats}
        df = pd.read_csv(trades_path)
        if df.empty or "pnl" not in df.columns:
            return {"global": default_stats}
        
        df["bucket"] = df.apply(_to_bucket, axis=1)
        
        # Calculate normalized PnL (percentage of capital at risk)
        # Entry cost = entry_price * quantity * multiplier
        df["entry_notional"] = df["entry_price"] * df["quantity"] * df.get("multiplier", 100.0)
        df["pnl_pct"] = df["pnl"] / df["entry_notional"]
        
        stats = {}
        # Глобальная стата
        results = df["pnl_pct"]
        wins = results[results > 0]
        losses = results[results < 0].abs()
        stats["global"] = {
            "win_rate": len(wins) / len(df) if len(df) > 0 else 0.55,
            "avg_win": float(wins.mean()) if not wins.empty else 0.3,
            "avg_loss": float(losses.mean()) if not losses.empty else 0.25,
            "sample_size": len(df)
        }

        # Стата по бакетам
        for bucket, b_df in df.groupby("bucket"):
            if len(b_df) < 30: continue
            b_res = b_df["pnl_pct"]
            b_wins = b_res[b_res > 0]
            b_losses = b_res[b_res < 0].abs()
            stats[bucket] = {
                "win_rate": len(b_wins) / len(b_res),
                "avg_win": float(b_wins.mean()) if not b_wins.empty else stats["global"]["avg_win"],
                "avg_loss": float(b_losses.mean()) if not b_losses.empty else stats["global"]["avg_loss"],
                "sample_size": len(b_df)
            }
            
        return stats
    except Exception:
        return {"global": default_stats}




def run_pipeline(
    config_path: str = "config_live.json",
    train_model: bool = True,
    open_report: bool = False,
    audit: bool = False,
) -> int:
    log = logging.getLogger("pipeline")

    log.info("=== Options Trading Alpha Engine ===")
    log.info("Старт: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    config = _load_config(config_path)

    if config:
        log.info("Конфиг загружен: %s", config_path)
    else:
        log.info("Конфиг не найден — используем значения по умолчанию")

    try:
        from data.quik_fetcher import load_underlying, load_option_quotes
        from models.feature_store import build_features
        from models.lgbm.trainer import train_model as fit_model
        from models.inference import apply_model_predictions
        from execution.filters.hard import apply_hard_filters
        from execution.filters.soft import apply_soft_filters
        from execution.sizer.kelly import fractional_kelly
        from backtest.engine import OptionBacktestEngine
        from backtest.robustness import RobustnessTester
        from monitoring.metrics import compute_kpis
        from config import RISK_CONFIG

    except Exception as exc:
        log.exception("Ошибка импорта модулей: %s", exc)
        return 1

    risk_cfg = {**RISK_CONFIG, **(config.get("RISK_CONFIG") or {})}
    pipeline_mode = config.get("pipeline_mode")
    if pipeline_mode not in {"forecast", "legacy"}:
        raise ValueError(
            f"Invalid pipeline_mode: {pipeline_mode!r}. "
            f"Must be one of: 'forecast', 'legacy'. "
            f"Config path: {config_path}"
        )

    if pipeline_mode == "forecast":
        log.info("--- Switching to FORECAST pipeline mode ---")
        from pipelines.forecast_pipeline import ForecastPipeline
        pipeline = ForecastPipeline()
        res = pipeline.run(config)
        return res.status

    # 1. Загрузка данных (Legacy)
    try:
        log.info("[1/7] Загрузка данных")

        underlying = load_underlying()
        options = load_option_quotes()

        log.info("    underlying: %d записей", len(underlying))
        log.info("    options:    %d записей", len(options))

        if options.empty:
            log.error("Котировки опционов отсутствуют — выход")
            return 2

    except Exception as exc:
        log.exception("Ошибка загрузки данных: %s", exc)
        return 1

    # 2. Feature engineering
    try:
        log.info("[2/7] Feature engineering")

        features = build_features(underlying, options)

        log.info(
            "    признаков: %d, строк: %d",
            len(features.columns),
            len(features),
        )

        if features.empty:
            log.warning("После очистки признаков не осталось — выход")
            return 0

    except Exception as exc:
        log.exception("Ошибка feature engineering: %s", exc)
        return 1

    # 3. Обучение модели
    train_metrics: Dict[str, Any] = {}

    if train_model:
        try:
            log.info("[3/7] Обучение модели")

            horizon = int(risk_cfg.get("target_horizon", 5))
            log.info("    целевой горизонт: %d бар", horizon)
            
            train_metrics = fit_model(features, horizon=horizon)

            log.info(
                "    backend=%s, train_loss=%.6f, val_loss=%.6f, F1=%.3f",
                train_metrics["backend"],
                train_metrics["training_loss"],
                train_metrics["validation_loss"],
                train_metrics["f1_score"],
            )

        except Exception as exc:
            log.exception("Ошибка обучения: %s", exc)
            train_metrics = {}

    else:
        log.info("[3/7] Обучение пропущено (--no-train)")

    # 4. Инференс
    try:
        log.info("[4/7] Применение модели")
        features = apply_model_predictions(features)

    except Exception as exc:
        log.exception("Ошибка инференса: %s", exc)
        return 1

    # 5. Фильтры
    try:
        log.info("[5/7] Фильтрация сигналов")

        potential = features[features["predicted_edge"] > 0].copy(deep=True)

        log.info("    кандидатов: %d", len(potential))

        if potential.empty:
            log.warning("Нет потенциальных сигналов — выход")
            _save_metrics(train_metrics, kpi={}, samples=len(features))
            return 0

        after_hard = apply_hard_filters(potential, risk_cfg)
        after_soft = apply_soft_filters(after_hard, risk_cfg)

        log.info(
            "    после hard: %d, после soft: %d",
            len(after_hard),
            len(after_soft),
        )

        if after_soft.empty:
            log.warning("Нет сигналов после фильтров — выход")
            _save_metrics(train_metrics, kpi={}, samples=len(features))
            return 0

    except Exception as exc:
        log.exception("Ошибка фильтрации: %s", exc)
        return 1

    # 6. Position sizing
    try:
        log.info("[6/7] Расчёт размеров позиций (Portfolio-Allocator + Kelly)")

        # Initialize Portfolio Allocator
        from execution.sizer.portfolio_allocator import PortfolioAllocator
        allocator = PortfolioAllocator(risk_cfg)
        allocator.reset()

        # Kelly Parameters from config
        kelly_frac_ui = float(risk_cfg.get("kelly_fraction", 0.20))
        max_pos_pct = float(risk_cfg.get("max_position_size_pct", 0.05))
        
        # Эмпирическая калибровка
        emp_stats = KellyStatsStore().load()
        gs = emp_stats
        log.info("    калибровка (Kelly Store): win_rate=%.2f, median_win=%.2f, median_loss=%.2f (n=%d)",
                 gs['win_rate'], gs['median_win'], gs['median_loss'], gs['sample_size'])

        sizes = []

        for _, row in after_soft.iterrows():
            # Signal preparation for allocator
            signal = {
                "underlying": row.get("underlying_symbol", "SPY"),
                "expiry": row.get("expiry", ""),
                "delta": row.get("delta", 0.0),
                "vega": row.get("vega", 0.0),
                "signal_confidence": float(row.get("signal_confidence", 0.5))
            }

            # Kelly sizing with budget constraint
            conf = float(row.get("signal_confidence", 0.5) or 0.5)
            multiplier = float(row.get("multiplier", 100.0))

            # Выбор бакета статы
            bucket = _to_bucket(row)
            stats = emp_stats.get(bucket, emp_stats)
            
            p = conf
            w = stats['median_win']
            l = stats['median_loss']

            # Initial Kelly calculation (without budget constraints)
            monetary_size = fractional_kelly(
                win_rate=p,
                avg_win=w,
                avg_loss=l,
                budget=portfolio_capital,
                kelly_frac=kelly_frac_ui,
                max_position_pct=max_pos_pct,
                max_fstar=0.20,
                min_avg_loss=0.1,
            )

            # Apply Portfolio Allocator
            allocatable_budget = allocator.available_risk_budget(signal)
            final_size = min(monetary_size, allocatable_budget)

            if pd.isna(final_size):
                final_size = 0.0

            fair_val = row.get("fair_value")
            mid_val = row.get("mid")

            option_price = float(fair_val if not pd.isna(fair_val) else mid_val if not pd.isna(mid_val) else 1.0)

            if pd.isna(option_price) or option_price <= 0:
                contracts = 0
            else:
                try:
                    contracts = int(final_size // (option_price * multiplier))
                except (ValueError, OverflowError):
                    contracts = 0

            if contracts < 1 and final_size > 0:
                contracts = 0

            # Update allocator with actual allocation
            actual_allocated = allocator.allocate(signal, contracts * option_price * multiplier)
            sizes.append(contracts)

        log.info(
            "    средний размер: %.2f контр., max: %.2f контр.",
            pd.Series(sizes).mean(),
            pd.Series(sizes).max(),
        )
        log.info(
            "    использовано капитала: %d / %d",
            int(allocator.used_capital),
            int(portfolio_capital)
        )

    except Exception as exc:
        log.exception("Ошибка расчёта размеров: %s", exc)
        return 1

    # 7. Бэктест
    try:
        log.info("[7/7] Бэктест")

        bt_cfg = config.get("BACKTEST_CONFIG", {}) or {}
        
        # Base parameters for engine
        engine_params = {
            "initial_capital": float(bt_cfg.get("initial_capital", 1_000_000)),
            "realized_vol": float(bt_cfg.get("realized_vol", 0.20)),
            "real_drift": float(bt_cfg.get("real_drift", 0.05)),
            "n_simulations": int(bt_cfg.get("n_simulations", 100)),
            "seed": bt_cfg.get("seed", 42),
            "r": float(bt_cfg.get("r", 0.04)),
            "dividend": float(bt_cfg.get("dividend", 0.0)),
            "sigma_for_pricing": bt_cfg.get("sigma_for_pricing"),
            "stop_loss_pct": bt_cfg.get("stop_loss_pct", 0.5),
            "take_profit_pct": bt_cfg.get("take_profit_pct", 1.0),
            "jump_lambda": float(bt_cfg.get("jump_lambda", 0.1)),
            "market_basis_std": float(bt_cfg.get("market_basis_std", 0.02)),
            "slippage_pct": float(bt_cfg.get("slippage_pct", 0.001)),
            "comm_per_contract": float(bt_cfg.get("comm_per_contract", 0.65)),
        }

        engine = OptionBacktestEngine(**engine_params)

        engine.run(after_soft, sizes_series)

        # Robustness Audit (Stress testing)
        if audit:
            log.info("Starting Robustness Audit...")
            tester = RobustnessTester(engine_params)
            tester.run_stress_matrix(after_soft, sizes_series)
            tester.save_report()
            log.info("Robustness Audit complete.")

        equity_curve = engine.get_equity_curve()
        trades = engine.get_trades()

        log.info(
            "    кривая капитала: %d точек, сделок: %d",
            len(equity_curve),
            len(trades),
        )

    except Exception as exc:
        log.exception("Ошибка бэктеста: %s", exc)
        return 1

    # KPI
    try:
        kpi = compute_kpis(equity_curve, trades)

        log.info("--- KPI ---")
        for k, v in kpi.items():
            log.info("    %s: %s", k, v)

    except Exception as exc:
        log.exception("Ошибка расчёта KPI: %s", exc)
        kpi = {}

    try:
        engine.save_reports()
        log.info("Отчёты сохранены: reports/")

    except Exception as exc:
        log.warning("Не удалось сохранить отчёты: %s", exc)

    _save_metrics(train_metrics, kpi=kpi, samples=len(features))

    if open_report:
        try:
            import webbrowser

            report_path = os.path.abspath("reports/report.html")

            if os.path.exists(report_path):
                webbrowser.open(f"file://{report_path}")

        except Exception:
            pass

    log.info("=== Пайплайн завершён ===")
    return 0


def _save_metrics(
    train_metrics: Dict[str, Any],
    kpi: Dict[str, Any],
    samples: int,
) -> None:
    os.makedirs("reports", exist_ok=True)

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "training_loss": train_metrics.get("training_loss", 0.0),
        "validation_loss": train_metrics.get("validation_loss", 0.0),
        "training_accuracy": train_metrics.get("training_accuracy", 0.0),
        "validation_accuracy": train_metrics.get("validation_accuracy", 0.0),
        "feature_importance": train_metrics.get("feature_importance", {}),
        "roc_auc": train_metrics.get("roc_auc", 0.0),
        "precision": train_metrics.get("precision", 0.0),
        "recall": train_metrics.get("recall", 0.0),
        "f1_score": train_metrics.get("f1_score", 0.0),
        "sharpe_ratio": kpi.get("sharpe_ratio", 0.0),
        "max_drawdown": kpi.get("max_drawdown", 0.0),
        "total_return": kpi.get("total_return", 0.0),
        "hit_rate": kpi.get("hit_rate", 0.0),
        "trading_samples": train_metrics.get("trading_samples", samples),
        "train_samples": train_metrics.get("train_samples", 0),
        "val_samples": train_metrics.get("val_samples", 0),
        "epochs": train_metrics.get("epochs", 0),
        "training_time": train_metrics.get("training_time", 0.0),
        "backend": train_metrics.get("backend", "unknown"),
    }

    with open("reports/model_metrics.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Options Alpha Engine pipeline"
    )

    parser.add_argument("--config", default="config_live.json")
    parser.add_argument(
        "--no-train",
        action="store_true",
        help="Не переобучать модель",
    )
    parser.add_argument("--open-report", action="store_true")
    parser.add_argument("--log-level", default="INFO")

    parser.add_argument(
        "--audit",
        action="store_true",
        help="Запустить аудит устойчивости (Robustness Stress Matrix)",
    )

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
