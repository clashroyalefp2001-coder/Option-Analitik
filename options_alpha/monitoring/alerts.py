# monitoring/alerts.py
"""Alerting rules for daily monitoring."""


def check_alerts(kpis, drift_metrics, config):
    """
    kpis: dict from monitoring.metrics.compute_kpis
    drift_metrics: dict from monitoring.drift.calculate_feature_drift
    config: dict with thresholds
    Returns list of alert strings.
    """
    alerts = []

    # KPI thresholds
    if kpis.get("sharpe", 0) < config.get("sharpe_min", 1.0):
        alerts.append(f"LOW SHARPE: {kpis['sharpe']:.2f} < {config['sharpe_min']}")

    if kpis.get("max_drawdown", 0) > config.get("max_dd", 0.2):
        alerts.append(f"HIGH DRAWDOWN: {kpis['max_drawdown']:.1%} > {config['max_dd']:.1%}")

    if kpis.get("hit_rate", 0) < config.get("hit_rate_min", 0.4):
        alerts.append(f"LOW HIT RATE: {kpis['hit_rate']:.1%} < {config['hit_rate_min']:.1%}")

    # Drift thresholds
    for feat, psi in drift_metrics.items():
        if psi > config.get("drift_psi_threshold", 0.2):
            alerts.append(f"HIGH DRIFT {feat}: PSI={psi:.3f} > {config['drift_psi_threshold']}")

    return alerts
