import pandas as pd

from gas_forecast.data.features import (
    DEFAULT_WEATHER_MODEL_FEATURES,
    build_weekly_model_features,
)


def test_build_weekly_model_features_keeps_lags_within_region():
    dates = pd.to_datetime(["2024-01-05", "2024-01-12"] * 2)
    storage = pd.DataFrame(
        {
            "date": dates,
            "duoarea": ["R01", "R01", "R02", "R02"],
            "storage_bcf": [100, 110, 200, 190],
            "weekly_change_bcf": [5, 10, -2, -10],
            "year": [2024, 2024, 2024, 2024],
            "month": [1, 1, 1, 1],
            "week_of_year": [1, 2, 1, 2],
        }
    )
    weather = pd.DataFrame(
        {
            "date": dates,
            "duoarea": ["R01", "R01", "R02", "R02"],
            "temperature_f": [30, 31, 70, 71],
            "hdd": [35, 34, 0, 0],
            "cdd": [0, 0, 5, 6],
            "weather_days": [7, 7, 7, 7],
        }
    )

    features = build_weekly_model_features(storage, weather)

    first_rows = features.groupby("duoarea").head(1)
    assert first_rows["weekly_change_lag1"].isna().all()
    assert first_rows["hdd_lag1"].isna().all()

    second_rows = features.groupby("duoarea").tail(1).set_index("duoarea")
    assert second_rows.loc["R01", "weekly_change_lag1"] == 5
    assert second_rows.loc["R02", "weekly_change_lag1"] == -2


def test_build_weekly_model_features_adds_rolling_surplus_and_season_features():
    dates = pd.date_range("2023-01-06", periods=60, freq="W-FRI")
    storage = pd.DataFrame(
        {
            "date": list(dates) * 2,
            "duoarea": ["R01"] * 60 + ["R02"] * 60,
            "storage_bcf": list(range(100, 160)) + list(range(300, 360)),
            "weekly_change_bcf": [float(i) for i in range(60)] * 2,
            "year": list(dates.year) * 2,
            "month": list(dates.month) * 2,
            "week_of_year": list(dates.isocalendar().week.astype(int)) * 2,
        }
    )
    weather = pd.DataFrame(
        {
            "date": list(dates) * 2,
            "duoarea": ["R01"] * 60 + ["R02"] * 60,
            "temperature_f": [40.0] * 60 + [80.0] * 60,
            "hdd": [25.0] * 60 + [0.0] * 60,
            "cdd": [0.0] * 60 + [15.0] * 60,
            "weather_days": [7] * 120,
        }
    )

    features = build_weekly_model_features(storage, weather)
    r01 = features.loc[features["duoarea"] == "R01"].reset_index(drop=True)

    assert r01.loc[4, "weekly_change_rolling_4wk"] == 1.5
    assert r01.loc[4, "hdd_rolling_4wk"] == 25.0
    assert r01.loc[53, "storage_vs_last_year"] == 52
    assert r01.loc[53, "storage_vs_5yr_avg"] == 52
    assert r01.loc[0, "is_withdrawal_season"] == 1
    assert r01.loc[14, "is_injection_season"] == 1
    assert set(DEFAULT_WEATHER_MODEL_FEATURES).issubset(features.columns)


def test_feature_builder_sorts_inputs_and_keeps_target_week_out_of_yoy_feature():
    dates = pd.date_range("2023-01-06", periods=60, freq="W-FRI")
    storage = pd.DataFrame(
        {
            "date": dates,
            "duoarea": "R01",
            "storage_bcf": range(100, 160),
            "weekly_change_bcf": [float(value) for value in range(60)],
            "year": dates.year,
            "month": dates.month,
            "week_of_year": dates.isocalendar().week.astype(int),
        }
    )
    weather = pd.DataFrame(
        {
            "date": dates,
            "duoarea": "R01",
            "temperature_f": 50.0,
            "hdd": 20.0,
            "cdd": 0.0,
            "weather_days": 7,
        }
    )

    shuffled = build_weekly_model_features(
        storage.sample(frac=1.0, random_state=7),
        weather.sample(frac=1.0, random_state=11),
    )
    baseline = build_weekly_model_features(storage, weather)

    assert shuffled.loc[1, "weekly_change_lag1"] == 0.0
    assert shuffled.loc[4, "weekly_change_rolling_4wk"] == 1.5
    assert baseline.loc[55, "weekly_change_yoy"] == 52.0

    changed_storage = storage.copy()
    changed_storage.loc[55, "weekly_change_bcf"] = 9_999.0
    changed = build_weekly_model_features(changed_storage, weather)

    assert changed.loc[55, "weekly_change_yoy"] == baseline.loc[55, "weekly_change_yoy"]
