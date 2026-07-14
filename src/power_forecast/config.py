from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


DEFAULT_ENV_PATHS = (Path("local.env"), Path("notebooks/local.env"))


def load_local_env(
    paths: Iterable[str | Path] = DEFAULT_ENV_PATHS,
    *,
    override: bool = False,
) -> None:
    """Load simple KEY=VALUE files without logging or returning secret values."""
    for candidate in paths:
        path = Path(candidate)
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or (not override and key in os.environ):
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value
