from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def _utc(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def select_as_of(
    frame: pd.DataFrame,
    origin: object,
    *,
    entity_keys: Sequence[str],
    valid_time_col: str = "valid_at",
    issued_time_col: str = "issued_at",
    retrieved_time_col: str | None = "retrieved_at",
    required_valid_times: Sequence[object] | None = None,
) -> pd.DataFrame:
    """Select the latest version of each entity known at a forecast origin."""
    required = {*entity_keys, valid_time_col, issued_time_col}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"As-of data missing required columns: {missing}")
    data = frame.copy()
    data[valid_time_col] = pd.to_datetime(data[valid_time_col], utc=True, errors="coerce")
    data[issued_time_col] = pd.to_datetime(data[issued_time_col], utc=True, errors="coerce")
    if data[[valid_time_col, issued_time_col]].isna().any().any():
        raise ValueError("As-of data contains invalid valid or issued timestamps.")
    origin_utc = _utc(origin)
    data = data.loc[data[issued_time_col] <= origin_utc].copy()
    sort_columns = [issued_time_col]
    if retrieved_time_col is not None and retrieved_time_col in data:
        data[retrieved_time_col] = pd.to_datetime(
            data[retrieved_time_col], utc=True, errors="coerce"
        )
        if data[retrieved_time_col].isna().any():
            raise ValueError("As-of data contains invalid retrieval timestamps.")
        data = data.loc[data[retrieved_time_col] <= origin_utc].copy()
        sort_columns.append(retrieved_time_col)
    if required_valid_times is not None:
        required_times = pd.DatetimeIndex(
            pd.to_datetime(list(required_valid_times), utc=True)
        )
        data = data.loc[data[valid_time_col].isin(required_times)]
    keys = [*entity_keys, valid_time_col]
    selected = (
        data.sort_values(sort_columns)
        .drop_duplicates(subset=keys, keep="last")
        .sort_values(keys)
        .reset_index(drop=True)
    )
    if required_valid_times is not None:
        present = pd.DatetimeIndex(selected[valid_time_col].unique())
        missing_times = required_times.difference(present)
        if len(missing_times):
            formatted = [value.isoformat() for value in missing_times[:5]]
            raise ValueError(f"No eligible vintage for required valid times: {formatted}")
    return selected
