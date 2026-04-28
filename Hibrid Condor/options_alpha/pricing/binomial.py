# pricing/binomial.py
"""Простейшая биномиальная модель American Call/Put."""
import math
from typing import Dict

def price_american(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    dividend: float,
    option_type: str = "call",
) -> Dict[str, float]:
    """Возвращает dict: fair_value, delta, gamma, vega, theta, rho."""
    try:
        # Safety checks for invalid inputs
        if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
            return {
                "fair_value": 0.0,
                "delta": 0.0,
                "gamma": 0.0,
                "vega": 0.0,
                "theta": 0.0,
                "rho": 0.0,
                "early_exercise_premium": 0.0,
                "moneyness": 0.0
            }
            
        dt = T
        u = math.exp(sigma * math.sqrt(dt))
        d = math.exp(-sigma * math.sqrt(dt))
        
        # Avoid division by zero
        if abs(u - d) < 1e-10:
            return {
                "fair_value": 0.0,
                "delta": 0.0,
                "gamma": 0.0,
                "vega": 0.0,
                "theta": 0.0,
                "rho": 0.0,
                "early_exercise_premium": 0.0,
                "moneyness": 0.0
            }
            
        p = (math.exp((r - dividend) * dt) - d) / (u - d)

        # простая оценка цены от одной ячейки
        if option_type == "call":
            payoff_up = max(S * u - K, 0)
            payoff_down = max(S * d - K, 0)
        else:
            payoff_up = max(K - S * u, 0)
            payoff_down = max(K - S * d, 0)

        fair_value = (p * payoff_up + (1 - p) * payoff_down) * math.exp(-r * dt)

        # конечные грексы (приближённые формулы)
        delta = (payoff_up - payoff_down) / (S * (u - d)) * math.exp(-r * dt)
        gamma = (payoff_up / (S * u) - payoff_down / (S * d)) / (S * (u - d) * (u - d)) * math.exp(-r * dt)
        vega = S * math.exp(-r * dt) * (u - d) * math.sqrt(dt) * (payoff_up)  # упрощённо
        theta = -r * fair_value
        rho = fair_value / r if r != 0 else 0.0

        # Calculate early exercise premium (placeholder for European case)
        european_value = fair_value  # Simplified: in a real binomial, this would be computed separately
        early_exercise_premium = max(0, fair_value - european_value)
        
        moneyness = math.log(S / K) if S > 0 and K > 0 else 0.0
        
        return {
            "fair_value": fair_value,
            "delta": delta,
            "gamma": gamma,
            "vega": vega,
            "theta": theta,
            "rho": rho,
            "early_exercise_premium": early_exercise_premium,
            "moneyness": moneyness
        }
    except:
        return {
            "fair_value": 0.0,
            "delta": 0.0,
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0,
            "rho": 0.0,
            "early_exercise_premium": 0.0,
            "moneyness": 0.0
        }
