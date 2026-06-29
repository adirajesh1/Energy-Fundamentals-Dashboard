from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

def save_versioned_parquet(
    df: pd.DataFrame,
    output_dir: str | Path,
    dataset_name: str | None = None,
    save_latest: bool = True,
) -> Path:
    """Save timestamped and optionally latest Parquet files.

    If dataset_name is not provided, use a string based on the input DataFrame's object id.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Use dataset_name or fall back to a DataFrame ID
    if dataset_name is None or dataset_name == "":
        dataset_base = f"df_{id(df)}"
    else:
        dataset_base = dataset_name

    versioned_path = output_dir / f"{dataset_base}_{timestamp}.parquet"
    df.to_parquet(versioned_path, index=False)

    if save_latest:
        latest_path = output_dir / f"{dataset_base}_latest.parquet"
        df.to_parquet(latest_path, index=False)

    return versioned_path