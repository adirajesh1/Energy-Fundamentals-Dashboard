from __future__ import annotations

import numpy as np


def _values(values) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(-1)


def mae(y_true, y_pred) -> float:
    return float(np.mean(np.abs(_values(y_true) - _values(y_pred))))


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((_values(y_true) - _values(y_pred)) ** 2)))


def bias(y_true, y_pred) -> float:
    return float(np.mean(_values(y_pred) - _values(y_true)))
