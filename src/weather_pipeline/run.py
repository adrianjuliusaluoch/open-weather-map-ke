# The pipeline: read counties, call the API, save one parquet file to the bucket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config
from .api import fetch_all
from .storage import upload


def main():
    run_time = datetime.now(timezone.utc)
    counties = pd.read_csv(config.COUNTIES_FILE)

    weather = fetch_all(counties)
    if weather.empty:
        raise SystemExit("No data came back, nothing uploaded")   # makes the run show as failed
    weather["ingested_at"] = run_time
    print(f"got {len(weather)} of {len(counties)} counties")

    # date folders (year/month/day) make the files easy to find and query later
    name = f"weather_{run_time:%Y%m%dT%H%M%SZ}.parquet"
    key = (f"raw/weather/year={run_time:%Y}/month={run_time:%m}/"
           f"day={run_time:%d}/{name}")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        weather.to_parquet(path, index=False)
        upload(path, key)
    print(f"uploaded {key}")


if __name__ == "__main__":
    main()