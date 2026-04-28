# models/feature_store.py
"""Формирование признаков из pricing и данных."""
import math
import pandas as pd
from pricing.binomial import price_american
from config import DEFAULT_SIGMA, DEFAULT_R, DEFAULT_DIVIDEND

def build_features(
    underlying: pd.DataFrame,
    options: pd.DataFrame,
) -> pd.DataFrame:
    """Создаёт DataFrame с признаками для каждой опционной серии."""
    rows = []
    
    # Debug: print first few rows to see what we have
    if len(options) > 0:
        print(f"[build_features] First row: {options.iloc[0].to_dict()}")
        print(f"[build_features] Columns: {list(options.columns)}")
    
    for _, row in options.iterrows():
        try:
            # Get required fields safely
            underlying_price = row.get("underlying_price", row.get("price", 100.0))
            strike = row.get("strike", 100.0)
            bid_val = row.get("bid", 0)
            ask_val = row.get("ask", 0)
            option_type = row.get("type", "call")
            
            # Debug: print values for first row
            if len(rows) == 0:
                print(f"[build_features] Row values: underlying_price={underlying_price}, strike={strike}, bid={bid_val}, ask={ask_val}, type={option_type}")
            
            # Skip rows with invalid required fields
            if pd.isna(underlying_price) or pd.isna(strike) or strike <= 0 or underlying_price <= 0:
                print(f"[build_features] Skipping row - invalid underlying_price={underlying_price}, strike={strike}")
                continue
            if pd.isna(bid_val) or pd.isna(ask_val) or bid_val == 0 or ask_val == 0:
                print(f"[build_features] Skipping row - invalid bid={bid_val}, ask={ask_val}")
                continue
            
            # Calculate mid price
            mid = (bid_val + ask_val) / 2.0
            
            # Skip rows with invalid mid price
            if pd.isna(mid) or mid == 0:
                print(f"[build_features] Skipping row - invalid mid={mid}")
                continue
            
            # Calculate fair value
            fair = price_american(
                S=float(underlying_price),
                K=float(strike),
                T=0.5,  # 6 месяцев до экспирации (можно параметризовать)
                r=DEFAULT_R,
                sigma=DEFAULT_SIGMA,
                dividend=DEFAULT_DIVIDEND,
                option_type=str(option_type),
            )
                
            mispricing = fair["fair_value"] - mid
            edge = fair["fair_value"] - ask_val if fair["fair_value"] > mid else mid - fair["fair_value"]
            
            # Calculate moneyness safely
            try:
                moneyness = math.log(float(underlying_price) / float(strike))
            except ValueError:
                moneyness = 0.0
            
            # Calculate days to expiry safely
            try:
                expiry_date = pd.to_datetime(row["expiry"])
                date_val = row["date"]
                if pd.isna(expiry_date) or pd.isna(date_val):
                    days_to_expiry = 30
                else:
                    days_to_expiry = max(1, (expiry_date - date_val).days)
            except:
                days_to_expiry = 30
            
            # Calculate bid-ask spread percentage safely
            try:
                bid_ask_spread_pct = (ask_val - bid_val) / mid * 100
            except:
                bid_ask_spread_pct = 0.0

            rows.append({
                "fair_value": fair["fair_value"],
                "mid": mid,
                "mispricing": mispricing,
                "bid_ask_adjusted_edge": edge,
                "delta": fair["delta"],
                "gamma": fair["gamma"],
                "vega": fair["vega"],
                "theta": fair["theta"],
                "moneyness": moneyness,
                "iv_rank": 0.5,  # placeholder
                "days_to_expiry": days_to_expiry,
                "iv_skew": 0.0,  # placeholder
                "iv_curvature": 0.0,  # placeholder
                "bid_ask_spread_pct": bid_ask_spread_pct,
                "open_interest": row.get("open_interest", 0),
                "daily_volume": row.get("volume", 0),
                "predicted_edge": edge,
                "signal_confidence": 0.8,  # placeholder confidence
                "signal_regime": "normal",  # placeholder regime
            })
        except Exception as e:
            # Пропускаем проблемные строки
            print(f"[build_features] Error processing row: {e}")
            continue

    print(f"[build_features] Successfully created {len(rows)} rows")
    return pd.DataFrame(rows)
