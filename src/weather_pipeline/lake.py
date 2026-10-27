# The lakehouse: a DuckLake catalog file plus parquet data files, both kept in the bucket
import tempfile
from pathlib import Path
import duckdb
from . import config, storage

CATALOG_KEY = "catalog/weather.ducklake"

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
        temp_min double,
        temp_max double,
        pressure bigint,
        humidity bigint,
        sea_level double,
        ground_level double,
        visibility double,
        wind_speed double,
        wind_degree double,
        wind_gust double,
        cloudiness bigint,
        rain_1h double,
        sunrise_time timestamptz,
        sunset_time timestamptz,
        ingested_at timestamptz,
        source_file varchar
    )
"""

def connect(catalog_path, read_only=False):
    # Open DuckDB with the bucket credentials and attach the lakehouse
    host = config.B2_ENDPOINT.replace("https://", "")
    region = host.split(".")[1]            # e.g. us-west-004

    con = duckdb.connect()
    con.execute("install ducklake")
    con.execute("load ducklake")
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
    con.execute(f"attach 'ducklake:{Path(catalog_path).as_posix()}' as weather_lake ({options})")
    return con

def load(parquet_path):
    # Add one raw parquet file to the lakehouse table, then save the catalog back
    name = Path(parquet_path).name
    with tempfile.TemporaryDirectory() as tmp:
        catalog = Path(tmp) / "weather.ducklake"
        storage.download_if_exists(CATALOG_KEY, catalog)

        con = connect(catalog)
        con.execute(CREATE_TABLE)

        # skip a file that was already loaded (protects against reruns)
        already = con.execute(
            "select count(*) from weather_lake.weather_observations where source_file = ?", [name]
        ).fetchone()[0]
        if already:
            print(f"already loaded, skipping {name}")
        else:
            con.execute(f"""
                insert into weather_lake.weather_observations by name
                select *, '{name}' as source_file
                from read_parquet('{Path(parquet_path).as_posix()}')
            """)
            print(f"loaded {name} into the lakehouse")

        con.execute("detach weather_lake")
        con.close()
        storage.upload(catalog, CATALOG_KEY)    # save the updated catalog