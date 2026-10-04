from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, login_manager
from ..models import User

bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def _safe_next(target):
    """Only allow redirects within this site."""
    if target and not urlparse(target).netloc and target.startswith("/"):
        return target
    return url_for("dashboard.index")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    errors, form = {}, {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("name", "email")}
        password = request.form.get("password", "")
        form["email"] = form["email"].lower()
        if not form["name"]:
            errors["name"] = "Enter your name."
        if "@" not in form["email"] or "." not in form["email"].split("@")[-1]:
            errors["email"] = "Enter a valid email address."
        elif User.query.filter_by(email=form["email"]).first():
            errors["email"] = "An account with this email already exists. Sign in instead."
        if len(password) < 8:
            errors["password"] = "Use at least 8 characters."
        if not errors:
            user = User(name=form["name"], email=form["email"])
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. Choose the cities you want to watch.")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html", errors=errors, form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    error, email = None, ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(_safe_next(request.args.get("next")))
        error = "That email and password don't match. Check them and try again."
    return render_template("auth/login.html", error=error, email=email)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
