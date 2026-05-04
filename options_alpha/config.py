# config.py
# Configuration for Options Alpha Engine

# Option pricing parameters
DEFAULT_SIGMA = 0.2          # Default volatility
DEFAULT_R = 0.04             # Risk-free rate
DEFAULT_DIVIDEND = 0.0       # No dividends

# Data paths
DATA_DIR = "data"
OPTIONS_QUOTES_FILE = "options_quotes.csv"
UNDERLYING_FILE = "underlying_prices.csv"

# ML parameters
LIGHTGBM_NUM_ESTIMATORS = 200
LIGHTGBM_LEARNING_RATE = 0.05

# Risk limits (configurable)
RISK_CONFIG = {
    "max_spread_pct": 3.0,            # maximum allowed spread % of mid (optimized)
    "min_open_interest": 100,         # minimum OI to trade (increased for liquidity)
    "min_daily_volume": 50,           # minimum daily volume (increased for liquidity)
    "min_days_to_expiry": 7,          # DTE lower bound (increased for stability)
    "max_gamma_exposure_pct": 0.02,   # gamma exposure as % of capital
    "max_vega_exposure_pct": 0.02,    # vega exposure as % of capital
    "max_delta_exposure_pct": 0.02,   # delta exposure as % of capital
    "max_position_size_pct": 0.03,    # position size as % of portfolio (reduced for safety)
    "max_daily_loss_pct": 0.02,       # max daily loss % of capital
    "min_edge": 0.001,                # minimum edge for soft filter (increased)
    "min_confidence": 0.75,           # minimum confidence for soft filter (increased)
    "target_horizon": 5,              # prediction horizon (for target calculation)
    "kelly_fraction": 0.20,           # conservative fractional Kelly (applied to f*)
    "initial_capital": 1000000.0,     # base portfolio capital for sizing
}

# Risk limits thresholds (for quick access)
RISK_LIMITS = {
    "max_delta_exposure_pct": 0.02,    # 2% of portfolio delta
    "max_gamma_exposure_pct": 0.02,    # 2% of capital
    "max_vega_exposure_pct": 0.02,     # 2% of capital
    "max_position_size_pct": 0.05,     # 5% of portfolio per position
    "max_daily_loss_pct": 0.02,        # 2% daily loss limit
}
