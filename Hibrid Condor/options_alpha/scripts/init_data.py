#!/usr/bin/env python3
"""Initialize features.parquet file for first run."""
import pandas as pd
import os

def main():
    # Create a minimal features DataFrame
    df = pd.DataFrame({
        'fair_value': [100.0],
        'mid': [100.0],
        'bid_ask_spread_pct': [0.01],
        'open_interest': [100],
        'daily_volume': [20],
        'days_to_expiry': [30],
        'bid_ask_adjusted_edge': [0.0],
        'delta': [0.5],
        'gamma': [0.1],
        'vega': [0.2],
        'theta': [-0.1],
        'moneyness': [0.0],
        'iv_rank': [0.5],
        'iv_skew': [0.0],
        'iv_curvature': [0.0],
    })
    
    os.makedirs('data', exist_ok=True)
    df.to_parquet('data/features.parquet')
    print('Initialized data/features.parquet')

if __name__ == '__main__':
    main()