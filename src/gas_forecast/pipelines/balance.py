from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

from gas_forecast.data.balance_api import get_monthly_state_data, get_daily_spot_price
from gas_forecast.data.regions import region_states, region_slug
from gas_forecast.data.paths import DEFAULT_PROCESSED_DIR, latest_processed_path
from gas_forecast.data.export import save_versioned_parquet
from gas_forecast.modeling.models import StructuralDisaggregator


def _artifact_matches_region(path: Path, region: str) -> bool:
    """Return whether a processed artifact contains only the requested region."""
    if not path.exists():
        return False
    try:
        frame = pd.read_parquet(path, columns=["duoarea"])
    except (KeyError, OSError, ValueError):
        return False
    return "duoarea" in frame and frame["duoarea"].eq(region).all()


def aggregate_price_to_weeks(daily_price: pd.DataFrame, weekly_dates: pd.Series) -> pd.DataFrame:
    """Compute average daily spot price during each storage week ending on Friday."""
    records = []
    for date in weekly_dates:
        start = date - pd.Timedelta(days=6)
        week_prices = daily_price[(daily_price["period"] >= start) & (daily_price["period"] <= date)]
        if not week_prices.empty:
            avg_price = week_prices["value"].mean()
        else:
            avg_price = np.nan
        records.append({"period": date, "value": avg_price})
    return pd.DataFrame(records)

def run_balance_pipeline(
    region: str,
    *,
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
    api_key: str | None = None,
    force_refresh: bool = False,
) -> Path:
    """
    Downloads, models, and saves the weekly supply-demand balance sheet for a region.
    """
    processed_dir = Path(processed_dir)
    slug = region_slug(region)
    states = list(region_states(region))

    # 1. Fetch raw datasets
    print(f"Fetching monthly EIA state-level data for {len(states)} states in region {region}...")
    monthly_raw = get_monthly_state_data(api_key, states, force_refresh=force_refresh)

    print("Fetching daily Henry Hub spot prices...")
    daily_price = get_daily_spot_price(api_key, force_refresh=force_refresh)

    # 2. Check if daily weather, weekly weather, or weekly storage exist, and run core pipeline if not
    weather_daily_path = latest_processed_path(region, "daily_weather", processed_dir)
    weather_weekly_path = latest_processed_path(region, "weekly_weather", processed_dir)
    storage_weekly_path = latest_processed_path(region, "weekly_storage", processed_dir)

    core_paths = (weather_daily_path, weather_weekly_path, storage_weekly_path)
    if not all(_artifact_matches_region(path, region) for path in core_paths):
        print(
            f"Missing or mismatched core data files for region {region}. "
            "Running the core data pipeline..."
        )
        from gas_forecast.pipelines.data import run_data_pipeline
        run_data_pipeline(region, api_key=api_key, processed_dir=processed_dir)

    # 3. Load daily regional weather
    daily_weather = pd.read_parquet(weather_daily_path)
    daily_weather["date"] = pd.to_datetime(daily_weather["date"])

    # 4. Load weekly regional weather
    weekly_weather = pd.read_parquet(weather_weekly_path)
    weekly_weather["date"] = pd.to_datetime(weekly_weather["date"])

    # 5. Load weekly storage changes
    weekly_storage = pd.read_parquet(storage_weekly_path)
    weekly_storage["date"] = pd.to_datetime(weekly_storage["date"])

    # 5. Fit disaggregation model
    print("Fitting weather & price disaggregation regressions on monthly data...")
    disagg = StructuralDisaggregator()
    disagg.fit(
        monthly_df=monthly_raw,
        daily_weather=daily_weather,
        daily_price=daily_price,
        states=states,
    )

    # 6. Align daily prices to weekly storage weeks
    print("Aggregating spot prices to weekly storage periods...")
    weekly_price = aggregate_price_to_weeks(daily_price, weekly_weather["date"])

    # 7. Predict weekly supply/demand components
    print("Predicting weekly components and calculating net regional balances...")
    weekly_balance = disagg.predict_weekly(weekly_weather, weekly_price)

    # 8. Merge actual storage and calculate net inflow / balancing discrepancy
    weekly_storage_clean = weekly_storage[["date", "weekly_change_bcf", "storage_bcf"]].copy()
    final_df = weekly_balance.merge(weekly_storage_clean, on="date", how="inner")

    # Net inflow/trade/balancing = Storage change - Local Balance
    final_df["net_inflow_balancing"] = final_df["weekly_change_bcf"] - final_df["local_balance"]

    # 9. Save output parquet file
    output_filename = f"{slug}_weekly_supply_demand_balance"
    saved_path = save_versioned_parquet(
        final_df,
        processed_dir,
        output_filename,
        save_latest=True,
    )
    print(f"Successfully saved balance sheet to: {saved_path}")
    return saved_path
