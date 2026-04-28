# pricing/binomial.py
"""Cox-Ross-Rubinstein биномиальная модель для американских опционов.

Возвращает справедливую стоимость и греки (delta, gamma, vega, theta, rho).
Vega/theta/rho считаются конечными разностями для надёжности.
"""

from __future__ import annotations

import math
from typing import Dict


_ZERO_RESULT: Dict[str, float] = {
    "fair_value": 0.0,
    "delta": 0.0,
    "gamma": 0.0,
    "vega": 0.0,
    "theta": 0.0,
    "rho": 0.0,
    "early_exercise_premium": 0.0,
    "moneyness": 0.0,
}


def _crr_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    dividend: float,
    option_type: str,
    steps: int,
    american: bool = True,
) -> float:
    """Возвращает теоретическую цену через CRR-дерево с N шагами.

    При american=False возвращается европейская цена (используется для
    подсчёта early_exercise_premium).
    """
    if T <= 0 or sigma <= 0 or steps <= 0:
        return 0.0

    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    p = (math.exp((r - dividend) * dt) - d) / (u - d)

    # Защита от вырожденных параметров (волатильность близка к нулю)
    if not (0.0 < p < 1.0):
        intrinsic = max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
        return intrinsic * math.exp(-r * T)

    # Терминальные payoff'ы
    is_call = option_type == "call"
    values = [0.0] * (steps + 1)
    for i in range(steps + 1):
        ST = S * (u ** (steps - i)) * (d ** i)
        values[i] = max(ST - K, 0.0) if is_call else max(K - ST, 0.0)

    # Идём назад с проверкой раннего исполнения
    for step in range(steps - 1, -1, -1):
        for i in range(step + 1):
            cont = disc * (p * values[i] + (1.0 - p) * values[i + 1])
            if american:
                ST = S * (u ** (step - i)) * (d ** i)
                exercise = max(ST - K, 0.0) if is_call else max(K - ST, 0.0)
                values[i] = max(cont, exercise)
            else:
                values[i] = cont
    return values[0]


def price_american(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    dividend: float = 0.0,
    option_type: str = "call",
    steps: int = 100,
) -> Dict[str, float]:
    """Возвращает dict: fair_value, delta, gamma, vega, theta, rho,
    early_exercise_premium, moneyness."""

    # Валидация входов
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return dict(_ZERO_RESULT)

    option_type = "call" if str(option_type).lower().startswith("c") else "put"

    try:
        # Базовая цена (american)
        fv = _crr_price(S, K, T, r, sigma, dividend, option_type, steps, american=True)

        # Цена аналогичного европейского — для премии раннего исполнения
        eu = _crr_price(S, K, T, r, sigma, dividend, option_type, steps, american=False)

        # Греки конечными разностями: устойчивее, чем замкнутые формулы для CRR
        h_S = max(S * 0.01, 1e-4)
        fv_up = _crr_price(S + h_S, K, T, r, sigma, dividend, option_type, steps)
        fv_dn = _crr_price(S - h_S, K, T, r, sigma, dividend, option_type, steps)
        delta = (fv_up - fv_dn) / (2 * h_S)
        gamma = (fv_up - 2 * fv + fv_dn) / (h_S ** 2)

        h_sigma = 0.01  # 1 vol point
        fv_vol_up = _crr_price(S, K, T, r, sigma + h_sigma, dividend, option_type, steps)
        # vega на 1% волатильности (классическое определение)
        vega = (fv_vol_up - fv) / (h_sigma * 100)

        h_T = max(T * 0.01, 1.0 / 365.0)
        if T - h_T > 0:
            fv_T_dn = _crr_price(S, K, T - h_T, r, sigma, dividend, option_type, steps)
            theta = (fv_T_dn - fv) / h_T / 365.0  # на 1 календарный день
        else:
            theta = 0.0

        h_r = 0.0001
        fv_r_up = _crr_price(S, K, T, r + h_r, sigma, dividend, option_type, steps)
        rho = (fv_r_up - fv) / (h_r * 100)  # на 1% ставки

        moneyness = math.log(S / K)
        early_exercise_premium = max(0.0, fv - eu)

        return {
            "fair_value": float(fv),
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(theta),
            "rho": float(rho),
            "early_exercise_premium": float(early_exercise_premium),
            "moneyness": float(moneyness),
        }
    except Exception:
        # На любых численных ошибках возвращаем нули, не роняя пайплайн
        return dict(_ZERO_RESULT)
