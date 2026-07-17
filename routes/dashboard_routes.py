from __future__ import annotations

from flask import Blueprint, render_template, session

from utils.decorators import login_required
from utils.charts import build_history_chart, build_real_fake_pie_chart
from database import get_db



dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    # Public landing page for anonymous visitors
    if not session.get("user_id"):
        return render_template("index.html")

    db = get_db()

    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN prediction_label='fake' THEN 1 ELSE 0 END) AS fake_cnt, SUM(CASE WHEN prediction_label='real' THEN 1 ELSE 0 END) AS real_cnt "
        "FROM prediction_history WHERE user_id=%s",
        (session["user_id"],),
    )
    stats = cur.fetchone() or {"total": 0, "fake_cnt": 0, "real_cnt": 0}

    cur.execute(
        "SELECT id, prediction_label, confidence, created_at, input_filename FROM prediction_history WHERE user_id=%s ORDER BY created_at DESC LIMIT 10",
        (session["user_id"],),
    )
    history = cur.fetchall() or []
    cur.close()

    chart = build_history_chart(db, session["user_id"])



    # Total dataset entries (from MySQL datasets table)
    cur2 = db.cursor(dictionary=True)
    cur2.execute("SELECT COUNT(*) AS cnt FROM datasets")
    dataset_total_row = cur2.fetchone() or {}
    cur2.close()
    dataset_total = int(dataset_total_row.get("cnt") or 0)

    # Total users
    cur3 = db.cursor(dictionary=True)
    cur3.execute("SELECT COUNT(*) AS cnt FROM users")
    total_users_row = cur3.fetchone() or {}
    cur3.close()
    total_users = int(total_users_row.get("cnt") or 0)

    pie_chart = build_real_fake_pie_chart(db, session["user_id"])

    return render_template(
        "user_dashboard.html",
        stats=stats,
        history=history,
        chart=chart,
        pie_chart=pie_chart,
        total_users=total_users,
        dataset_total=dataset_total,
    )


