# Options Trading Advisor

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the pipeline**
   ```bash
   python main.py
   ```
3. **(Optional) Build Docker**
   ```bash
   docker build -t options-alpha .
   docker run -v $(pwd)/data:/app/data options-alpha
   ```

## Structure

```
options_alpha/
├─ data/          # Data loaders, cleaners, validators
├─ models/        # Feature store + ML model
├─ backtest/      # Engine and metrics
├─ execution/     # Filters, sizing, kills
├─ monitoring/    # KPI and drift detection
├─ main.py        # Orchestrator
├─ Dockerfile
├─ requirements.txt
└─ README.md
```
