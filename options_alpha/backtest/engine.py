# backtest/engine.py
"""Движки бэктеста.

Содержит два класса:

* ``BacktestEngine`` — старый упрощённый движок. Сохраняется для обратной
  совместимости (используется walk_forward.py и старыми тестами).
* ``OptionBacktestEngine`` — реалистичный опционный бэктест: симулирует
  движение базового актива методом GBM до даты экспирации и ежедневно
  переоценивает позицию через Black-Scholes.

  Особенности портфельного моделирования:
  - Динамические маржинальные требования (Proxy SPAN/Reg-T) для шортов.
  - Проверка покупательской способности (Buying Power) перед входом.
  - Path-dependent liquidation: при падении свободного эквити ниже порога 
    путь симуляции считается ликвидированным.

Главные идеи реалистичного движка
---------------------------------
1. Открытие позиции по теоретической цене с учётом проскальзывания.
2. Для каждой сделки прогоняется ``n_simulations`` траекторий цены
   базового актива до экспирации (геометрическое броуновское движение
   с параметром ``realized_vol``).
3. На каждом шаге опцион переоценивается BS моделью с
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

from backtest.costs import adjust_price_for_entry, calculate_transaction_costs, calculate_exercise_assignment_costs
from pricing.binomial import _crr_price, price_american


from scipy.stats import norm

def _black_scholes_vanilla(S, K, T, r, sigma, q, opt_type="call"):
    """Аналитическая модель (Market Reality Proxy). 
    Векторизованная версия для высокой производительности.
    """
    if np.isscalar(T) and T <= 0:
        if opt_type == "call":
            return np.maximum(S - K, 0.0)
        else:
            return np.maximum(K - S, 0.0)
    
    # Регуляризация параметров (работает и для скаляров, и для массивов)
    S = np.maximum(S, 1e-6)
    sigma = np.maximum(sigma, 1e-4)
    T = np.maximum(T, 1e-8) # Избегаем деления на 0
    
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if opt_type == "call":
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    
    return np.maximum(price, 0.0)


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
    """Реалистичный бэктест с защитой от цикличности.
    
    Методы защиты:
    1. Market Reality != Signal Model: Бэктест использует BS-аналитику, 
       сигнал использует CRR-деревья.
    2. Merton Jump Diffusion: Рынок в бэктесте прыгает, сигнал ждет GBM.
    3. Stochastic Liquidity Basis: Стохастический шум в ценах опционов.
    4. Tail Risk Logging: VaR/CVaR по каждой сделке.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        realized_vol: float = 0.20,
        real_drift: float = 0.0,
        n_simulations: int = 100,
        seed: Optional[int] = 42,
        r: float = 0.04,
        dividend: float = 0.0,
        sigma_for_pricing: Optional[float] = None,
        stop_loss_pct: Optional[float] = 0.5,
        take_profit_pct: Optional[float] = 1.0,
        # Параметры "Рыночного Хаоса"
        jump_lambda: float = 0.1,    # Прыжки (раз в 10 лет на акцию в среднем)
        market_basis_std: float = 0.02, # 2% шум в котировках
        # Параметры издержек (для стресс-тестов)
        slippage_pct: float = 0.001,
        comm_per_contract: float = 0.65,
    ):
        self.initial_capital = float(initial_capital)
        self.realized_vol = float(realized_vol)
        self.real_drift = float(real_drift)
        self.n_simulations = int(n_simulations)
        self.seed = seed
        self.r = float(r)
        self.dividend = float(dividend)
        self.sigma_for_pricing = float(sigma_for_pricing if sigma_for_pricing is not None else realized_vol)
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.jump_lambda = jump_lambda
        self.market_basis_std = market_basis_std
        self.slippage_pct = slippage_pct
        self.comm_per_contract = comm_per_contract

        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[float] = [self.initial_capital]
        self.equity_curve_raw: List[float] = [self.initial_capital]
        self.equity_dates: List[Optional[datetime]] = []
        self.margin_utilization_curve: List[float] = [0.0]

    # ------------------------------------------------------------------
    # Основной публичный API
    # ------------------------------------------------------------------

    def run(self, signals: pd.DataFrame, sizes, realized_world_idx: Optional[int] = None) -> None:
        """Прогоняет бэктест по сигналам с указанными размерами позиций.
        
        Рефракторинг: переход на динамический учёт портфеля (snapshots) 
        вместо накопительных матриц для корректной обработки маржи и ликвидации.
        """
        if signals is None or len(signals) == 0:
            return

        rng = np.random.default_rng(self.seed)

        if realized_world_idx is None:
            realized_world_idx = rng.integers(0, self.n_simulations)

        trade_specs = self._build_trade_specs(signals, sizes)
        if not trade_specs:
            return

        has_dates = "date" in signals.columns
        if has_dates:
            signals_dates = pd.to_datetime(signals["date"])
            start_global = signals_dates.min()
            max_expiry_days = max(spec["days_to_expiry"] for spec in trade_specs)
            end_global = signals_dates.max() + timedelta(days=max_expiry_days)
            total_days = (end_global - start_global).days + 1
            self.equity_dates = [start_global + timedelta(days=d) for d in range(total_days)]
        else:
            max_days = max(spec["days_to_expiry"] for spec in trade_specs)
            total_days = max_days + 1
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            self.equity_dates = [today + timedelta(days=d) for d in range(total_days)]

        # Генерируем рыночные пути
        dt = 1.0 / 365.0
        z_noise = rng.standard_normal((self.n_simulations, total_days))
        jump_noise = (rng.random((self.n_simulations, total_days)) < self.jump_lambda * dt).astype(float)
        jump_sizes = jump_noise * rng.normal(-0.05, 0.1, (self.n_simulations, total_days))
        
        log_rets = (self.real_drift - 0.5 * self.realized_vol**2) * dt + \
                   self.realized_vol * math.sqrt(dt) * z_noise + jump_sizes
        
        path_ivs = self.sigma_for_pricing * (1 + rng.normal(0, 0.05, self.n_simulations))

        # --- PORTFOLIO LEDGER (Cash tracking) ---
        path_cash = np.full((self.n_simulations, total_days), self.initial_capital)
        
        # --- PORTFOLIO SNAPSHOTS (MTM, Margin, Equity) ---
        path_equity = np.zeros((self.n_simulations, total_days))
        path_margin_utilization = np.zeros((self.n_simulations, total_days))
        path_reserved_margin = np.zeros((self.n_simulations, total_days))
        path_position_value = np.zeros((self.n_simulations, total_days))
        path_terminated = np.zeros(self.n_simulations, dtype=bool)
        
        # Реестр активных позиций по каждому пути симуляции
        # Каждая запись: Dict с матрицами PV и Margin только для этого пути
        open_positions: List[List[Dict[str, Any]]] = [[] for _ in range(self.n_simulations)]

        daily_groups: Dict[int, List[Dict[str, Any]]] = {}
        for spec in trade_specs:
            row_date = pd.to_datetime(spec.get("date", datetime.now()))
            offset = (row_date - start_global).days if has_dates else 0
            if offset not in daily_groups:
                daily_groups[offset] = []
            daily_groups[offset].append(spec)

        # Основной цикл бэктеста
        for d in range(total_days):
            # 1. Перенос Cash с предыдущего дня
            if d > 0:
                path_cash[:, d] = path_cash[:, d-1]

            # 2. Обработка естественных выходов и обновление Snapshot (MTM)
            for s in range(self.n_simulations):
                # Если путь терминирован (банкротство), копируем состояние и выходим
                if path_terminated[s]:
                    path_equity[s, d] = path_equity[s, d-1]
                    path_cash[s, d] = path_cash[s, d-1]
                    path_reserved_margin[s, d] = 0.0
                    path_position_value[s, d] = 0.0
                    continue

                # Проверка естественных закрытий СЕГОДНЯ (Stop Loss, Take Profit, Expiry)
                for pos in open_positions[s][:]:
                    if d == pos['start_day'] + pos['exit_day']:
                        # Позиция закрывается сегодня по плану симуляции
                        rel_d = d - pos['start_day']
                        pv_exit = pos['pv_matrix'][rel_d]
                        # Считаем итоговый приток в Cash
                        exit_proceeds = (pos['side_sign'] * pv_exit * pos['qty_mult']) - pos['exit_fee']
                        path_cash[s, d:] += exit_proceeds
                        
                        # Если это наш "реализованный" путь — фиксируем сделку в лог
                        if s == realized_world_idx and pos['trade_record'] and not pos.get('closed', False):
                            tr = pos['trade_record']
                            tr["exit_date"] = self.equity_dates[d] if d < len(self.equity_dates) else None
                            tr["days_held"] = d - pos['start_day']
                            # PnL = Денежный поток при закрытии + Денежный поток при открытии
                            tr["pnl"] = exit_proceeds + pos['entry_outlay']
                            tr["return"] = tr["pnl"] / tr["margin_required"] if tr["margin_required"] > 0 else 0
                            tr["is_executed"] = True
                            self.trades.append(tr)
                            pos['closed'] = True
                            
                        open_positions[s].remove(pos)

                # Предварительный расчет Snapshot (для Buying Power новых сделок)
                day_pv = 0.0
                day_margin = 0.0
                for pos in open_positions[s]:
                    rel_d = d - pos['start_day']
                    day_pv += pos['pv_matrix'][rel_d] * pos['side_sign'] * pos['qty_mult']
                    day_margin += pos['margin_matrix'][rel_d]
                
                path_position_value[s, d] = day_pv
                path_reserved_margin[s, d] = day_margin
                path_equity[s, d] = path_cash[s, d] + day_pv

            # 3. Исполнение новых сигналов на сегодня
            if d in daily_groups:
                day_signals = daily_groups[d]
                
                # Bucketed Fuzzy Priority: группируем близкие edge и рандомизируем внутри групп.
                # Это сохраняет иерархию сильных сигналов, устраняя микро-оптимизм.
                epsilon = 0.0005 # 5 bps tolerance
                day_signals.sort(key=lambda x: x.get("edge", 0.0), reverse=True)
                
                buckets = []
                if day_signals:
                    current_bucket = [day_signals[0]]
                    for i in range(1, len(day_signals)):
                        if abs(day_signals[i].get("edge", 0.0) - current_bucket[0].get("edge", 0.0)) < epsilon:
                            current_bucket.append(day_signals[i])
                        else:
                            buckets.append(current_bucket)
                            current_bucket = [day_signals[i]]
                    buckets.append(current_bucket)
                
                final_ordered_signals = []
                for b in buckets:
                    rng.shuffle(b)
                    final_ordered_signals.extend(b)

                for spec in final_ordered_signals:
                    sim_res = self._simulate_trade_on_paths(
                        spec, log_rets, path_ivs, d, rng, realized_world_idx=realized_world_idx
                    )
                    trade_rec = sim_res["trade_record"]
                    
                    side_sign = 1 if trade_rec["side"] == "buy" else -1
                    qty_mult = trade_rec["quantity"] * trade_rec["multiplier"]
                    entry_fee = trade_rec["quantity"] * self.comm_per_contract
                    entry_outlay = (side_sign * trade_rec["entry_price"] * qty_mult) + entry_fee
                    
                    margin_entry = sim_res["daily_margin_matrix"][:, 0]
                    
                    # Portfolio Margin Check: Покупательская способность на основе Equity (NLV)
                    # BP = Equity - Reserved Margin
                    excess_liq_snapshot = path_equity[:, d] - path_reserved_margin[:, d]
                    needed_bp = entry_outlay if trade_rec["side"] == "buy" else np.maximum(margin_entry + entry_outlay, 0.0)

                    # Можно открывать сделку только если путь не банкрот и хватает BP
                    is_active_path = (path_equity[:, d] > 0) & (excess_liq_snapshot >= needed_bp)

                    if not is_active_path.any():
                        if not (path_equity[:, d] <= 0).all():
                            if realized_world_idx < len(is_active_path) and not is_active_path[realized_world_idx]:
                                trade_rec["pnl"] = 0.0
                                trade_rec["return"] = 0.0
                                trade_rec["exit_reason"] = "skipped (no BP)"
                                trade_rec["is_executed"] = False
                                self.trades.append(trade_rec)
                        continue

                    # EXECUTE
                    path_cash[is_active_path, d:] -= entry_outlay
                    
                    for s in np.where(is_active_path)[0]:
                        # Добавляем в реестр
                        open_positions[s].append({
                            'start_day': d,
                            'exit_day': int(sim_res['exit_day'][s]),
                            'side_sign': side_sign,
                            'qty_mult': qty_mult,
                            'entry_outlay': -entry_outlay, # Сохраняем как поток (отрицательный outlay = приток)
                            'pv_matrix': sim_res['market_val_matrix'][s],
                            'margin_matrix': sim_res['daily_margin_matrix'][s],
                            'exit_fee': float(sim_res['exit_fee_sim'][s]),
                            'trade_record': trade_rec if s == realized_world_idx else None,
                            'closed': False
                        })
                        
                        # Snapshot Update: учитываем новую сделку сразу для Liquidation Check ниже
                        path_position_value[s, d] += (trade_rec["entry_price"] * side_sign * qty_mult)
                        path_reserved_margin[s, d] += margin_entry[s]
                        path_equity[s, d] = path_cash[s, d] + path_position_value[s, d]

                    # Мы НЕ добавляем в self.trades здесь. Только при закрытии.

            # 4. End-of-Day Risk Management (Liquidation & Bankruptcy Check)
            # EL = Equity - Margin
            excess_liquidity = path_equity[:, d] - path_reserved_margin[:, d]
            
            # Ликвидация: EL < 0. Мы ликвидируем только живые пути.
            margin_breach = (excess_liquidity < 0) & (path_equity[:, d] > 0)
            
            if margin_breach.any():
                # Penalty slippage for urgent liquidation (e.g., 2.5x normal slippage)
                liq_slippage = self.slippage_pct * 2.5
                
                for s in np.where(margin_breach)[0]:
                    # Incremental Liquidation: закрываем по одной позиции до восстановления маржи
                    # Сортируем так, чтобы в первую очередь закрывать позиции с максимальной эффективностью для EL
                    # Эффективность = Освобождаемая маржа - Просадка при реализации (Slippage)
                    def get_liq_priority(p):
                        rel_idx = d - p['start_day']
                        m = p['margin_matrix'][rel_idx]
                        pv_abs = abs(p['pv_matrix'][rel_idx] * p['qty_mult'])
                        return m - (pv_abs * liq_slippage)
                    
                    open_positions[s].sort(key=get_liq_priority, reverse=True)
                    
                    while (path_equity[s, d] - path_reserved_margin[s, d] < 0) and open_positions[s]:
                        pos = open_positions[s].pop(0) 
                        rel_d = d - pos['start_day']
                        pv_mid = pos['pv_matrix'][rel_d]
                        
                        # Exit price with penalty
                        liq_price = pv_mid * (1.0 - pos['side_sign'] * liq_slippage)
                        liq_proceeds = (pos['side_sign'] * liq_price * pos['qty_mult']) - pos['exit_fee']
                        
                        path_cash[s, d:] += liq_proceeds
                        
                        # Logging for realized path
                        if s == realized_world_idx and pos['trade_record'] and not pos.get('closed', False):
                            tr = pos['trade_record']
                            real_pnl = liq_proceeds + pos['entry_outlay']
                            
                            tr["exit_date"] = self.equity_dates[d] if d < len(self.equity_dates) else None
                            tr["exit_reason"] = "liquidation"
                            tr["pnl"] = real_pnl
                            tr["return"] = real_pnl / tr["margin_required"] if tr["margin_required"] > 0 else 0
                            tr["days_held"] = d - pos['start_day']
                            tr["is_executed"] = True
                            self.trades.append(tr)
                            pos['closed'] = True
                        
                        # Recompute Snapshot после закрытия одной позиции
                        day_pv = sum(p['pv_matrix'][d - p['start_day']] * p['side_sign'] * p['qty_mult'] for p in open_positions[s])
                        day_margin = sum(p['margin_matrix'][d - p['start_day']] for p in open_positions[s])
                        path_position_value[s, d] = day_pv
                        path_reserved_margin[s, d] = day_margin
                        path_equity[s, d] = path_cash[s, d] + day_pv

            # Final Bankruptcy Check (Equity <= 0)
            bankrupt_now = (path_equity[:, d] <= 0) & (~path_terminated)
            if bankrupt_now.any():
                liq_slippage_bankrupt = self.slippage_pct * 5.0 # Тяжелое проскальзывание при крахе
                for s in np.where(bankrupt_now)[0]:
                    path_terminated[s] = True
                    # Честный Waterfall: немедленная ликвидация всех позиций по рынку
                    for pos in open_positions[s][:]:
                        rel_d = d - pos['start_day']
                        pv_mid = pos['pv_matrix'][rel_d]
                        liq_price = pv_mid * (1.0 - pos['side_sign'] * liq_slippage_bankrupt)
                        liq_proceeds = (pos['side_sign'] * liq_price * pos['qty_mult']) - pos['exit_fee']
                        
                        # IMPORTANT: update ledger for ALL simulation paths
                        path_cash[s, d:] += liq_proceeds
                        
                        # Logging only for realized path
                        if s == realized_world_idx and pos['trade_record'] and not pos.get('closed', False):
                            tr = pos['trade_record']
                            tr["exit_reason"] = "bankruptcy"
                            tr["exit_date"] = self.equity_dates[d] if d < len(self.equity_dates) else None
                            
                            real_pnl = liq_proceeds + pos['entry_outlay']
                            tr["pnl"] = real_pnl
                            tr["return"] = real_pnl / tr["margin_required"] if tr["margin_required"] > 0 else -1.0
                            tr["is_executed"] = True
                            
                            self.trades.append(tr)
                            pos['closed'] = True
                            
                        open_positions[s].remove(pos)
                
                # Freeze state for bankrupt paths. 
                # We can keep negative equity internally to reflect depth of ruin.
                path_equity[bankrupt_now, d:] = path_cash[bankrupt_now, d]
                path_reserved_margin[bankrupt_now, d:] = 0.0
                path_position_value[bankrupt_now, d:] = 0.0

            # 5. Итоговая загрузка метрик маржи
            with np.errstate(divide='ignore', invalid='ignore'):
                # Если Equity <= 0, а маржа есть — утилизация критическая
                util = np.zeros(self.n_simulations)
                mask_positive = path_equity[:, d] > 0
                mask_distressed = (path_equity[:, d] <= 0) & (path_reserved_margin[:, d] > 0)
                
                util[mask_positive] = path_reserved_margin[mask_positive, d] / path_equity[mask_positive, d]
                util[mask_distressed] = np.inf # Standard signal for distressed state
                path_margin_utilization[:, d] = util

        # Выгрузка результатов: Equity curve для отчётов обрезаем по 0 (absorbing boundary)
        # Но внутренний стейт path_equity сохраняем как есть для риск-аудита
        self.equity_curve = np.maximum(path_equity[realized_world_idx], 0.0).tolist()
        self.equity_curve_raw = path_equity[realized_world_idx].tolist()
        self.margin_utilization_curve = path_margin_utilization[realized_world_idx].tolist()

        # Статистика по всем путям для интереса (опционально)
        # self.equity_mean = path_equity.mean(axis=0).tolist()
        # Можно добавить portfolio_var = np.percentile(path_equity, 5, axis=0)

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
                "multiplier": self._safe_float(row.get("multiplier"), 100.0),
                "option_symbol": row.get("option_symbol", "OPT"),
                "date": row.get("date")
            })
        return specs

    def _simulate_trade_on_paths(
        self,
        spec: Dict[str, Any],
        log_rets: np.ndarray,
        path_ivs: np.ndarray,
        offset: int,
        rng: np.random.Generator,
        realized_world_idx: int = 0,
    ) -> Dict[str, Any]:
        """
        Production-grade ВЕКТОРНАЯ симуляция сделки по набору рыночных путей.
        Ускорена в сотни раз за счет использования NumPy операций вместо циклов.
        """
        S0 = spec["S"]
        K = spec["K"]
        opt_type = spec["type"]
        n_days = spec["days_to_expiry"]
        qty = spec["qty"]
        side = spec["side"]

        side_sign = 1.0 if side == "buy" else -1.0
        multiplier = float(spec.get("multiplier", 100.0))

        exec_entry = adjust_price_for_entry(
            spec["entry_price"],
            is_buy=(side == "buy"),
            slippage_pct=self.slippage_pct,
        )

        entry_cost = calculate_transaction_costs(
            exec_entry,
            qty,
            comm_per_contract=self.comm_per_contract,
        )

        n_sims = self.n_simulations

        # Подготовка данных
        base_ivs = np.maximum(path_ivs, 0.05)
        
        # Генерируем пути S сразу для всех симуляций
        # log_rets: (n_sims, total_days)
        trade_log_rets = log_rets[:, offset : offset + n_days]
        S_path = S0 * np.exp(np.cumsum(trade_log_rets, axis=1))
        # Добавляем начальную цену S0 в начало пути (столбец 0)
        S_path = np.column_stack([np.full(n_sims, S0), S_path])

        # Матрицы для отслеживания состояния
        exit_pnl = np.zeros(n_sims)
        exit_price_sim = np.zeros(n_sims)
        exit_fee_sim = np.zeros(n_sims)
        exit_day = np.full(n_sims, n_days)
        exit_reason = ["expiry"] * n_sims
        active_mask = np.ones(n_sims, dtype=bool)
        
        # Matrix to store market values for consistent margin tracking
        market_val_matrix = np.zeros((n_sims, n_days + 1))
        market_val_matrix[:, 0] = exec_entry

        # Основной цикл по дням (неизбежен для path-dependent выходов)
        for d in range(1, n_days + 1):
            if not active_mask.any():
                break
                
            S = S_path[:, d]
            t_rem = max((n_days - d) / 365.0, 0.0)

            # 1. Рассчитываем динамическую IV (Skew/Smile proxy)
            spot_move = (S / S0) - 1.0
            if opt_type == "put":
                iv_adj = base_ivs * (1.0 + np.maximum(-spot_move, 0.0) * 1.5)
            else:
                iv_adj = base_ivs * (1.0 + np.maximum(-spot_move, 0.0) * 0.5)
            
            # Добавляем шум IV
            iv_adj *= (1.0 + rng.normal(0.0, 0.02, size=n_sims))
            iv_adj = np.maximum(iv_adj, 0.03)

            # 2. Оцениваем рыночную стоимость (BS)
            if t_rem > 0:
                theo_value = _black_scholes_vanilla(
                    S=S, K=K, T=t_rem, r=self.r, sigma=iv_adj, q=self.dividend, opt_type=opt_type
                )
                basis = 1.0 + rng.normal(0, self.market_basis_std, size=n_sims)
                market_value = np.maximum(theo_value * basis, 0.0)
            else:
                market_value = np.zeros(n_sims)

            # Store current market value
            market_val_matrix[active_mask, d] = market_value[active_mask]

            # 3. Текущий PnL (MTM)
            mtm_pnl = ((market_value - exec_entry) * side_sign * qty * multiplier) - entry_cost
            
            # 4. Проверка условий выхода (Stop Loss / Take Profit)
            if self.stop_loss_pct is not None:
                sl_threshold = -abs(exec_entry * qty * multiplier * self.stop_loss_pct)
                new_exit_mask = active_mask & (mtm_pnl <= sl_threshold)
                if new_exit_mask.any():
                    exit_cost = calculate_transaction_costs(market_value[new_exit_mask], qty, self.comm_per_contract)
                    exit_pnl[new_exit_mask] = ((market_value[new_exit_mask] - exec_entry) * side_sign * qty * multiplier) - entry_cost - exit_cost
                    exit_price_sim[new_exit_mask] = market_value[new_exit_mask]
                    exit_fee_sim[new_exit_mask] = exit_cost
                    exit_day[new_exit_mask] = d
                    for idx in np.where(new_exit_mask)[0]: exit_reason[idx] = "stop_loss"
                    active_mask[new_exit_mask] = False

            if self.take_profit_pct is not None:
                tp_threshold = abs(exec_entry * qty * multiplier * self.take_profit_pct)
                new_exit_mask = active_mask & (mtm_pnl >= tp_threshold)
                if new_exit_mask.any():
                    exit_cost = calculate_transaction_costs(market_value[new_exit_mask], qty, self.comm_per_contract)
                    exit_pnl[new_exit_mask] = ((market_value[new_exit_mask] - exec_entry) * side_sign * qty * multiplier) - entry_cost - exit_cost
                    exit_price_sim[new_exit_mask] = market_value[new_exit_mask]
                    exit_fee_sim[new_exit_mask] = exit_cost
                    exit_day[new_exit_mask] = d
                    for idx in np.where(new_exit_mask)[0]: exit_reason[idx] = "take_profit"
                    active_mask[new_exit_mask] = False

            # 5. Экспирация
            if d == n_days:
                new_exit_mask = active_mask
                if new_exit_mask.any():
                    intrinsic = np.maximum(S[new_exit_mask] - K, 0.0) if opt_type == "call" else np.maximum(K - S[new_exit_mask], 0.0)
                    assignment_fee = calculate_exercise_assignment_costs(qty)
                    exit_cost = np.where(intrinsic > 0, assignment_fee, 0.0)
                    
                    realized_exit_pnl = ((intrinsic - exec_entry) * side_sign * qty * multiplier) - entry_cost - exit_cost
                    exit_pnl[new_exit_mask] = realized_exit_pnl
                    exit_price_sim[new_exit_mask] = intrinsic
                    exit_fee_sim[new_exit_mask] = exit_cost
                    exit_day[new_exit_mask] = d
                    active_mask[new_exit_mask] = False

        # Обнуляем рыночную стоимость ПОСЛЕ дня выхода (EOD convention)
        # В день выхода позиция еще имеет стоимость (Mark-to-Market по цене выхода)
        for s in range(n_sims):
            market_val_matrix[s, exit_day[s] + 1:] = 0.0

        # 6. Агрегация статистики
        # Считаем P&L для каждой симуляции по унифицированной формуле: exit_cash_flow + entry_cash_flow
        # entry_cash_flow = -entry_outlay
        entry_outlay_sim = (side_sign * exec_entry * qty * multiplier) + entry_cost
        entry_cash_flow = -entry_outlay_sim
        
        # exit_cash_flow: PnL реализация на d = exit_day
        exit_cash_flow = (side_sign * exit_price_sim * qty * multiplier) - exit_fee_sim
        simulation_pnls = exit_cash_flow + entry_cash_flow

        # Реализованный PnL (одна конкретная вселенная)
        realized_pnl = float(simulation_pnls[realized_world_idx])
        realized_exit_day = int(exit_day[realized_world_idx])
        realized_exit_reason = exit_reason[realized_world_idx]

        # Advanced Risk-Aware Dynamic Margin Model
        # This implementation follows a risk-based logic close to brokerage standards
        # for individual positions, but WITHOUT portfolio correlation offsets (not true PM).
        # For shorts: Premium + max(20% * Spot - OTM_Amount, 10% * Spot)
        def calc_margin_vector(prem, spot):
            if side == "buy":
                # For longs, requirement is simply the premium paid
                return prem * qty * multiplier
            else:
                # OTM Amount calculation
                if opt_type == "call":
                    otm_amount = np.maximum(0.0, K - spot)
                else:
                    otm_amount = np.maximum(0.0, spot - K)
                
                m1 = 0.20 * spot - otm_amount
                m2 = 0.10 * spot
                # Для шорт-опционов маржа = Премия + Максимум из (20% база - OTM) и (10% база)
                # Добавляем небольшой буфер 5%
                margin_per_unit = (prem + np.maximum(m1, m2)) * 1.05
                return margin_per_unit * qty * multiplier

        margin_req_initial = float(calc_margin_vector(exec_entry, S0))
        ret = realized_pnl / margin_req_initial if margin_req_initial > 0 else 0.0

        # Calculate Dynamic Margin Matrix
        daily_margin_matrix = np.zeros((n_sims, n_days + 1))
        
        for d_idx in range(n_days + 1):
            daily_margin_matrix[:, d_idx] = calc_margin_vector(market_val_matrix[:, d_idx], S_path[:, d_idx])

        # Zero out margin after exit_day for each sim path
        for s in range(n_sims):
            daily_margin_matrix[s, exit_day[s] + 1:] = 0.0

        # Monte Carlo stats for the trade using unified simulation_pnls
        mean_pnl = float(np.mean(simulation_pnls))
        var_95 = float(np.percentile(simulation_pnls, 5))
        tail_losses = simulation_pnls[simulation_pnls <= var_95]
        cvar_95 = float(tail_losses.mean()) if len(tail_losses) > 0 else var_95

        trade_record = {
            "entry_date": spec.get("date", datetime.now()),
            "option_symbol": spec.get("option_symbol", "OPT"),
            "moneyness": float(math.log(S0 / K)) if S0 > 0 and K > 0 else 0.0,
            "days_to_expiry": int(n_days),
            "type": opt_type,
            "side": side,
            "quantity": qty,
            "multiplier": multiplier,
            "entry_price": exec_entry,
            "pnl": realized_pnl,
            "return": ret,
            "margin_required": margin_req_initial,
            "expected_pnl": mean_pnl,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "win_rate_sim": float((simulation_pnls > 0).mean()),
            "days_held": realized_exit_day,
            "exit_reason": realized_exit_reason,
        }

        return {
            "daily_margin_matrix": daily_margin_matrix,
            "market_val_matrix": market_val_matrix,
            "exit_day": exit_day,
            "exit_price_sim": exit_price_sim,
            "exit_fee_sim": exit_fee_sim,
            "trade_record": trade_record,
        }

    def _simulate_trade(self, spec: Dict[str, Any], rng: np.random.Generator) -> Dict[str, Any]:
        """Legacy fallback (unused in current run loop)."""
        # (This is the old method that didn't use shared paths)
        # Keeping it for conceptual reference or removing it if desired.
        return {}


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

    def get_results(self) -> Dict[str, Any]:
        return {
            "capital": self.equity_curve[-1] if self.equity_curve else self.initial_capital,
            "trades": pd.DataFrame(self.trades),
            "equity_curve": pd.Series(self.equity_curve),
        }

    def save_reports(self) -> None:
        """Публичный интерфейс для сохранения отчётов."""
        # Рассчитываем пиковую загрузку маржи для отчета (с защитой от inf)
        peak_margin = max(self.margin_utilization_curve) if self.margin_utilization_curve else 0.0
        peak_margin_str = "DISTRESSED" if np.isinf(peak_margin) else f"{peak_margin:.2%}"
        
        extra_kpis = {
            "n_simulations": self.n_simulations,
            "realized_vol": self.realized_vol,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "peak_margin_utilization": peak_margin_str
        }
        
        _save_reports(
            self.equity_curve,
            self.trades,
            extra_kpis,
            tag="OptionBacktestEngine",
            margin_curve=self.margin_utilization_curve
        )


# ---------------------------------------------------------------------------
# Общий код для сохранения отчётов
# ---------------------------------------------------------------------------


def _save_reports(
    equity_curve: List[float],
    trades: List[Dict[str, Any]],
    extra_kpis: Optional[Dict[str, Any]],
    tag: str,
    margin_curve: Optional[List[float]] = None
) -> None:
    """Сохраняет equity_curve.csv, trades.csv и report.html в reports/."""
    os.makedirs("reports", exist_ok=True)

    pd.Series(equity_curve).to_csv("reports/equity_curve.csv", index=False)
    if margin_curve:
        pd.Series(margin_curve).to_csv("reports/margin_utilization.csv", index=False)

    if trades:
        pd.DataFrame(trades).to_csv("reports/trades.csv", index=False)

    equity_series = pd.Series(equity_curve)
    all_trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    
    # Filter for executed trades to calculate core KPIs
    executed_df = all_trades_df[all_trades_df["is_executed"] == True] if "is_executed" in all_trades_df.columns else all_trades_df
    
    total_return = (
        (equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0]
        if len(equity_series) > 1 and equity_series.iloc[0] != 0
        else 0
    )
    roll_max = equity_series.cummax()
    drawdown = (
        (equity_series - roll_max) / roll_max * 100
        if len(equity_series) > 1 and (roll_max > 0).all()
        else pd.Series([0])
    )
    max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0

    hit_rate = 0.0
    if not executed_df.empty and "pnl" in executed_df.columns:
        profitable = (executed_df["pnl"] > 0).sum()
        hit_rate = profitable / len(executed_df) if len(executed_df) > 0 else 0
    
    execution_rate = len(executed_df) / len(trades) if trades else 0.0
    peak_margin_str = extra_kpis.get("peak_margin_utilization", "N/A") if extra_kpis else "N/A"

    extras_html = ""
    if extra_kpis:
        extras_html = (
            "<h3>Параметры симуляции</h3><ul>"
            + "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in extra_kpis.items())
            + "</ul>"
        )

    trade_rows_html = ""
    if not all_trades_df.empty:
        cols = [c for c in ("entry_date", "exit_date", "type", "side", "quantity",
                            "entry_price", "pnl", "expected_pnl", "return", "exit_reason",
                            "win_rate_sim") if c in all_trades_df.columns]
        if cols:
            head = "".join(f"<th>{c}</th>" for c in cols)
            body = ""
            for _, r in all_trades_df.iterrows():
                # Color code PnL
                pnl_val = r.get("pnl", 0)
                pnl_class = "positive" if pnl_val > 0 else "negative" if pnl_val < 0 else ""
                
                cells = ""
                for c in cols:
                    val = r[c]
                    if c == "pnl":
                        cells += f"<td class='{pnl_class}'>{val}</td>"
                    else:
                        cells += f"<td>{val}</td>"
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
        .warning {{ color: #f39c12; }}
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
            <div class="kpi-value {
                'warning' if (
                    peak_margin_str not in ('N/A', 'DISTRESSED')
                    and float(peak_margin_str.strip('%')) > 80
                ) else 'negative' if peak_margin_str == 'DISTRESSED' else ''
            }">{peak_margin_str}</div>
            <div class="kpi-label">Peak Margin Usage</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{len(executed_df)} / {len(trades)}</div>
            <div class="kpi-label">Executed / Total ({execution_rate:.1%})</div>
        </div>
    </div>
    {extras_html}
    <h2>Trade Details</h2>
    {trade_rows_html}
</body>
</html>"""

    with open("reports/report.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    # Сохраняем все сделки в CSV
    if not all_trades_df.empty:
        all_trades_df.to_csv("reports/trades.csv", index=False)

    print(f"[{tag}] Reports saved to reports/")
