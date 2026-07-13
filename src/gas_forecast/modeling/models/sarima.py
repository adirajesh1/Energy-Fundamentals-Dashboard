import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from gas_forecast.modeling.models.base import WeeklyChangeForecastModel
from gas_forecast.modeling.models.training import select_training_history


class WeeklyChangeSARIMAModel(WeeklyChangeForecastModel):
    """Seasonal ARIMA on the weekly change time series."""

    def __init__(
        self,
        order: tuple[int, int, int] = (1, 0, 1),
        seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 52),
        lookback_years: int | None = None,
    ) -> None:
        self.order = order
        self.seasonal_order = seasonal_order
        self.lookback_years = lookback_years
        self._fitted = None

    @property
    def name(self) -> str:
        p, d, q = self.order
        P, D, Q, s = self.seasonal_order
        return f"SARIMA({p},{d},{q})({P},{D},{Q},{s})"

    def fit(self, storage: pd.DataFrame) -> "WeeklyChangeSARIMAModel":
        train = select_training_history(
            storage,
            lookback_years=self.lookback_years,
        )
        series = train["weekly_change_bcf"].dropna()

        self._fitted = SARIMAX(
            series,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)

        return self

    def predict(self, evaluation: pd.DataFrame) -> pd.DataFrame:
        if self._fitted is None:
            raise RuntimeError("Call fit() before predict().")

        steps = len(evaluation)
        forecast = self._fitted.get_forecast(steps=steps)
        intervals = forecast.conf_int(alpha=0.32)

        return pd.DataFrame(
            {
                "predicted_weekly_change": forecast.predicted_mean.to_numpy(),
                "lower_band": intervals.iloc[:, 0].to_numpy(),
                "upper_band": intervals.iloc[:, 1].to_numpy(),
            }
        )
