# backtest/engine.py
"""Движки бэктеста.

Содержит два класса:

* ``BacktestEngine`` — старый упрощённый движок. Сохраняется для обратной
  совместимости (используется walk_forward.py и старыми тестами).
* ``OptionBacktestEngine`` — реалистичный опционный бэктест: симулирует
  движение базового актива методом GBM до даты экспирации и ежедневно
  переоценивает позицию через биномиальную модель Cox-Ross-Rubinstein.

Главные идеи реалистичного движка
---------------------------------
1. Открытие позиции по теоретической цене с учётом проскальзывания.
2. Для каждой сделки прогоняется ``n_simulations`` траекторий цены
   базового актива до экспирации (геометрическое броуновское движение
   с параметром ``realized_vol``).
3. На каждом шаге опцион переоценивается биномиальной моделью с
   уменьшающимся ``T`` — это даёт реалистичную динамику P&L (тета,
   гамма, реализованная волатильность).
4. Позиция закрывается при достижении стоп-лосса/тейк-профита либо в
   день экспирации по внутренней стоимости.
5. Equity curve строится по дням (общая временная сетка), не по сделкам.
6. KPI получаются осмысленными: hit_rate в (0, 1), Sharpe — в
   разумном диапазоне.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backtest.costs import adjust_price_for_entry, calculate_transaction_costs
from pricing.binomial import _crr_price, price_american


# ---------------------------------------------------------------------------
# Старый движок: оставлен ради обратной совместимости (walk_forward, тесты).
# Не использовать в новом коде — KPI получаются невалидными.
# ---------------------------------------------------------------------------


def backtest_engine(signals, initial_capital: float = 1_000_000) -> Dict[str, Any]:
    """Wrapper function for backward compatibility (legacy, see module docstring)."""
    engine = BacktestEngine(initial_capital=initial_capital)
    for idx, row in signals.iterrows():
        price = row.get("fair_value", row.get("mid", 0))
        engine.execute_trade(row["signal"], price, row.get("quantity", 1))
        engine.mark_to_market(price)
    results = engine.get_results()
    return {
        "capital": engine.capital,
        "equity_curve": results["equity_curve"],
        "trades": results["trades"],
    }


class BacktestEngine:
    """Упрощённый движок (legacy). См. ``OptionBacktestEngine``."""

    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[float] = [initial_capital]
        self.date = datetime.now()

    def execute_trade(self, signal: str, price: float, quantity: float = 1) -> None:
        if signal == "BUY":
            exec_price = adjust_price_for_entry(price, is_buy=True)
            cost = calculate_transaction_costs(exec_price, quantity)
            self.capital -= (exec_price * quantity) + cost
            self.positions.append({
                "entry_date": self.date,
                "type": "long",
                "entry_price": exec_price,
                "quantity": quantity,
                "entry_capital": self.capital,
            })
        elif signal == "SELL":
            exec_price = adjust_price_for_entry(price, is_buy=False)
            cost = calculate_transaction_costs(exec_price, quantity)
            self.capital += (exec_price * quantity) - cost
            for pos in self.positions:
                pnl = (exec_price - pos["entry_price"]) * pos["quantity"] - cost
                self.trades.append({
                    "entry_date": pos["entry_date"],
                    "exit_date": self.date,
                    "pnl": pnl,
                    "return": pnl / pos["entry_price"] if pos["entry_price"] > 0 else 0,
                })
            self.positions = []

    def mark_to_market(self, current_price: float) -> None:
        total_value = self.capital
        for pos in self.positions:
            total_value += pos["quantity"] * current_price
        self.equity_curve.append(total_value)

    def get_results(self) -> Dict[str, Any]:
        return {
            "capital": self.capital,
            "trades": pd.DataFrame(self.trades),
            "equity_curve": pd.Series(self.equity_curve),
        }

    def run(self, signals, sizes) -> None:
        price = 0.0
        for idx, row in signals.iterrows():
            signal_type = "BUY" if row.get("predicted_edge", 0) > 0 else "SELL"
            price = row.get("fair_value", row.get("mid", 0))
            if price <= 0:
                continue
            if hasattr(sizes, "iloc"):
                quantity = sizes.iloc[idx] if idx < len(sizes) else 1
            else:
                quantity = sizes if sizes > 0 else 1
            if quantity <= 0:
                continue
            self.execute_trade(signal_type, price, quantity)
            self.mark_to_market(price)
        if self.positions:
            last_price = price if price > 0 else 100.0
            total_qty = sum(pos["quantity"] for pos in self.positions)
            self.execute_trade("SELL", last_price, total_qty)

    def save_reports(self) -> None:
        _save_reports(
            equity_curve=self.equity_curve,
            trades=self.trades,
            extra_kpis=None,
            tag="BacktestEngine",
        )

    def get_equity_curve(self) -> pd.Series:
        return pd.Series(self.equity_curve)

    def get_trades(self) -> pd.DataFrame:
        return pd.DataFrame(self.trades)


# ---------------------------------------------------------------------------
# Новый движок: реалистичный опционный бэктест
# ---------------------------------------------------------------------------


class OptionBacktestEngine:
    """Реалистичный бэктест опционных сделок.

    Параметры
    ---------
    initial_capital : float
        Начальный капитал портфеля.
    realized_vol : float
        Реализованная волатильность для GBM-симуляции базового актива.
        Должна отражать историческую волатильность underlying'а
        (а не IV, которая используется для расчёта теоретической цены).
    n_simulations : int
        Количество траекторий цены, по которым усредняется P&L каждой
        сделки. Чем больше — тем более стабильные KPI.
    seed : int | None
        Seed для воспроизводимости.
    r : float
        Безрисковая ставка (для модели CRR).
    dividend : float
        Дивидендная доходность (или, для фьючерсных опционов, может
        использоваться как стоимость переноса).
    sigma_for_pricing : float
        Волатильность, используемая в биномиальной модели для переоценки
        опциона (implied volatility). По умолчанию = realized_vol.
    stop_loss_pct : float | None
        Уровень стоп-лосса в % от цены входа (например, 0.5 → -50%).
        ``None`` отключает.
    take_profit_pct : float | None
        Уровень тейк-профита (например, 1.0 → +100%). ``None`` отключает.
    binomial_steps : int
        Количество шагов CRR-дерева при переоценке. Меньше → быстрее.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        realized_vol: float = 0.20,
        real_drift: float = 0.0, # Добавили реальный дрифт (вместо r-d)
        n_simulations: int = 200, # Увеличили для точности хвостов
        seed: Optional[int] = 42,
        r: float = 0.04,
        dividend: float = 0.0,
        sigma_for_pricing: Optional[float] = None,
        stop_loss_pct: Optional[float] = 0.5,
        take_profit_pct: Optional[float] = 1.0,
        binomial_steps: int = 30,
    ):
        self.initial_capital = float(initial_capital)
        self.realized_vol = float(realized_vol)
        self.real_drift = float(real_drift)
        self.n_simulations = int(n_simulations)
        self.seed = seed
        self.r = float(r)
        self.dividend = float(dividend)
        # Если sigma_for_pricing не задана, берем realized_vol, 
        # но в идеале здесь должна быть "грязная" волатильность с шумом
        self.sigma_for_pricing = float(
            sigma_for_pricing if sigma_for_pricing is not None else realized_vol
        )
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.binomial_steps = int(binomial_steps)

        # Результаты
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[float] = [self.initial_capital]
        self.equity_dates: List[Optional[datetime]] = [None]

    # ------------------------------------------------------------------
    # Основной публичный API
    # ------------------------------------------------------------------

    def run(self, signals: pd.DataFrame, sizes) -> None:
        """Прогоняет бэктест по сигналам с указанными размерами позиций.

        ``signals`` — DataFrame со столбцами:
            underlying_price, strike, type ('call'/'put'),
            fair_value (или mid), days_to_expiry, side ('buy'/'sell'),
            predicted_edge, date (optional).
        ``sizes`` — Series или скаляр с количеством контрактов.
        """
        if signals is None or len(signals) == 0:
            return

        # rng для GBM и шума
        rng = np.random.default_rng(self.seed)

        # Подготовим список сделок: (params, qty, side)
        trade_specs = self._build_trade_specs(signals, sizes)
        if not trade_specs:
            return

        # Календарная сетка P&L
        # Если есть колонка 'date', считаем абсолютную сетку. Иначе относительную.
        has_dates = "date" in signals.columns
        if has_dates:
            signals_dates = pd.to_datetime(signals["date"])
            start_global = signals_dates.min()
            max_expiry_days = max(spec["days_to_expiry"] for spec in trade_specs)
            end_global = signals_dates.max() + timedelta(days=max_expiry_days)
            total_days = (end_global - start_global).days + 1
            daily_pnl = np.zeros(total_days, dtype=float)
            
            # Совместимость дат для equity_dates
            self.equity_dates = [start_global + timedelta(days=d) for d in range(total_days)]
        else:
            max_days = max(spec["days_to_expiry"] for spec in trade_specs)
            total_days = max_days + 1
            daily_pnl = np.zeros(total_days, dtype=float)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            self.equity_dates = [today + timedelta(days=d) for d in range(total_days)]

        for i, spec in enumerate(trade_specs):
            sim_results = self._simulate_trade(spec, rng)
            mean_daily_value = sim_results["mean_daily_value"]
            
            # Определяем смещение (offset) для этой сделки
            offset = 0
            if has_dates:
                row_date = pd.to_datetime(signals.iloc[i].get("date"))
                offset = (row_date - start_global).days

            # Дневные приращения P&L (mark-to-market) суммируем в общую кривую
            # mean_daily_value[d] - это накопленный P&L сделки на день d
            daily_increments = np.diff(mean_daily_value, prepend=0.0)
            # Учитываем, что на [0] у нас уже P&L первого дня (входные издержки)
            # В коде _simulate_trade: value_per_day[0] = -entry_cost
            
            for d, inc in enumerate(daily_increments):
                if offset + d < total_days:
                    daily_pnl[offset + d] += inc
            
            # Финализируем сделку
            self.trades.append(sim_results["trade_record"])

        # Equity curve: накапливаем дневные изменения от initial_capital
        equity = np.zeros(total_days, dtype=float)
        equity[0] = self.initial_capital + daily_pnl[0]
        for d in range(1, total_days):
            equity[d] = equity[d - 1] + daily_pnl[d]
            
        self.equity_curve = equity.tolist()

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _build_trade_specs(self, signals: pd.DataFrame, sizes) -> List[Dict[str, Any]]:
        specs: List[Dict[str, Any]] = []
        # Для итерации по sizes по позициям — нужен сброшенный индекс
        sizes_list: List[float]
        if isinstance(sizes, pd.Series):
            sizes_list = [float(x) if pd.notna(x) else 0.0 for x in sizes.tolist()]
        elif isinstance(sizes, (list, tuple, np.ndarray)):
            sizes_list = [float(x) if pd.notna(x) else 0.0 for x in sizes]
        else:
            try:
                sizes_list = [float(sizes)] * len(signals)
            except (TypeError, ValueError):
                sizes_list = [1.0] * len(signals)

        for i, (_, row) in enumerate(signals.iterrows()):
            qty = sizes_list[i] if i < len(sizes_list) else 0.0
            if qty <= 0:
                continue

            S = self._safe_float(row.get("underlying_price"))
            K = self._safe_float(row.get("strike"))
            opt_type = str(row.get("type", "call")).lower()
            if not opt_type.startswith(("c", "p")):
                opt_type = "call"
            opt_type = "call" if opt_type.startswith("c") else "put"

            entry_price = self._safe_float(row.get("fair_value", row.get("mid", 0.0)))
            if entry_price <= 0:
                continue

            dte = int(self._safe_float(row.get("days_to_expiry", 0.0)))
            if dte <= 0:
                continue
            if S <= 0 or K <= 0:
                continue

            side_raw = str(row.get("side", "")).lower()
            edge = self._safe_float(row.get("predicted_edge", 0.0))
            if side_raw in ("buy", "sell"):
                side = side_raw
            else:
                # Совместимость со старым кодом: edge>0 → BUY, иначе SELL
                side = "buy" if edge > 0 else "sell"

            specs.append({
                "S": S,
                "K": K,
                "type": opt_type,
                "entry_price": entry_price,
                "days_to_expiry": dte,
                "side": side,
                "qty": qty,
                "edge": edge,
            })
        return specs

    def _simulate_trade(
        self, spec: Dict[str, Any], rng: np.random.Generator
    ) -> Dict[str, Any]:
        """Симулирует одну сделку: GBM + ежедневная переоценка.

        Возвращает:
            mean_daily_value : np.ndarray[float] — средняя ст-ть позиции
                по дням (включая день 0 = после входа).
            trade_record     : dict — запись для self.trades.
        """
        S0 = spec["S"]
        K = spec["K"]
        T0 = spec["days_to_expiry"] / 365.0
        opt_type = spec["type"]
        n_days = spec["days_to_expiry"]
        qty = spec["qty"]
        side = spec["side"]
        entry_price = spec["entry_price"]

        # Цена входа с проскальзыванием
        is_buy = side == "buy"
        exec_entry = adjust_price_for_entry(entry_price, is_buy=is_buy)
        entry_cost = calculate_transaction_costs(exec_entry, qty)

        # Стоимость позиции (для лонга это инвестиция, для шорта — кредит):
        # Условимся, что P&L на единицу = (exit - entry) * sign(side),
        # где sign=+1 для buy, -1 для sell.
        side_sign = 1.0 if is_buy else -1.0

        # Параметры GBM
        sigma_real = max(self.realized_vol, 1e-4)
        
        # BREAKING CIRCULARITY (Point 5.1): 
        # Добавляем шум к волатильности переоценки, чтобы бэктест не был 
        # идеальной копией сигнальной модели.
        sigma_noise = rng.normal(0, 0.02) # 2% std dev noise
        sigma_iv = max(self.sigma_for_pricing + sigma_noise, 1e-4)
        
        dt = 1.0 / 365.0
        mu = self.real_drift # Использование РЕАЛЬНОГО дрифта вместо r-d

        # Симуляция
        n_sims = max(self.n_simulations, 1)
        daily_value_matrix = np.zeros((n_sims, n_days + 1), dtype=float)
        exit_pnl_per_sim = np.zeros(n_sims, dtype=float)
        exit_day_per_sim = np.zeros(n_sims, dtype=int)
        exit_reason_per_sim: List[str] = []

        # ... (код SL/TP без изменений) ...
        # Стоп-лосс / тейк-профит уровни в абсолютных ценах опциона
        sl_level = (
            entry_price * (1 - self.stop_loss_pct)
            if (self.stop_loss_pct is not None and is_buy)
            else None
        )
        tp_level = (
            entry_price * (1 + self.take_profit_pct)
            if (self.take_profit_pct is not None and is_buy)
            else None
        )
        # Для шорта: SL = цена выросла на stop_loss_pct, TP = упала на TP%
        if not is_buy:
            sl_level = (
                entry_price * (1 + self.stop_loss_pct)
                if self.stop_loss_pct is not None
                else None
            )
            tp_level = (
                entry_price * (1 - self.take_profit_pct)
                if self.take_profit_pct is not None
                else None
            )

        for sim_idx in range(n_sims):
            # GBM траектория цены underlying (n_days+1 точек, t=0..n_days)
            S_path = np.zeros(n_days + 1, dtype=float)
            S_path[0] = S0
            if n_days > 0:
                z = rng.standard_normal(n_days)
                # Дрифт реального мира
                drift = (mu - 0.5 * sigma_real ** 2) * dt
                diffusion = sigma_real * math.sqrt(dt)
                log_returns = drift + diffusion * z
                S_path[1:] = S0 * np.exp(np.cumsum(log_returns))

            # Ежедневная переоценка опциона
            opt_value = np.zeros(n_days + 1, dtype=float)
            opt_value[0] = entry_price
            exited = False
            exit_day = n_days
            exit_reason = "expiry"

            for d in range(1, n_days + 1):
                t_remaining = (n_days - d) / 365.0
                S_t = S_path[d]
                if t_remaining <= 0:
                    if opt_type == "call":
                        opt_value[d] = max(S_t - K, 0.0)
                    else:
                        opt_value[d] = max(K - S_t, 0.0)
                else:
                    opt_value[d] = _crr_price(
                        S=S_t,
                        K=K,
                        T=t_remaining,
                        r=self.r,
                        sigma=sigma_iv, 
                        dividend=self.dividend,
                        option_type=opt_type,
                        steps=self.binomial_steps,
                        american=True,
                    )

                if not exited:
                    if is_buy:
                        if sl_level is not None and opt_value[d] <= sl_level:
                            exited = True
                            exit_day = d
                            exit_reason = "stop_loss"
                        elif tp_level is not None and opt_value[d] >= tp_level:
                            exited = True
                            exit_day = d
                            exit_reason = "take_profit"
                    else:
                        if sl_level is not None and opt_value[d] >= sl_level:
                            exited = True
                            exit_day = d
                            exit_reason = "stop_loss"
                        elif tp_level is not None and opt_value[d] <= tp_level:
                            exited = True
                            exit_day = d
                            exit_reason = "take_profit"

            if exited:
                exit_price = opt_value[exit_day]
            else:
                exit_price = opt_value[n_days]
                exit_day = n_days

            exec_exit = adjust_price_for_entry(exit_price, is_buy=not is_buy)
            exit_cost = calculate_transaction_costs(exec_exit, qty)
            pnl = (exec_exit - exec_entry) * side_sign * qty - entry_cost - exit_cost

            value_per_day = np.zeros(n_days + 1, dtype=float)
            value_per_day[0] = -entry_cost
            for d in range(1, n_days + 1):
                if d <= exit_day:
                    mtm_pnl = (opt_value[d] - exec_entry) * side_sign * qty - entry_cost
                    if d == exit_day: mtm_pnl -= exit_cost
                    value_per_day[d] = mtm_pnl
                else:
                    value_per_day[d] = pnl

            daily_value_matrix[sim_idx] = value_per_day
            exit_pnl_per_sim[sim_idx] = pnl
            exit_day_per_sim[sim_idx] = exit_day
            exit_reason_per_sim.append(exit_reason)

        # Статистика распределения P&L
        mean_pnl = float(np.mean(exit_pnl_per_sim))
        var_95 = float(np.percentile(exit_pnl_per_sim, 5))
        cvar_95 = float(exit_pnl_per_sim[exit_pnl_per_sim <= var_95].mean()) if any(exit_pnl_per_sim <= var_95) else var_95
        
        # Усредняем по дням
        mean_daily_value = daily_value_matrix.mean(axis=0)

        if exit_reason_per_sim:
            from collections import Counter
            most_common_reason = Counter(exit_reason_per_sim).most_common(1)[0][0]
        else:
            most_common_reason = "expiry"

        trade_record = {
            "entry_date": datetime.now(),
            "exit_date": datetime.now() + timedelta(days=int(np.mean(exit_day_per_sim))),
            "S0": S0, "K": K, "type": opt_type, "side": side, "quantity": qty,
            "entry_price": exec_entry,
            "pnl": mean_pnl,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "return": mean_pnl / (exec_entry * qty) if exec_entry * qty > 0 else 0.0,
            "days_held": float(np.mean(exit_day_per_sim)),
            "exit_reason": most_common_reason,
            "win_rate_sim": float((exit_pnl_per_sim > 0).mean()),
        }

        return {"mean_daily_value": mean_daily_value, "trade_record": trade_record}

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or pd.isna(value):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    # ------------------------------------------------------------------
    # Совместимый API
    # ------------------------------------------------------------------

    def get_equity_curve(self) -> pd.Series:
        return pd.Series(self.equity_curve)

    def get_trades(self) -> pd.DataFrame:
        return pd.DataFrame(self.trades)

    def save_reports(self) -> None:
        _save_reports(
            equity_curve=self.equity_curve,
            trades=self.trades,
            extra_kpis={
                "n_simulations": self.n_simulations,
                "realized_vol": self.realized_vol,
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct,
            },
            tag="OptionBacktestEngine",
        )


# ---------------------------------------------------------------------------
# Общий код для сохранения отчётов
# ---------------------------------------------------------------------------


def _save_reports(
    equity_curve: List[float],
    trades: List[Dict[str, Any]],
    extra_kpis: Optional[Dict[str, Any]],
    tag: str,
) -> None:
    """Сохраняет equity_curve.csv, trades.csv и report.html в reports/."""
    os.makedirs("reports", exist_ok=True)

    pd.Series(equity_curve).to_csv("reports/equity_curve.csv", index=False)

    if trades:
        pd.DataFrame(trades).to_csv("reports/trades.csv", index=False)

    equity_series = pd.Series(equity_curve)
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()

    total_return = (
        (equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0]
        if len(equity_series) > 1 and equity_series.iloc[0] != 0
        else 0
    )
    roll_max = equity_series.cummax()
    drawdown = (
        (equity_series - roll_max) / roll_max * 100
        if len(equity_series) > 1
        else pd.Series([0])
    )
    max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0

    hit_rate = 0.0
    if not trades_df.empty and "pnl" in trades_df.columns:
        profitable = (trades_df["pnl"] > 0).sum()
        hit_rate = profitable / len(trades_df) if len(trades_df) > 0 else 0

    extras_html = ""
    if extra_kpis:
        extras_html = (
            "<h3>Параметры симуляции</h3><ul>"
            + "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in extra_kpis.items())
            + "</ul>"
        )

    trade_rows_html = ""
    if not trades_df.empty:
        cols = [c for c in ("entry_date", "exit_date", "type", "side", "quantity",
                            "entry_price", "pnl", "return", "exit_reason",
                            "win_rate_sim") if c in trades_df.columns]
        if cols:
            head = "".join(f"<th>{c}</th>" for c in cols)
            body = ""
            for _, r in trades_df.iterrows():
                cells = "".join(f"<td>{r[c]}</td>" for c in cols)
                body += f"<tr>{cells}</tr>"
            trade_rows_html = f"<table><tr>{head}</tr>{body}</table>"
    if not trade_rows_html:
        trade_rows_html = "<p>No trades</p>"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Trading Strategy Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .kpi-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .kpi-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .kpi-label {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #c0392b; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; font-size: 13px; }}
        th {{ background-color: #3498db; color: white; }}
    </style>
</head>
<body>
    <h1>Trading Strategy Performance Report ({tag})</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-value {'positive' if total_return >= 0 else 'negative'}">{total_return:.4f}</div>
            <div class="kpi-label">Total Return</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value negative">{max_drawdown:.4f}</div>
            <div class="kpi-label">Max Drawdown (%)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value {'positive' if hit_rate >= 0.5 else 'negative'}">{hit_rate:.4f}</div>
            <div class="kpi-label">Hit Rate</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{len(trades)}</div>
            <div class="kpi-label">Total Trades</div>
        </div>
    </div>
    {extras_html}
    <h2>Trade Details</h2>
    {trade_rows_html}
</body>
</html>"""

    with open("reports/report.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[{tag}] Reports saved to reports/")
