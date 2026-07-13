import pandas as pd
import pytest

from gas_forecast.modeling.models import FiveYearWeeklyAverageModel


def test_legacy_model_fit_uses_the_history_it_receives():
    storage = pd.DataFrame(
        {
            "date": pd.to_datetime(["2019-01-04", "2020-01-03", "2021-01-01"]),
            "year": [2019, 2020, 2021],
            "week_of_year": [1, 1, 1],
            "weekly_change_bcf": [10.0, 20.0, 30.0],
        }
    )

    model = FiveYearWeeklyAverageModel(lookback_years=2).fit(storage)
    prediction = model.predict(pd.DataFrame({"week_of_year": [1]}))

    assert prediction.loc[0, "predicted_weekly_change"] == pytest.approx(25.0)
