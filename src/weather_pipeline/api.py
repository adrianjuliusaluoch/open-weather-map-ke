# Get current weather for each county by coordinates
import time
import pandas as pd
import requests
from . import config

# Columns that can be missing; forcing float keeps every parquet file's types the same
FLOAT_COLS = ["sea_level", "ground_level", "visibility", "wind_speed",
              "wind_degree", "wind_gust", "rain_1h"]

def parse(row, data):
    # Pick the fields we keep from one API response
    main = data["main"]
    wind = data.get("wind", {})
    sys_info = data.get("sys", {})
    return {
        "county": row.county,                      # our own label
        "latitude": row.latitude,
        "longitude": row.longitude,
        "place_name": data.get("name"),            # API's name, reference only
        "country_code": sys_info.get("country"),
        "observed_at": pd.to_datetime(data["dt"], unit="s", utc=True),
        "weather_id": data["weather"][0]["id"],
        "weather_main": data["weather"][0]["main"],
        "weather_description": data["weather"][0]["description"],
        "temperature": main["temp"],
        "feels_like": main["feels_like"],
        "temp_min": main["temp_min"],
        "temp_max": main["temp_max"],
        "pressure": main["pressure"],
        "humidity": main["humidity"],
        "sea_level": main.get("sea_level"),
        "ground_level": main.get("grnd_level"),
        "visibility": data.get("visibility"),
        "wind_speed": wind.get("speed"),
        "wind_degree": wind.get("deg"),
        "wind_gust": wind.get("gust"),
        "cloudiness": data.get("clouds", {}).get("all"),
        "rain_1h": data.get("rain", {}).get("1h"),
        "sunrise_time": pd.to_datetime(sys_info.get("sunrise"), unit="s", utc=True),
        "sunset_time": pd.to_datetime(sys_info.get("sunset"), unit="s", utc=True),
    }

def get_weather(row):
    # One call per county, retried if the API is busy
    params = {"lat": row.latitude, "lon": row.longitude,
              "appid": config.OWM_API_KEY, "units": "metric"}
    for attempt in range(config.MAX_TRIES):
        try:
            response = requests.get(config.WEATHER_URL, params=params, timeout=30)
        except requests.RequestException as e:
            print(f"{row.county}: {type(e).__name__}")   # type only, so the key never prints
        else:
            if response.status_code == 200:
                return parse(row, response.json())
            if response.status_code not in (429, 500, 502, 503, 504):
                print(f"{row.county}: HTTP {response.status_code}")
                return None
        time.sleep(2 ** (attempt + 1))
    print(f"{row.county}: gave up after {config.MAX_TRIES} tries")
    return None

def fetch_all(counties):
    # Loop over all counties, one at a time, gently
    readings = []
    for row in counties.itertuples():
        reading = get_weather(row)
        if reading:
            readings.append(reading)
        time.sleep(config.PAUSE)

    weather = pd.DataFrame(readings)
    if not weather.empty:
        weather[FLOAT_COLS] = weather[FLOAT_COLS].astype("float64")
    return weather