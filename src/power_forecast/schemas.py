from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

import pandas as pd


ERCOT_GEOGRAPHY = "ERCOT"
VINTAGE_COLUMNS = (
    "source",
    "product_id",
    "issued_at",
    "retrieved_at",
    "valid_at",
    "geography",
    "source_hash",
)


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_column(
    frame: pd.DataFrame,
    aliases: Iterable[str],
    *,
    required: bool = True,
) -> str | None:
    lookup = {normalized_name(column): column for column in frame.columns}
    for alias in aliases:
        column = lookup.get(normalized_name(alias))
        if column is not None:
            return column
    if required:
        raise ValueError(f"None of the expected columns were found: {list(aliases)}")
    return None


def frame_hash(frame: pd.DataFrame) -> str:
    """Stable content hash used for publication provenance."""
    payload = frame.to_json(orient="split", date_format="iso", index=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def payload_hash(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def as_utc_series(values: pd.Series, *, name: str) -> pd.Series:
    result = pd.to_datetime(values, utc=True, errors="coerce")
    if result.isna().any():
        raise ValueError(f"Invalid timestamps in {name!r}.")
    return result


def validate_vintage_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(VINTAGE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Power vintage data missing required columns: {missing}")
    data = frame.copy()
    for column in ("issued_at", "retrieved_at", "valid_at"):
        data[column] = as_utc_series(data[column], name=column)
    if (data["issued_at"] > data["retrieved_at"]).any():
        raise ValueError("issued_at cannot be later than retrieved_at.")
    if data[["source", "product_id", "geography", "source_hash"]].isna().any().any():
        raise ValueError("Vintage provenance fields cannot be null.")
    return data.sort_values(["product_id", "issued_at", "valid_at"]).reset_index(drop=True)


def horizon_bucket(hours: pd.Series | int) -> pd.Series | str:
    def label(value: int) -> str:
        if value <= 24:
            return "h001_024"
        if value <= 72:
            return "h025_072"
        return "h073_168"

    if isinstance(hours, pd.Series):
        return hours.astype(int).map(label)
    return label(int(hours))
