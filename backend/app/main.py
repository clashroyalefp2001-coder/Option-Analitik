from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import pipeline, data, metrics, moex

app = FastAPI(title="Option Analitik API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Подключение роутеров
app.include_router(pipeline.router, prefix="/internal_fastapi/pipeline", tags=["pipeline"])
app.include_router(data.router, prefix="/internal_fastapi/data", tags=["data"])
app.include_router(metrics.router, prefix="/internal_fastapi/metrics", tags=["metrics"])
app.include_router(moex.router, prefix="/internal_fastapi/moex", tags=["moex"])

# Backward compatibility for old endpoints
@app.get("/internal_fastapi/options")
def get_options_legacy(limit: int = 200, instrument: str = None):
    from app.services.pipeline_service import read_options_board
    rows = read_options_board(limit=limit, instrument=instrument)
    return {"rows": rows}

@app.get("/internal_fastapi/instruments")
def get_instruments_legacy():
    from app.services.pipeline_service import get_available_instruments
    instruments = get_available_instruments()
    return {"instruments": instruments}

@app.get("/internal_fastapi/trades")
def get_trades_legacy():
    from app.services.pipeline_service import read_trades
    trades = read_trades()
    return {"trades": trades}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=False)

