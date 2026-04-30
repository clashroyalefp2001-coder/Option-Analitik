# monitoring/drift.py
"""Детекция дрейфа и аномалий в данных."""

import numpy as np
import pandas as pd
from typing import Dict, Optional

def detect_data_drift(current_features: pd.DataFrame, reference_features: pd.DataFrame, threshold: float = 0.1) -> Dict:
    """
    Проверяет, не изменилось ли распределение признаков (дрейф).
    
    Args:
        current_features: Текущие признаки
        reference_features: Ссылочные признаки (из прошлой модели)
        threshold: Порог для PSI (Population Stability Index)
    
    Returns:
        dict: {'has_drift': bool, 'psi_scores': dict, 'alert': str}
    """
    if reference_features.empty:
        return {'has_drift': False, 'psi_scores': {}, 'alert': 'Нет референсных данных'}
    
    psi_scores = {}
    has_drift = False
    
    for col in current_features.columns:
        if col not in reference_features.columns:
            continue
            
        current = current_features[col].dropna()
        reference = reference_features[col].dropna()
        
        # Бининг для расчета PSI
        bins = np.linspace(min(current.min(), reference.min()), 
                          max(current.max(), reference.max()), 
                          10)
        
        # Распределения
        current_dist = np.histogram(current, bins=bins)[0]
        reference_dist = np.histogram(reference, bins=bins)[0]
        
        # Нормализация
        current_dist = current_dist / len(current)
        reference_dist = reference_dist / len(reference)
        
        # Расчет PSI
        psi = 0
        for c, r in zip(current_dist, reference_dist):
            if c > 0 and r > 0:
                psi += (c - r) * np.log(c / r)
        
        psi_scores[col] = psi
        
        if psi > threshold:
            has_drift = True
    
    alert = ""
    if has_drift:
        alert = f"WARNING: Data drift detected! PSI threshold exceeded: {threshold}"
    
    return {
        'has_drift': has_drift,
        'psi_scores': psi_scores,
        'alert': alert
    }

def detect_anomalies(features: pd.DataFrame, method: str = 'iqr', threshold: float = 1.5) -> pd.DataFrame:
    """
    Обнаруживает аномалии в данных.
    
    Args:
        features: DataFrame с признаками
        method: 'iqr' (метод межквартильного размаха) или 'zscore'
        threshold: Порог для определения аномалий
    
    Returns:
        DataFrame с флагом аномалий
    """
    anomaly_flags = pd.DataFrame(index=features.index)
    
    # Проверяем только числовые колонки
    numeric_cols = features.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        if method == 'iqr':
            Q1 = features[col].quantile(0.25)
            Q3 = features[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            anomaly_flags[f'{col}_anomaly'] = (features[col] < lower_bound) | (features[col] > upper_bound)
            
        elif method == 'zscore':
            z_scores = np.abs((features[col] - features[col].mean()) / features[col].std())
            anomaly_flags[f'{col}_anomaly'] = z_scores > threshold
    
    return anomaly_flags