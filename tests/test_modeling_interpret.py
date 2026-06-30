import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from gas_forecast.modeling.interpret import permutation_importance_table


def test_permutation_importance_table_returns_sorted_feature_importance():
    X = pd.DataFrame(
        {
            "signal": [0, 1, 2, 3, 4, 5],
            "noise": [1, 1, 1, 1, 1, 1],
        }
    )
    y = pd.Series([0, 2, 4, 6, 8, 10])
    model = RandomForestRegressor(n_estimators=20, random_state=42).fit(X, y)

    importance = permutation_importance_table(
        model,
        X,
        y,
        n_repeats=3,
        random_state=42,
    )

    assert importance["feature"].tolist() == ["signal", "noise"]
    assert {"feature", "importance_mean", "importance_std"}.issubset(
        importance.columns
    )
