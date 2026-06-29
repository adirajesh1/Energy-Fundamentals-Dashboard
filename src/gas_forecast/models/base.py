from abc import ABC, abstractmethod

import pandas as pd


class WeeklyChangeForecastModel(ABC):
    """Interface for weekly storage change forecast models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable model name used in chart titles and legends."""

    @abstractmethod
    def fit(self, storage: pd.DataFrame) -> "WeeklyChangeForecastModel":
        """Train the model on historical storage data."""

    @abstractmethod
    def predict(self, evaluation: pd.DataFrame) -> pd.DataFrame:
        """
        Score rows in ``evaluation``.

        ``evaluation`` must include ``week_of_year``. Returned columns must
        include ``predicted_weekly_change`` and may include ``lower_band`` and
        ``upper_band`` for uncertainty visualization.
        """
