"""Read helpers shared by the web pages, the API and the alert checker."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app

from .models import City, Reading


def local_now():
    """Current local time in Uzbekistan as a naive datetime (matches stored readings)."""
    tz = ZoneInfo(current_app.config["TIMEZONE"])
    return datetime.now(tz).replace(tzinfo=None)


def current_hour():
    return local_now().replace(minute=0, second=0, microsecond=0)


def current_reading(city):
    """Latest reading that isn't in the future."""
    return (city.readings.filter(Reading.time <= current_hour(),
                                 Reading.us_aqi.isnot(None))
            .order_by(Reading.time.desc()).first())


def history(city, hours):
    start = current_hour() - timedelta(hours=hours - 1)
    return (city.readings.filter(Reading.time >= start, Reading.time <= current_hour())
            .order_by(Reading.time).all())


def forecast(city, hours=72):
    now = current_hour()
    return (city.readings.filter(Reading.time > now,
                                 Reading.time <= now + timedelta(hours=hours))
            .order_by(Reading.time).all())


def daily_summary(readings):
    """Group hourly readings into days: [{date, min, max, avg}]."""
    days = {}
    for r in readings:
        if r.us_aqi is None:
            continue
        days.setdefault(r.time.date(), []).append(r.us_aqi)
    return [{"date": d, "min": min(v), "max": max(v), "avg": round(sum(v) / len(v))}
            for d, v in sorted(days.items())]


def cities_with_current():
    """Every city with its current reading, worst air first."""
    rows = [(city, current_reading(city)) for city in City.query.all()]
    return sorted(rows, key=lambda row: -(row[1].us_aqi if row[1] else -1))
