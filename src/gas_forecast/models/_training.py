import pandas as pd


def holdout_training_frame(
    storage: pd.DataFrame,
    *,
    lookback_years: int | None = None,
) -> tuple[pd.DataFrame, int]:
    """Return rows strictly before the evaluation year (optionally windowed)."""
    eval_year = int(storage["year"].max())
    train = storage.loc[storage["year"] < eval_year].sort_values("date")
    if lookback_years is not None:
        train = train.loc[train["year"] >= eval_year - lookback_years]
    return train, eval_year
