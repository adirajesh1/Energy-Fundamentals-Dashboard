from __future__ import annotations

from pathlib import Path

import pandas as pd

from energy_forecast.artifacts import (
    load_parquet_cache,
    save_versioned_parquet,
    write_parquet_cache,
)
from oil_forecast.data.eia import fetch_weekly_crude_series
from oil_forecast.fundamentals import build_weekly_crude_balance, forecast_next_week


DEFAULT_CACHE_DIR = Path("datasets/cache/oil")
DEFAULT_PROCESSED_DIR = Path("datasets/processed")
RAW_CACHE_NAME = "us_weekly_crude_raw.parquet"
BALANCE_DATASET = "us_weekly_crude_balance"


def refresh_oil_data(
    api_key: str | None = None,
    *,
    start: str = "2010-01-01",
    end: str | None = None,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
) -> dict[str, Path]:
    raw = fetch_weekly_crude_series(api_key, start=start, end=end)
    balance = build_weekly_crude_balance(raw)
    raw_path = Path(cache_dir) / RAW_CACHE_NAME
    write_parquet_cache(raw, raw_path)
    balance_path = save_versioned_parquet(
        balance,
        processed_dir,
        BALANCE_DATASET,
        save_latest=True,
    )
    return {"raw": raw_path, "balance": balance_path}


def load_oil_balance(
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
) -> pd.DataFrame:
    path = Path(processed_dir) / f"{BALANCE_DATASET}_latest.parquet"
    balance = load_parquet_cache(path)
    if balance.empty:
        raise FileNotFoundError("Run oil-data refresh before forecasting oil fundamentals.")
    return balance


def build_oil_forecast(
    *,
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
) -> pd.DataFrame:
    forecast = forecast_next_week(load_oil_balance(processed_dir))
    save_versioned_parquet(
        forecast,
        processed_dir,
        "us_weekly_crude_forecast",
        save_latest=True,
    )
    return forecast
