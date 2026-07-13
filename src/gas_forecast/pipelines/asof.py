"""Pipelines that materialize point-in-time forecasting inputs from vintages."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from gas_forecast.data.balance_asof import build_asof_balance_features
from gas_forecast.data.export import save_versioned_parquet
from gas_forecast.data.paths import DEFAULT_PROCESSED_DIR, latest_processed_path
from gas_forecast.data.regions import region_slug
from gas_forecast.data.weather_scenarios import select_weather_scenario_as_of


def _load_origins(
    region: str,
    *,
    processed_dir: Path,
    origins_path: str | Path | None,
) -> pd.DataFrame:
    """Load and scope model-table forecast origins to one storage region."""
    path = (
        Path(origins_path)
        if origins_path is not None
        else latest_processed_path(region, "weekly_model_features", processed_dir)
    )
    if not path.exists():
        raise FileNotFoundError(f"Missing balance feature origins: {path}")

    origins = pd.read_parquet(path)
    if "duoarea" not in origins.columns:
        raise ValueError(f"Balance feature origins in {path} are missing 'duoarea'.")
    scoped = origins.loc[origins["duoarea"] == region].copy()
    if scoped.empty:
        raise ValueError(f"No origins for region {region!r} were found in {path}.")
    return scoped


def run_weather_scenario_pipeline(
    region: str,
    *,
    scenarios_path: str | Path,
    as_of: str | pd.Timestamp,
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
) -> Path:
    """Select and save the weather forecast version available at one origin."""
    scenarios_path = Path(scenarios_path)
    if not scenarios_path.exists():
        raise FileNotFoundError(f"Missing weather scenario archive: {scenarios_path}")

    selected = select_weather_scenario_as_of(
        pd.read_parquet(scenarios_path),
        as_of,
        region=region,
    )
    if selected.empty:
        raise ValueError(
            f"No weather scenarios for {region!r} were available at {as_of!r}."
        )

    return save_versioned_parquet(
        selected,
        processed_dir,
        f"{region_slug(region)}_weekly_weather_scenario",
        save_latest=True,
    )


def run_asof_balance_pipeline(
    region: str,
    *,
    vintages_path: str | Path,
    origins_path: str | Path | None = None,
    as_of_col: str | None = "date",
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
) -> Path:
    """Build and save point-in-time balance lag features for a storage region.

    The input vintages must retain every historical version and its real
    ``available_at`` timestamp. The retrospective balance artifact produced by
    ``gas-data balance`` is not a substitute for that archive.
    """
    vintages_path = Path(vintages_path)
    if not vintages_path.exists():
        raise FileNotFoundError(f"Missing balance vintage archive: {vintages_path}")

    processed_dir = Path(processed_dir)
    origins = _load_origins(
        region,
        processed_dir=processed_dir,
        origins_path=origins_path,
    )
    vintages = pd.read_parquet(vintages_path)
    if "duoarea" in vintages.columns and not vintages["duoarea"].eq(region).any():
        raise ValueError(
            f"No balance vintages for region {region!r} were found in {vintages_path}."
        )
    features = build_asof_balance_features(
        origins,
        vintages,
        as_of_col=as_of_col,
    )
    return save_versioned_parquet(
        features,
        processed_dir,
        f"{region_slug(region)}_weekly_asof_balance_features",
        save_latest=True,
    )
