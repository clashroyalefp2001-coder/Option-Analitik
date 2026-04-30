"""FastAPI app · точка входа."""
import asyncio
import sys

import warnings
import pandas as pd

# Включаем режим Copy-on-Write (убирает ChainedAssignmentError warning в новых версиях)
pd.options.mode.copy_on_write = True

# На всякий случай полностью скрываем все FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)

# На Windows для asyncio.create_subprocess_exec нужен Proactor event loop.
# SelectorEventLoop (иногда выбирается под Python 3.14) бросает
# NotImplementedError при запуске подпроцессов.
# Надо установить политику ДО инициализации uvicorn-loop.
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        # На не-Windows или очень старых версиях свойства может не быть
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import backtest, data, logs, metrics, strategy, training

app = FastAPI(
    title="Option-Analitik API",
    description="Backend для UI стратегии Option-Analitik (Si 06.2026)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(data.router)
app.include_router(strategy.router)
app.include_router(training.router)
app.include_router(backtest.router)
app.include_router(logs.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "pipeline_root": str(settings.pipeline_root)}
