"""Capacity / Risk Monitoring – tracks portfolio utilization and liquidity constraints.

Provides a simple API to compute key capacity metrics after the back‑test.
Metrics tracked:
- avg_margin_util – average margin utilization across active positions (if available)
- peak_margin_util – maximum instantaneous margin utilization (if available)
- capital_rejection_rate – % of incoming signals rejected because of risk constraints
- underlying_concentration – % of capital allocated to the most‑exposed underlying
- vega_load – ratio of aggregate vega exposure to the configured vega limit
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger("capacity_monitor")


class CapacityMetrics:
    def __init__(self, allocator_state: Dict[str, Any] | None = None):
        self.state = allocator_state or {}

    def compute(self) -> Dict[str, Any]:
        # Extract known state, default to 0 / safe values
        capital = self.state.get("initial_capital", 1_000_000.0)
        used_capital = self.state.get("used_capital", 0.0)
        gross_exposure = self.state.get("gross_exposure", used_capital)
        max_gross_exposure = self.state.get("max_gross_exposure", 1.0)
        vega_exposure = self.state.get("vega_exposure", 0.0)
        max_vega_exposure = self.state.get("max_vega_exposure", 1.0)
        underlying_exposure = self.state.get("underlying_exposure", 0.0)
        rejected_signals = self.state.get("rejected_signals", 0)
        total_signals = self.state.get("total_signals", 1)

        # Compute metrics safely
        avg_margin_util = self.state.get("avg_margin_util", 0.0)
        peak_margin_util = self.state.get("peak_margin_util", 0.0)
        capital_rejection_rate = rejected_signals / total_signals if total_signals else 0.0
        underlying_concentration = underlying_exposure / capital if capital else 0.0
        vega_load = vega_exposure / max_vega_exposure if max_vega_exposure else 0.0

        return {
            "avg_margin_util": avg_margin_util,
            "peak_margin_util": peak_margin_util,
            "capital_rejection_rate": capital_rejection_rate,
            "underlying_concentration": underlying_concentration,
            "vega_load": vega_load,
        }

    def log(self) -> None:
        metrics = self.compute()
        for k, v in metrics.items():
            logger.info("Capacity %s: %.4f", k, v)
