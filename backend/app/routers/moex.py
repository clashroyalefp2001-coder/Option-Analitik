from fastapi import APIRouter, HTTPException
import asyncio
from ..services import moex_live_fetcher, moex_history_fetcher

router = APIRouter()

@router.get("/live/{symbol}")
async def get_live_data(symbol: str):
    fetcher = moex_live_fetcher.MoexIssFetcher(underlying_asset=symbol)
    snapshot = await fetcher.get_live_snapshot()
    if not snapshot:
        raise HTTPException(status_code=500, detail="Failed to fetch live data from MOEX")
    return snapshot

@router.get("/history/{symbol}")
async def get_history_data(symbol: str, start: str, end: str):
    fetcher = moex_history_fetcher.MoexHistoryFetcher()
    df = await fetcher.fetch_history(
        engine="futures",
        market="forts",
        security=symbol,
        start_date=start,
        end_date=end
    )
    if df.empty:
        return {"data": [], "count": 0}
    return {"data": df.to_dict(orient="records"), "count": len(df)}
