# The pipeline: call the API, save the raw file, add it to the lakehouse
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from . import config, lake, storage
from .api import fetch_all

def main():
    run_time = datetime.now(timezone.utc)
    counties = pd.read_csv(config.COUNTIES_FILE)

    weather = fetch_all(counties)
    if weather.empty:
        raise SystemExit("No data came back, nothing uploaded")   # makes the run show as failed
    weather["ingested_at"] = run_time
    print(f"got {len(weather)} of {len(counties)} counties")

    # raw layer: one parquet file per run, in date folders, so any run can be replayed
    name = f"weather_{run_time:%Y%m%dT%H%M%SZ}.parquet"
    key = f"raw/weather/year={run_time:%Y}/month={run_time:%m}/day={run_time:%d}/{name}"

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        weather.to_parquet(path, index=False)
        storage.upload(path, key)
        print(f"uploaded {key}")

        # lakehouse layer: the same file goes into the DuckLake table
        lake.load(path)

if __name__ == "__main__":
    main()