from datetime import timedelta

from flask import Blueprint, abort, render_template, request

from .. import geo
from ..models import City
from ..queries import cities_with_current, current_hour, current_reading, daily_summary, forecast

bp = Blueprint("main", __name__)

POLLUTANT_INFO = [
    # column, name, short, what it is
    ("pm2_5", "Fine particles", "PM2.5",
     "Smoke and exhaust particles small enough to reach deep into the lungs."),
    ("pm10", "Coarse particles", "PM10",
     "Dust, pollen and road grit. Rises sharply during dust storms."),
    ("nitrogen_dioxide", "Nitrogen dioxide", "NO₂",
     "Mostly from vehicle engines. Peaks at rush hour."),
    ("ozone", "Ozone", "O₃",
     "Forms in sunlight from other pollutants. Highest on hot afternoons."),
    ("sulphur_dioxide", "Sulphur dioxide", "SO₂",
     "From burning coal and from industry."),
    ("carbon_monoxide", "Carbon monoxide", "CO",
     "From incomplete burning of fuel, including traffic and heating."),
]


@bp.route("/")
def index():
    rows = cities_with_current()
    slug = request.args.get("city", "tashkent")
    featured = next((row for row in rows if row[0].slug == slug), rows[0] if rows else None)
    next_hours = forecast(featured[0], 24) if featured else []
    return render_template("index.html", rows=rows, featured=featured,
                           next_hours=next_hours, geo=geo)


@bp.route("/city/<slug>")
def city(slug):
    city = City.query.filter_by(slug=slug).first()
    if city is None:
        abort(404)
    reading = current_reading(city)
    days = daily_summary(forecast(city, 96))[:4]
    today = current_hour().date()
    return render_template("city.html", city=city, reading=reading, days=days,
                           next_hours=forecast(city, 24),
                           today=today, tomorrow=today + timedelta(days=1),
                           pollutants=POLLUTANT_INFO,
                           all_cities=City.query.order_by(City.name).all())


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/developers")
def developers():
    return render_template("developers.html")
