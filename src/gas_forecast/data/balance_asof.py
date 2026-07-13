"""Point-in-time feature construction for weekly supply-demand balance data."""

from __future__ import annotations

import numpy as np
import pandas as pd


BALANCE_ASOF_FEATURE_COLUMNS = (
    "local_balance_lag1",
    "net_inflow_balancing_lag1",
    "net_inflow_balancing_rolling_4wk",
)

_BALANCE_VALUE_COLUMNS = (
    "local_balance",
    "net_inflow_balancing",
)

_BALANCE_VINTAGE_COLUMNS = (
    "date",
    "duoarea",
    "available_at",
    *_BALANCE_VALUE_COLUMNS,
)


def _as_utc_timestamp(value: object) -> pd.Timestamp:
    """Return one timestamp in UTC for point-in-time comparisons."""
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError("A valid as-of timestamp is required.")
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def validate_balance_vintages(balance_vintages: pd.DataFrame) -> pd.DataFrame:
    """Validate a weekly regional balance table with explicit availability times."""
    missing = sorted(set(_BALANCE_VINTAGE_COLUMNS) - set(balance_vintages.columns))
    if missing:
        raise ValueError(f"Balance vintages missing required columns: {missing}")

    data = balance_vintages.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    data["available_at"] = pd.to_datetime(
        data["available_at"],
        errors="coerce",
        utc=True,
    )
    if data["date"].isna().any():
        raise ValueError("Balance vintages contain invalid source dates.")
    if data["available_at"].isna().any():
        raise ValueError("Balance vintages contain invalid available_at timestamps.")
    if data["duoarea"].isna().any() or data["duoarea"].astype(str).eq("").any():
        raise ValueError("Balance vintages require a non-empty duoarea on every row.")

    for column in _BALANCE_VALUE_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any():
            raise ValueError(f"Balance vintages contain missing {column!r} values.")

    if data.duplicated(subset=["date", "duoarea", "available_at"]).any():
        raise ValueError(
            "Balance vintages contain duplicate (date, duoarea, available_at) rows."
        )

    return data.sort_values(["duoarea", "date", "available_at"]).reset_index(drop=True)


def latest_balance_as_of(
    balance_vintages: pd.DataFrame,
    as_of: str | pd.Timestamp,
    *,
    region: str | None = None,
) -> pd.DataFrame:
    """Return the most recent revision for each balance week known at ``as_of``."""
    data = validate_balance_vintages(balance_vintages)
    available = data.loc[data["available_at"] <= _as_utc_timestamp(as_of)].copy()
    if region is not None:
        available = available.loc[available["duoarea"] == region].copy()

    selected = available.sort_values("available_at").drop_duplicates(
        subset=["date", "duoarea"],
        keep="last",
    )
    return selected.sort_values(["duoarea", "date"]).reset_index(drop=True)


def _prepare_origins(
    origins: pd.DataFrame,
    *,
    as_of_col: str | None,
) -> pd.DataFrame:
    """Return one normalized regional forecast origin per target week."""
    required = {"date", "duoarea"}
    if as_of_col is not None:
        required.add(as_of_col)
    missing = sorted(required - set(origins.columns))
    if missing:
        raise ValueError(f"Balance feature origins missing required columns: {missing}")

    data = origins.loc[:, list(required)].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    if data["date"].isna().any():
        raise ValueError("Balance feature origins contain invalid dates.")
    if data["duoarea"].isna().any() or data["duoarea"].astype(str).eq("").any():
        raise ValueError("Balance feature origins require a non-empty duoarea.")
    if data.duplicated(subset=["date", "duoarea"]).any():
        raise ValueError("Balance feature origins contain duplicate (date, duoarea) rows.")

    if as_of_col is None:
        # A date-only origin means the opening instant of that UTC day. Callers
        # with intraday availability data should supply an explicit as-of column.
        data["balance_as_of"] = pd.to_datetime(data["date"], utc=True)
    else:
        data["balance_as_of"] = pd.to_datetime(
            data[as_of_col],
            errors="coerce",
            utc=True,
        )
        if data["balance_as_of"].isna().any():
            raise ValueError(f"Balance feature origins contain invalid {as_of_col!r} values.")

    return data.sort_values(["duoarea", "date"]).reset_index(drop=True)


def build_asof_balance_features(
    origins: pd.DataFrame,
    balance_vintages: pd.DataFrame,
    *,
    as_of_col: str | None = None,
) -> pd.DataFrame:
    """Build lagged balance features using only vintages known at each origin.

    The output is keyed by ``(date, duoarea)`` and can be merged into the main
    weekly model table. The four-week rolling feature is populated only when all
    four source weeks were available at the origin, matching the base feature
    table's strict four-week rolling-window behavior.
    """
    vintage_data = validate_balance_vintages(balance_vintages)
    origin_data = _prepare_origins(origins, as_of_col=as_of_col)

    records: list[dict[str, object]] = []
    for origin in origin_data.itertuples(index=False):
        target_date = pd.Timestamp(origin.date)
        as_of = _as_utc_timestamp(origin.balance_as_of)
        available = vintage_data.loc[
            (vintage_data["duoarea"] == origin.duoarea)
            & (vintage_data["available_at"] <= as_of)
        ]
        latest = available.sort_values("available_at").drop_duplicates(
            subset="date",
            keep="last",
        )
        known_by_date = latest.set_index("date")

        source_dates = [target_date - pd.Timedelta(weeks=lag) for lag in range(1, 5)]
        source_rows = [
            known_by_date.loc[source_date]
            if source_date in known_by_date.index
            else None
            for source_date in source_dates
        ]
        lag1 = source_rows[0]
        complete_window = all(row is not None for row in source_rows)
        records.append(
            {
                "date": target_date,
                "duoarea": origin.duoarea,
                "balance_as_of": as_of,
                "local_balance_lag1": (
                    float(lag1["local_balance"]) if lag1 is not None else np.nan
                ),
                "net_inflow_balancing_lag1": (
                    float(lag1["net_inflow_balancing"])
                    if lag1 is not None
                    else np.nan
                ),
                "net_inflow_balancing_rolling_4wk": (
                    float(
                        np.mean(
                            [
                                float(row["net_inflow_balancing"])
                                for row in source_rows
                                if row is not None
                            ]
                        )
                    )
                    if complete_window
                    else np.nan
                ),
                "balance_history_weeks": sum(row is not None for row in source_rows),
                "balance_lag1_source_date": source_dates[0] if lag1 is not None else pd.NaT,
                "balance_lag1_available_at": (
                    lag1["available_at"] if lag1 is not None else pd.NaT
                ),
                "balance_rolling_4wk_latest_available_at": (
                    max(row["available_at"] for row in source_rows if row is not None)
                    if complete_window
                    else pd.NaT
                ),
            }
        )

    return pd.DataFrame(records).sort_values(["duoarea", "date"]).reset_index(drop=True)
