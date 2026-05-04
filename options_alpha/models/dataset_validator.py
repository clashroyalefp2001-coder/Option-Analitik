import numpy as np
import pandas as pd
from dataclasses import dataclass
import logging

@dataclass
class ValidationReport:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, any]
    
    def print_summary(self):
        log = logging.getLogger("validator")
        log.info(f"Validation {'PASSED' if self.is_valid else 'FAILED'}")
        if self.errors:
            log.error("Errors:")
            for e in self.errors: log.error(f"  - {e}")
        if self.warnings:
            log.warning("Warnings:")
            for w in self.warnings: log.warning(f"  - {w}")

class DatasetValidator:
    def validate_market_df(self, df: pd.DataFrame) -> ValidationReport:
        errors, warnings, metrics = [], [], {}
        
        n_rows = len(df)
        metrics["n_rows"] = n_rows
        if n_rows < 1000:
            warnings.append(f"Sample size {n_rows} < 1000")
            
        if "timestamp" not in df.columns:
            date_cols = [c for c in df.columns if c.lower() in ["timestamp", "date", "datetime"]]
            if not date_cols:
                errors.append("Column 'timestamp' missing from market data")
                return ValidationReport(False, errors, warnings, metrics)
            else:
                ts_col = date_cols[0]
        else:
            ts_col = "timestamp"
            
        duplicates = df[ts_col].duplicated().sum()
        metrics["duplicate_timestamps"] = int(duplicates)
        if duplicates > 0:
            errors.append(f"Found {duplicates} duplicate timestamps")
            
        if not df[ts_col].is_monotonic_increasing:
            errors.append("Timestamps are not monotonically increasing")
            
        time_diff = df[ts_col].diff().dt.days
        max_gap = time_diff.max()
        metrics["max_gap_days"] = float(max_gap) if pd.notna(max_gap) else 0.0
        if max_gap > 10:
            warnings.append(f"Max time gap is {max_gap} days")
            
        num_cols = df.select_dtypes(include=[np.number])
        if not num_cols.empty:
            nan_pct = num_cols.isna().mean().max() * 100
            metrics["max_nan_pct"] = float(nan_pct)
            if nan_pct > 10.0:
                warnings.append(f"Max NaN percentage across columns is {nan_pct:.2f}% > 10%")
                
        is_valid = len(errors) == 0
        return ValidationReport(is_valid, errors, warnings, metrics)

    def validate_feature_df(self, df: pd.DataFrame) -> ValidationReport:
        errors, warnings, metrics = [], [], {}
        metrics["n_features"] = len(df.columns)
        
        constant_cols = []
        near_constant_cols = []
        for col in df.columns:
            if col.lower() in ["timestamp", "date"]: continue
            if pd.api.types.is_numeric_dtype(df[col]):
                val_counts = df[col].value_counts(normalize=True, dropna=False)
                if len(val_counts) <= 1:
                    constant_cols.append(col)
                elif len(val_counts) > 0 and val_counts.iloc[0] > 0.99:
                    near_constant_cols.append(col)
                    
        if constant_cols: warnings.append(f"Constant columns: {constant_cols}")
        if near_constant_cols: warnings.append(f"Near-constant columns (>99% single value): {near_constant_cols}")
            
        num_df = df.select_dtypes(include=[np.number])
        if not num_df.empty and len(num_df.columns) > 1:
            corr_matrix = num_df.corr().abs()
            upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
            high_corr_cols = [column for column in upper_tri.columns if any(upper_tri[column] > 0.98)]
            if high_corr_cols:
                warnings.append(f"Highly correlated features (>0.98): {high_corr_cols}")
                
        leakage_keywords = ['future', 'next', 'target', 'label', 'direction']
        leakage_cols = [col for col in df.columns if any(k in col.lower() for k in leakage_keywords)]
        if leakage_cols:
            errors.append(f"Potential data leakage (forbidden keywords in feature names): {leakage_cols}")
            
        is_valid = len(errors) == 0
        return ValidationReport(is_valid, errors, warnings, metrics)

    def validate_labels(self, df: pd.DataFrame) -> ValidationReport:
        errors, warnings, metrics = [], [], {}
        
        if "direction_class" not in df.columns:
            errors.append("Column 'direction_class' missing from labels")
            return ValidationReport(False, errors, warnings, metrics)
            
        class_balance = df["direction_class"].value_counts(normalize=True).to_dict()
        metrics["class_balance"] = {str(k): float(v) for k, v in class_balance.items()}
        for cls, pct in class_balance.items():
            if pct < 0.05:
                warnings.append(f"Class '{cls}' is underrepresented ({pct*100:.2f}%)")
                
        if class_balance:
            max_pct = max(class_balance.values())
            if max_pct > 0.9:
                warnings.append(f"Highly imbalanced labels, one class dominates ({max_pct*100:.2f}%)")
                
        warnings.append("Horizon overlap/leakage alignment check requires manual verification of target shift.")
        
        is_valid = len(errors) == 0
        return ValidationReport(is_valid, errors, warnings, metrics)
