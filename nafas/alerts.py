"""Email alerts when a watched city's air crosses the user's threshold.

Each subscription works like a thermostat with hysteresis:

    AQI rises to >= threshold            -> send alert, open episode
    AQI stays high                       -> stay quiet (no hourly spam)
    AQI drops below threshold - margin   -> send all-clear, close episode
"""

import logging

from flask import current_app

from .aqi import category_for
from .extensions import db
from .mailer import send_email
from .models import AlertLog, Subscription
from .queries import current_reading

log = logging.getLogger(__name__)


def evaluate(subscription, aqi, margin):
    """Pure decision function: returns 'alert', 'all_clear' or None."""
    if aqi is None:
        return None
    if not subscription.alerting and aqi >= subscription.threshold:
        return "alert"
    if subscription.alerting and aqi < subscription.threshold - margin:
        return "all_clear"
    return None


def _compose(sub, aqi, kind):
    cat = category_for(aqi)
    city = sub.city.name
    url = f"{current_app.config['SITE_URL']}/city/{sub.city.slug}"
    if kind == "alert":
        subject = f"Air quality in {city} is now {cat.name.lower()} (AQI {aqi})"
        text = (f"Hi {sub.user.name},\n\n"
                f"The air quality index in {city} has reached {aqi}, above your alert "
                f"level of {sub.threshold}.\n\n{cat.advice}\n\n"
                f"We'll email you again when it improves.\n\nDetails: {url}\n")
    else:
        subject = f"Air in {city} has improved (AQI {aqi})"
        text = (f"Hi {sub.user.name},\n\n"
                f"The air quality index in {city} is back down to {aqi} "
                f"({cat.name.lower()}).\n\nDetails: {url}\n")
    return subject, text


def check_alerts():
    """Run after each data refresh. Returns the number of emails sent."""
    margin = current_app.config["ALERT_HYSTERESIS"]
    sent = 0
    current_by_city = {}
    for sub in Subscription.query.all():
        if sub.city_id not in current_by_city:
            current_by_city[sub.city_id] = current_reading(sub.city)
        reading = current_by_city[sub.city_id]
        aqi = reading.us_aqi if reading else None
        kind = evaluate(sub, aqi, margin)
        if kind is None:
            continue
        subject, text = _compose(sub, aqi, kind)
        try:
            send_email(sub.user.email, subject, text)
        except Exception:  # noqa: BLE001 - one bad mailbox shouldn't stop the run
            log.exception("Could not email %s", sub.user.email)
            continue
        sub.alerting = kind == "alert"
        db.session.add(AlertLog(subscription=sub, kind=kind, us_aqi=aqi))
        sent += 1
    db.session.commit()
    return sent
