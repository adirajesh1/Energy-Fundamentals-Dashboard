from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import pandas as pd


IndexSplit = tuple[list[int], list[int]]


@dataclass(frozen=True)
class RollingOriginSplitter:
    """Frequency-agnostic rolling-origin splitter using exact timestamps."""

    time_col: str
    initial_train_end: object
    validation_horizon: object
    step: object
    train_start: object | None = None
    lookback: object | None = None
    embargo: object = pd.Timedelta(0)

    def split(self, frame: pd.DataFrame) -> Iterator[IndexSplit]:
        if self.time_col not in frame:
            raise ValueError(f"Missing time column {self.time_col!r}.")
        times = pd.to_datetime(frame[self.time_col], utc=True, errors="coerce")
        if times.isna().any():
            raise ValueError("RollingOriginSplitter found invalid timestamps.")
        horizon = pd.Timedelta(self.validation_horizon)
        step = pd.Timedelta(self.step)
        embargo = pd.Timedelta(self.embargo)
        if horizon <= pd.Timedelta(0) or step <= pd.Timedelta(0):
            raise ValueError("validation_horizon and step must be positive.")
        train_end = pd.Timestamp(self.initial_train_end)
        train_end = train_end.tz_localize("UTC") if train_end.tzinfo is None else train_end.tz_convert("UTC")
        explicit_start = None if self.train_start is None else pd.Timestamp(self.train_start)
        if explicit_start is not None:
            explicit_start = explicit_start.tz_localize("UTC") if explicit_start.tzinfo is None else explicit_start.tz_convert("UTC")
        lookback = None if self.lookback is None else pd.Timedelta(self.lookback)
        if lookback is not None and lookback <= pd.Timedelta(0):
            raise ValueError("lookback must be positive when supplied.")

        max_time = times.max()
        while True:
            val_start = train_end + embargo
            val_end = val_start + horizon
            if val_start > max_time:
                break
            lower = train_end - lookback if lookback is not None else explicit_start
            train_mask = times < train_end
            if lower is not None:
                train_mask &= times >= lower
            val_mask = (times >= val_start) & (times < val_end)
            train_idx = frame.index[train_mask].tolist()
            val_idx = frame.index[val_mask].tolist()
            if val_idx:
                if not train_idx:
                    raise ValueError("Rolling-origin split produced an empty training window.")
                yield train_idx, val_idx
            train_end += step
