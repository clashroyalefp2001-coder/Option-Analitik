"""Чтение и сохранение конфигурации стратегии."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.pipeline import read_config, write_config

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class StrategyConfig(BaseModel):
    config: dict


@router.get("/config")
def get_config() -> dict:
    return {"config": read_config()}


@router.put("/config")
def put_config(payload: StrategyConfig) -> dict:
    write_config(payload.config)
    return {"ok": True}
