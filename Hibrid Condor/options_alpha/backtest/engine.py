# backtest/engine.py
"""Движок бектеста: эмулирует сделки на основе сигналов."""
import pandas as pd
from datetime import datetime
from backtest.costs import calculate_transaction_costs, adjust_price_for_entry

def backtest_engine(signals, initial_capital=1_000_000):
    """Wrapper function for backward compatibility."""
    engine = BacktestEngine(initial_capital=initial_capital)
    
    for idx, row in signals.iterrows():
        price = row.get('fair_value', row.get('mid', 0))
        engine.execute_trade(row['signal'], price, row.get('quantity', 1))
        engine.mark_to_market(price)
    
    results = engine.get_results()
    return {
        'capital': engine.capital,
        'equity_curve': results['equity_curve'],
        'trades': results['trades']
    }

class BacktestEngine:
    def __init__(self, initial_capital=1_000_000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = [initial_capital]
        self.date = datetime.now()

    def execute_trade(self, signal, price, quantity=1):
        """Исполняет вход или выход из позиции."""
        if signal == 'BUY':
            exec_price = adjust_price_for_entry(price, is_buy=True)
            cost = calculate_transaction_costs(exec_price, quantity)
            self.capital -= (exec_price * quantity) + cost
            self.positions.append({
                'entry_date': self.date,
                'type': 'long',
                'entry_price': exec_price,
                'quantity': quantity,
                'entry_capital': self.capital
            })
        elif signal == 'SELL':
            exec_price = adjust_price_for_entry(price, is_buy=False)
            cost = calculate_transaction_costs(exec_price, quantity)
            self.capital += (exec_price * quantity) - cost
            # Закрываем открытые позиции
            for pos in self.positions:
                pnl = (exec_price - pos['entry_price']) * pos['quantity'] - cost
                self.trades.append({
                    'entry_date': pos['entry_date'],
                    'exit_date': self.date,
                    'pnl': pnl,
                    'return': pnl / pos['entry_price'] if pos['entry_price'] > 0 else 0
                })
            self.positions = []

    def mark_to_market(self, current_price):
        """Переоценка текущих позиций."""
        total_value = self.capital
        for pos in self.positions:
            total_value += pos['quantity'] * current_price
        self.equity_curve.append(total_value)

    def get_results(self):
        return {
            'capital': self.capital,
            'trades': pd.DataFrame(self.trades),
            'equity_curve': pd.Series(self.equity_curve)
        }

    def run(self, signals, sizes):
        """Run backtest over signals with position sizes."""
        for idx, row in signals.iterrows():
            # Determine signal type based on predicted edge
            signal_type = 'BUY' if row.get('predicted_edge', 0) > 0 else 'SELL'
            # Use fair_value or mid price for execution
            price = row.get('fair_value', row.get('mid', 0))
            if price <= 0:
                continue
            # Determine quantity from sizes (could be Series or scalar)
            if hasattr(sizes, 'iloc'):
                quantity = sizes.iloc[idx] if idx < len(sizes) else 1
            else:
                quantity = sizes if sizes > 0 else 1
            if quantity <= 0:
                continue
            self.execute_trade(signal_type, price, quantity)
            self.mark_to_market(price)
        # Close any remaining open positions at the last price
        if self.positions:
            last_price = price if 'price' in locals() else 100.0
            total_qty = sum(pos['quantity'] for pos in self.positions)
            self.execute_trade('SELL', last_price, total_qty)

    def save_reports(self):
        """Сохраняет отчеты в файлы и генерирует HTML отчет."""
        import os
        import webbrowser
        from datetime import datetime
        
        os.makedirs('reports', exist_ok=True)
        
        # Save equity curve
        pd.Series(self.equity_curve).to_csv('reports/equity_curve.csv', index=False)
        
        # Save trades
        if self.trades:
            pd.DataFrame(self.trades).to_csv('reports/trades.csv', index=False)
        
        # Compute KPIs
        equity_series = pd.Series(self.equity_curve)
        trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
        
        # Calculate basic metrics
        total_return = (equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0] if len(equity_series) > 1 else 0
        roll_max = equity_series.cummax()
        drawdown = (equity_series - roll_max) / roll_max * 100 if len(equity_series) > 1 else 0
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        hit_rate = 0.0
        if not trades_df.empty:
            profitable = (trades_df['pnl'] > 0).sum()
            hit_rate = profitable / len(trades_df) if len(trades_df) > 0 else 0
        
        # Generate HTML report
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Trading Strategy Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .kpi-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .kpi-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .kpi-label {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #c0392b; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #3498db; color: white; }}
    </style>
</head>
<body>
    <h1>Trading Strategy Performance Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-value {'positive' if total_return >= 0 else 'negative'}">{total_return:.4f}</div>
            <div class="kpi-label">Total Return</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value negative">{max_drawdown:.4f}</div>
            <div class="kpi-label">Max Drawdown</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value {'positive' if hit_rate >= 0.5 else 'negative'}">{hit_rate:.4f}</div>
            <div class="kpi-label">Hit Rate</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{len(self.trades)}</div>
            <div class="kpi-label">Total Trades</div>
        </div>
    </div>
    
    <h2>Trade Details</h2>
    {'<table><tr><th>Entry Date</th><th>Exit Date</th><th>P&L</th><th>Return</th></tr>' + ''.join([f"<tr><td>{t['entry_date']}</td><td>{t['exit_date']}</td><td>{t['pnl']:.2f}</td><td>{t['return']:.4f}</td></tr>" for t in self.trades]) + '</table>' if self.trades else '<p>No trades</p>'}
</body>
</html>"""
        
        with open('reports/report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("[BacktestEngine] Reports saved to reports/")
        
        # Open report with file:// protocol (absolute path for Windows)
        report_path = os.path.abspath('reports/report.html')
        # Convert to forward slashes and add file:// protocol
        webbrowser.open(f'file:///{report_path.replace("\\", "/")}')

    def get_equity_curve(self):
        """Возвращает кривую капитала."""
        return pd.Series(self.equity_curve)

    def get_trades(self):
        """Возвращает список сделок."""
        return pd.DataFrame(self.trades)