from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

def save_versioned_parquet(
    df: pd.DataFrame,
    output_dir: str | Path,
    dataset_name: str,
    save_latest: bool = True,
) -> Path:
    """Save timestamped and optionally latest Parquet files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    versioned_path = output_dir / f"{dataset_name}_{timestamp}.parquet"

    df.to_parquet(versioned_path, index=False)

    if save_latest:
        latest_path = output_dir / f"{dataset_name}_latest.parquet"
        df.to_parquet(latest_path, index=False)

    return versioned_path