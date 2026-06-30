from __future__ import annotations

import pandas as pd
from sklearn.inspection import permutation_importance


def permutation_importance_table(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    n_repeats: int = 10,
    random_state: int = 42,
    scoring: str = "neg_mean_absolute_error",
) -> pd.DataFrame:
    """Return a sorted permutation-importance table for a fitted model."""
    result = permutation_importance(
        model,
        X,
        y,
        n_repeats=n_repeats,
        random_state=random_state,
        scoring=scoring,
    )
    return (
        pd.DataFrame(
            {
                "feature": X.columns,
                "importance_mean": result.importances_mean,
                "importance_std": result.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )
