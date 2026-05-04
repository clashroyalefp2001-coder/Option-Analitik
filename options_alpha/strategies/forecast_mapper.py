import pandas as pd
from typing import Dict, Any, Optional

class ForecastStrategyMapper:
    def __init__(self, bull_t: float = 0.6, bear_t: float = 0.6):
        self.bull_threshold = bull_t
        self.bear_threshold = bear_t

    def map_forecast_to_structure(
        self,
        forecast: Dict[str, float],
        chain: pd.DataFrame,
        regime: str = "mean-revert",
        volatility: float = 0.2
    ) -> Optional[Dict[str, Any]]:
        bull = forecast.get("bull_prob", 0.0)
        bear = forecast.get("bear_prob", 0.0)
        neutral = forecast.get("neutral_prob", 0.0)

        is_high_vol = volatility > 0.3
        
        if regime == "breakout":
             return self._straddle(chain)
             
        if bull > self.bull_threshold and not is_high_vol:
            return self._structure(chain, "call", bullish=True)
            
        if bull > self.bull_threshold and is_high_vol:
            return self._structure(chain, "put", bullish=True)
            
        if bear > self.bear_threshold and not is_high_vol:
            return self._structure(chain, "put", bullish=False)
             
        if neutral > max(bull, bear) and not is_high_vol and regime in ["mean-revert", "compression"]:
            return self._iron_condor(chain)
            
        return None

    def _structure(self, chain: pd.DataFrame, o_type: str, bullish: bool) -> Optional[Dict[str, Any]]:
        df = chain[chain["type"] == o_type].copy()
        if df.empty: return None
        base = float(chain["underlying_price"].iloc[0]) if "underlying_price" in chain.columns else float(df["strike"].median())
        
        df["otm_pct"] = (df["strike"] - base).abs() / base

        if bullish and o_type == "put":
             # Bull put spread: SELL put slightly OTM, BUY put further OTM
             # e.g., slightly OTM ~ 1-3%, further OTM > 3%
             otm_puts = df[df["strike"] < base].sort_values("strike", ascending=False)
             if len(otm_puts) < 2: return None
             short_candidates = otm_puts[otm_puts["otm_pct"] >= 0.01]
             if short_candidates.empty:
                 short_candidates = otm_puts
             short_leg = short_candidates.iloc[0]
             
             long_candidates = otm_puts[otm_puts["strike"] < short_leg["strike"]]
             if long_candidates.empty: return None
             long_leg = long_candidates.iloc[0]

             return {
                 "strategy_name": "bull_put_spread",
                 "legs": [
                     {"symbol": short_leg["option_symbol"], "side": "sell", "strike": short_leg["strike"], "type": "put"},
                     {"symbol": long_leg["option_symbol"], "side": "buy", "strike": long_leg["strike"], "type": "put"}
                 ]
             }
             
        if not bullish and o_type == "put":
             # Bear put spread: BUY put slightly OTM, SELL put further OTM
             otm_puts = df[df["strike"] < base].sort_values("strike", ascending=False)
             if len(otm_puts) < 2: return None
             long_candidates = otm_puts[otm_puts["otm_pct"] >= 0.01]
             if long_candidates.empty:
                 long_candidates = otm_puts
             long_leg = long_candidates.iloc[0]
             
             short_candidates = otm_puts[otm_puts["strike"] < long_leg["strike"]]
             if short_candidates.empty: return None
             short_leg = short_candidates.iloc[0]

             return {
                 "strategy_name": "bear_put_spread",
                 "legs": [
                     {"symbol": long_leg["option_symbol"], "side": "buy", "strike": long_leg["strike"], "type": "put"},
                     {"symbol": short_leg["option_symbol"], "side": "sell", "strike": short_leg["strike"], "type": "put"}
                 ]
             }

        if bullish and o_type == "call":
             # Bull call spread: BUY call slightly OTM, SELL call further OTM
             otm_calls = df[df["strike"] > base].sort_values("strike", ascending=True)
             if len(otm_calls) < 2: return None
             long_candidates = otm_calls[otm_calls["otm_pct"] >= 0.01]
             if long_candidates.empty:
                 long_candidates = otm_calls
             long_leg = long_candidates.iloc[0]
             
             short_candidates = otm_calls[otm_calls["strike"] > long_leg["strike"]]
             if short_candidates.empty: return None
             short_leg = short_candidates.iloc[0]

             return {
                "strategy_name": "bull_call_spread",
                "legs": [
                    {"symbol": long_leg["option_symbol"], "side": "buy", "strike": long_leg["strike"], "type": "call"},
                    {"symbol": short_leg["option_symbol"], "side": "sell", "strike": short_leg["strike"], "type": "call"}
                ]
            }

        return None
        
    def _straddle(self, chain: pd.DataFrame) -> Optional[Dict[str, Any]]:
        base = chain["underlying_price"].iloc[0] if "underlying_price" in chain.columns else chain["strike"].median()
        chain["dist"] = (chain["strike"] - base).abs()
        calls = chain[chain["type"] == "call"].sort_values("dist")
        puts = chain[chain["type"] == "put"].sort_values("dist")
        if calls.empty or puts.empty: return None
        return {
            "strategy_name": "long_straddle",
            "legs": [
                 {"symbol": calls.iloc[0]["option_symbol"], "side": "buy", "strike": calls.iloc[0]["strike"], "type": "call"},
                 {"symbol": puts.iloc[0]["option_symbol"], "side": "buy", "strike": puts.iloc[0]["strike"], "type": "put"}
            ]
        }
        
    def _iron_condor(self, chain: pd.DataFrame) -> Optional[Dict[str, Any]]:
        base = chain["underlying_price"].iloc[0] if "underlying_price" in chain.columns else chain["strike"].median()
        calls = chain[chain["type"] == "call"].sort_values("strike", ascending=True)
        puts = chain[chain["type"] == "put"].sort_values("strike", ascending=False)
        otm_calls = calls[calls["strike"] > base]
        otm_puts = puts[puts["strike"] < base]
        if len(otm_calls) < 2 or len(otm_puts) < 2: return None
        return {
             "strategy_name": "iron_condor",
             "legs": [
                  {"symbol": otm_puts.iloc[0]["option_symbol"], "side": "sell", "strike": otm_puts.iloc[0]["strike"], "type": "put"},
                  {"symbol": otm_puts.iloc[1]["option_symbol"], "side": "buy", "strike": otm_puts.iloc[1]["strike"], "type": "put"},
                  {"symbol": otm_calls.iloc[0]["option_symbol"], "side": "sell", "strike": otm_calls.iloc[0]["strike"], "type": "call"},
                  {"symbol": otm_calls.iloc[1]["option_symbol"], "side": "buy", "strike": otm_calls.iloc[1]["strike"], "type": "call"}
             ]
        }
