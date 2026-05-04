#!/usr/bin/env python3
"""Калибровка fractional Kelly по истории сделок.

Берёт reports/trades.csv (или путь из аргумента), считает win-rate, средний
выигрыш и проигрыш, и рекомендует kelly_frac для соответствующего риск-профиля.
"""

from __future__ import annotations

import argparse
import os
import sys
import pandas as pd


def calibrate(trades_path: str = "reports/trades.csv") -> dict:
    if not os.path.exists(trades_path):
        raise FileNotFoundError(f"Файл сделок не найден: {trades_path}")

    df = pd.read_csv(trades_path)
    if df.empty or "pnl" not in df.columns:
        raise ValueError("Нет колонки 'pnl' или нет данных в trades.csv")

    # Calculate normalized PnL (percentage of capital at risk)
    df["entry_notional"] = df["entry_price"] * df["quantity"] * df.get("multiplier", 100.0)
    df["pnl_pct"] = df["pnl"] / df["entry_notional"]

    wins = df[df["pnl_pct"] > 0]["pnl_pct"]
    losses = df[df["pnl_pct"] < 0]["pnl_pct"].abs()

    win_rate = len(wins) / len(df) if len(df) else 0.0
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0

    # Constants to match production sizer
    MIN_AVG_LOSS = 0.10
    MAX_WIN_RATE = 0.80

    # Regularization for calibration
    reg_win_rate = min(win_rate, MAX_WIN_RATE)
    reg_avg_loss = max(avg_loss, MIN_AVG_LOSS)

    if reg_avg_loss == 0 or reg_win_rate == 0:
        full_kelly = 0.0
    else:
        b = avg_win / reg_avg_loss
        # Классический Kelly: f* = (p*b - q) / b
        full_kelly = (reg_win_rate * b - (1 - reg_win_rate)) / b

    # Рекомендации по доле full Kelly:
    # 0.25 — консервативно, 0.5 — агрессивно
    return {
        "trades": int(len(df)),
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "full_kelly": round(full_kelly, 4),
        "recommended_kelly_frac": round(max(0.0, min(0.5, full_kelly * 0.25)), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", default="reports/trades.csv")
    args = parser.parse_args()
    try:
        result = calibrate(args.trades)
    except Exception as exc:
        print(f"[calibrate_kelly] Ошибка: {exc}")
        return 1
    print("=== Kelly calibration ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
