from __future__ import annotations

from pathlib import Path
import os

from gas_forecast.data.cache import DEFAULT_CACHE_DIR
from gas_forecast.data.regions import region_slug

DEFAULT_PROCESSED_DIR = Path("datasets/processed")
DEFAULT_LEGACY_WEATHER_CACHE_DIR = Path("datasets/raw/weather_cache")


def weather_cache_dir(cache_dir: str | Path = DEFAULT_CACHE_DIR) -> Path:
    """Return the per-state weather incremental cache directory."""
    return Path(cache_dir) / "weather"


def latest_processed_path(
    region: str,
    dataset: str,
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
) -> Path:
    """Return the latest processed parquet path for a region and dataset name."""
    slug = region_slug(region)
    return Path(processed_dir) / f"{slug}_{dataset}_latest.parquet"


def resolve_api_key(api_key: str | None = None) -> str:
    """
    Resolve the EIA API key from parameters, env, or dotenv files.
    
    Args:
        api_key: Optional API key passed by the caller.
        
    Returns:
        The resolved API key string.
        
    Raises:
        ValueError: If no API key is found.
    """
    if api_key:
        return api_key
    try:
        from dotenv import load_dotenv
        load_dotenv("local.env")
        load_dotenv("notebooks/local.env")
    except ImportError:
        pass
    resolved = os.getenv("EIA_API_KEY")
    if not resolved:
        raise ValueError(
            "EIA API key required. Pass api_key= or set EIA_API_KEY in the "
            "environment (optionally via local.env or notebooks/local.env)."
        )
    return resolved
