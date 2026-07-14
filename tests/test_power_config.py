from __future__ import annotations

import os

from power_forecast.config import load_local_env


def test_load_local_env_reads_values_without_overriding_existing(tmp_path, monkeypatch):
    env_path = tmp_path / "local.env"
    env_path.write_text(
        "# credentials\nERCOT_SUBSCRIPTION_KEY='from-file'\nERCOT_ID_TOKEN=token-value\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ERCOT_SUBSCRIPTION_KEY", "from-process")
    monkeypatch.delenv("ERCOT_ID_TOKEN", raising=False)

    load_local_env([env_path])

    assert os.environ["ERCOT_SUBSCRIPTION_KEY"] == "from-process"
    assert os.environ["ERCOT_ID_TOKEN"] == "token-value"
