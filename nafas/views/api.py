"""Public JSON API (read-only)."""

from flask import Blueprint, jsonify, request

from ..aqi import category_for
from ..models import City
from ..queries import current_reading, daily_summary, forecast, history

bp = Blueprint("api", __name__, url_prefix="/api/v1")

MAX_HISTORY_HOURS = 24 * 31


@bp.after_request
def allow_cross_origin(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def _city_or_404(slug):
    city = City.query.filter_by(slug=slug).first()
    if city is None:
        return None, (jsonify(error=f"Unknown city '{slug}'. See /api/v1/cities."), 404)
    return city, None


def _city_json(city, reading=None):
    data = {
        "slug": city.slug, "name": city.name, "region": city.region,
        "latitude": city.latitude, "longitude": city.longitude,
    }
    if reading is not None:
        cat = category_for(reading.us_aqi)
        data["current"] = reading.to_dict()
        data["current"]["category_name"] = cat.name if cat else None
    return data


@bp.route("/cities")
def cities():
    return jsonify(cities=[_city_json(c, current_reading(c))
                           for c in City.query.order_by(City.name)])


@bp.route("/cities/<slug>")
def city(slug):
    city, error = _city_or_404(slug)
    if error:
        return error
    return jsonify(_city_json(city, current_reading(city)))


@bp.route("/cities/<slug>/history")
def city_history(slug):
    city, error = _city_or_404(slug)
    if error:
        return error
    try:
        hours = int(request.args.get("hours", 24))
    except ValueError:
        return jsonify(error="'hours' must be a whole number."), 400
    hours = max(1, min(hours, MAX_HISTORY_HOURS))
    return jsonify(city=city.slug, hours=hours,
                   readings=[r.to_dict() for r in history(city, hours)])


@bp.route("/cities/<slug>/forecast")
def city_forecast(slug):
    city, error = _city_or_404(slug)
    if error:
        return error
    upcoming = forecast(city, 96)
    days = [{**d, "date": d["date"].isoformat(),
             "category": category_for(d["max"]).key} for d in daily_summary(upcoming)]
    return jsonify(city=city.slug, hourly=[r.to_dict() for r in upcoming], daily=days)
