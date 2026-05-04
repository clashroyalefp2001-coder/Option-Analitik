#!/usr/bin/env python3
"""Dedicated Kelly Stats Store for isolated Kelly artifact management."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict


class KellyStatsStore:
    """Dedicated Kelly Stats Store with isolated artifact management."""
    
    def __init__(self, storage_path: str = "storage/kelly_stats.json"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    
    def load(self) -> dict:
        """Load Kelly statistics from storage."""
        if not os.path.exists(self.storage_path):
            return self._get_default_stats()
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
            self.validate_schema(stats)
            return stats
        except Exception as exc:
            print(f"Warning: Failed to load Kelly stats: {exc}")
            return self._get_default_stats()
    
    def save(self, stats: dict) -> None:
        """Save Kelly statistics to storage."""
        try:
            self.validate_schema(stats)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise RuntimeError(f"Failed to save Kelly stats: {exc}")
    
    def validate_schema(self, stats: dict) -> None:
        """Validate Kelly statistics schema."""
        required_fields = {
            "updated_at": str,
            "sample_size": int,
            "win_rate": float,
            "median_win": float,
            "median_loss": float,
            "cvar_95": float,
            "pnl_distribution": list
        }
        
        for field, field_type in required_fields.items():
            if field not in stats:
                raise ValueError(f"Missing required field: {field}")
            
            if not isinstance(stats[field], field_type):
                raise ValueError(f"Field {field} must be {field_type.__name__}, got {type(stats[field]).__name__}")
        
        if stats["sample_size"] < 0:
            raise ValueError("sample_size must be non-negative")
        
        if not 0 <= stats["win_rate"] <= 1:
            raise ValueError("win_rate must be between 0 and 1")
    
    def _get_default_stats(self) -> dict:
        """Get default Kelly statistics."""
        return {
            "updated_at": datetime.now().isoformat(),
            "sample_size": 0,
            "win_rate": 0.0,
            "median_win": 0.0,
            "median_loss": 0.0,
            "cvar_95": 0.0,
            "pnl_distribution": []
        }