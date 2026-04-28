"""SSE-стрим логов пайплайна."""
import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.services import pipeline as pipe

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/stream")
async def stream():
    """Server-Sent Events: каждые 500мс отдаёт хвост логов и состояние шага."""
    async def event_generator():
        last_idx = 0
        while True:
            tail = pipe.get_run_state().get("log_tail", [])
            if last_idx < len(tail):
                # шлём только новое
                new_chunk = tail[last_idx:]
                last_idx = len(tail)
                payload = {
                    "lines": new_chunk,
                    "step": pipe.get_run_state().get("step"),
                    "running": pipe.is_running(),
                }
                yield {"event": "log", "data": json.dumps(payload, ensure_ascii=False)}
            else:
                # heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "running": pipe.is_running(),
                        "step": pipe.get_run_state().get("step"),
                    }),
                }
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.get("/tail")
def tail(n: int = 200) -> dict:
    """Последние N строк лога текущего/последнего прогона."""
    state = pipe.get_run_state()
    lines = state.get("log_tail", [])[-n:]
    return {"lines": lines, "step": state.get("step"), "running": state.get("running")}
