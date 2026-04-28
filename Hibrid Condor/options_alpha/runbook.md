# Runbook – Options Trading Advisor

## Daily run

1. **Update Excel sheet**: The file `Option Si 06.2026.xlsx` must be updated every minute with live `bid`/`ask` and other quotes.
2. **Auto-watcher**: `watcher.py` will automatically detect changes and re-run `main.py`.
3. **Check logs**: Logs printed to console will show pipeline stages, KPI and any drift alerts.

## Re-training

If a drift is detected or a new model is required:

```bash
python main.py  # re-runs with latest data, retrains LGBM, overwrites models/lgbm/model.pkl
``` 

## Rollback

1. **Revert Git**: Checkout a known good commit.
2. **Clear Data**: `rm -rf data/*.parquet model.yaml`.
3. **Re-run**: `python main.py`.

## Docker production

```bash
docker run -d -v /mnt/data:/app/data options-alpha
``` 
The container will automatically start the pipeline and expose logs via stdout.
