# Settings and secrets, all read from environment variables
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
COUNTIES_FILE = ROOT / "data" / "reference" / "counties.csv"

OWM_API_KEY = os.environ["OWM_API_KEY"]
B2_ENDPOINT = os.environ["B2_ENDPOINT"]
B2_KEY_ID = os.environ["B2_KEY_ID"]
B2_APP_KEY = os.environ["B2_APP_KEY"]
B2_BUCKET = os.environ["B2_BUCKET"]

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
PAUSE = 1.1       # seconds between calls (free plan allows 60 a minute)
MAX_TRIES = 3