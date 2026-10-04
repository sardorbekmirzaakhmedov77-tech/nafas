"""Minimal CSRF protection for form posts."""

import hmac
import secrets

from flask import abort, request, session


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def verify_csrf():
    if request.method != "POST" or request.path.startswith("/api/"):
        return
    sent = request.form.get("_csrf", "")
    expected = session.get("_csrf", "")
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400, description="Your session expired. Reload the page and try again.")
