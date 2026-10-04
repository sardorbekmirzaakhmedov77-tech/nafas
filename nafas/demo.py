"""Realistic generated data for DEMO_MODE.

Mimics the patterns of real air in Uzbekistan: traffic peaks in the morning
and evening, night-time temperature inversions that trap smog, multi-day
weather episodes, and dust events that hit the western desert cities hardest.
The numbers are made up, and the site says so when demo mode is on.
"""

import math
import random
from datetime import timedelta

from flask import current_app

from .aqi import combined_aqi
from .collector import upsert_readings
from .extensions import db
from .models import City
from .queries import current_hour

# Typical PM2.5 baseline (µg/m³) and how dusty each city tends to be.
PROFILE = {
    "tashkent": (38, 0.2), "almalyk": (41, 0.25), "samarkand": (26, 0.3),
    "bukhara": (24, 0.7), "namangan": (34, 0.3), "andijan": (36, 0.3),
    "fergana": (35, 0.35), "nukus": (22, 1.0), "urgench": (23, 0.9),
    "qarshi": (25, 0.6), "termez": (27, 0.8), "navoiy": (22, 0.6),
    "jizzakh": (21, 0.4), "guliston": (24, 0.4),
}


def _city_series(slug, start, hours):
    base, dustiness = PROFILE.get(slug, (25, 0.4))
    rng = random.Random(f"{slug}-{start.date().isoformat()}")
    weather = 0.0   # slow multi-day swings (stagnant air vs. windy fronts)
    dust = 0.0      # dust event intensity
    rows = []
    for h in range(hours):
        t = start + timedelta(hours=h)
        hour = t.hour
        weather = 0.97 * weather + rng.gauss(0, 0.06)
        if rng.random() < 0.004 * dustiness:
            dust = rng.uniform(80, 220) * dustiness
        dust *= 0.93

        traffic = 0.35 * math.exp(-((hour - 8.5) ** 2) / 4) + 0.5 * math.exp(-((hour - 20.5) ** 2) / 6)
        inversion = 0.25 if hour >= 22 or hour <= 5 else 0.0
        afternoon_mix = -0.25 * math.exp(-((hour - 15) ** 2) / 8)
        weekend = -0.12 if t.weekday() >= 5 else 0.0

        level = base * math.exp(weather) * (1 + traffic + inversion + afternoon_mix + weekend)
        pm25 = max(2.0, level + dust * 0.25 + rng.gauss(0, 2))
        pm10 = pm25 * rng.uniform(1.5, 1.9) + dust
        no2 = max(3.0, 18 + 40 * traffic * (base / 30) + rng.gauss(0, 4))
        ozone = max(5.0, 35 + 60 * math.exp(-((hour - 15) ** 2) / 10) + rng.gauss(0, 6))
        so2 = max(1.0, 4 + base / 8 + rng.gauss(0, 1.5))
        co = max(120.0, 220 + 9 * level + rng.gauss(0, 25))

        rows.append({
            "time": t, "pm2_5": round(pm25, 1), "pm10": round(pm10, 1),
            "nitrogen_dioxide": round(no2, 1), "ozone": round(ozone, 1),
            "sulphur_dioxide": round(so2, 1), "carbon_monoxide": round(co, 0),
        })

    # Smooth into a 24-hour rolling mean for the index, as real AQI does.
    window = []
    for row in rows:
        window.append(row)
        window = window[-24:]
        avg25 = sum(r["pm2_5"] for r in window) / len(window)
        avg10 = sum(r["pm10"] for r in window) / len(window)
        row["us_aqi"] = combined_aqi(avg25, avg10)
    return rows


def seed_demo_data():
    """Generate history + forecast for every city, relative to now."""
    cfg = current_app.config
    now = current_hour()
    # The random seed depends on the start date, so re-seeding within the
    # same day reproduces the same series.
    start = now - timedelta(days=cfg["HISTORY_DAYS"])
    hours = (cfg["HISTORY_DAYS"] + cfg["FORECAST_DAYS"]) * 24
    for city in City.query.all():
        upsert_readings(city, _city_series(city.slug, start, hours))
    db.session.commit()
    return {"ok": [c.slug for c in City.query.all()], "failed": [], "demo": True}
