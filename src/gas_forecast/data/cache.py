"""Compatibility exports for shared parquet/time-series artifact helpers."""

from pathlib import Path

from energy_forecast.artifacts import (
    compute_date_gaps,
    load_parquet_cache,
    merge_timeseries,
    split_gap_into_periods,
    write_parquet_cache,
)


DEFAULT_CACHE_DIR = Path("datasets/cache")

__all__ = [
    "DEFAULT_CACHE_DIR",
    "compute_date_gaps",
    "load_parquet_cache",
    "merge_timeseries",
    "split_gap_into_periods",
    "write_parquet_cache",
]
