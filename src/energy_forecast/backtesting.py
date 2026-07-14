from __future__ import annotations

from sklearn.base import clone
import pandas as pd

from energy_forecast.evaluation import bias, mae, rmse


def run_backtest(
    frame: pd.DataFrame,
    *,
    feature_cols: list[str],
    target_col: str,
    time_col: str,
    model,
    splitter,
    prediction_col: str = "prediction",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run estimator-agnostic rolling backtests on prebuilt features."""
    required = {time_col, target_col, *feature_cols}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Backtest data missing required columns: {missing}")
    predictions: list[pd.DataFrame] = []
    metrics: list[dict[str, float | int]] = []
    for fold, (train_idx, val_idx) in enumerate(splitter.split(frame), start=1):
        train = frame.loc[train_idx].dropna(subset=[target_col, *feature_cols])
        val = frame.loc[val_idx].dropna(subset=[target_col, *feature_cols])
        if train.empty or val.empty:
            continue
        fitted = clone(model).fit(train[feature_cols], train[target_col])
        predicted = fitted.predict(val[feature_cols])
        output = val[[time_col, target_col]].copy()
        output[prediction_col] = predicted
        output["fold"] = fold
        predictions.append(output)
        metrics.append(
            {
                "fold": fold,
                "mae": mae(output[target_col], predicted),
                "rmse": rmse(output[target_col], predicted),
                "bias": bias(output[target_col], predicted),
                "n_samples": len(output),
            }
        )
    if not predictions:
        return pd.DataFrame(), pd.DataFrame()
    result = pd.concat(predictions, ignore_index=True)
    metrics.append(
        {
            "fold": "overall",
            "mae": mae(result[target_col], result[prediction_col]),
            "rmse": rmse(result[target_col], result[prediction_col]),
            "bias": bias(result[target_col], result[prediction_col]),
            "n_samples": len(result),
        }
    )
    return result, pd.DataFrame(metrics)
