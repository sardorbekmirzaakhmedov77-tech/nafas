from types import SimpleNamespace

from nafas.alerts import check_alerts, evaluate
from nafas.extensions import db
from nafas.models import AlertLog, City, Reading, Subscription, User
from nafas.queries import current_hour


def sub(threshold=101, alerting=False):
    return SimpleNamespace(threshold=threshold, alerting=alerting)


def test_alert_fires_when_crossing_threshold():
    assert evaluate(sub(), 120, margin=10) == "alert"


def test_no_repeat_while_episode_open():
    assert evaluate(sub(alerting=True), 140, margin=10) is None


def test_hysteresis_prevents_flapping():
    # Dipping just under the line doesn't close the episode...
    assert evaluate(sub(alerting=True), 95, margin=10) is None
    # ...falling clearly below it does.
    assert evaluate(sub(alerting=True), 90, margin=10) == "all_clear"


def test_missing_data_is_ignored():
    assert evaluate(sub(), None, margin=10) is None


def _set_current_aqi(city, aqi):
    reading = city.readings.filter(Reading.time == current_hour()).first()
    reading.us_aqi = aqi
    db.session.commit()


def test_full_alert_cycle(seeded):
    user = User(name="Test", email="t@example.com")
    user.set_password("password123")
    city = City.query.filter_by(slug="tashkent").first()
    s = Subscription(user=user, city=city, threshold=101)
    db.session.add_all([user, s])
    db.session.commit()

    _set_current_aqi(city, 160)
    assert check_alerts() == 1
    assert s.alerting

    assert check_alerts() == 0          # still high, no second email

    _set_current_aqi(city, 60)
    assert check_alerts() == 1
    assert not s.alerting
    kinds = [a.kind for a in AlertLog.query.order_by(AlertLog.id)]
    assert kinds == ["alert", "all_clear"]
