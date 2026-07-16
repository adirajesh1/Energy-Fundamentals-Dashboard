import pytest
import pandas as pd

from gas_forecast.modeling.evaluation import bias, mae, rmse, evaluate_forecast
from gas_forecast.modeling.models import WeeklyChangeForecastModel


class RecordingModel(WeeklyChangeForecastModel):
    def __init__(self):
        self.fit_years = None

    @property
    def name(self) -> str:
        return "Recording"

    def fit(self, storage: pd.DataFrame) -> "RecordingModel":
        self.fit_years = sorted(storage["year"].unique().tolist())
        return self

    def predict(self, evaluation: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"predicted_weekly_change": [0.0] * len(evaluation)})


def test_modeling_metrics_calculate_expected_values():
    y_true = [3.0, 5.0, 7.0]
    y_pred = [2.0, 5.0, 10.0]

    assert mae(y_true, y_pred) == pytest.approx(4 / 3)
    assert rmse(y_true, y_pred) == pytest.approx((10 / 3) ** 0.5)
    assert bias(y_true, y_pred) == pytest.approx(-2 / 3)


def test_modeling_metrics_ignore_pandas_index_alignment():
    y_true = pd.Series([3.0, 5.0, 7.0], index=[10, 11, 12])
    y_pred = pd.Series([2.0, 5.0, 10.0], index=[0, 1, 2])

    assert mae(y_true, y_pred) == pytest.approx(4 / 3)
    assert rmse(y_true, y_pred) == pytest.approx((10 / 3) ** 0.5)
    assert bias(y_true, y_pred) == pytest.approx(-2 / 3)


def test_evaluate_forecast_fits_only_years_before_requested_year():
    storage = pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-01-07", "2023-01-06", "2024-01-05"]),
            "year": [2022, 2023, 2024],
            "week_of_year": [1, 1, 1],
            "weekly_change_bcf": [1.0, 2.0, 3.0],
        }
    )
    model = RecordingModel()

    evaluate_forecast(storage, model, year=2023)

    assert model.fit_years == [2022]
