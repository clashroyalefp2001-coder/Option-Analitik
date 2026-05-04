from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Any
from ..services import pipeline_service as pipeline

router = APIRouter()

class RunRequest(BaseModel):
    useLive: bool = False

@router.post("/run")
async def run_pipeline(req: RunRequest, background_tasks: BackgroundTasks):
    try:
        print(f"DEBUG: run_pipeline called with req={req}")
        if pipeline.is_running():
            raise HTTPException(status_code=400, detail="Пайплайн уже запущен")
        
        # Запуск пайплайна в фоне
        async def run_task():
            try:
                print(f"DEBUG: run_task, no_train={not req.useLive}")
                await pipeline.run_pipeline_subprocess(no_train=not req.useLive)
            except Exception as e:
                print(f"Pipeline error: {e}")
                
        background_tasks.add_task(run_task)
        return {"status": "ok", "message": "Pipeline started"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: run_pipeline exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/run")
async def run_pipeline_get(background_tasks: BackgroundTasks):
    return await run_pipeline(RunRequest(useLive=True), background_tasks)

@router.get("/status")
def get_status() -> dict[str, Any]:
    return pipeline.get_run_state()

@router.get("/history")
def get_history() -> list[dict[str, Any]]:
    return pipeline.list_training_history()

@router.get("/config")
def get_config() -> dict[str, Any]:
    return pipeline.read_config()

@router.post("/config")
def update_config(payload: dict[str, Any]):
    pipeline.write_config(payload)
    return {"status": "ok"}
