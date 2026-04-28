# Options Alpha Engine – Trading Advisor for American Options on MOEX

## Overview
This project implements a production‑grade, multi‑stage pipeline for trading American options on the Moscow Exchange (MOEX). It follows the classic quant research workflow:

1. **Data** – fetch, clean, validate market data.
2. **Pricing** – compute fair values and Greeks (binomial model).
3. **Feature engineering** – build structural, volatility, liquidity, and event features.
4. **ML modeling** – train a ranking/edge‑prediction model (LightGBM baseline with fallback).
5. **Backtesting** – walk‑forward validation, cost‑aware execution simulation.
6. **Risk & execution** – hard/soft filters, Kelly sizing, TP/SL, Greek limits.
7. **Monitoring** – KPI tracking, drift detection, alerts.

The code is structured to be safe for iterative changes via Kilo Code: layers are isolated, imports are one‑directional, and tests cover core modules.

## Project Structure
```
options_alpha/
├── main.py                     # Orchestrator (run daily pipeline)
├── config.py                   # Global settings and risk configs
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image definition
├── .github/workflows/ci.yml    # CI (lint, test, build)
│
├── data/                       # Data layer
│   ├── fetcher.py              # MOEX API / mock loaders
│   ├── cleaner.py              # Dedup, null checks, alignment
│   ├── validator.py            # Sanity checks
│   └── features/               # (reserved)
│
├── pricing/                    # Pricing layer
│   └── binomial.py             # CRR American option pricer + Greeks
│
├── models/                     # Models layer
│   ├── feature_store.py        # Build feature matrix
│   └── lgbm/trainer.py         # Baseline model trainer
│
├── backtest/                   # Backtesting layer
│   ├── engine.py               # Event‑driven backtester
│   ├── costs.py                # Commission & slippage
│   ├── metrics.py              # Sharpe, MaxDD, HitRate, Calmar
│   └── walk_forward.py         # Rolling validation
│
├── execution/                  # Risk & execution layer
│   ├── filters/hard.py         # Liquidity filters
│   ├── filters/soft.py         # Edge / confidence filters
│   ├── sizer/kelly.py          # Fractional Kelly sizing
│   ├── exits/rules.py          # TP/SL/time/signal‑flip exits
│   └── portfolio/limits.py     # Greek / concentration limits
│
├── monitoring/                 # Monitoring & MLOps
│   ├── metrics.py              # Daily KPIs
│   ├── drift.py                # PSI, performance drift
│   └── alerts.py               # Alert rules
│
├── storage/                    # Persistence
│   └── data_repo.py            # Parquet/CSV save‑load helpers
│
└── tests/                      # Unit tests
    ├── test_data.py
    ├── test_pricing.py
    ├── test_feature_store.py
    ├── test_backtest.py
    └── test_execution.py
```

## Quick Start

### Prerequisites
- Python 3.9+
- pip / uv

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the pipeline (local)
```bash
cd options_alpha
python main.py
```
Expected output:
```
✅ Pipeline completed. Formed N potential signals
📁 Model saved to: models/lgbm/model.pkl

--- Back‑test and metrics ---
Final equity: 999,992.01
Total P&L: -7.99

KPIs:
  sharpe: -6.48
  max_drawdown: 0.000008
  hit_rate: 0.0
  calmar: -41.99
  annual_return: -0.00034
```

### Run tests
```bash
pytest tests/ -v
```

### Build Docker image
```bash
docker build -t options-alpha:latest .
docker run --rm options-alpha:latest
```

### CI
Pushes to `main`/`master` trigger GitHub Actions to run tests on multiple Python versions.

## Next Steps (Roadmap)
- Expand feature engineering (order‑book microstructure signals).
- Improve backtest realism (partial fills, latency, market impact).
- Add advanced models (MLP, ensembles, uncertainty‑aware GP).
- Paper‑trading mode with broker integration.
- Dashboard (Streamlit/Dash) for live KPI & drift monitoring.
- Automated retraining scheduler and model registry.

## Notes
- All console output uses ASCII to avoid encoding issues on Windows.
- Risk settings are centralized in `config.RISK_CONFIG` for easy tuning.
- Tests are intentionally lightweight to run quickly in CI; extend coverage as features grow.