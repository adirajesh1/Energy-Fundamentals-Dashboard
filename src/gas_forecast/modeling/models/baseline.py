import pandas as pd

from gas_forecast.modeling.models.base import WeeklyChangeForecastModel
from gas_forecast.modeling.models.training import select_training_history


class FiveYearWeeklyAverageModel(WeeklyChangeForecastModel):
    """Forecast weekly change using the mean (and std) by week-of-year."""

    def __init__(self, lookback_years: int = 5) -> None:
        self.lookback_years = lookback_years
        self._weekly_profile: pd.DataFrame | None = None

    @property
    def name(self) -> str:
        return f"{self.lookback_years}-Year Weekly Average"

    def fit(self, storage: pd.DataFrame) -> "FiveYearWeeklyAverageModel":
        training = select_training_history(
            storage,
            lookback_years=self.lookback_years,
        )
        profile = (
            training.groupby("week_of_year")["weekly_change_bcf"]
            .agg(predicted_weekly_change="mean", weekly_change_std="std")
            .reset_index()
        )
        mean_std = float(profile["weekly_change_std"].dropna().mean()) if not profile["weekly_change_std"].dropna().empty else 0.0
        profile["weekly_change_std"] = profile["weekly_change_std"].fillna(mean_std)
        self._weekly_profile = profile
        return self

    def predict(self, evaluation: pd.DataFrame) -> pd.DataFrame:
        if self._weekly_profile is None:
            raise RuntimeError("Call fit() before predict().")

        preds = evaluation[["week_of_year"]].merge(
            self._weekly_profile, on="week_of_year", how="left"
        )
        preds["lower_band"] = (
            preds["predicted_weekly_change"] - preds["weekly_change_std"]
        )
        preds["upper_band"] = (
            preds["predicted_weekly_change"] + preds["weekly_change_std"]
        )
        return preds
