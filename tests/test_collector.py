"""Live-mode collection, with the Open-Meteo API replaced by a fake."""

from datetime import timedelta

import requests

from nafas import collector
from nafas.models import City, Reading
from nafas.queries import current_hour


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status}")

    def json(self):
        return self.payload


def _payload(hours=6, aqi=60):
    start = current_hour() - timedelta(hours=hours - 2)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {"hourly": {"time": times, "us_aqi": [aqi + i for i in range(hours)],
                       "pm2_5": [12.0] * hours, "pm10": [30.0] * hours}}


def test_collect_all_live(app, monkeypatch):
    app.config["DEMO_MODE"] = False
    calls = []

    class Session:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, params, timeout):
            calls.append(params)
            if params["latitude"] == City.query.filter_by(slug="nukus").first().latitude:
                return FakeResponse({}, status=503)   # one city's request fails
            return FakeResponse(_payload())

    monkeypatch.setattr(collector.requests, "Session", Session)
    monkeypatch.setattr(collector.time, "sleep", lambda s: None)

    summary = collector.collect_all()
    assert summary["failed"] == ["nukus"]
    assert len(summary["ok"]) == 13
    assert calls[0]["past_days"] == app.config["HISTORY_DAYS"]   # first run backfills
    tashkent = City.query.filter_by(slug="tashkent").first()
    assert tashkent.readings.count() == 6 and tashkent.last_fetched_at

    # Second run: only tops up, and updates existing hours instead of duplicating
    calls.clear()
    collector.collect_all()
    tashkent_call = next(c for c in calls if c["latitude"] == tashkent.latitude)
    assert tashkent_call["past_days"] == 2
    assert tashkent.readings.count() == 6
    assert Reading.query.filter_by(city=tashkent).order_by(Reading.time).first().us_aqi == 60
