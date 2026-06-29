from __future__ import annotations

import requests
import pandas as pd


EIA_WEEKLY_STORAGE_URL = (
    "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
)


def fetch_weekly_storage_raw(
    api_key: str,
    *,
    length: int = 5000,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """
    Download weekly natural gas storage data from the EIA API.

    Parameters
    ----------
    api_key:
        EIA API key.
    length:
        Maximum number of records requested from the API.
    timeout:
        Maximum number of seconds to wait for the API response.

    Returns
    -------
    pd.DataFrame
        Weekly storage records returned by the EIA API.

    Raises
    ------
    ValueError
        If the API key is missing.
    requests.HTTPError
        If the EIA API returns an unsuccessful HTTP response.
    KeyError
        If the expected data is missing from the API response.
    """
    if not api_key:
        raise ValueError(
            "EIA API key is missing. Set EIA_API_KEY in local.env."
        )

    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": length,
    }

    response = requests.get(
        EIA_WEEKLY_STORAGE_URL,
        params=params,
        timeout=timeout,
    )
    response.raise_for_status()

    payload = response.json()

    try:
        records = payload["response"]["data"]
    except KeyError as exc:
        raise KeyError(
            "The EIA response did not contain response.data."
        ) from exc

    return pd.DataFrame(records)

def clean_weekly_storage(raw_df, start_date=None, end_date=None):
    df = raw_df.copy()

    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["series-description"] = df["series-description"].astype(str)

    if start_date is not None:
        df = df[df["period"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["period"] <= pd.to_datetime(end_date)]

    df["year"] = df["period"].dt.year
    df["month"] = df["period"].dt.month
    df["week_of_year"] = df["period"].dt.isocalendar().week.astype(int)

    df = df.sort_values(["duoarea", "period"]).reset_index(drop=True)

    validate_weekly_storage(df)

    return df
    
def select_region(storage: pd.DataFrame, region: str | list[str]) -> pd.DataFrame:
    if isinstance(region, str):
        regions = [region]
    else:
        regions = region

    available_regions = set(storage["duoarea"].unique())
    missing_regions = [r for r in regions if r not in available_regions]
    if missing_regions:
        raise ValueError(f"Region(s) {missing_regions} not found in storage['duoarea']")
    
    selected_storage = storage.loc[storage["duoarea"].isin(regions)]
    validate_storage_region(selected_storage)

    return selected_storage



def calculate_weekly_storage_change(storage: pd.DataFrame) -> pd.DataFrame:
    storage['weekly_change_bcf'] = storage['value'].diff()
    return storage

def prepare_storage_model_data(storage: pd.DataFrame) -> pd.DataFrame:
    df = storage.copy()

    df = df.rename(columns={
        "period": "date",
        "value": "storage_bcf",
    })

    df = df[
        ["date", "storage_bcf", "weekly_change_bcf", "year", "month", "week_of_year", "duoarea"]
    ]

    df = df.dropna(subset=["weekly_change_bcf"])

    return df.reset_index(drop=True)

# validation
def validate_weekly_storage(storage: pd.DataFrame) -> None:
    required_columns = {
        "period",
        "value",
        "series-description",
        "duoarea",
        "year",
        "month",
        "week_of_year",
    }

    missing_cols = required_columns - set(storage.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

    if storage["period"].isna().any():
        raise ValueError("Found missing values in 'period'.")

    if storage["value"].isna().any():
        n_missing = storage["value"].isna().sum()
        raise ValueError(f"Found {n_missing} missing values in 'value'.")

    if (storage["value"] < 0).any():
        raise ValueError("Found negative values in 'value'.")

    if not storage.sort_values(["duoarea", "period"]).index.equals(storage.index):
        raise ValueError("Storage data is not sorted by ['duoarea', 'period'].")


def validate_storage_region(df: pd.DataFrame) -> None:
    if df["period"].duplicated().any():
        raise ValueError("Selected region has duplicate periods.")

    if not df["period"].is_monotonic_increasing:
        raise ValueError("Selected region is not sorted by period.")