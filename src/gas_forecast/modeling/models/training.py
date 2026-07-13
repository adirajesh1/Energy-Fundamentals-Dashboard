from __future__ import annotations

import pandas as pd


def select_training_history(
    storage: pd.DataFrame,
    *,
    lookback_years: int | None = None,
) -> pd.DataFrame:
    """Return the supplied history, optionally limited to recent calendar years.

    Model classes must only fit on the rows passed to them. Holdout selection
    belongs to the evaluator or backtest runner, which keeps the fit contract
    explicit and prevents a second, implicit holdout inside individual models.
    """
    required_columns = {"date", "year", "weekly_change_bcf"}
    missing = required_columns - set(storage.columns)
    if missing:
        raise ValueError(f"Storage is missing required columns: {sorted(missing)}")

    history = storage.copy().sort_values("date")
    if history.empty:
        raise ValueError("Cannot fit a forecast model with no historical rows.")

    if lookback_years is None:
        return history
    if lookback_years < 1:
        raise ValueError("lookback_years must be at least 1.")

    latest_year = int(history["year"].max())
    first_year = latest_year - lookback_years + 1
    return history.loc[history["year"] >= first_year].copy()
