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
        
        # Ensure a regularly spaced W-FRI index
        train_dt = train.copy()
        train_dt["date"] = pd.to_datetime(train_dt["date"])
        train_dt = train_dt.set_index("date").sort_index()

        min_date = train_dt.index.min()
        max_date = train_dt.index.max()
        if pd.notna(min_date) and pd.notna(max_date):
            full_idx = pd.date_range(start=min_date, end=max_date, freq="W-FRI")
            series = train_dt["weekly_change_bcf"].reindex(full_idx)
            # Linearly interpolate gaps and fill ends
            series = series.interpolate(method="linear").ffill().bfill()
        else:
            series = train_dt["weekly_change_bcf"].dropna()

        self._last_train_date = series.index[-1]

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

        eval_dates = pd.to_datetime(evaluation["date"])
        max_eval_date = eval_dates.max()
        last_train_date = getattr(self, "_last_train_date", None)

        if last_train_date is not None and pd.notna(max_eval_date) and max_eval_date > last_train_date:
            # Generate predictions for the complete date range up to max_eval_date
            forecast_idx = pd.date_range(start=last_train_date, end=max_eval_date, freq="W-FRI")
            if forecast_idx[0] == last_train_date:
                forecast_idx = forecast_idx[1:]
            
            steps = len(forecast_idx)
            forecast = self._fitted.get_forecast(steps=steps)
            forecast_mean = pd.Series(forecast.predicted_mean.to_numpy(), index=forecast_idx)
            intervals = forecast.conf_int(alpha=0.32)
            lower_band = pd.Series(intervals.iloc[:, 0].to_numpy(), index=forecast_idx)
            upper_band = pd.Series(intervals.iloc[:, 1].to_numpy(), index=forecast_idx)

            pred_mean = eval_dates.map(forecast_mean).to_numpy()
            pred_lower = eval_dates.map(lower_band).to_numpy()
            pred_upper = eval_dates.map(upper_band).to_numpy()
        else:
            # Fallback to positional steps
            steps = len(evaluation)
            if steps > 0:
                forecast = self._fitted.get_forecast(steps=steps)
                intervals = forecast.conf_int(alpha=0.32)
                pred_mean = forecast.predicted_mean.to_numpy()
                pred_lower = intervals.iloc[:, 0].to_numpy()
                pred_upper = intervals.iloc[:, 1].to_numpy()
            else:
                import numpy as np
                pred_mean, pred_lower, pred_upper = np.array([]), np.array([]), np.array([])

        return pd.DataFrame(
            {
                "predicted_weekly_change": pred_mean,
                "lower_band": pred_lower,
                "upper_band": pred_upper,
            }
        )
