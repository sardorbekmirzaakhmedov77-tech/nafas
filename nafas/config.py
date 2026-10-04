import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _database_url():
    url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'nafas.db'}")
    # Hosting providers often hand out "postgres://" URLs; SQLAlchemy needs the driver named.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uzbekistan uses a single time zone, so every reading is stored in local time.
    TIMEZONE = "Asia/Tashkent"

    # Data source
    OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
    HISTORY_DAYS = int(os.environ.get("HISTORY_DAYS", 31))
    FORECAST_DAYS = int(os.environ.get("FORECAST_DAYS", 4))

    # DEMO_MODE fills the database with realistic generated data instead of
    # calling the API. Useful offline, in CI, and for screenshots.
    DEMO_MODE = _bool("DEMO_MODE", False)

    # Background jobs: hourly data refresh + alert checks.
    ENABLE_SCHEDULER = _bool("ENABLE_SCHEDULER", True)

    # Alerts: an episode closes once AQI falls this far below the threshold,
    # so a value hovering around the line doesn't send an email every hour.
    ALERT_HYSTERESIS = 10

    # Email (optional). Without MAIL_SERVER, emails are printed to the log.
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_FROM = os.environ.get("MAIL_FROM", "Nafas <alerts@nafas.local>")
    SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    DEMO_MODE = True
    ENABLE_SCHEDULER = False
    SECRET_KEY = "test"
