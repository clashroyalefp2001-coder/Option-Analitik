"""Эндпоинты обучения модели."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.services import pipeline as pipe

router = APIRouter(prefix="/api/training", tags=["training"])
log = logging.getLogger(__name__)


async def _run_pipeline_safely(no_train: bool) -> None:
    """Обёртка для фоновой задачи: ловит исключения, чтобы они не
    терялись молча (asyncio.create_task без await)."""
    try:
        await pipe.run_pipeline_subprocess(no_train=no_train)
    except Exception:
        log.exception("Фоновый запуск пайплайна завершился с ошибкой")


@router.get("/history")
def history() -> dict:
    return {"runs": pipe.list_training_history()}


@router.post("/run")
async def run() -> dict:
    if pipe.is_running():
        raise HTTPException(status_code=409, detail="Пайплайн уже выполняется")
    # Запускаем полный пайплайн как fire-and-forget в текущем event loop.
    # UI получит логи через /api/logs/stream.
    asyncio.create_task(_run_pipeline_safely(False))
    return {"started": True}


@router.get("/state")
def state() -> dict:
    return pipe.get_run_state()
