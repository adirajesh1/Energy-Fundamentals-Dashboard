import pandas as pd
import requests

from oil_forecast.data import eia


def test_weekly_crude_adapter_fetches_each_required_eia_series(monkeypatch):
    requested = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": {
                    "data": [
                        {"period": "2009-12-25", "value": "99"},
                        {"period": "2026-07-10", "value": "1"},
                    ]
                }
            }

    def fake_get(url, **kwargs):
        requested.append(url.rsplit("/", 1)[-1])
        return Response()

    monkeypatch.setattr(eia.requests, "get", fake_get)
    result = eia.fetch_weekly_crude_series("test-key")

    assert set(requested) == set(eia.EIA_WEEKLY_CRUDE_SERIES.values())
    assert set(result["component"]) == set(eia.EIA_WEEKLY_CRUDE_SERIES)
    assert pd.api.types.is_datetime64_any_dtype(result["period"])
    assert result["value"].eq(1.0).all()
    assert result["period"].min() >= pd.Timestamp("2010-01-01")


def test_weekly_crude_adapter_retries_transient_request_failure(monkeypatch):
    calls = 0

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": {"data": [{"period": "2026-07-10", "value": "1"}]}}

    def fake_get(url, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise requests.ConnectionError("temporary")
        return Response()

    monkeypatch.setattr(eia.requests, "get", fake_get)

    eia.fetch_weekly_crude_series("test-key")

    assert calls == len(eia.EIA_WEEKLY_CRUDE_SERIES) + 1
