from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from database import get_db
from predict import get_predictor

from utils.decorators import login_required


api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok"})


def _get_json():
    return request.get_json(silent=True) or {}


@api_bp.route("/login", methods=["POST"])
def api_login():
    data = _get_json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username, password_hash, role, is_active FROM users WHERE username=%s LIMIT 1", (username,))
    user = cur.fetchone()
    cur.close()

    if not user or not user.get("is_active", 1):
        return jsonify({"error": "Invalid credentials"}), 401

    from utils.security import check_password

    if not check_password(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = int(user["id"])
    session["username"] = user["username"]
    session["role"] = user["role"]

    return jsonify({"ok": True, "role": user["role"]})


@api_bp.route("/register", methods=["POST"])
def api_register():
    data = _get_json()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    confirm = data.get("confirm_password") or ""

    if not username or not email or not password or not confirm:
        return jsonify({"error": "All fields are required"}), 400

    import re

    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
        return jsonify({"error": "Invalid username"}), 400
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return jsonify({"error": "Invalid email"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT id FROM users WHERE username=%s LIMIT 1", (username,))
    if cur.fetchone():
        cur.close()
        return jsonify({"error": "Username already exists"}), 409

    cur.execute("SELECT id FROM users WHERE email=%s LIMIT 1", (email,))
    if cur.fetchone():
        cur.close()
        return jsonify({"error": "Email already exists"}), 409

    cur.close()

    from utils.security import hash_password

    password_hash = hash_password(password)
    cur2 = db.cursor()
    cur2.execute(
        "INSERT INTO users (username, email, password_hash, role, is_active) VALUES (%s,%s,%s,'user',1)",
        (username, email, password_hash),
    )
    db.commit()
    cur2.close()

    return jsonify({"ok": True}), 201


@api_bp.route("/predict", methods=["POST"])
@login_required
def api_predict():
    data = _get_json()
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    predictor = get_predictor()
    result = predictor.predict(text)

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO prediction_history (user_id, input_text, input_filename, prediction_label, confidence) VALUES (%s,%s,%s,%s,%s)",
        (session["user_id"], text, None, result["prediction_label"], result["confidence"]),
    )
    db.commit()
    cur.close()

    return jsonify(
        {
            "prediction_label": result["prediction_label"],
            "confidence": result["confidence"],
            "metadata": result.get("metadata", {}),
        }
    )


@api_bp.route("/history", methods=["GET"])
@login_required
def api_history():
    page = max(int(request.args.get("page", "1") or 1), 1)
    per_page = 10
    offset = (page - 1) * per_page

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT COUNT(*) AS cnt FROM prediction_history WHERE user_id=%s",
        (session["user_id"],),
    )
    total = (cur.fetchone() or {}).get("cnt", 0)

    cur.execute(
        "SELECT id, prediction_label, confidence, created_at, input_filename FROM prediction_history "
        "WHERE user_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (session["user_id"], per_page, offset),
    )
    rows = cur.fetchall() or []
    cur.close()

    return jsonify(
        {
            "page": page,
            "per_page": per_page,
            "total": total,
            "rows": rows,
        }
    )


@api_bp.route("/report", methods=["GET"])
@login_required
def api_report():
    unit = (request.args.get("unit") or "daily").lower()
    export = (request.args.get("export") or "0").lower() in ("1", "true", "yes")
    limit = int(request.args.get("limit", "30") or 30)

    db = get_db()

    from utils.reports import (
        get_daily_reports,
        get_weekly_reports,
        get_monthly_reports,
        export_reports_csv,
    )

    if unit == "daily":
        rows = get_daily_reports(db, limit=limit)
    elif unit == "weekly":
        rows = get_weekly_reports(db, limit=limit)
    elif unit == "monthly":
        rows = get_monthly_reports(db, limit=limit)
    else:
        return jsonify({"error": "Invalid unit. Use daily|weekly|monthly"}), 400

    if export:
        from config import Config
        from pathlib import Path

        export_dir = Path(Config.DATASET_FOLDER).parent / "reports_exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"report_{unit}.csv"
        abs_path = export_reports_csv(rows, str(export_path))
        return jsonify({"exported": True, "path": abs_path, "unit": unit, "rows": rows})

    return jsonify({"unit": unit, "rows": rows})


@api_bp.route("/users", methods=["GET"])
@login_required
def api_users():
    # JSON-only endpoint. Restricted to admin.
    if session.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT id, username, email, role, is_active, created_at FROM users ORDER BY created_at DESC"
    )
    rows = cur.fetchall() or []
    cur.close()
    return jsonify({"rows": rows})



