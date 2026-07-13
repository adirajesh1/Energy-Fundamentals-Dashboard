from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests

from gas_forecast.data.cache import load_parquet_cache, write_parquet_cache
from gas_forecast.data.paths import DEFAULT_CACHE_DIR, resolve_api_key

# Mapping of state names to two-letter abbreviations (Lower 48 + DC)
STATE_TO_ABBR = {
    "Alabama": "AL", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI",
    "Wyoming": "WY", "Alaska": "AK", "Hawaii": "HI"
}

EIA_LSUM_URL = "https://api.eia.gov/v2/natural-gas/sum/lsum/data/"
EIA_PRI_URL = "https://api.eia.gov/v2/natural-gas/pri/fut/data/"

def fetch_eia_api_paginated(
    url: str,
    params: dict[str, str | list[str] | int],
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Download data from EIA API v2 with pagination support."""
    frames: list[pd.DataFrame] = []
    offset = 0
    length = 5000

    query_params = params.copy()
    query_params["length"] = length
    
    while True:
        query_params["offset"] = offset
        response = requests.get(url, params=query_params, timeout=timeout)
        response.raise_for_status()
        
        payload = response.json()
        try:
            records = payload["response"]["data"]
        except KeyError as exc:
            raise KeyError("The EIA response did not contain response.data.") from exc
            
        if not records:
            break
            
        chunk = pd.DataFrame(records)
        frames.append(chunk)
        
        if len(chunk) < length:
            break
            
        offset += length

    if not frames:
        return pd.DataFrame()
        
    return pd.concat(frames, ignore_index=True)

def fetch_monthly_state_data_raw(
    api_key: str,
    states: list[str],
    start_date: str = "2010-01-01",
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    Fetch raw monthly dry production and consumption data for a list of states.
    """
    key = resolve_api_key(api_key)
    
    chunk_size = 5
    all_frames: list[pd.DataFrame] = []
    
    for i in range(0, len(states), chunk_size):
        chunk_states = states[i:i + chunk_size]
        series_codes: list[str] = []
        for state in chunk_states:
            abbr = STATE_TO_ABBR.get(state)
            if not abbr:
                continue
            # Production & Consumption series
            series_codes.extend([
                f"N9050{abbr}2",     # Marketed Natural Gas Production (MMcf)
                f"N3010{abbr}2",     # Residential Consumption (MMcf)
                f"N3020{abbr}2",     # Commercial Consumption (MMcf)
                f"N3035{abbr}2",     # Industrial Consumption (MMcf)
                f"N3045{abbr}2",     # Deliveries to Electric Power Consumers (MMcf)
                f"N3050{abbr}2",     # Natural Gas Citygate Price ($/Mcf)
            ])

        # Always fetch national baseline series in the first chunk to enable downscaling
        if i == 0:
            series_codes.extend([
                "N9070US2",  # U.S. Dry Natural Gas Production (MMcf)
                "N9050US2",  # U.S. Marketed Natural Gas Production (MMcf)
                "N9140US2",  # U.S. Natural Gas Total Consumption (MMcf)
                "N9160US2",  # U.S. Natural Gas Lease and Plant Fuel Consumption (MMcf)
                "N9170US2",  # U.S. Natural Gas Pipeline & Distribution Use (MMcf)
            ])

        if not series_codes:
            continue

        params: dict[str, str | list[str] | int] = {
            "api_key": key,
            "frequency": "monthly",
            "data[0]": "value",
            "facets[series][]": series_codes,
            "start": start_date[:7], # YYYY-MM
        }
        if end_date:
            params["end"] = end_date[:7]

        print(f"Fetching monthly data chunk {i // chunk_size + 1} for states: {', '.join(chunk_states)}...")
        df_chunk = fetch_eia_api_paginated(EIA_LSUM_URL, params)
        if not df_chunk.empty:
            all_frames.append(df_chunk)

    if not all_frames:
        return pd.DataFrame()

    return pd.concat(all_frames, ignore_index=True)

def fetch_daily_spot_price_raw(
    api_key: str,
    start_date: str = "2010-01-01",
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    Fetch daily Henry Hub Spot Price data (RNGWHHD).
    """
    key = resolve_api_key(api_key)
    params: dict[str, str | list[str] | int] = {
        "api_key": key,
        "frequency": "daily",
        "data[0]": "value",
        "facets[series][]": ["RNGWHHD"],
        "start": start_date,
    }
    if end_date:
        params["end"] = end_date

    return fetch_eia_api_paginated(EIA_PRI_URL, params)

def get_monthly_state_data(
    api_key: str,
    states: list[str],
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Get monthly state-level data from cache or fetch from API.
    """
    cache_dir = Path(cache_dir)
    # Sort states for a deterministic cache filename
    sorted_states = sorted(states)
    states_hash = "-".join(STATE_TO_ABBR.get(s, s) for s in sorted_states)
    cache_path = cache_dir / "balance" / f"state_monthly_{states_hash}.parquet"
    
    if not force_refresh and cache_path.exists():
        return load_parquet_cache(cache_path)

    df = fetch_monthly_state_data_raw(api_key, sorted_states)
    if not df.empty:
        # Convert period column to datetime
        df["period"] = pd.to_datetime(df["period"] + "-01")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        write_parquet_cache(df, cache_path)
    return df

def get_daily_spot_price(
    api_key: str,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Get daily spot price from cache or fetch from API.
    """
    cache_dir = Path(cache_dir)
    cache_path = cache_dir / "balance" / "daily_spot_price.parquet"

    if not force_refresh and cache_path.exists():
        return load_parquet_cache(cache_path)

    df = fetch_daily_spot_price_raw(api_key)
    if not df.empty:
        df["period"] = pd.to_datetime(df["period"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        write_parquet_cache(df, cache_path)
    return df
