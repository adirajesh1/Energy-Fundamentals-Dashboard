"""Conformal prediction intervals and coverage diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd


def _as_1d_float_array(values: Iterable[float]) -> np.ndarray:
    return np.asarray(values, dtype="float64").ravel()


def _validate_coverage(coverage: float) -> None:
    if not 0.0 < coverage < 1.0:
        raise ValueError("coverage must be strictly between 0 and 1.")


@dataclass
class ConformalIntervalCalibrator:
    """Symmetric absolute-error conformal calibrator for point forecasts."""

    coverage: float = 0.80
    radius_: float | None = field(default=None, init=False)
    calibration_samples_: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        _validate_coverage(self.coverage)

    def fit(
        self,
        actuals: Iterable[float],
        point_predictions: Iterable[float],
    ) -> "ConformalIntervalCalibrator":
        """Fit a finite-sample conformal radius from calibration residuals."""
        actual = _as_1d_float_array(actuals)
        predicted = _as_1d_float_array(point_predictions)
        if len(actual) != len(predicted):
            raise ValueError("actuals and point_predictions must have the same length.")

        valid = np.isfinite(actual) & np.isfinite(predicted)
        residuals = np.abs(actual[valid] - predicted[valid])
        if len(residuals) == 0:
            raise ValueError("At least one finite calibration residual is required.")

        rank = min(len(residuals), int(np.ceil((len(residuals) + 1) * self.coverage)))
        self.radius_ = float(np.sort(residuals)[rank - 1])
        self.calibration_samples_ = len(residuals)
        return self

    def predict_intervals(self, point_predictions: Iterable[float]) -> pd.DataFrame:
        """Return lower and upper bounds around point forecasts."""
        if self.radius_ is None:
            raise ValueError("Fit the conformal calibrator before predicting intervals.")
        predicted = _as_1d_float_array(point_predictions)
        return pd.DataFrame(
            {
                "interval_lower": predicted - self.radius_,
                "interval_upper": predicted + self.radius_,
            }
        )


def add_rolling_conformal_intervals(
    predictions: pd.DataFrame,
    *,
    target_col: str,
    prediction_col: str = "predicted_weekly_change",
    date_col: str = "date",
    coverage: float = 0.80,
    min_calibration_samples: int = 20,
    group_cols: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Add intervals calibrated only on earlier out-of-fold residuals.

    Rows that share a date are calibrated before any of their residuals enter
    the history. This matters when several model outputs share an origin or a
    date: none may calibrate itself from its own realized target.
    """
    _validate_coverage(coverage)
    if min_calibration_samples < 1:
        raise ValueError("min_calibration_samples must be at least 1.")

    required = {target_col, prediction_col, date_col, *group_cols}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Predictions missing required interval columns: {missing}")

    data = predictions.copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    if data[date_col].isna().any():
        raise ValueError("Prediction interval calibration requires valid dates.")
    data["_source_order"] = np.arange(len(data))
    data = data.sort_values([*group_cols, date_col, "_source_order"], kind="stable")

    data["interval_lower"] = np.nan
    data["interval_upper"] = np.nan
    data["interval_radius"] = np.nan
    data["calibration_samples"] = 0
    data["nominal_coverage"] = coverage

    grouped_frames = (
        data.groupby(list(group_cols), dropna=False, sort=False)
        if group_cols
        else [(None, data)]
    )
    for _, group in grouped_frames:
        residuals: list[float] = []
        for _, same_date in group.groupby(date_col, sort=True):
            row_indices = same_date.index
            data.loc[row_indices, "calibration_samples"] = len(residuals)
            if len(residuals) >= min_calibration_samples:
                calibrator = ConformalIntervalCalibrator(coverage=coverage).fit(
                    residuals,
                    np.zeros(len(residuals)),
                )
                intervals = calibrator.predict_intervals(
                    same_date[prediction_col].to_numpy()
                )
                data.loc[row_indices, "interval_lower"] = intervals[
                    "interval_lower"
                ].to_numpy()
                data.loc[row_indices, "interval_upper"] = intervals[
                    "interval_upper"
                ].to_numpy()
                data.loc[row_indices, "interval_radius"] = calibrator.radius_

            actual = pd.to_numeric(same_date[target_col], errors="coerce").to_numpy()
            predicted = pd.to_numeric(
                same_date[prediction_col],
                errors="coerce",
            ).to_numpy()
            valid = np.isfinite(actual) & np.isfinite(predicted)
            residuals.extend(np.abs(actual[valid] - predicted[valid]).tolist())

    return (
        data.sort_values("_source_order", kind="stable")
        .drop(columns="_source_order")
        .reset_index(drop=True)
    )


def interval_metrics(
    actuals: Iterable[float],
    lower: Iterable[float],
    upper: Iterable[float],
    *,
    coverage: float,
) -> dict[str, float | int]:
    """Summarize empirical coverage, tail misses, and interval width."""
    _validate_coverage(coverage)
    actual = _as_1d_float_array(actuals)
    lower_bound = _as_1d_float_array(lower)
    upper_bound = _as_1d_float_array(upper)
    if not (len(actual) == len(lower_bound) == len(upper_bound)):
        raise ValueError("actuals, lower, and upper must have the same length.")

    valid = np.isfinite(actual) & np.isfinite(lower_bound) & np.isfinite(upper_bound)
    actual = actual[valid]
    lower_bound = lower_bound[valid]
    upper_bound = upper_bound[valid]
    if (lower_bound > upper_bound).any():
        raise ValueError("Interval lower bounds cannot exceed upper bounds.")
    if len(actual) == 0:
        return {
            "nominal_coverage": coverage,
            "empirical_coverage": np.nan,
            "coverage_error": np.nan,
            "average_interval_width": np.nan,
            "below_interval_rate": np.nan,
            "above_interval_rate": np.nan,
            "interval_samples": 0,
        }

    below = actual < lower_bound
    above = actual > upper_bound
    empirical_coverage = float((~(below | above)).mean())
    return {
        "nominal_coverage": coverage,
        "empirical_coverage": empirical_coverage,
        "coverage_error": empirical_coverage - coverage,
        "average_interval_width": float((upper_bound - lower_bound).mean()),
        "below_interval_rate": float(below.mean()),
        "above_interval_rate": float(above.mean()),
        "interval_samples": len(actual),
    }
