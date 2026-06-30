import pytest
import pandas as pd

from gas_forecast.modeling.evaluate import bias, mae, rmse


def test_modeling_metrics_calculate_expected_values():
    y_true = [3.0, 5.0, 7.0]
    y_pred = [2.0, 5.0, 10.0]

    assert mae(y_true, y_pred) == pytest.approx(4 / 3)
    assert rmse(y_true, y_pred) == pytest.approx((10 / 3) ** 0.5)
    assert bias(y_true, y_pred) == pytest.approx(-2 / 3)


def test_modeling_metrics_ignore_pandas_index_alignment():
    y_true = pd.Series([3.0, 5.0, 7.0], index=[10, 11, 12])
    y_pred = pd.Series([2.0, 5.0, 10.0], index=[0, 1, 2])

    assert mae(y_true, y_pred) == pytest.approx(4 / 3)
    assert rmse(y_true, y_pred) == pytest.approx((10 / 3) ** 0.5)
    assert bias(y_true, y_pred) == pytest.approx(-2 / 3)
