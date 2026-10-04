from datetime import UTC, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .aqi import category_for
from .extensions import db


def utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    region = db.Column(db.String(80), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    last_fetched_at = db.Column(db.DateTime)

    readings = db.relationship("Reading", back_populates="city", lazy="dynamic",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<City {self.slug}>"


class Reading(db.Model):
    """One hour of air-quality data for one city (past, present or forecast)."""

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    time = db.Column(db.DateTime, nullable=False)  # local time, start of hour
    us_aqi = db.Column(db.Integer)
    pm2_5 = db.Column(db.Float)
    pm10 = db.Column(db.Float)
    nitrogen_dioxide = db.Column(db.Float)
    ozone = db.Column(db.Float)
    sulphur_dioxide = db.Column(db.Float)
    carbon_monoxide = db.Column(db.Float)

    city = db.relationship("City", back_populates="readings")

    __table_args__ = (
        db.UniqueConstraint("city_id", "time", name="uq_reading_city_time"),
        db.Index("ix_reading_city_time", "city_id", "time"),
    )

    POLLUTANTS = ("pm2_5", "pm10", "nitrogen_dioxide", "ozone",
                  "sulphur_dioxide", "carbon_monoxide")

    @property
    def category(self):
        return category_for(self.us_aqi)

    def to_dict(self):
        cat = self.category
        return {
            "time": self.time.isoformat(timespec="minutes"),
            "us_aqi": self.us_aqi,
            "category": cat.key if cat else None,
            **{p: (round(getattr(self, p), 1) if getattr(self, p) is not None else None)
               for p in self.POLLUTANTS},
        }


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    subscriptions = db.relationship("Subscription", back_populates="user",
                                    cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Subscription(db.Model):
    """A user watching a city, with the AQI at which they want an email."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    threshold = db.Column(db.Integer, nullable=False, default=100)
    # True while an alert episode is open (AQI went above the threshold and
    # hasn't come back down yet). Prevents an email every hour.
    alerting = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="subscriptions")
    city = db.relationship("City")
    alerts = db.relationship("AlertLog", back_populates="subscription",
                             cascade="all, delete-orphan",
                             order_by="AlertLog.sent_at.desc()")

    __table_args__ = (db.UniqueConstraint("user_id", "city_id", name="uq_sub_user_city"),)


class AlertLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription.id"), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # "alert" or "all_clear"
    us_aqi = db.Column(db.Integer, nullable=False)
    sent_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    subscription = db.relationship("Subscription", back_populates="alerts")
