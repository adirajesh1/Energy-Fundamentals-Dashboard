import pandas as pd

from gas_forecast.models.base import WeeklyChangeForecastModel


def evaluate_forecast(
    storage: pd.DataFrame,
    model: WeeklyChangeForecastModel,
    *,
    year: int | None = None,
) -> pd.DataFrame:
    """Fit a model and compare its predictions to actual weekly changes."""
    if year is None:
        year = storage["year"].max()

    actuals = storage.loc[
        storage["year"] == year, ["date", "week_of_year", "weekly_change_bcf"]
    ].copy()

    model.fit(storage)
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
