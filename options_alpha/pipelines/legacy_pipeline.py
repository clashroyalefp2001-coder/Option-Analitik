import logging
import pandas as pd
from typing import Dict, Any
from options_alpha.execution.sizer.portfolio_allocator import PortfolioAllocator
from options_alpha.storage.kelly_stats_store import KellyStatsStore
from options_alpha.execution.sizer.distributional_kelly import distributional_kelly, _generate_synthetic_returns
from options_alpha.execution.sizer.kelly import fractional_kelly
from options_alpha.backtest.engine import OptionBacktestEngine
from options_alpha.monitoring.metrics import compute_kpis
from options_alpha.config import RISK_CONFIG

logger = logging.getLogger("legacy_pipeline")

def run_legacy_pipeline(config: Dict[str, Any], risk_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Run the legacy pipeline with Kelly calibration and portfolio allocation."""
    try:
        # Imports
        from options_alpha.data.quik_fetcher import load_underlying, load_option_quotes
        from options_alpha.models.feature_store import build_features
        from options_alpha.models.lgbm.trainer import train_model as fit_model
        from options_alpha.models.inference import apply_model_predictions
        from options_alpha.execution.filters.hard import apply_hard_filters
        from options_alpha.execution.filters.soft import apply_soft_filters
        from options_alpha.execution.sizer.kelly import fractional_kelly as fk
        from options_alpha.backtest.engine import OptionBacktestEngine
        from options_alpha.backtest.robustness import RobustnessTester
        from options_alpha.monitoring.metrics import compute_kpis

        logger.info("[1/7] Loading data")
        underlying = load_underlying()
        options = load_option_quotes()
        logger.info("    underlying: %d records", len(underlying))
        logger.info("    options: %d records", len(options))

        if options.empty:
            logger.error("No option quotes available")
            return {"status": 2, "error": "No option quotes"}

        # Feature engineering
        logger.info("[2/7] Feature engineering")
        features = build_features(underlying, options)
        logger.info("    features: %d columns, %d rows", len(features.columns), len(features))
        if features.empty:
            return {"status": 0, "error": "No features"}

        # Model training
        train_metrics = {}
        if config.get("train_model", True):
            logger.info("[3/7] Training model")
            horizon = int(risk_cfg.get("target_horizon", 5))
            train_metrics = fit_model(features, horizon=horizon)
            logger.info("    F1=%.3f, train_loss=%.6f", train_metrics.get("f1_score",0), train_metrics.get("training_loss",0))

        # Inference
        logger.info("[4/7] Inference")
        features = apply_model_predictions(features)
        potential = features[features["predicted_edge"] > 0].copy()
        logger.info("    candidates: %d", len(potential))
        if potential.empty:
            return {"status": 0, "message": "No signals"}

        # Filtering
        logger.info("[5/7] Filtering")
        after_hard = apply_hard_filters(potential, risk_cfg)
        after_soft = apply_soft_filters(after_hard, risk_cfg)
        logger.info("    after hard: %d, after soft: %d", len(after_hard), len(after_soft))
        if after_soft.empty:
            return {"status": 0, "message": "No signals after filters"}

        # Portfolio allocation & sizing
        logger.info("[6/7] Portfolio allocation")
        allocator = PortfolioAllocator(risk_cfg)
        portfolio_capital = risk_cfg.get("initial_capital", 1_000_000.0)
        
        # Load calibrated Kelly stats
        kelly_store = KellyStatsStore()
        emp_stats = kelly_store.load()
        logger.info("    Kelly stats: win_rate=%.2f, median_win=%.2f, median_loss=%.2f",
                    emp_stats['win_rate'], emp_stats['median_win'], emp_stats['median_loss'])

        max_pos_pct = risk_cfg.get("max_position_size_pct", 0.05)
        kelly_frac = risk_cfg.get("kelly_fraction", 0.20)
        
        sizes = []
        for _, row in after_soft.iterrows():
            signal = {
                "underlying": row.get("underlying_symbol", "SPY"),
                "expiry": row.get("expiry", ""),
                "delta": row.get("delta", 0.0),
                "vega": row.get("vega", 0.0),
                "signal_confidence": float(row.get("signal_confidence", 0.5))
            }
            
            # Distributional Kelly sizing
            conf = float(row.get("signal_confidence", 0.5) or 0.5)
            multiplier = float(row.get("multiplier", 100.0))
            bucket = _to_bucket(row)
            stats = emp_stats.get(bucket, emp_stats)
            
            # Generate synthetic returns for distributional Kelly
            returns = _generate_synthetic_returns(
                stats['win_rate'], 
                stats['median_win'], 
                stats['median_loss'], 
                1000
            )
            
            kelly_fraction = distributional_kelly(returns, confidence=0.95, tail_penalty="cvar")
            monetary_size = kelly_fraction * portfolio_capital * kelly_frac
            
            allocatable = allocator.available_risk_budget(signal)
            final_size = min(monetary_size, allocatable)
            
            if pd.isna(final_size):
                final_size = 0.0
            
            option_price = float(row.get("fair_value") or row.get("mid") or 1.0)
            if pd.isna(option_price) or option_price <= 0:
                contracts = 0
            else:
                try:
                    contracts = int(final_size // (option_price * multiplier))
                except (ValueError, OverflowError):
                    contracts = 0
            
            if contracts < 1 and final_size > 0:
                contracts = 0
            
            allocator.allocate(signal, contracts * option_price * multiplier)
            sizes.append(contracts)

        logger.info("    avg size: %.2f, max: %.2f contracts", 
                    pd.Series(sizes).mean(), pd.Series(sizes).max())

        # Backtesting
        logger.info("[7/7] Backtesting")
        engine = OptionBacktestEngine(
            initial_capital=risk_cfg.get("initial_capital", 1_000_000.0),
            n_simulations=config.get("BACKTEST_CONFIG", {}).get("n_simulations", 100),
            slippage_pct=config.get("BACKTEST_CONFIG", {}).get("slippage_pct", 0.001)
        )
        all_signals = after_soft.copy()
        all_signals["size"] = sizes
        engine.run(all_signals, all_signals["size"])
        
        kpis = engine.get_kpis()
        engine.save_reports()
        
        logger.info("    Sharpe=%.2f, Return=%.2f%%", kpis.get("sharpe_ratio",0), kpis.get("total_return",0)*100)
        
        # Capacity / Risk Metrics
        from options_alpha.monitoring.capacity_monitor import CapacityMetrics
        cap_metrics = CapacityMetrics({
            "initial_capital": portfolio_capital,
            "used_capital": allocator.used_capital,
            "gross_exposure": allocator.gross_exposure,
            "max_gross_exposure": risk_cfg.get("max_gross_exposure", 1.0),
            "vega_exposure": allocator.total_vega,
            "max_vega_exposure": risk_cfg.get("max_vega_exposure", 1.0),
            "underlying_exposure": max(allocator.by_underlying.values()) if allocator.by_underlying else 0.0,
            "rejected_signals": 0,
            "total_signals": len(potential),
            "avg_margin_util": 0.0,
            "peak_margin_util": 0.0,
        }).compute()
        for k, v in cap_metrics.items():
            logger.info("Capacity %s: %.4f", k, v)
        
        return {
            "status": 0,
            "kpis": kpis,
            "train_metrics": train_metrics,
            "allocator_used_capital": allocator.used_capital,
            "total_candidates": len(potential),
            "trades_executed": len(engine.trades),
            "capacity_metrics": cap_metrics
        }

    except Exception as exc:
        logger.exception("Pipeline error: %s", exc)
        return {"status": 1, "error": str(exc)}