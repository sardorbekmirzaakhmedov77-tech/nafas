import logging
from dataclasses import asdict

import click
from flask import Flask, render_template

from .aqi import CATEGORIES, SKY_STOPS, category_for, sky_for
from .cities import CITIES
from .config import Config
from .extensions import db, login_manager
from .security import csrf_token, verify_csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db.init_app(app)
    login_manager.init_app(app)

    from .views.api import bp as api_bp
    from .views.auth import bp as auth_bp
    from .views.dashboard import bp as dashboard_bp
    from .views.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    app.before_request(verify_csrf)

    @app.context_processor
    def template_helpers():
        return {
            "csrf_token": csrf_token,
            "category_for": category_for,
            "sky_for": sky_for,
            "AQI_CATEGORIES": CATEGORIES,
            "SKY_STOPS": SKY_STOPS,
            "AQI_JSON": {"categories": [asdict(c) for c in CATEGORIES], "sky": SKY_STOPS},
            "demo_mode": app.config["DEMO_MODE"],
        }

    @app.template_filter("hour")
    def hour_filter(dt):
        return dt.strftime("%H:%M")

    @app.template_filter("local")
    def local_filter(dt_utc):
        """Stored UTC timestamp -> local Uzbekistan time."""
        from datetime import UTC
        from zoneinfo import ZoneInfo
        return dt_utc.replace(tzinfo=UTC).astimezone(ZoneInfo(app.config["TIMEZONE"]))

    @app.template_filter("weekday")
    def weekday_filter(d):
        return d.strftime("%A")

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404,
                               message="That page doesn't exist."), 404

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message=error.description), 400

    with app.app_context():
        db.create_all()
        seed_cities()

    register_cli(app)
    # The hourly scheduler is started by the entry point (run.py / wsgi.py),
    # not here, so CLI commands and tests never spawn background jobs.
    return app


def seed_cities():
    from .models import City
    known = {c.slug for c in City.query.all()}
    for slug, name, region, lat, lon in CITIES:
        if slug not in known:
            db.session.add(City(slug=slug, name=name, region=region,
                                latitude=lat, longitude=lon))
    db.session.commit()


def register_cli(app):
    @app.cli.command("collect")
    def collect_command():
        """Fetch the latest data for every city now."""
        from .collector import collect_all
        summary = collect_all()
        click.echo(f"Updated {len(summary['ok'])} cities, {len(summary['failed'])} failed.")

    @app.cli.command("check-alerts")
    def check_alerts_command():
        """Send any due alert emails now."""
        from .alerts import check_alerts
        click.echo(f"Sent {check_alerts()} alerts.")
