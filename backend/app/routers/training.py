"""Эндпоинты обучения модели."""
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.services import pipeline as pipe

router = APIRouter(prefix="/api/training", tags=["training"])


@router.get("/history")
def history() -> dict:
    return {"runs": pipe.list_training_history()}


@router.post("/run")
async def run(background: BackgroundTasks) -> dict:
    if pipe.is_running():
        raise HTTPException(status_code=409, detail="Пайплайн уже выполняется")
    # Запускаем полный пайплайн (включая обучение). UI получит логи через /api/logs/stream
    background.add_task(asyncio.create_task, pipe.run_pipeline_subprocess(no_train=False))
    return {"started": True}


@router.get("/state")
def state() -> dict:
    return pipe.get_run_state()
