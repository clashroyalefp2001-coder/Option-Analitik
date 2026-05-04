import logging
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any

from strategies.threshold_engine import ThresholdEngine
from strategies.forecast_mapper import ForecastStrategyMapper

@dataclass
class PipelineResult:
    status: int
    message: str
    metrics: Dict[str, Any]

def update_kelly_stats_from_oos_trades(trades: list, store_path: str = "storage/kelly_stats.json") -> None:
    """Update Kelly stats from OOS trades only (past closed trades)."""
    from datetime import datetime
    
    if not trades:
        return
    
    import numpy as np
    
    executed_trades = [t for t in trades if t.get("is_executed", False)]
    if not executed_trades:
        return
    
    pnls = [t.get("pnl", 0) for t in executed_trades]
    pnl_array = np.array(pnls)
    
    wins = pnl_array[pnl_array > 0]
    losses = pnl_array[pnl_array < 0]
    
    win_rate = len(wins) / len(pnls) if len(pnls) > 0 else 0.5
    median_win = float(np.median(wins)) if len(wins) > 0 else 0.0
    median_loss = float(np.median(np.abs(losses))) if len(losses) > 0 else 0.0
    
    var_95 = float(np.percentile(pnl_array, 5)) if len(pnl_array) > 0 else 0.0
    tail_losses = pnl_array[pnl_array <= var_95]
    cvar_95 = float(tail_losses.mean()) if len(tail_losses) > 0 else 0.0
    
    from options_alpha.storage.kelly_stats_store import KellyStatsStore
    store = KellyStatsStore(storage_path=store_path)
    
    stats = {
        "updated_at": datetime.now().isoformat(),
        "sample_size": len(executed_trades),
        "win_rate": win_rate,
        "median_win": median_win,
        "median_loss": median_loss,
        "cvar_95": cvar_95,
        "pnl_distribution": pnls[-1000:]
    }
    
    store.save(stats)


@dataclass
class ForecastPipelineResult:
    fold_metrics: list
    oos_predictions: pd.DataFrame
    thresholds: dict
    calibration_metrics: dict
    selected_trades: pd.DataFrame

class ForecastPipeline:
    def __init__(self):
        self.log = logging.getLogger("forecast_pipeline")

    def run(self, config: Dict[str, Any]) -> PipelineResult:
        from data.quik_fetcher import fetch_moex_market_data, load_option_quotes
        from models.feature_store import build_market_features, MarketLabelBuilder, DatasetValidator
        from models.lgbm.trainer import MarketForecaster, generate_purged_walk_forward_splits, train_walk_forward_fold
        from backtest.engine import OptionBacktestEngine
        from monitoring.metrics import ForecastDiagnosticsReport

        class SignalGenerator:
            def generate(self, mapped: dict | None, ts: datetime):
                if not mapped: return pd.DataFrame()
                return pd.DataFrame([{"date": ts, "option_symbol": l["symbol"], "side": l["side"], 
                                      "strike": l["strike"], "type": l["type"], "strategy_instance": mapped["strategy_name"]} 
                                     for l in mapped["legs"]])

        try:
            self.log.info("Fetching market data...")
            market_df = fetch_moex_market_data(
                symbol=config.get("symbol", "SiM4"),
                start_date=config.get("start_date", "2015-01-01"),
                end_date=config.get("end_date", "2024-05-01")
            )
            self.log.info("Market data rows: %d", len(market_df))

            features_df = build_market_features(market_df)
            label_builder = MarketLabelBuilder(
                horizon=config.get("forecast_horizon", 5),
                direction_threshold=config.get("direction_threshold", 0.005)
            )
            labels_all = label_builder.build(market_df)
            
            validator = DatasetValidator()
            report_m = validator.validate_market_df(market_df)
            report_f = validator.validate_feature_df(features_df)
            report_l = validator.validate_labels(labels_all)
            
            if not report_m.is_valid: 
                self.log.error("Market data validation failed: %s", report_m.errors)
                raise ValueError(f"Market data validation failed: {report_m.errors}")
            if not report_f.is_valid: 
                self.log.error("Feature validation failed: %s", report_f.errors)
                raise ValueError(f"Feature validation failed: {report_f.errors}")
            if not report_l.is_valid: 
                self.log.error("Label validation failed: %s", report_l.errors)
                raise ValueError(f"Label validation failed: {report_l.errors}")
            
            merged = pd.merge(features_df, labels_all, on="timestamp")
            columns_to_drop = ["timestamp", "direction_class", "regime_class", "future_return", "future_realized_vol_h", "future_min", "tail_down"]
            X = merged.drop(columns=columns_to_drop, errors="ignore")
            
            non_numeric_cols = X.select_dtypes(include=["object", "string", "category", "datetime"]).columns
            if not non_numeric_cols.empty:
                self.log.info("Dropping non-numeric columns for training: %s", list(non_numeric_cols))
                X = X.drop(columns=non_numeric_cols)

            y = merged["direction_class"]

            n_rows = len(merged)
            train_size = config.get("train_size", 500)
            val_size = config.get("val_size", 100)
            embargo = config.get("embargo", 5)
            
            if train_size + val_size + embargo > n_rows:
                train_size = max(10, int(n_rows * 0.6))
                val_size = max(5, int(n_rows * 0.2))
                embargo = min(embargo, max(0, int(n_rows * 0.05)))

            splits = generate_purged_walk_forward_splits(n_rows=n_rows, train_size=train_size, val_size=val_size, horizon=config.get("forecast_horizon", 5), embargo=embargo)
            if not splits:
                raise ValueError("Not enough data to generate training splits.")
                
            backtest_signals = []
            
            report_gen = ForecastDiagnosticsReport(output_dir="reports")
            threshold_engine = ThresholdEngine(base_percentile=80.0, min_history=50)
            bull_probs_history = []
            bear_probs_history = []
            
            sig_gen = SignalGenerator()
            options_pool = load_option_quotes()
            forecaster = MarketForecaster()
            
            self.log.info("Backtesting on OOS...")
            
            for split in splits:
                artifact = train_walk_forward_fold(X, y, split)
                
                forecaster.model = artifact.model
                forecaster.features = artifact.features
                forecaster.calibrator = artifact.calibrator
                forecaster.is_trained = True
                
                for idx in split["val_idx"]:
                    day_ts = merged.iloc[idx]["timestamp"]
                    day_chain = options_pool[options_pool["date"] == day_ts].copy()
                    if day_chain.empty: continue
                    
                    day_chain["underlying_price"] = market_df[market_df["timestamp"] == day_ts]["close"].iloc[0]
                    day_probs = forecaster.predict_distribution(X.iloc[[idx]])
                    
                    day_regime = labels_all[labels_all["timestamp"] == day_ts]["regime_class"].iloc[0]
                    day_vol = features_df[features_df["timestamp"] == day_ts]["rv_20"].iloc[0]
                    
                    bull_probs_history.append(day_probs["bull_prob"])
                    bear_probs_history.append(day_probs["bear_prob"])
                    
                    bull_t = threshold_engine.compute_dynamic_threshold(bull_probs_history, 0.5, day_regime)
                    bear_t = threshold_engine.compute_dynamic_threshold(bear_probs_history, 0.5, day_regime)
                    
                    mapper = ForecastStrategyMapper(bull_t, bear_t)
                    mapped = mapper.map_forecast_to_structure(
                        {
                            "direction_probs": {
                                "bull_prob": day_probs["bull_prob"],
                                "bear_prob": day_probs["bear_prob"],
                                "neutral_prob": day_probs.get("neutral_prob", 0.0)
                            },
                            "expected_move": 0.0,  # TODO: integrate magnitude model output
                            "vol_forecast": day_vol,
                            "iv_percentile": 0.5,  # placeholder – should be derived from market data
                            "iv_rank": 0.5,        # placeholder
                            "surface_percentile": 0.5,  # placeholder
                            "regime": day_regime,
                            "confidence": max(day_probs.values())
                        },
                        chain_snapshot=day_chain
                    )
                    if mapped:
                        backtest_signals.append(sig_gen.generate(mapped, day_ts))
                    
            total_eval_days = sum(len(s["val_idx"]) for s in splits)
            stats = {
                "total_days_evaluated": total_eval_days,
                "days_with_signals": len(backtest_signals),
                "days_rejected": total_eval_days - len(backtest_signals),
                "rejection_rate": (total_eval_days - len(backtest_signals)) / total_eval_days if total_eval_days > 0 else 0
            }
            report_gen.generate_signal_rejection_stats(stats)
            
            if not backtest_signals:
                self.log.warning("No signals.")
                return PipelineResult(status=0, message="No signals", metrics=artifact.metrics)
                
            all_signals = pd.concat(backtest_signals).reset_index(drop=True)
            options_lookup = options_pool[["option_symbol", "date", "mid"]].drop_duplicates()
            all_signals = pd.merge(all_signals, options_lookup, on=["option_symbol", "date"], how="left")
 
            engine = OptionBacktestEngine(
                initial_capital=config.get("RISK_CONFIG", {}).get("initial_capital", 1000000.0),
                n_simulations=config.get("BACKTEST_CONFIG", {}).get("n_simulations", 100),
                slippage_pct=config.get("BACKTEST_CONFIG", {}).get("slippage_pct", 0.001)
            )
            all_signals["size"] = 10.0
            engine.run(all_signals, all_signals["size"])
            
             kpis = engine.get_kpis()
             self.log.info("Backtest results: Sharpe=%.2f, Return=%.2f", kpis.get("sharpe_ratio", 0), kpis.get("total_return", 0))
             engine.save_reports()
             
             # Обновляем Kelly-статистику на основе OOS-сделок
            update_kelly_stats_from_oos_trades(engine.trades)
            
            # Возвращаем структурированный результат
            return ForecastPipelineResult(
                fold_metrics=[artifact.metrics] if hasattr(artifact, 'metrics') else [],
                oos_predictions=pd.DataFrame(),
                thresholds={"bull_t": bull_t, "bear_t": bear_t} if 'bull_t' in locals() else {},
                calibration_metrics={},
                selected_trades=pd.DataFrame(engine.trades) if engine.trades else pd.DataFrame()
            )
            all_signals["size"] = 10.0
            engine.run(all_signals, all_signals["size"])
            
            kpis = engine.get_kpis()
            self.log.info("Backtest results: Sharpe=%.2f, Return=%.2f", kpis.get("sharpe_ratio", 0), kpis.get("total_return", 0))
            engine.save_reports()
            
            # Обновляем Kelly-статистику на основе OOS-сделок
            update_kelly_stats_from_oos_trades(engine.trades)
            
            # Возвращаем структурированный результат
            return ForecastPipelineResult(
                fold_metrics=[artifact.metrics] if hasattr(artifact, 'metrics') else [],
                oos_predictions=pd.DataFrame(),
                thresholds={"bull_t": bull_t, "bear_t": bear_t} if 'bull_t' in locals() else {},
                calibration_metrics={},
                selected_trades=pd.DataFrame(engine.trades) if engine.trades else pd.DataFrame()
            )
            all_signals["size"] = 10.0
            engine.run(all_signals, all_signals["size"])
            
             kpis = engine.get_kpis()
             self.log.info("Backtest results: Sharpe=%.2f, Return=%.2f", kpis.get("sharpe_ratio",0), kpis.get("total_return",0))
             engine.save_reports()
            
            # Обновляем Kelly-статистику на основе OOS-сделок
            update_kelly_stats_from_oos_trades(engine.trades)
            
            # Возвращаем структурированный результат
            return ForecastPipelineResult(
                fold_metrics=[artifact.metrics] if hasattr(artifact, 'metrics') else [],
                oos_predictions=pd.DataFrame(),  # Placeholder for actual OOS predictions
                thresholds={"bull_t": bull_t, "bear_t": bear_t} if 'bull_t' in locals() else {},
                calibration_metrics={},  # Placeholder for calibration metrics
                selected_trades=pd.DataFrame(engine.trades) if engine.trades else pd.DataFrame()
            )

        except Exception as exc:
            self.log.exception("Forecast pipeline error: %s", exc)
            return PipelineResult(status=1, message=str(exc), metrics={})
