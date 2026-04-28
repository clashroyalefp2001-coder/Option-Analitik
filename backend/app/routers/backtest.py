"""Эндпоинты бэктеста: запуск, кривая капитала, сделки."""
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.services import pipeline as pipe

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run")
async def run(background: BackgroundTasks, no_train: bool = Query(default=False)) -> dict:
    if pipe.is_running():
        raise HTTPException(status_code=409, detail="Пайплайн уже выполняется")
    background.add_task(asyncio.create_task, pipe.run_pipeline_subprocess(no_train=no_train))
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
