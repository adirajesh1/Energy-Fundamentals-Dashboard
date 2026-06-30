from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


def _as_1d_float_array(values) -> np.ndarray:
    return np.asarray(values, dtype="float64").ravel()


def mae(y_true, y_pred) -> float:
    """Return mean absolute error."""
    return float(mean_absolute_error(_as_1d_float_array(y_true), _as_1d_float_array(y_pred)))


def rmse(y_true, y_pred) -> float:
    """Return root mean squared error."""
    return float(root_mean_squared_error(_as_1d_float_array(y_true), _as_1d_float_array(y_pred)))


def bias(y_true, y_pred) -> float:
    """Return average forecast error, actual minus predicted."""
    true = _as_1d_float_array(y_true)
    pred = _as_1d_float_array(y_pred)
    return float((true - pred).mean())
