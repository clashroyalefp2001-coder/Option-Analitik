# Option-Analitik · Backend

FastAPI-сервис, оборачивающий пайплайн `Hibrid Condor/options_alpha/` и
поставляющий данные React-фронтенду.

## Запуск

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API будет доступно на `http://localhost:8000`. Swagger UI: `/docs`.

## Endpoints

- `GET  /api/health`                — health check
- `GET  /api/metrics`               — метрики последнего прогона (KPI + ML)
- `GET  /api/options`               — нормализованная опционная доска
- `GET  /api/data/profile`          — профиль данных (число contractов, диапазоны)
- `GET  /api/strategy/config`       — текущая конфигурация стратегии
- `PUT  /api/strategy/config`       — обновить конфигурацию
- `GET  /api/training/history`      — история обучений модели
- `POST /api/training/run`          — запустить переобучение
- `POST /api/backtest/run`          — запустить полный пайплайн
- `GET  /api/backtest/equity`       — кривая капитала
- `GET  /api/backtest/trades`       — список сделок
- `GET  /api/logs/stream`           — SSE-стрим логов в реальном времени

Все ответы — JSON. Конфигурация и логи живут на диске (`config_live.json`,
`reports/`, `logs/`), пайплайн запускается через `subprocess` асинхронно.
