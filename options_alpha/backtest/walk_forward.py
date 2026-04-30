# backtest/walk_forward.py
"""Walk-forward validation for time-series."""
import pandas as pd
import numpy as np
from backtest.engine import BacktestEngine
from backtest.metrics import calculate_sharpe, calculate_max_drawdown, calculate_hit_rate

def walk_forward_split(df, n_splits=5, test_size=0.2):
    """
    Generates indices for train/test splits in chronological order.
    Returns list of (train_index, test_index) tuples.
    """
    n = len(df)
    test_n = int(n * test_size)
    step = max(1, (n - test_n) // n_splits)
    splits = []
    for i in range(n_splits):
        train_end = i * step + test_n
        test_start = train_end
        test_end = test_start + test_n
        if test_end > n:
            break
        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)
        splits.append((train_idx, test_idx))
    return splits

def run_walk_forward(df, feature_cols, target_col, model_trainer):
    """
    Runs walk-forward validation using provided model trainer.
    model_trainer: function(X_train, y_train) -> model (with predict method)
    Returns aggregated metrics.
    """
    all_trades = []
    all_equity = []
    splits = walk_forward_split(df)
    for train_idx, test_idx in splits:
        train = df.iloc[train_idx]
        test = df.iloc[test_idx]
        
        X_train = train[feature_cols]
        y_train = train[target_col]
        X_test = test[feature_cols]
        
        # Train model
        model = model_trainer(X_train, y_train)
        
        # Predict signals (threshold at 0 for regression)
        preds = model.predict(X_test)
        signals = np.where(preds > 0, 'BUY', 'SELL')
        
        # Run backtest on test period
        engine = BacktestEngine()
        for idx, row in test.iterrows():
            price = row['underlying_price']  # Simplification: use underlying price for entry
            signal = signals[idx - test.index[0]]  # align
            engine.execute_trade(signal, price, quantity=1)
            engine.mark_to_market(price)
        
        results = engine.get_results()
        all_trades.append(results['trades'])
        all_equity.append(results['equity_curve'])
    
    # Aggregate
    trades_df = pd.concat(all_trades, ignore_index=True)
    equity_series = pd.concat(all_equity, ignore_index=True)
    
    # Metrics
    returns = equity_series.pct_change().fillna(0)
    sharpe = calculate_sharpe(returns)
    max_dd = calculate_max_drawdown(equity_series.tolist())
    hit_rate = calculate_hit_rate(trades_df.to_dict('records'))
    
    return {
        'trades': trades_df,
        'equity_curve': equity_series,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'hit_rate': hit_rate
    }
