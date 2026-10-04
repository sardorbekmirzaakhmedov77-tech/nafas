"""Fetches hourly air-quality data from Open-Meteo and stores it.

Open-Meteo serves CAMS (Copernicus Atmosphere Monitoring Service) model data,
which covers every location, including cities without ground stations.
"""

import logging
import time
from datetime import datetime

import requests
from flask import current_app

from .extensions import db
from .models import City, Reading, utcnow

log = logging.getLogger(__name__)

API_FIELDS = {
    # Open-Meteo variable -> Reading column
    "us_aqi": "us_aqi",
    "pm2_5": "pm2_5",
    "pm10": "pm10",
    "nitrogen_dioxide": "nitrogen_dioxide",
    "ozone": "ozone",
    "sulphur_dioxide": "sulphur_dioxide",
    "carbon_monoxide": "carbon_monoxide",
}


class FetchError(Exception):
    pass


def fetch_city(city, past_days, session=None, retries=3):
    """Call the API for one city. Retries with exponential backoff."""
    cfg = current_app.config
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "hourly": ",".join(API_FIELDS),
        "past_days": past_days,
        "forecast_days": cfg["FORECAST_DAYS"],
        "timezone": cfg["TIMEZONE"],
    }
    http = session or requests
    last_error = None
    for attempt in range(retries):
        try:
            resp = http.get(cfg["OPEN_METEO_URL"], params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise FetchError(f"{city.slug}: {last_error}")


def parse_hourly(payload):
    """Turn Open-Meteo's column arrays into a list of row dicts."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    rows = []
    for i, stamp in enumerate(times):
        row = {"time": datetime.fromisoformat(stamp)}
        for api_name, column in API_FIELDS.items():
            values = hourly.get(api_name)
            row[column] = values[i] if values and i < len(values) else None
        if row["us_aqi"] is not None:
            row["us_aqi"] = round(row["us_aqi"])
        rows.append(row)
    return rows


def upsert_readings(city, rows):
    """Insert new hours and update existing ones (forecasts get revised)."""
    if not rows:
        return 0
    start, end = rows[0]["time"], rows[-1]["time"]
    existing = {r.time: r for r in city.readings.filter(Reading.time >= start,
                                                        Reading.time <= end)}
    for row in rows:
        reading = existing.get(row["time"])
        if reading is None:
            reading = Reading(city=city, time=row["time"])
            db.session.add(reading)
        for column in API_FIELDS.values():
            value = row.get(column)
            if value is not None or reading.id is None:
                setattr(reading, column, value)
    return len(rows)


def collect_all():
    """Refresh every city. One failing city never stops the others."""
    if current_app.config["DEMO_MODE"]:
        from .demo import seed_demo_data
        return seed_demo_data()

    summary = {"ok": [], "failed": []}
    with requests.Session() as session:
        for city in City.query.order_by(City.id).all():
            # First run backfills a month of history; later runs just top up.
            past_days = 2 if city.last_fetched_at else current_app.config["HISTORY_DAYS"]
            try:
                payload = fetch_city(city, past_days, session=session)
                count = upsert_readings(city, parse_hourly(payload))
                city.last_fetched_at = utcnow()
                db.session.commit()
                summary["ok"].append(city.slug)
                log.info("Collected %s hours for %s", count, city.slug)
            except FetchError as exc:
                db.session.rollback()
                summary["failed"].append(city.slug)
                log.warning("Fetch failed: %s", exc)
    return summary
