from __future__ import annotations

import pandas as pd

_WEATHER_JOIN_COLUMNS = (
    "date",
    "duoarea",
    "temperature_f",
    "hdd",
    "cdd",
    "weather_days",
)


def join_weather_storage(
    storage: pd.DataFrame,
    weather: pd.DataFrame,
) -> pd.DataFrame:
    """Join weekly storage and weather on EIA week-ending Friday and region."""
    missing_storage = {"date", "duoarea"} - set(storage.columns)
    if missing_storage:
        raise ValueError(
            f"Storage missing required columns: {sorted(missing_storage)}"
        )

    missing_weather = set(_WEATHER_JOIN_COLUMNS) - set(weather.columns)
    if missing_weather:
        raise ValueError(
            f"Weather missing required columns: {sorted(missing_weather)}"
        )

    weather_subset = weather[list(_WEATHER_JOIN_COLUMNS)]
    return storage.merge(
        weather_subset,
        on=["date", "duoarea"],
        how="inner",
        validate="one_to_one",
    )
