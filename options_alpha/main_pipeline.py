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


def run_pipeline(
    config_path: str = "config_live.json",
    train_model: bool = True,
    open_report: bool = False,
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
        from monitoring.metrics import compute_kpis
        from config import RISK_CONFIG
    except Exception as exc:
        log.exception("Ошибка импорта модулей: %s", exc)
        return 1

    risk_cfg = {**RISK_CONFIG, **(config.get("RISK_CONFIG") or {})}

    # 1. Загрузка данных
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

            train_metrics = fit_model(features)

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
        log.info("[6/7] Расчёт размеров позиций")

        budget = 1_000_000.0
        max_pos = risk_cfg.get("max_position_size_pct", 0.05) * budget

        kelly_frac_ui = float(risk_cfg.get("kelly_fraction", 0.25))

        if pd.isna(kelly_frac_ui) or kelly_frac_ui <= 0:
            log.warning(
                "Некорректный Kelly fraction — используется 0.25"
            )
            kelly_frac_ui = 0.25

        sizes = []

        for _, row in after_soft.iterrows():
            edge = float(row.get("predicted_edge", 0.0) or 0.0)
            conf = float(row.get("signal_confidence", 0.5) or 0.5)

            avg_win = max(edge, 1e-6)
            avg_loss = max(edge * 0.6, 1e-6)

            monetary_size = fractional_kelly(
                edge=edge,
                win_rate=conf,
                loss_rate=1 - conf,
                avg_win=avg_win,
                avg_loss=avg_loss,
                budget=max_pos,
                kelly_frac=kelly_frac_ui,
            )

            if pd.isna(monetary_size):
                monetary_size = 0.0

            fair_val = row.get("fair_value")
            mid_val = row.get("mid")

            op_raw = fair_val if not pd.isna(fair_val) else mid_val
            op_raw = op_raw if not pd.isna(op_raw) else 1.0

            option_price = float(op_raw)

            if pd.isna(option_price) or option_price <= 0:
                contracts = 0
            else:
                try:
                    contracts = int(monetary_size // option_price)
                except (ValueError, OverflowError):
                    contracts = 0

            if contracts < 1 and monetary_size > 0:
                contracts = 1

            sizes.append(float(contracts))

        sizes_series = pd.Series(
            sizes,
            index=after_soft.index,
            name="size",
        )

        log.info(
            "    средний размер: %.2f контр., max: %.2f контр.",
            sizes_series.mean(),
            sizes_series.max(),
        )

    except Exception as exc:
        log.exception("Ошибка расчёта размеров: %s", exc)
        return 1

    # 7. Бэктест
    try:
        log.info("[7/7] Бэктест")

        bt_cfg = config.get("BACKTEST_CONFIG", {}) or {}

        engine = OptionBacktestEngine(
            initial_capital=float(bt_cfg.get("initial_capital", 1_000_000)),
            realized_vol=float(bt_cfg.get("realized_vol", 0.20)),
            n_simulations=int(bt_cfg.get("n_simulations", 100)),
            seed=bt_cfg.get("seed", 42),
            r=float(bt_cfg.get("r", 0.04)),
            dividend=float(bt_cfg.get("dividend", 0.0)),
            sigma_for_pricing=bt_cfg.get("sigma_for_pricing"),
            stop_loss_pct=bt_cfg.get("stop_loss_pct", 0.5),
            take_profit_pct=bt_cfg.get("take_profit_pct", 1.0),
            binomial_steps=int(bt_cfg.get("binomial_steps", 30)),
        )

        engine.run(after_soft, sizes_series)

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

    args = parser.parse_args()

    _setup_logging(args.log_level)

    return run_pipeline(
        config_path=args.config,
        train_model=not args.no_train,
        open_report=args.open_report,
    )


if __name__ == "__main__":
    sys.exit(main())