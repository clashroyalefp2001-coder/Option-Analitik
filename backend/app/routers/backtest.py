"""Эндпоинты бэктеста: запуск, кривая капитала, сделки."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from app.services import pipeline as pipe

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
log = logging.getLogger(__name__)


async def _run_pipeline_safely(no_train: bool) -> None:
    """Обёртка для фоновой задачи: ловит исключения, чтобы они не
    терялись молча (asyncio.create_task без await)."""
    try:
        await pipe.run_pipeline_subprocess(no_train=no_train)
    except Exception:
        log.exception("Фоновый запуск пайплайна завершился с ошибкой")


@router.post("/run")
async def run(no_train: bool = Query(default=False)) -> dict:
    if pipe.is_running():
        raise HTTPException(status_code=409, detail="Пайплайн уже выполняется")
    # Запускаем как fire-and-forget в текущем event loop.
    # FastAPI BackgroundTasks не подходит — он исполняет sync-функции в
    # worker-потоке без event loop.
    asyncio.create_task(_run_pipeline_safely(no_train))
    return {"started": True, "no_train": no_train}


@router.get("/equity")
def equity() -> dict:
    return {"points": pipe.read_equity_curve()}


@router.get("/trades")
def trades() -> dict:
    return {"trades": pipe.read_trades()}


@router.get("/state")
def state() -> dict:
    return pipe.get_run_state()
