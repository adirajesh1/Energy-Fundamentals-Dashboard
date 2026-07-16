import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from gas_forecast.data import add_calendar_features
from gas_forecast.modeling.models.base import WeeklyChangeForecastModel
from gas_forecast.modeling.models.training import select_training_history


def _fourier_features(
    frame: pd.DataFrame,
    *,
    period: float = 52.0,
    n_harmonics: int = 3,
    time_col: str = "week_of_year",
) -> pd.DataFrame:
    t = frame[time_col].astype(float)
    features = {}
    for k in range(1, n_harmonics + 1):
        angle = 2 * np.pi * k * t / period
        features[f"sin_{k}"] = np.sin(angle)
        features[f"cos_{k}"] = np.cos(angle)
    return pd.DataFrame(features, index=frame.index)


# _seasonal_features was removed in favor of add_calendar_features from gas_forecast.data


class WeeklyChangeLinearRegressionModel(WeeklyChangeForecastModel):
    """Linear regression on cyclical week-of-year and month features."""

    def __init__(self, lookback_years: int | None = None) -> None:
        self.lookback_years = lookback_years
        self._model: LinearRegression | None = None
        self._residual_std: float | None = None

    @property
    def name(self) -> str:
        return "Linear Regression (seasonal)"

    def fit(self, storage: pd.DataFrame) -> "WeeklyChangeLinearRegressionModel":
        train = select_training_history(
            storage,
            lookback_years=self.lookback_years,
        )
        train = train.dropna(subset=["weekly_change_bcf"])

        features = add_calendar_features(train)[["week_sin", "week_cos", "month_sin", "month_cos"]]
        target = train["weekly_change_bcf"]

        self._model = LinearRegression().fit(features, target)
        residuals = target - self._model.predict(features)
        self._residual_std = float(residuals.std())
        return self

    def predict(self, evaluation: pd.DataFrame) -> pd.DataFrame:
        if self._model is None or self._residual_std is None:
            raise RuntimeError("Call fit() before predict().")

        features = add_calendar_features(evaluation)[["week_sin", "week_cos", "month_sin", "month_cos"]]
        predicted = self._model.predict(features)

        return pd.DataFrame(
            {
                "predicted_weekly_change": predicted,
                "lower_band": predicted - self._residual_std,
                "upper_band": predicted + self._residual_std,
            }
        )


class WeeklyChangeFourierRegressionModel(WeeklyChangeForecastModel):
    """Linear regression with K Fourier harmonics on week-of-year."""

    def __init__(
        self,
        lookback_years: int | None = None,
        n_harmonics: int = 3,
        period: float = 52.0,
    ) -> None:
        self.lookback_years = lookback_years
        self.n_harmonics = n_harmonics
        self.period = period
        self._model: LinearRegression | None = None
        self._residual_std: float | None = None

    @property
    def name(self) -> str:
        return f"Fourier Regression (K={self.n_harmonics})"

    def fit(self, storage: pd.DataFrame) -> "WeeklyChangeFourierRegressionModel":
        train = select_training_history(
            storage,
            lookback_years=self.lookback_years,
        )
        train = train.dropna(subset=["weekly_change_bcf"])

        features = _fourier_features(
            train, period=self.period, n_harmonics=self.n_harmonics
        )
        target = train["weekly_change_bcf"]

        self._model = LinearRegression().fit(features, target)
        residuals = target - self._model.predict(features)
        self._residual_std = float(residuals.std())
        return self

    def predict(self, evaluation: pd.DataFrame) -> pd.DataFrame:
        if self._model is None or self._residual_std is None:
            raise RuntimeError("Call fit() before predict().")

        features = _fourier_features(
            evaluation, period=self.period, n_harmonics=self.n_harmonics
        )
        predicted = self._model.predict(features)

        return pd.DataFrame(
            {
                "predicted_weekly_change": predicted,
                "lower_band": predicted - self._residual_std,
                "upper_band": predicted + self._residual_std,
            }
        )
