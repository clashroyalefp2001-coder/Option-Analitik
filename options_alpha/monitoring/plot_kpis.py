#!/usr/bin/env python3
"""
Beautiful visualization of trading strategy KPIs.
Minimalist design, intuitive layout, easy-to-interpret graphics.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
import os

# Set style for minimalist look
plt.style.use('seaborn-v0_8-darkgrid')
COLORS = {
    'equity': '#2c3e50',
    'drawdown': '#e74c3c',
    'positive': '#27ae60',
    'negative': '#c0392b',
    'accent': '#3498db'
}

def load_data():
    """Load equity curve and trades from CSV files."""
    equity_path = "data/equity_curve.csv"
    trades_path = "data/trades.csv"
    
    equity = None
    trades = None
    
    if os.path.exists(equity_path):
        equity = pd.read_csv(equity_path, index_col=0, parse_dates=True)
    
    if os.path.exists(trades_path):
        trades = pd.read_csv(trades_path)
    
    # If not saved yet, try to generate from backtest results
    if equity is None:
        print("[plot_kpis] No equity curve found. Run main.py first.")
        return None, None
    
    return equity, trades

def plot_equity_curve(equity_series, save_path="reports/equity_curve.png"):
    """Plot equity curve with clean design."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Convert to Series if DataFrame
    if isinstance(equity_series, pd.DataFrame):
        equity_series = equity_series.iloc[:, 0]
    
    ax.plot(equity_series.index, equity_series.values, 
            color=COLORS['equity'], linewidth=2, label='Portfolio Value')
    
    # Add initial capital line
    ax.axhline(y=equity_series.iloc[0], color='gray', linestyle='--', alpha=0.7, label='Initial Capital')
    
    # Fill area
    ax.fill_between(equity_series.index, equity_series.values, 
                     equity_series.iloc[0], alpha=0.1, color=COLORS['equity'])
    
    # Formatting
    ax.set_title('Portfolio Equity Curve', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Equity (RUB)', fontsize=12)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"[plot_kpis] Equity curve saved to {save_path}")
    plt.close()

def plot_drawdown(equity_series, save_path="reports/drawdown.png"):
    """Plot drawdown over time."""
    # Calculate drawdown
    roll_max = equity_series.cummax()
    drawdown = (equity_series - roll_max) / roll_max * 100
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.fill_between(drawdown.index, drawdown.values, 0, 
                     color=COLORS['drawdown'], alpha=0.3, label='Drawdown')
    ax.plot(drawdown.index, drawdown.values, 
            color=COLORS['drawdown'], linewidth=1.5)
    
    ax.set_title('Portfolio Drawdown', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Drawdown (%)', fontsize=12)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"[plot_kpis] Drawdown plot saved to {save_path}")
    plt.close()

def plot_kpi_summary(kpis, save_path="reports/kpi_summary.png"):
    """Create a horizontal bar chart of KPIs."""
    # Convert kpis dict to DataFrame
    df = pd.DataFrame(list(kpis.items()), columns=['Metric', 'Value'])
    
    # Format values
    def format_value(val):
        if isinstance(val, float):
            return f'{val:.4f}'
        return str(val)
    
    df.loc[:, 'Formatted'] = df['Value'].apply(format_value)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Color bars based on positive/negative
    colors = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in df['Value']]
    
    bars = ax.barh(df['Metric'], df['Value'], color=colors, alpha=0.8)
    
    # Add value labels
    for bar, val, fmt in zip(bars, df['Value'], df['Formatted']):
        width = bar.get_width()
        ax.text(width * 1.01, bar.get_y() + bar.get_height()/2, 
                fmt, va='center', fontsize=10)
    
    ax.set_title('Key Performance Indicators', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Value', fontsize=12)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"[plot_kpis] KPI summary saved to {save_path}")
    plt.close()

def plot_trade_distribution(trades_df, save_path="reports/trade_distribution.png"):
    """Plot distribution of trade P&L if trades exist."""
    if trades_df is None or len(trades_df) == 0:
        print("[plot_kpis] No trades to plot.")
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Histogram of P&L
    axes[0].hist(trades_df['pnl'], bins=20, color=COLORS['accent'], alpha=0.7, edgecolor='black')
    axes[0].axvline(x=0, color='red', linestyle='--', alpha=0.7)
    axes[0].set_title('Trade P&L Distribution', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('P&L', fontsize=12)
    axes[0].set_ylabel('Frequency', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    # Cumulative P&L
    cumulative_pnl = trades_df['pnl'].cumsum()
    axes[1].plot(cumulative_pnl.index, cumulative_pnl.values, 
             color=COLORS['equity'], linewidth=2)
    axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.7)
    axes[1].fill_between(cumulative_pnl.index, cumulative_pnl.values, 0, 
                        alpha=0.1, color=COLORS['equity'])
    axes[1].set_title('Cumulative P&L', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Trade #', fontsize=12)
    axes[1].set_ylabel('Cumulative P&L', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"[plot_kpis] Trade distribution saved to {save_path}")
    plt.close()

def generate_report(equity, trades, kpis):
    """Generate all plots and a simple HTML report."""
    os.makedirs("reports", exist_ok=True)
    
    # Plot equity curve
    if equity is not None:
        plot_equity_curve(equity)
        plot_drawdown(equity)
    
    # Plot KPI summary
    if kpis:
        plot_kpi_summary(kpis)
    
    # Plot trade distribution
    if trades is not None and len(trades) > 0:
        plot_trade_distribution(trades)
    
    # Generate simple HTML report
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trading Strategy Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9; }
            h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .kpi-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .kpi-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .kpi-label { font-size: 14px; color: #7f8c8d; margin-top: 5px; }
            .positive { color: #27ae60; }
            .negative { color: #c0392b; }
            img { max-width: 100%; height: auto; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <h1>Trading Strategy Performance Report</h1>
        <div class="kpi-grid">
    """
    
    # Add KPI cards
    for metric, value in kpis.items():
        css_class = ""
        if isinstance(value, (int, float)):
            if value >= 0:
                css_class = "positive"
            else:
                css_class = "negative"
            formatted = f"{value:.4f}"
        else:
            formatted = str(value)
        
        html_content += f"""
            <div class="kpi-card">
                <div class="kpi-value {css_class}">{formatted}</div>
                <div class="kpi-label">{metric.replace('_', ' ').title()}</div>
            </div>
        """
    
    html_content += """
        </div>
        <h2>Charts</h2>
        <img src="equity_curve.png" alt="Equity Curve">
        <img src="drawdown.png" alt="Drawdown">
        <img src="kpi_summary.png" alt="KPI Summary">
    """
    
    if trades is not None and len(trades) > 0:
        html_content += '<img src="trade_distribution.png" alt="Trade Distribution">\n'
    
    html_content += """
    </body>
    </html>
    """
    
    with open("reports/report.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("[plot_kpis] HTML report generated: reports/report.html")

def main():
    """Main function to generate all visualizations."""
    print("[plot_kpis] Loading data...")
    equity, trades = load_data()
    
    if equity is None:
        return
    
    # Compute KPIs (if not already computed)
    from monitoring.metrics import compute_kpis
    kpis = compute_kpis(equity, trades.to_dict("records") if trades is not None else [])
    
    print(f"[plot_kpis] Generating visualizations...")
    generate_report(equity, trades, kpis)
    print("[plot_kpis] Done! Check the 'reports' directory.")

if __name__ == "__main__":
    main()
