# strategies/strategy_factory.py
from .straddle import StraddleStrategy
from .butterfly import ButterflyStrategy

_STRATEGIES = {
    "straddle": StraddleStrategy,
    "butterfly": ButterflyStrategy,
}

def get_strategy(name: str):
    cls = _STRATEGIES.get(name, StraddleStrategy)
    return cls()