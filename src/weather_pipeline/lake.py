# The lakehouse: DuckLake with its catalog in Supabase Postgres and its data files in the bucket
from pathlib import Path

import duckdb

from . import config

# Columns kept in the lakehouse table (raw files keep everything, so nothing is lost)
COLUMNS = [
    "county", "latitude", "longitude", "place_name", "country_code", "observed_at",
    "weather_id", "weather_main", "weather_description", "temperature", "feels_like",
    "pressure", "humidity", "ground_level", "visibility", "wind_speed", "wind_degree",
    "wind_gust", "cloudiness", "rain_1h", "ingested_at",
]

CREATE_TABLE = """
    create table if not exists weather_lake.weather_observations (
        county varchar,
        latitude double,
        longitude double,
        place_name varchar,
        country_code varchar,
        observed_at timestamptz,
        weather_id bigint,
        weather_main varchar,
        weather_description varchar,
        temperature double,
        feels_like double,
        pressure bigint,
        humidity bigint,
        ground_level double,
        visibility double,
        wind_speed double,
        wind_degree double,
        wind_gust double,
        cloudiness bigint,
        rain_1h double,
        ingested_at timestamptz,
        source_file varchar
    )
"""


def connect(read_only=False):
    # Open DuckDB with the bucket credentials and attach the lakehouse
    host = config.B2_ENDPOINT.replace("https://", "")
    region = host.split(".")[1]            # e.g. us-west-004

    con = duckdb.connect()
    for extension in ("ducklake", "postgres"):
        con.execute(f"install {extension}")
        con.execute(f"load {extension}")
    con.execute(f"""
        create or replace secret b2 (
            type s3, key_id '{config.B2_KEY_ID}', secret '{config.B2_APP_KEY}',
            endpoint '{host}', region '{region}', url_style 'path'
        )
    """)

    # limit 0 = always write real parquet files in the bucket
    options = f"data_path 's3://{config.B2_BUCKET}/lake/', data_inlining_row_limit 0"
    if read_only:
        options += ", read_only"
    con.execute(f"attach 'ducklake:postgres:{config.PG_CATALOG}' as weather_lake ({options})")
    return con


def load(parquet_path):
    # Add one raw parquet file to the lakehouse table
    name = Path(parquet_path).name
    con = connect()
    con.execute(CREATE_TABLE)

    # skip a file that was already loaded (protects against reruns)
    already = con.execute(
        "select count(*) from weather_lake.weather_observations where source_file = ?", [name]
    ).fetchone()[0]
    if already:
        print(f"already loaded, skipping {name}")
    else:
        columns = ", ".join(COLUMNS)
        con.execute(f"""
            insert into weather_lake.weather_observations ({columns}, source_file)
            select {columns}, '{name}' as source_file
            from read_parquet('{Path(parquet_path).as_posix()}')
        """)
        print(f"loaded {name} into the lakehouse")

    con.execute("detach weather_lake")
    con.close()