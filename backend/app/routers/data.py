"""Эндпоинты данных опционной доски."""
from fastapi import APIRouter, Query

from app.config import settings
from app.services.pipeline import read_options_board

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/options")
def options(limit: int = Query(default=200, ge=1, le=2000)) -> dict:
    rows = read_options_board(limit=limit)
    return {"rows": rows, "count": len(rows)}


@router.get("/data/profile")
def data_profile() -> dict:
    rows = read_options_board(limit=None)
    if not rows:
        return {"error": "Нет данных", "file": str(settings.config_path.parent / "Option Si 06.2026.xlsx")}
    if "error" in (rows[0] if rows else {}):
        return {"error": rows[0]["error"]}
    calls = sum(1 for r in rows if str(r.get("type", "")).lower() == "call")
    puts = sum(1 for r in rows if str(r.get("type", "")).lower() == "put")
    strikes = [float(r["strike"]) for r in rows if r.get("strike") not in (None, "", 0)]
    days = [float(r.get("days_to_expiry", 0) or 0) for r in rows]
    return {
        "total": len(rows),
        "calls": calls,
        "puts": puts,
        "strike_min": min(strikes) if strikes else 0,
        "strike_max": max(strikes) if strikes else 0,
        "days_min": min(days) if days else 0,
        "days_max": max(days) if days else 0,
        "file": "Option Si 06.2026.xlsx",
    }
