from __future__ import annotations

from typing import Any


def build_reports(db) -> dict[str, Any]:
    cur = db.cursor(dictionary=True)

    # Distribution (overall)
    # Use a consistent variable name: `avg_confidence` is expected by admin_dashboard.html.
    cur.execute(
        "SELECT prediction_label, AVG(confidence) AS avg_confidence, COUNT(*) AS cnt "
        "FROM prediction_history GROUP BY prediction_label"
    )
    dist = cur.fetchall() or []


    # Last 14 days counts
    cur.execute(
        "SELECT DATE(created_at) AS day, COUNT(*) AS cnt "
        "FROM prediction_history GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 14"
    )
    last_days = cur.fetchall() or []

    cur.close()

    return {
        "distribution": dist,
        "last_days": last_days,
    }


def _fetch_time_bucket(db, *, unit: str, label: str | None, start_date_sql: str | None = None):
    """Internal helper.

    unit: 'day' | 'week' | 'month'
    label: if provided, group by prediction_label as well.
    """

    cur = db.cursor(dictionary=True)

    # MySQL: DATE(created_at) is day; YEARWEEK(created_at, 1) for week; DATE_FORMAT for month
    if unit == "day":
        select_expr = "DATE(created_at)"
        group_expr = "DATE(created_at)"
        order_expr = "day"
    elif unit == "week":
        # ISO week (mode 1)
        select_expr = "STR_TO_DATE(CONCAT(YEARWEEK(created_at, 1), ' Sunday'), '%X%V %W')"
        group_expr = "STR_TO_DATE(CONCAT(YEARWEEK(created_at, 1), ' Sunday'), '%X%V %W')"
        order_expr = "day"
    elif unit == "month":
        select_expr = "DATE_FORMAT(created_at, '%Y-%m-01')"
        group_expr = "DATE_FORMAT(created_at, '%Y-%m-01')"
        order_expr = "day"
    else:
        raise ValueError("Invalid time unit")

    where = ""
    params: list[Any] = []
    if start_date_sql:
        where = " WHERE created_at >= %s"
        params.append(start_date_sql)

    if label:
        cur.execute(
            f"""
            SELECT {select_expr} AS day, prediction_label, COUNT(*) AS cnt
            FROM prediction_history
            {where}
            GROUP BY {group_expr}, prediction_label
            ORDER BY {order_expr} DESC
            """.strip(),
            tuple(params),
        )
    else:
        cur.execute(
            f"""
            SELECT {select_expr} AS day, COUNT(*) AS cnt
            FROM prediction_history
            {where}
            GROUP BY {group_expr}
            ORDER BY {order_expr} DESC
            """.strip(),
            tuple(params),
        )

    rows = cur.fetchall() or []
    cur.close()
    return rows


def get_daily_reports(db, *, limit: int = 30, label_breakdown: bool = True):
    # limit number of buckets by slicing results in python (MySQL compatibility for date ranges varies)
    rows = _fetch_time_bucket(db, unit="day", label="prediction_label" if label_breakdown else None)
    # rows ordered desc; keep up to limit unique days
    days_seen = []
    out_rows = []
    day_set = set()
    for r in rows:
        d = r.get("day")
        if d not in day_set:
            if len(days_seen) >= limit:
                break
            day_set.add(d)
            days_seen.append(d)
        out_rows.append(r)
    return out_rows


def get_weekly_reports(db, *, limit: int = 12, label_breakdown: bool = True):
    rows = _fetch_time_bucket(db, unit="week", label="prediction_label" if label_breakdown else None)
    days_seen = []
    out_rows = []
    day_set = set()
    for r in rows:
        d = r.get("day")
        if d not in day_set:
            if len(days_seen) >= limit:
                break
            day_set.add(d)
            days_seen.append(d)
        out_rows.append(r)
    return out_rows


def get_monthly_reports(db, *, limit: int = 24, label_breakdown: bool = True):
    rows = _fetch_time_bucket(db, unit="month", label="prediction_label" if label_breakdown else None)
    days_seen = []
    out_rows = []
    day_set = set()
    for r in rows:
        d = r.get("day")
        if d not in day_set:
            if len(days_seen) >= limit:
                break
            day_set.add(d)
            days_seen.append(d)
        out_rows.append(r)
    return out_rows


def export_reports_csv(rows: list[dict[str, Any]], path: str) -> str:
    """Export provided rows to CSV path. Returns absolute path."""
    import csv
    import os

    os.makedirs(os.path.dirname(path), exist_ok=True)
    abs_path = os.path.abspath(path)

    if not rows:
        # create empty csv with headers
        with open(abs_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["day", "prediction_label", "cnt"])
        return abs_path

    headers = list(rows[0].keys())
    with open(abs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return abs_path


