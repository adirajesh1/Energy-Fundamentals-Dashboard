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
    coverage: float = 0.80,
    min_calibration: int = 30,
    lower_col: str = "lower_bound",
    upper_col: str = "upper_bound",
) -> pd.DataFrame:
    """Calibrate each row using only earlier residuals in its horizon bucket."""
    required = {actual_col, prediction_col, time_col, horizon_bucket_col}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Interval input missing required columns: {missing}")
    data = predictions.copy()
    data[time_col] = pd.to_datetime(data[time_col], utc=True)
    data = data.sort_values([time_col, horizon_bucket_col]).reset_index(drop=True)
    data[lower_col] = np.nan
    data[upper_col] = np.nan
    data["calibration_count"] = 0
    history: dict[object, list[float]] = {}
    for origin, origin_rows in data.groupby(time_col, sort=True):
        del origin
        pending: list[tuple[object, float]] = []
        for idx, row in origin_rows.iterrows():
            bucket = row[horizon_bucket_col]
            residuals = history.setdefault(bucket, [])
            data.at[idx, "calibration_count"] = len(residuals)
            if len(residuals) >= min_calibration:
                radius = conformal_quantile(residuals, coverage)
                data.at[idx, lower_col] = float(row[prediction_col]) - radius
                data.at[idx, upper_col] = float(row[prediction_col]) + radius
            if pd.notna(row[actual_col]) and pd.notna(row[prediction_col]):
                pending.append((bucket, abs(float(row[actual_col]) - float(row[prediction_col]))))
        for bucket, residual in pending:
            history[bucket].append(residual)
    return data
