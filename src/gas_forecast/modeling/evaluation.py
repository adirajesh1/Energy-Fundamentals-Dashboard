from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from gas_forecast.modeling.models.base import WeeklyChangeForecastModel


def _as_1d_float_array(values) -> np.ndarray:
    return np.asarray(values, dtype="float64").ravel()


def mae(y_true, y_pred) -> float:
    """Return mean absolute error."""
    return float(mean_absolute_error(_as_1d_float_array(y_true), _as_1d_float_array(y_pred)))


def rmse(y_true, y_pred) -> float:
    """Return root mean squared error."""
    return float(root_mean_squared_error(_as_1d_float_array(y_true), _as_1d_float_array(y_pred)))


def bias(y_true, y_pred) -> float:
    """Return average forecast error, actual minus predicted."""
    true = _as_1d_float_array(y_true)
    pred = _as_1d_float_array(y_pred)
    return float((true - pred).mean())


def evaluate_forecast(
    storage: pd.DataFrame,
    model: WeeklyChangeForecastModel,
    *,
    year: int | None = None,
) -> pd.DataFrame:
    """Fit on years before ``year`` and compare predictions to that year's actuals."""
    if year is None:
        year = storage["year"].max()

    training_storage = storage.loc[storage["year"] < year].copy()
    actuals = storage.loc[
        storage["year"] == year, ["date", "week_of_year", "weekly_change_bcf"]
    ].copy()

    if training_storage.empty:
        raise ValueError(f"No training rows exist before evaluation year {year}.")
    if actuals.empty:
        raise ValueError(f"No actual rows exist for evaluation year {year}.")

    model.fit(training_storage)
    preds = model.predict(actuals)

    result = actuals.copy()
    for col in preds.columns:
        result[col] = preds[col].values

    result["forecast_deviation"] = (
        result["weekly_change_bcf"] - result["predicted_weekly_change"]
    )

    if {"lower_band", "upper_band"}.issubset(result.columns):
        result["outside_band"] = (
            (result["weekly_change_bcf"] > result["upper_band"])
            | (result["weekly_change_bcf"] < result["lower_band"])
        )
    else:
        result["outside_band"] = False

    return result


def error_metrics(forecast: pd.DataFrame) -> pd.DataFrame:
    """Calculate error metrics for a forecast."""
    mae_val = mean_absolute_error(forecast["weekly_change_bcf"], forecast["predicted_weekly_change"])
    rmse_val = root_mean_squared_error(forecast["weekly_change_bcf"], forecast["predicted_weekly_change"])
    r2 = r2_score(forecast["weekly_change_bcf"], forecast["predicted_weekly_change"])
    return pd.DataFrame({"Model": [mae_val, rmse_val, r2]}, index=["MAE", "RMSE", "R2"])
