# Rebuild the weather table in the new catalog from the raw files in the bucket
from pathlib import PurePosixPath

from . import config, lake


def main():
    con = lake.connect()
    con.execute(lake.CREATE_TABLE)

    # the path holds year/month/day, so sorting the names puts the oldest first
    pattern = f"s3://{config.B2_BUCKET}/raw/weather/**/*.parquet"
    files = sorted(row[0] for row in con.execute(f"select file from glob('{pattern}')").fetchall())
    print(f"found {len(files)} raw files")

    columns = ", ".join(lake.COLUMNS)
    for path in files:
        name = PurePosixPath(path).name

        # skip a file that is already in the new table, so the script can be run again safely
        already = con.execute(
            "select count(*) from weather_lake.weather_observations where source_file = ?", [name]
        ).fetchone()[0]
        if already:
            continue

        con.execute(f"""
            insert into weather_lake.weather_observations ({columns}, source_file)
            select {columns}, '{name}' as source_file
            from read_parquet('{path}')
        """)
        print(f"replayed {name}")

    con.execute("detach weather_lake")
    con.close()


if __name__ == "__main__":
    main()