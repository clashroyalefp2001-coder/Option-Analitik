"""Drift Monitoring – tracks feature and prediction drift using PSI, KS, etc."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, Tuple, Optional

def psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Population Stability Index."""
    def _scale(subset):
        breakpoints = np.linspace(0, 100, buckets + 1)
        percents = np.percentile(subset, breakpoints)
        percents[0] = -np.inf
        percents[-1] = np.inf
        hist = np.histogram(subset, bins=percents)[0]
        return hist / len(subset)
    e_hist = _scale(expected)
    a_hist = _scale(actual)
    # Avoid zero division
    e_hist = np.where(e_hist == 0, 0.0001, e_hist)
    a_hist = np.where(a_hist == 0, 0.0001, a_hist)
    return np.sum((e_hist - a_hist) * np.log(e_hist / a_hist))

def ks_test(expected: np.ndarray, actual: np.ndarray) -> Tuple[float, float]:
    """Kolmogorov-Smirnov test."""
    return stats.ks_2samp(expected, actual)

def feature_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    feature_cols: Optional[list] = None
) -> Dict[str, Dict[str, float]]:
    """Compute PSI and KS for each feature."""
    if feature_cols is None:
        feature_cols = reference.columns.tolist()
    drift_report = {}
    for col in feature_cols:
        if col not in reference.columns or col not in current.columns:
            continue
        ref_vals = reference[col].dropna().values
        cur_vals = current[col].dropna().values
        if len(ref_vals) == 0 or len(cur_vals) == 0:
            continue
        psi_val = psi(ref_vals, cur_vals)
        ks_stat, ks_pval = ks_test(ref_vals, cur_vals)
        drift_report[col] = {"psi": psi_val, "ks_statistic": ks_stat, "ks_pvalue": ks_pval}
    return drift_report

def prediction_drift(
    reference_preds: np.ndarray,
    current_preds: np.ndarray,
    reference_labels: Optional[np.ndarray] = None,
    current_labels: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """Monitor drift in prediction distribution and optionally label drift."""
    psi_val = psi(reference_preds, current_preds)
    ks_stat, ks_pval = ks_test(reference_preds, current_preds)
    result = {
        "prediction_psi": psi_val,
        "prediction_ks_statistic": ks_stat,
        "prediction_ks_pvalue": ks_pval,
    }
    if reference_labels is not None and current_labels is not None:
        label_psi = psi(reference_labels, current_labels)
        label_ks_stat, label_ks_pval = ks_test(reference_labels, current_labels)
        result.update({
            "label_psi": label_psi,
            "label_ks_statistic": label_ks_stat,
            "label_ks_pvalue": label_ks_pval,
        })
    return result