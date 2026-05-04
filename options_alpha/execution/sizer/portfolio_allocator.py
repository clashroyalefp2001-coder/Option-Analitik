import pandas as pd
import numpy as np
from typing import Dict, Any, List

class PortfolioAllocator:
    """Manages portfolio-level risk constraints and available capital for position sizing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initial_capital = config.get("initial_capital", 1_000_000.0)
        self.max_gross_exposure = config.get("max_gross_exposure", 1.0)  # fraction of capital
        self.max_net_exposure = config.get("max_net_exposure", 0.5)
        self.max_single_position = config.get("max_single_position", 0.05)  # per underlying
        self.max_expiry_concentration = config.get("max_expiry_concentration", 0.3)  # per expiry
        self.max_delta_exposure = config.get("max_delta_exposure", 0.2)  # portfolio delta limit
        self.max_vega_exposure = config.get("max_vega_exposure", 0.3)  # portfolio vega limit

        # Current state (will be updated by pipeline)
        self.current_positions: List[Dict[str, Any]] = []
        self.used_capital = 0.0
        self.gross_exposure = 0.0
        self.net_exposure = 0.0
        self.by_underlying: Dict[str, float] = {}
        self.by_expiry: Dict[str, float] = {}
        self.total_delta = 0.0
        self.total_vega = 0.0

    def reset(self):
        """Reset allocator state for new sizing round."""
        self.current_positions = []
        self.used_capital = 0.0
        self.gross_exposure = 0.0
        self.net_exposure = 0.0
        self.by_underlying.clear()
        self.by_expiry.clear()
        self.total_delta = 0.0
        self.total_vega = 0.0

    def available_risk_budget(self, signal: Dict[str, Any]) -> float:
        """Calculate remaining capital available for a new signal, respecting all constraints."""
        # Start with total capital minus already used
        budget = self.initial_capital - self.used_capital
        if budget <= 0:
            return 0.0

        # Apply per‑signal constraints
        underlying = signal.get("underlying")
        expiry = signal.get("expiry")
        delta = signal.get("delta", 0.0)
        vega = signal.get("vega", 0.0)

        # 1. Underlying concentration
        underlying_used = self.by_underlying.get(underlying, 0.0)
        underlying_limit = self.initial_capital * self.max_single_position
        underlying_available = underlying_limit - underlying_used
        if underlying_available < 0:
            underlying_available = 0.0

        # 2. Expiry concentration
        expiry_used = self.by_expiry.get(expiry, 0.0)
        expiry_limit = self.initial_capital * self.max_expiry_concentration
        expiry_available = expiry_limit - expiry_used
        if expiry_available < 0:
            expiry_available = 0.0

        # 3. Delta limit
        delta_after = self.total_delta + delta
        delta_limit = self.initial_capital * self.max_delta_exposure
        delta_available = delta_limit - abs(delta_after)  # simplify: treat delta as signed
        if delta_available < 0:
            delta_available = 0.0

        # 4. Vega limit
        vega_after = self.total_vega + vega
        vega_limit = self.initial_capital * self.max_vega_exposure
        vega_available = vega_limit - abs(vega_after)
        if vega_available < 0:
            vega_available = 0.0

        # 5. Gross exposure cap
        gross_after = self.gross_exposure  # we will add position size later; approximate
        gross_limit = self.initial_capital * self.max_gross_exposure
        gross_available = gross_limit - gross_after
        if gross_available < 0:
            gross_available = 0.0

        # The actual budget is the minimum of all available amounts
        budget = min(budget,
                     underlying_available,
                     expiry_available,
                     delta_available,
                     vega_available,
                     gross_available)

        return max(budget, 0.0)

    def check_underlying_limit(self, underlying: str, size: float) -> bool:
        """Check if adding `size` to underlying would exceed limit."""
        current = self.by_underlying.get(underlying, 0.0)
        limit = self.initial_capital * self.max_single_position
        return (current + size) <= limit

    def check_expiry_limit(self, expiry: str, size: float) -> bool:
        current = self.by_expiry.get(expiry, 0.0)
        limit = self.initial_capital * self.max_expiry_concentration
        return (current + size) <= limit

    def check_delta_limit(self, delta: float) -> bool:
        new_total = self.total_delta + delta
        limit = self.initial_capital * self.max_delta_exposure
        return abs(new_total) <= limit

    def check_vega_limit(self, vega: float) -> bool:
        new_total = self.total_vega + vega
        limit = self.initial_capital * self.max_vega_exposure
        return abs(new_total) <= limit

    def allocate(self, signal: Dict[str, Any], desired_size: float) -> float:
        """Return the size to allocate after applying all constraints."""
        budget = self.available_risk_budget(signal)
        size = min(desired_size, budget)

        # Update state if we allocate
        if size > 0:
            underlying = signal.get("underlying")
            expiry = signal.get("expiry")
            delta = signal.get("delta", 0.0)
            vega = signal.get("vega", 0.0)

            self.by_underlying[underlying] = self.by_underlying.get(underlying, 0.0) + size
            self.by_expiry[expiry] = self.by_expiry.get(expiry, 0.0) + size
            self.total_delta += delta
            self.total_vega += vega
            self.used_capital += size
            self.gross_exposure += size  # approximate; could be more precise
            self.current_positions.append({**signal, "size": size})

        return size