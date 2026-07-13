import pandas as pd
import pytest
from sklearn.base import BaseEstimator, RegressorMixin

from gas_forecast.modeling.backtesting import run_backtest
from gas_forecast.modeling.intervals import (
    ConformalIntervalCalibrator,
    add_rolling_conformal_intervals,
    interval_metrics,
)
from gas_forecast.modeling.splitters import ExpandingWindowSplitter


class MeanRegressor(BaseEstimator, RegressorMixin):
    def fit(self, X, y):
        self.mean_ = float(y.mean())
        return self

    def predict(self, X):
        return [self.mean_] * len(X)


def test_conformal_interval_calibrator_uses_finite_sample_error_rank():
    calibrator = ConformalIntervalCalibrator(coverage=0.80).fit(
        actuals=[1.0, 2.0, 3.0, 4.0],
        point_predictions=[0.0, 0.0, 0.0, 0.0],
    )

    intervals = calibrator.predict_intervals([10.0])

    assert calibrator.radius_ == pytest.approx(4.0)
    assert intervals.loc[0, "interval_lower"] == pytest.approx(6.0)
    assert intervals.loc[0, "interval_upper"] == pytest.approx(14.0)


def test_rolling_conformal_intervals_use_only_earlier_dates():
    predictions = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-05", periods=4, freq="W-FRI"),
            "weekly_change_bcf": [1.0, 2.0, 50.0, 4.0],
            "predicted_weekly_change": [0.0, 0.0, 0.0, 0.0],
        }
    )

    result = add_rolling_conformal_intervals(
        predictions,
        target_col="weekly_change_bcf",
        coverage=0.50,
        min_calibration_samples=2,
    )

    assert result["calibration_samples"].tolist() == [0, 1, 2, 3]
    assert pd.isna(result.loc[1, "interval_radius"])
    assert result.loc[2, "interval_radius"] == pytest.approx(2.0)
    assert result.loc[2, "interval_upper"] == pytest.approx(2.0)


def test_interval_metrics_report_coverage_and_tail_misses():
    metrics = interval_metrics(
        actuals=[0.0, 10.0],
        lower=[-1.0, -1.0],
        upper=[1.0, 1.0],
        coverage=0.80,
    )

    assert metrics["empirical_coverage"] == pytest.approx(0.5)
    assert metrics["above_interval_rate"] == pytest.approx(0.5)
    assert metrics["below_interval_rate"] == pytest.approx(0.0)
    assert metrics["average_interval_width"] == pytest.approx(2.0)


def test_backtest_attaches_interval_coverage_metrics_when_requested():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-05", periods=7, freq="W-FRI"),
            "feature": range(7),
            "weekly_change_bcf": [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0],
        }
    )
    splitter = ExpandingWindowSplitter(
        "date",
        initial_train_start="2024-01-05",
        initial_train_end="2024-01-26",
        val_weeks=1,
        step_weeks=1,
    )

    predictions, metrics = run_backtest(
        frame,
        feature_cols=["feature"],
        target_col="weekly_change_bcf",
        date_col="date",
        model=MeanRegressor(),
        splitter=splitter,
        interval_coverage=0.80,
        min_calibration_samples=1,
    )

    assert {"interval_lower", "interval_upper", "interval_radius"}.issubset(
        predictions.columns
    )
    assert {"empirical_coverage", "average_interval_width", "interval_samples"}.issubset(
        metrics.columns
    )
    assert metrics.loc[metrics["fold"] == "overall", "interval_samples"].iloc[0] > 0
