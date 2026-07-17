from __future__ import annotations

from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in.", "warning")
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    """Admin-only decorator.

    Normal users must never be able to access /admin/* routes.
    Admin access is granted only when session['is_admin'] is truthy.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("admin_login.admin_login"))
        # Extra safety: ensure admin_id exists.
        if not session.get("admin_id"):
            session.pop("is_admin", None)
            return redirect(url_for("admin_login.admin_login"))
        return fn(*args, **kwargs)

    return wrapper



