# pricing/binomial.py
import math
import numpy as np

def _crr_price(S, K, T, r, sigma, dividend, option_type, steps=30, american=True):
    """Cox-Ross-Rubinstein binomial model."""
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    q = (math.exp((r - dividend) * dt) - d) / (u - d)
    df = math.exp(-r * dt)
    
    # Initialize asset prices at maturity
    fs = np.zeros(steps + 1)
    for i in range(steps + 1):
        if option_type == 'call':
            fs[i] = max(S * (u ** (steps - i)) * (d ** i) - K, 0)
        else:
            fs[i] = max(K - S * (u ** (steps - i)) * (d ** i), 0)
    
    # Iterative valuation
    for j in range(steps - 1, -1, -1):
        for i in range(j + 1):
            fs[i] = df * (q * fs[i] + (1 - q) * fs[i+1])
            if american:
                st = S * (u ** (j - i)) * (d ** i)
                if option_type == 'call':
                    fs[i] = max(fs[i], st - K)
                else:
                    fs[i] = max(fs[i], K - st)
    return fs[0]

def price_american(S, K, T, r, sigma, dividend, option_type, steps=30):
    """Returns price and greeks using binomial model."""
    price = _crr_price(S, K, T, r, sigma, dividend, option_type, steps, True)
    
    # Greek estimation (simplified)
    # Delta
    h = 0.01 * S
    p_up = _crr_price(S + h, K, T, r, sigma, dividend, option_type, steps, True)
    p_dn = _crr_price(S - h, K, T, r, sigma, dividend, option_type, steps, True)
    delta = (p_up - p_dn) / (2 * h)
    
    # Gamma
    gamma = (p_up - 2 * price + p_dn) / (h ** 2)
    
    # Vega
    hv = 0.01
    p_v_up = _crr_price(S, K, T, r, sigma + hv, dividend, option_type, steps, True)
    vega = (p_v_up - price) / hv / 100 # per 1%
    
    # Theta
    ht = 1/365
    if T > ht:
        p_t = _crr_price(S, K, T - ht, r, sigma, dividend, option_type, steps, True)
        theta = (p_t - price) # per day
    else:
        theta = -price / (T * 365)
        
    return {
        "fair_value": price,
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": 0.0,
        "early_exercise_premium": 0.0
    }

def calculate_iv(market_price, S, K, T, r, dividend, option_type, steps=30, american=True):
    """Calculates implied volatility using bisection method."""
    if market_price <= 0:
        return 0.0
    
    low = 0.001
    high = 4.0
    
    # Check bounds
    if _crr_price(S, K, T, r, high, dividend, option_type, steps, american) < market_price:
        return high
    if _crr_price(S, K, T, r, low, dividend, option_type, steps, american) > market_price:
        return low
        
    for _ in range(20): # 20 iterations is usually enough for 4 decimal places
        mid_sigma = (low + high) / 2
        price = _crr_price(S, K, T, r, mid_sigma, dividend, option_type, steps, american)
        
        if price > market_price:
            high = mid_sigma
        else:
            low = mid_sigma
            
    return (low + high) / 2
