from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import AlertLog, City, Subscription
from ..queries import current_reading

bp = Blueprint("dashboard", __name__, url_prefix="/alerts")

THRESHOLDS = [
    # value, full label, short label
    (51, "Moderate or worse", "Moderate (51+)"),
    (101, "Unhealthy for sensitive groups or worse", "Sensitive groups (101+)"),
    (151, "Unhealthy or worse", "Unhealthy (151+)"),
    (201, "Very unhealthy or worse", "Very unhealthy (201+)"),
]


def _own_subscription(sub_id):
    sub = db.session.get(Subscription, sub_id)
    if sub is None or sub.user_id != current_user.id:
        abort(404)
    return sub


@bp.route("/")
@login_required
def index():
    subs = sorted(current_user.subscriptions, key=lambda s: s.city.name)
    watched = [(sub, current_reading(sub.city)) for sub in subs]
    watched_ids = {sub.city_id for sub in subs}
    available = [c for c in City.query.order_by(City.name) if c.id not in watched_ids]
    history = (AlertLog.query.join(Subscription)
               .filter(Subscription.user_id == current_user.id)
               .order_by(AlertLog.sent_at.desc()).limit(12).all())
    return render_template("dashboard/index.html", watched=watched, available=available,
                           history=history, thresholds=THRESHOLDS)


@bp.route("/watch", methods=["POST"])
@login_required
def watch():
    city = City.query.filter_by(slug=request.form.get("city", "")).first()
    if city is None:
        abort(400, description="Choose a city from the list.")
    threshold = _parse_threshold(request.form.get("threshold"))
    exists = Subscription.query.filter_by(user_id=current_user.id, city_id=city.id).first()
    if not exists:
        db.session.add(Subscription(user_id=current_user.id, city_id=city.id, threshold=threshold))
        db.session.commit()
        flash(f"Watching {city.name}. You'll get an email when the air reaches your alert level.")
    return redirect(request.form.get("back") or url_for("dashboard.index"))


@bp.route("/<int:sub_id>/threshold", methods=["POST"])
@login_required
def update(sub_id):
    sub = _own_subscription(sub_id)
    sub.threshold = _parse_threshold(request.form.get("threshold"))
    sub.alerting = False  # re-evaluate from scratch at the new level
    db.session.commit()
    flash(f"Alert level for {sub.city.name} updated.")
    return redirect(url_for("dashboard.index"))


@bp.route("/<int:sub_id>/stop", methods=["POST"])
@login_required
def stop(sub_id):
    sub = _own_subscription(sub_id)
    name = sub.city.name
    db.session.delete(sub)
    db.session.commit()
    flash(f"Stopped watching {name}.")
    return redirect(url_for("dashboard.index"))


def _parse_threshold(value):
    allowed = {t for t, _, _ in THRESHOLDS}
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 101
    return value if value in allowed else 101
