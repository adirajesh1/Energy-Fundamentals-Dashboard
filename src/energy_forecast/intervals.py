from __future__ import annotations

import math

import numpy as np
import pandas as pd


def conformal_quantile(abs_residuals, coverage: float) -> float:
    """Finite-sample conformal quantile of absolute residuals."""
    values = np.asarray(abs_residuals, dtype=float)
    values = values[np.isfinite(values)]
    if not 0 < coverage < 1:
        raise ValueError("coverage must be between 0 and 1.")
    if len(values) == 0:
        return float("nan")
    rank = min(len(values), math.ceil((len(values) + 1) * coverage))
    return float(np.partition(values, rank - 1)[rank - 1])


def add_horizon_conformal_intervals(
    predictions: pd.DataFrame,
    *,
    actual_col: str,
    prediction_col: str,
    time_col: str = "forecast_origin",
    horizon_bucket_col: str = "horizon_bucket",
    target_time_col: str | None = None,
    coverage: float = 0.80,
    min_calibration: int = 30,
    lower_col: str = "lower_bound",
    upper_col: str = "upper_bound",
) -> pd.DataFrame:
    """Calibrate each row using only earlier residuals in its horizon bucket."""
    required = {actual_col, prediction_col, time_col, horizon_bucket_col}
    if target_time_col and target_time_col in predictions.columns:
        required.add(target_time_col)
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Interval input missing required columns: {missing}")
    data = predictions.copy()
    data[time_col] = pd.to_datetime(data[time_col], utc=True)
    if target_time_col and target_time_col in data.columns:
        data[target_time_col] = pd.to_datetime(data[target_time_col], utc=True)
    data = data.sort_values([time_col, horizon_bucket_col]).reset_index(drop=True)
    data[lower_col] = np.nan
    data[upper_col] = np.nan
    data["calibration_count"] = 0
    
    history: dict[object, list[float]] = {}
    pending_residuals: list[tuple[pd.Timestamp, object, float]] = []
    
    for origin, origin_rows in data.groupby(time_col, sort=True):
        # 1. Release pending residuals that have been realized before/at this origin
        if target_time_col and target_time_col in data.columns:
            realized = [p for p in pending_residuals if p[0] <= origin]
            pending_residuals = [p for p in pending_residuals if p[0] > origin]
            for _, bucket, residual in realized:
                history.setdefault(bucket, []).append(residual)
                
        # 2. Calibrate current origin predictions
        for idx, row in origin_rows.iterrows():
            bucket = row[horizon_bucket_col]
            residuals = history.get(bucket, [])
            data.at[idx, "calibration_count"] = len(residuals)
            if len(residuals) >= min_calibration:
                radius = conformal_quantile(residuals, coverage)
                data.at[idx, lower_col] = float(row[prediction_col]) - radius
                data.at[idx, upper_col] = float(row[prediction_col]) + radius
                
        # 3. Queue new residuals
        current_residuals: list[tuple[object, float]] = []
        for _, row in origin_rows.iterrows():
            if pd.notna(row[actual_col]) and pd.notna(row[prediction_col]):
                res_val = abs(float(row[actual_col]) - float(row[prediction_col]))
                bucket = row[horizon_bucket_col]
                if target_time_col and target_time_col in data.columns:
                    # Target delivery time is when this residual is realized
                    realization_time = row[target_time_col]
                    pending_residuals.append((realization_time, bucket, res_val))
                else:
                    current_residuals.append((bucket, res_val))
                    
        if not target_time_col or target_time_col not in data.columns:
            # Fallback (old behavior): add residuals immediately to history
            for bucket, residual in current_residuals:
                history.setdefault(bucket, []).append(residual)
                
    return data
