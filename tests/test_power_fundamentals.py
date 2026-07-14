import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, RegressorMixin

from power_forecast.backtesting import run_power_backtest
from power_forecast.fundamentals import (
    GAS_HEAT_CONTENT_MMBTU_PER_BCF,
    build_physical_stack,
)
from power_forecast.models.correction import _rolling_predictions, fit_predict_correction


def test_physical_stack_balances_and_bounds_gas_generation():
    hours = pd.date_range("2026-07-13T01:00:00Z", periods=24, freq="h")
    forecast = pd.DataFrame(
        {
            "forecast_origin": pd.Timestamp("2026-07-13T00:00:00Z"),
            "delivery_hour": hours,
            "load_forecast_mw": 70_000.0,
            "wind_forecast_mw": 15_000.0,
            "solar_forecast_mw": np.maximum(0, np.sin(np.linspace(-1, 2, 24))) * 10_000,
            "nuclear_mw": 5_000.0,
            "hydro_mw": 1_000.0,
            "other_nonthermal_mw": 500.0,
            "net_imports_mw": 200.0,
            "battery_net_discharge_mw": 300.0,
            "available_capacity_mw": 90_000.0,
            "conventional_outage_mw": 3_000.0,
        }
    )
    result = build_physical_stack(forecast, heat_rate=7.5)
    assert np.abs(result["balance_error_mw"]).max() < 1e-8
    assert (result["gas_generation_mw"] >= 0).all()
    assert (result["gas_generation_mw"] <= result["dispatchable_thermal_mw"]).all()
    expected = result["gas_generation_mw"] * 7.5 / GAS_HEAT_CONTENT_MMBTU_PER_BCF
    np.testing.assert_allclose(result["gas_burn_bcf_base"], expected)
    assert result["gas_burn_bcf_base"].sum() == pytest.approx(expected.sum())


def test_negative_residual_becomes_curtailment_and_still_balances():
    forecast = pd.DataFrame(
        {
            "forecast_origin": [pd.Timestamp("2026-04-01T00:00:00Z")],
            "delivery_hour": [pd.Timestamp("2026-04-01T01:00:00Z")],
            "load_forecast_mw": [10_000.0],
            "wind_forecast_mw": [12_000.0],
            "solar_forecast_mw": [5_000.0],
            "nuclear_mw": [4_000.0],
            "hydro_mw": [0.0],
            "other_nonthermal_mw": [0.0],
            "net_imports_mw": [0.0],
            "battery_net_discharge_mw": [0.0],
        }
    )
    result = build_physical_stack(forecast)
    assert result.loc[0, "dispatchable_thermal_mw"] == 0
    assert result.loc[0, "curtailment_mw"] == pytest.approx(11_000.0)
    assert result.loc[0, "balance_error_mw"] == pytest.approx(0.0)


def test_correction_is_not_promoted_when_it_does_not_beat_baseline():
    origins = pd.date_range("2026-01-01", periods=5, freq="D", tz="UTC")
    rows = []
    for origin in origins:
        for horizon in range(1, 49):
            baseline = 50_000.0 + horizon
            rows.append(
                {
                    "forecast_origin": origin,
                    "delivery_hour": origin + pd.Timedelta(hours=horizon),
                    "baseline_mw": baseline,
                    "actual_mw": baseline,
                    "horizon_hour": horizon,
                }
            )
    history = pd.DataFrame(rows)
    future = history.loc[history["forecast_origin"] == origins[-1]].copy()
    result, selection = fit_predict_correction(history, future)
    assert not selection.promoted
    assert selection.model_name == "ercot_baseline"
    np.testing.assert_allclose(result["forecast_mw"], result["baseline_mw"])

    history["component"] = "load"
    predictions, metrics = run_power_backtest(
        history, components=("load",)
    )
    assert not predictions.empty
    assert set(metrics["model"]) == {"ercot_baseline", "hour_of_week_fallback"}


def test_rolling_correction_training_excludes_undelivered_labels():
    fit_sizes = []

    class RecordingRegressor(RegressorMixin, BaseEstimator):
        def fit(self, features, target):
            fit_sizes.append(len(features))
            return self

        def predict(self, features):
            return np.zeros(len(features))

    origins = pd.date_range("2026-01-01", periods=4, freq="D", tz="UTC")
    rows = []
    for origin in origins:
        for horizon in (*range(1, 41), 72):
            rows.append(
                {
                    "forecast_origin": origin,
                    "delivery_hour": origin + pd.Timedelta(hours=horizon),
                    "horizon_bucket": "test",
                    "baseline_mw": 100.0,
                    "actual_mw": 100.0,
                }
            )
    _rolling_predictions(
        pd.DataFrame(rows),
        RecordingRegressor(),
        ["baseline_mw"],
    )
    assert fit_sizes == [103]
