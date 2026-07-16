from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests


EIA_SERIES_URL = "https://api.eia.gov/v2/seriesid/{series_id}"
EIA_WEEKLY_CRUDE_SERIES = {
    "production_kbpd": "WCRFPUS2",
    "refinery_inputs_kbpd": "WCRRIUS2",
    "imports_kbpd": "WCRIMUS2",
    "exports_kbpd": "WCREXUS2",
    "commercial_stocks_kb": "WCESTUS1",
    "spr_stocks_kb": "WCSSTUS1",
}


def _resolve_api_key(api_key: str | None) -> str:
    if api_key:
        return api_key
    try:
        from dotenv import load_dotenv

        for path in (Path("local.env"), Path("notebooks/local.env")):
            load_dotenv(path)
    except ImportError:
        pass
    resolved = os.getenv("EIA_API_KEY")
    if not resolved:
        raise ValueError("EIA API key required. Pass api_key= or set EIA_API_KEY.")
    return resolved


def _fetch_series(
    api_key: str,
    series_id: str,
    *,
    start: str | None,
    end: str | None,
    timeout: float,
) -> pd.DataFrame:
    params: dict[str, Any] = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": 0,
        "length": 5000,
    }
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    records: list[dict[str, Any]] = []
    while True:
        response = requests.get(
            EIA_SERIES_URL.format(series_id=series_id),
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        page = response.json().get("response", {}).get("data", [])
        records.extend(page)
        if len(page) < params["length"]:
            break
        params["offset"] += params["length"]
    return pd.DataFrame(records)


def fetch_weekly_crude_series(
    api_key: str | None = None,
    *,
    start: str | None = "2010-01-01",
    end: str | None = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Fetch the weekly U.S. crude series used by the fundamentals model."""
    key = _resolve_api_key(api_key)
    frames: list[pd.DataFrame] = []
    for component, series_id in EIA_WEEKLY_CRUDE_SERIES.items():
        frame = _fetch_series(
            key,
            series_id,
            start=start,
            end=end,
            timeout=timeout,
        )
        if frame.empty:
            raise ValueError(f"EIA returned no weekly data for {series_id}.")
        frame = frame[["period", "value"]].copy()
        frame["component"] = component
        frame["series_id"] = series_id
        frames.append(frame)

    result = pd.concat(frames, ignore_index=True)
    result["period"] = pd.to_datetime(result["period"], errors="coerce")
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    if result[["period", "value"]].isna().any().any():
        raise ValueError("EIA weekly crude data contains invalid dates or values.")
    return result.sort_values(["period", "component"]).reset_index(drop=True)
