from fastapi import APIRouter
from ..services import pipeline_service as pipeline

router = APIRouter()

@router.get("/options")
def get_options(limit: int = 200, instrument: str = None):
    rows = pipeline.read_options_board(limit=limit, instrument=instrument)
    return {"rows": rows}

@router.get("/profile")
def get_data_profile(instrument: str = None):
    file_name = pipeline.get_data_source_file()
    rows = pipeline.read_options_board(instrument=instrument)
    
    if not rows or (len(rows) == 1 and "error" in rows[0]):
        return {"file": file_name, "total": 0}
        
    calls = sum(1 for r in rows if r.get("type", "").lower() == "call" or r.get("option_type", "").lower() == "call")
    puts = sum(1 for r in rows if r.get("type", "").lower() == "put" or r.get("option_type", "").lower() == "put")
    
    strikes = [float(r["strike"]) for r in rows if str(r.get("strike", "")).replace('.', '', 1).isdigit()]
    days = [float(r["days_to_expiry"]) for r in rows if str(r.get("days_to_expiry", "")).replace('.', '', 1).isdigit()]
    
    return {
        "file": file_name,
        "total": len(rows),
        "calls": calls,
        "puts": puts,
        "strike_min": min(strikes) if strikes else 0,
        "strike_max": max(strikes) if strikes else 0,
        "days_min": min(days) if days else 0,
        "days_max": max(days) if days else 0,
    }

@router.get("/instruments")
def get_instruments():
    instruments = pipeline.get_available_instruments()
    return {"instruments": instruments}

@router.get("/trades")
def get_trades():
    trades = pipeline.read_trades()
    return {"trades": trades}
