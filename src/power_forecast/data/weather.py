from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests

from power_forecast.schemas import ERCOT_GEOGRAPHY, find_column


WEATHER_FEATURE_COLUMNS = (
    "temperature_f",
    "wind_speed_100m_mph",
    "shortwave_radiation_wm2",
    "cloud_cover_pct",
)

ERCOT_WEATHER_POINTS = (
    # Population/load-center approximation for a system-wide public-data MVP.
    (32.7767, -96.7970, 0.27),  # Dallas-Fort Worth
    (29.7604, -95.3698, 0.25),  # Houston
    (30.2672, -97.7431, 0.18),  # Austin
    (29.4241, -98.4936, 0.16),  # San Antonio
    (33.5779, -101.8552, 0.08),  # West Texas wind region
    (26.2034, -98.2300, 0.06),  # Rio Grande Valley
)


def normalize_weather_forecasts(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize an archived, issued-at weather forecast table."""
    valid_col = find_column(frame, ["valid_at", "delivery_hour", "time", "datetime"])
    issued_col = find_column(frame, ["issued_at", "run_time", "initialization_time"])
    result = pd.DataFrame()
    result["valid_at"] = pd.to_datetime(frame[valid_col], utc=True, errors="coerce")
    result["issued_at"] = pd.to_datetime(frame[issued_col], utc=True, errors="coerce")
    if result[["valid_at", "issued_at"]].isna().any().any():
        raise ValueError("Weather forecasts require valid UTC issue and delivery times.")
    aliases = {
        "temperature_f": ["temperature_f", "temperature_2m_f", "temperature_2m"],
        "wind_speed_100m_mph": ["wind_speed_100m_mph", "wind_speed_100m"],
        "shortwave_radiation_wm2": ["shortwave_radiation_wm2", "shortwave_radiation"],
        "cloud_cover_pct": ["cloud_cover_pct", "cloud_cover"],
    }
    for output, candidates in aliases.items():
        column = find_column(frame, candidates, required=False)
        result[output] = pd.to_numeric(frame[column], errors="coerce") if column else 0.0
    result["geography"] = ERCOT_GEOGRAPHY
    return result.sort_values(["issued_at", "valid_at"]).reset_index(drop=True)


@dataclass
class OpenMeteoForecastClient:
    """Collect a population/load-center-weighted ERCOT weather forecast."""

    base_url: str = "https://api.open-meteo.com/v1/forecast"
    timeout: float = 30.0

    def fetch_ercot_forecast(self, *, issued_at: object | None = None) -> pd.DataFrame:
        issue = pd.Timestamp.now(tz="UTC") if issued_at is None else pd.Timestamp(issued_at)
        issue = issue.tz_localize("UTC") if issue.tzinfo is None else issue.tz_convert("UTC")
        weighted: list[pd.DataFrame] = []
        for latitude, longitude, weight in ERCOT_WEATHER_POINTS:
            response = requests.get(
                self.base_url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "hourly": "temperature_2m,wind_speed_100m,shortwave_radiation,cloud_cover",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "timezone": "UTC",
                    "forecast_days": 8,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            hourly = response.json().get("hourly", {})
            point = pd.DataFrame(
                {
                    "valid_at": pd.to_datetime(hourly.get("time", []), utc=True),
                    "temperature_f": hourly.get("temperature_2m", []),
                    "wind_speed_100m_mph": hourly.get("wind_speed_100m", []),
                    "shortwave_radiation_wm2": hourly.get("shortwave_radiation", []),
                    "cloud_cover_pct": hourly.get("cloud_cover", []),
                }
            )
            for column in WEATHER_FEATURE_COLUMNS:
                point[column] = pd.to_numeric(point[column], errors="coerce") * weight
            weighted.append(point)
        combined = pd.concat(weighted, ignore_index=True)
        result = combined.groupby("valid_at", as_index=False)[list(WEATHER_FEATURE_COLUMNS)].sum()
        result["issued_at"] = issue
        result["geography"] = ERCOT_GEOGRAPHY
        return result
