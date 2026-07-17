from __future__ import annotations

from flask import Blueprint, redirect, url_for

from utils.decorators import login_required


dashboard_alias_bp = Blueprint("dashboard_alias", __name__)


@dashboard_alias_bp.route("/dashboard")
@login_required
def dashboard_alias():
    # Existing UI is mounted at blueprint route '/' (rendering user_dashboard.html).
    return redirect(url_for("dashboard.index"))

