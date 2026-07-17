from __future__ import annotations

from typing import Any


def build_history_chart(db, user_id: int) -> dict[str, Any]:
    cur = db.cursor(dictionary=True)

    # Last N predictions time series grouped by day
    cur.execute(
        "SELECT DATE(created_at) AS day, prediction_label, COUNT(*) AS cnt "
        "FROM prediction_history WHERE user_id=%s "
        "GROUP BY DATE(created_at), prediction_label "
        "ORDER BY day DESC LIMIT 14",
        (user_id,),
    )
    rows = cur.fetchall() or []
    cur.close()

    # Pivot
    days = sorted({r["day"] for r in rows})
    fake = [0] * len(days)
    real = [0] * len(days)

    day_index = {d: i for i, d in enumerate(days)}
    for r in rows:
        i = day_index[r["day"]]
        if r["prediction_label"] == "fake":
            fake[i] = int(r["cnt"])
        else:
            real[i] = int(r["cnt"])

    return {
        "labels": days,
        "datasets": [
            {"label": "Real", "data": real, "borderColor": "#22c55e", "backgroundColor": "rgba(34,197,94,0.2)"},
            {"label": "Fake", "data": fake, "borderColor": "#ef4444", "backgroundColor": "rgba(239,68,68,0.2)"},
        ],
    }


def build_real_fake_pie_chart(db, user_id: int) -> dict[str, Any]:
    """Pie chart data for real vs fake predictions.

    Returned format matches Chart.js data object.
    """

    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT prediction_label, COUNT(*) AS cnt "
        "FROM prediction_history WHERE user_id=%s "
        "GROUP BY prediction_label",
        (user_id,),
    )
    rows = cur.fetchall() or []
    cur.close()

    real_cnt = 0
    fake_cnt = 0
    for r in rows:
        if r.get("prediction_label") == "real":
            real_cnt = int(r.get("cnt") or 0)
        elif r.get("prediction_label") == "fake":
            fake_cnt = int(r.get("cnt") or 0)

    return {
        "labels": ["Real", "Fake"],
        "datasets": [
            {
                "label": "Real vs Fake",
                "data": [real_cnt, fake_cnt],
                "backgroundColor": ["rgba(34,197,94,0.8)", "rgba(239,68,68,0.8)"],
                "borderColor": ["#22c55e", "#ef4444"],
                "borderWidth": 1,
            }
        ],
    }


