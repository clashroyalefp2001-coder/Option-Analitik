import pandas as pd
import numpy as np
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from backtest.engine import OptionBacktestEngine

log = logging.getLogger(__name__)

class RobustnessTester:
    """Фреймворк для стресс-тестирования стратегии (Robustness Audit)."""

    def __init__(self, engine_base_params: Dict[str, Any]):
        self.base_params = engine_base_params.copy()
        # Hardened defaults
        self.base_params["realized_vol"] = float(self.base_params.get("realized_vol") or 0.20)
        self.base_params["sigma_for_pricing"] = float(self.base_params.get("sigma_for_pricing") or self.base_params["realized_vol"])
        
        self.results: List[Dict[str, Any]] = []

    def _compute_kpis(self, equity_curve: List[float]) -> Dict[str, float]:
        """Расчет ключевых метрик для одного прогона с защитой от NaN."""
        if not equity_curve or len(equity_curve) < 2:
            return {"sharpe": 0.0, "cagr": -1.0, "max_dd": 1.0, "calmar": -1.0}
        
        eq = np.array(equity_curve)
        # Защита от деления на ноль: если баланс 0, доходность -100%
        with np.errstate(divide='ignore', invalid='ignore'):
            returns = np.diff(eq) / eq[:-1]
            returns = np.nan_to_num(returns, nan=-1.0, posinf=0.0, neginf=-1.0)
        
        # Annualized Return (CAGR)
        days = len(eq)
        total_ret = (eq[-1] / eq[0]) - 1 if eq[0] > 0 else -1.0
        # Если была ликвидация, CAGR должен быть -100%
        if eq[-1] <= 0:
            cagr = -1.0
        else:
            cagr = (1 + total_ret) ** (252 / max(days, 1)) - 1
        
        # Sharpe
        vol = returns.std() * np.sqrt(252)
        sharpe = (returns.mean() * 252) / vol if vol > 0 else -10.0 # Сильный штраф за нулевую волатильность при смерти
        
        # Max Drawdown
        cum_max = np.maximum.accumulate(eq)
        # Если cum_max == 0, значит счет уже мертв
        with np.errstate(divide='ignore', invalid='ignore'):
            dd = np.where(cum_max > 0, (eq - cum_max) / cum_max, -1.0)
        max_dd = abs(float(dd.min()))
        
        calmar = cagr / max_dd if max_dd > 0 else -1.0
        
        return {
            "sharpe": float(sharpe),
            "cagr": float(cagr),
            "max_dd": float(max_dd),
            "calmar": float(calmar)
        }

    def run_stress_matrix(self, signals: pd.DataFrame, sizes: pd.Series):
        """Запуск полной матрицы стресс-тестов."""
        
        base_vol = float(self.base_params.get("realized_vol") or 0.20)
        base_sigma = float(self.base_params.get("sigma_for_pricing") or base_vol)
        base_jump = float(self.base_params.get("jump_lambda") or 0.1)
        base_basis = float(self.base_params.get("market_basis_std") or 0.02)
        base_slip = float(self.base_params.get("slippage_pct") or 0.001)
        base_comm = float(self.base_params.get("comm_per_contract") or 0.65)
        
        stress_grid = {
            "realized_vol": [0.70 * base_vol, 0.85 * base_vol, 1.0 * base_vol, 1.15 * base_vol, 1.30 * base_vol],
            "sigma_for_pricing": [0.80 * base_sigma, 0.90 * base_sigma, 1.0 * base_sigma, 1.10 * base_sigma, 1.20 * base_sigma],
            "jump_lambda": [0.0, 0.05, 0.10, 0.20, 0.40],
            "market_basis_std": [0.00, 0.01, 0.02, 0.04, 0.06],
            "slippage_pct": [0.0005, 0.001, 0.002, 0.003, 0.005],
            "comm_per_contract": [0.65, 1.00, 1.50, 2.00]
        }

        # 1. Основные тесты по сетке
        total_tests = sum(len(v) for v in stress_grid.values())
        current_test = 0
        
        for param, values in stress_grid.items():
            for val in values:
                current_test += 1
                if current_test % 5 == 0:
                    log.info(f"Progress: {current_test}/{total_tests} stress tests completed...")
                
                params = self.base_params.copy()
                params[param] = val
                params["n_simulations"] = 25 # Ускоряем еще сильнее для аудита
                
                engine = OptionBacktestEngine(**params)
                engine.run(signals, sizes)
                
                kpis = self._compute_kpis(engine.equity_curve)
                trades_df = pd.DataFrame(engine.trades)
                wr = (trades_df["pnl"] > 0).mean() if not trades_df.empty else 0
                
                # Добавляем пиковую загрузку маржи
                peak_margin = max(engine.margin_utilization_curve) if hasattr(engine, 'margin_utilization_curve') else 0.0
                
                self.results.append({
                    "test_type": "stress",
                    "param": param,
                    "value": val,
                    "win_rate": wr,
                    "peak_margin": peak_margin,
                    **kpis
                })

        # 2. Тест на стабильность Seed
        for s in range(10):
            params = self.base_params.copy()
            params["seed"] = 1000 + s # Разные сиды
            
            engine = OptionBacktestEngine(**params)
            engine.run(signals, sizes)
            
            kpis = self._compute_kpis(engine.equity_curve)
            trades_df = pd.DataFrame(engine.trades)
            wr = (trades_df["pnl"] > 0).mean() if not trades_df.empty else 0
            
            peak_margin = max(engine.margin_utilization_curve) if hasattr(engine, 'margin_utilization_curve') else 0.0
            
            self.results.append({
                "test_type": "seed_stability",
                "param": "seed",
                "value": s,
                "win_rate": wr,
                "peak_margin": peak_margin,
                **kpis
            })

    def get_report(self) -> str:
        """Генерация Markdown отчета."""
        df = pd.DataFrame(self.results)
        if df.empty:
            return "No results to report."
        
        # Считаем Sharpe Elasticity
        base_vol = self.base_params["realized_vol"]
        base_sharpe_df = df[(df["test_type"] == "stress") & 
                            (df["param"] == "realized_vol") & 
                            (np.isclose(df["value"], base_vol))]
        
        base_sharpe = base_sharpe_df["sharpe"].mean() if not base_sharpe_df.empty else df["sharpe"].mean()
        
        if np.isnan(base_sharpe) or base_sharpe == 0:
             base_sharpe = 1.0 # Avoid division by zero

        sharpe_min = df["sharpe"].min()
        sharpe_max = df["sharpe"].max()
        elasticity = (sharpe_max - sharpe_min) / base_sharpe
        
        # Sign Flip Rate
        flips = (df["cagr"] < 0).sum()
        flip_rate = flips / len(df)
        avg_wr = df["win_rate"].mean()
        
        report = []
        report.append("# Strategy Robustness Audit Report")
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n## Executive Summary")
        report.append(f"- **Sharpe Elasticity**: {elasticity:.2%} ({'Excellent' if elasticity < 0.2 else 'Normal' if elasticity < 0.4 else 'Suspicious' if elasticity < 0.6 else 'STRESS'})")
        report.append(f"- **Sign Flip Rate**: {flip_rate:.2%} ({'Healthy' if flip_rate < 0.2 else 'Vulnerable'})")
        report.append(f"- **Average Stress Win Rate**: {avg_wr:.2%}")
        
        report.append("\n## Stress Matrix Results")
        report.append("| Test | Param | Value | Sharpe | CAGR | MaxDD | WinRate | PeakMargin |")
        report.append("| :--- | :---- | :---- | :----- | :--- | :---- | :------ | :--------- |")
        
        # Sort by impact
        df_sorted = df.sort_values(["test_type", "param", "value"])
        for _, row in df_sorted.iterrows():
            margin_str = f"{row['peak_margin']:.2%}" if 'peak_margin' in row else "N/A"
            report.append(f"| {row['test_type']} | {row['param']} | {row['value']:.4f} | {row['sharpe']:.2f} | {row['cagr']:.2%} | {row['max_dd']:.2%} | {row['win_rate']:.2%} | {margin_str} |")
            
        return "\n".join(report)

    def save_report(self, path: Optional[str] = None):
        """Сохранение отчёта с использованием абсолютных путей для надёжности."""
        if path is None:
            # Путь относительно папки, где лежит этот файл
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            path = os.path.join(base_dir, "reports", "robustness_audit.md")
        
        report = self.get_report()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n[Robustness] Detailed report explicitly saved to: {path}")
        except Exception as e:
            print(f"\n[Robustness] ERROR saving report to {path}: {e}")

        # Summary to console
        print("\n=== ROBUSTNESS AUDIT SUMMARY ===")
        df = pd.DataFrame(self.results)
        if not df.empty:
            agg_dict = {"sharpe": ["mean", "min", "max"]}
            if "peak_margin" in df.columns:
                agg_dict["peak_margin"] = ["max"]
            
            summary = df.groupby(["test_type", "param"]).agg(agg_dict).reset_index()
            print(summary.to_string(index=False))
