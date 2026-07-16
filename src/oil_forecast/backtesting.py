from __future__ import annotations

import pandas as pd

from energy_forecast.evaluation import bias, mae, rmse
from energy_forecast.intervals import add_horizon_conformal_intervals
from energy_forecast.splitters import RollingOriginSplitter
from oil_forecast.fundamentals import OilFundamentalsModel, _validate_balance


def run_oil_backtest(
    balance: pd.DataFrame,
    *,
    initial_train_weeks: int = 156,
    interval_coverage: float = 0.80,
    min_calibration: int = 30,
    lookback_years: int = 5,
    recent_weeks: int = 4,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run expanding one-week origins for the oil fundamentals model."""
    data = _validate_balance(balance)
    data = data.dropna(subset=["commercial_stock_change_mmbbl"]).reset_index(drop=True)
    if initial_train_weeks < 1 or initial_train_weeks >= len(data):
        raise ValueError("initial_train_weeks must leave train and validation rows.")
    splitter = RollingOriginSplitter(
        "date",
        initial_train_end=data.loc[initial_train_weeks, "date"],
        validation_horizon="7D",
        step="7D",
    )
    outputs: list[pd.DataFrame] = []
    for train_idx, validation_idx in splitter.split(data):
        train = data.loc[train_idx]
        model = OilFundamentalsModel(
            lookback_years=lookback_years,
            recent_weeks=recent_weeks,
        ).fit(train)
        for idx in validation_idx:
            forecast = model.predict([data.loc[idx, "date"]])
            forecast["actual_mmbbl"] = data.loc[idx, "commercial_stock_change_mmbbl"]
            outputs.append(forecast)
    if not outputs:
        return pd.DataFrame(), pd.DataFrame()

    predictions = pd.concat(outputs, ignore_index=True)
    predictions["horizon_bucket"] = "h1"
    predictions = add_horizon_conformal_intervals(
        predictions,
        actual_col="actual_mmbbl",
        prediction_col="prediction_mmbbl",
        time_col="forecast_origin",
        target_time_col="date",
        coverage=interval_coverage,
        min_calibration=min_calibration,
        lower_col="lower_bound_mmbbl",
        upper_col="upper_bound_mmbbl",
    )

    metrics: list[dict[str, object]] = []
    for model_name, column in (
        ("seasonal_level_fundamentals", "prediction_mmbbl"),
        ("last_change_baseline", "last_change_baseline_mmbbl"),
    ):
        metrics.append(
            {
                "model": model_name,
                "mae": mae(predictions["actual_mmbbl"], predictions[column]),
                "rmse": rmse(predictions["actual_mmbbl"], predictions[column]),
                "bias": bias(predictions["actual_mmbbl"], predictions[column]),
                "n_samples": len(predictions),
            }
        )
    return predictions, pd.DataFrame(metrics)
