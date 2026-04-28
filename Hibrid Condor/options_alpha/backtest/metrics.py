# backtest/metrics.py
"""Торговые метрики для оценки стратегии."""
import numpy as np

def calculate_sharpe(returns, risk_free_rate=0.0, periods_per_year=252):
    """Рассчитывает годовую Sharpe ratio."""
    if len(returns) == 0 or np.std(returns) == 0:
        return 0.0
    excess = returns - risk_free_rate / periods_per_year
    return np.mean(excess) / np.std(excess) * np.sqrt(periods_per_year)

def calculate_max_drawdown(equity_curve):
    """Максимальная просадка от пика."""
    if len(equity_curve) == 0:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd

def calculate_hit_rate(trades):
    """Процент прибыльных сделок."""
    if len(trades) == 0:
        return 0.0
    profitable = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return profitable / len(trades)

def calculate_calmar(annual_return, max_drawdown):
    """Calmar ratio = annual return / max drawdown."""
    if max_drawdown == 0:
        return 0.0
    return annual_return / max_drawdown