"""Calibration Monitoring – track Brier score, Expected Calibration Error (ECE), and reliability curve.

Used by pipelines to assess the quality of probabilistic forecasts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Tuple


def brier_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean squared error between true binary outcomes and predicted probabilities."""
    return float(np.mean(np.square(y_pred - y_true)))


def ece(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error – weighted average absolute deviation between
    predicted probability and empirical frequency in each probability bin.
    """
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.digitize(y_pred, bin_edges, right=True) - 1
    ece_val = 0.0
    total = len(y_true)
    for i in range(n_bins):
        mask = bin_ids == i
        if mask.sum() == 0:
            continue
        prob_avg = y_pred[mask].mean()
        true_avg = y_true[mask].mean()
        ece_val += np.abs(prob_avg - true_avg) * mask.sum() / total
    return float(ece_val)


def reliability_curve(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """Return a DataFrame for a reliability diagram.
    Columns: bin_center, mean_pred, freq_true, count
    """
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_ids = np.digitize(y_pred, bin_edges, right=True) - 1
    rows = []
    for i in range(n_bins):
        mask = bin_ids == i
        if mask.sum() == 0:
            continue
        rows.append({
            "bin_center": bin_centers[i],
            "mean_pred": float(y_pred[mask].mean()),
            "freq_true": float(y_true[mask].mean()),
            "count": int(mask.sum()),
        })
    return pd.DataFrame(rows)
