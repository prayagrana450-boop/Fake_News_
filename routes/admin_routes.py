from __future__ import annotations

import json

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database import get_db
from utils.decorators import admin_required, login_required
from utils.reports import build_reports


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def dashboard():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS users_cnt FROM users WHERE role='user'")
    users_cnt = (cur.fetchone() or {}).get("users_cnt", 0)

    cur.execute("SELECT COUNT(*) AS predictions_cnt FROM prediction_history")
    predictions_cnt = (cur.fetchone() or {}).get("predictions_cnt", 0)

    cur.execute(
        "SELECT prediction_label, COUNT(*) AS cnt FROM prediction_history GROUP BY prediction_label"
    )
    dist = cur.fetchall() or []

    cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 6")
    recent_users = cur.fetchall() or []

    cur.close()

    reports = build_reports(db)

    return render_template(
        "admin_dashboard.html",
        users_cnt=users_cnt,
        predictions_cnt=predictions_cnt,
        dist=dist,
        recent_users=recent_users,
        reports=reports,
    )


@admin_bp.route("/admin/datasets", methods=["GET", "POST"])
@admin_required
def datasets():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        # Create
        text = (request.form.get("text") or "").strip()
        label = (request.form.get("label") or "").strip().lower()
        if not text or not label:
            flash("Text and label are required.", "danger")
            return redirect(url_for("admin.datasets"))
        if label not in ("real", "fake"):
            flash("Label must be 'real' or 'fake'.", "danger")
            return redirect(url_for("admin.datasets"))
        cur2 = db.cursor()
        cur2.execute(
            "INSERT INTO datasets (text, label, created_by) VALUES (%s,%s,%s)",
            (text, label, session["user_id"]),
        )
        db.commit()
        cur2.close()
        flash("Dataset entry added.", "success")
        return redirect(url_for("admin.datasets"))

    # Read list
    q = (request.args.get("q") or "").strip()
    where = ""
    params = []
    if q:
        where = "WHERE text LIKE %s OR label LIKE %s"
        params.extend([f"%{q}%", f"%{q}%"])

    page = max(int(request.args.get("page", "1") or 1), 1)
    per_page = 10
    offset = (page - 1) * per_page

    cur.execute(f"SELECT COUNT(*) AS cnt FROM datasets {where}", tuple(params))
    total = (cur.fetchone() or {}).get("cnt", 0)

    cur.execute(
        f"SELECT id, label, text, created_at, created_by FROM datasets {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        tuple(params + [per_page, offset]),
    )
    rows = cur.fetchall() or []
    cur.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template("admin_datasets.html", rows=rows, page=page, total_pages=total_pages, total=total, q=q)


@admin_bp.route("/admin/datasets/delete/<int:dataset_id>")
@admin_required
def delete_dataset(dataset_id: int):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM datasets WHERE id=%s", (dataset_id,))
    db.commit()
    cur.close()
    flash("Dataset entry deleted.", "success")
    return redirect(url_for("admin.datasets"))


@admin_bp.route("/admin/datasets/edit/<int:dataset_id>", methods=["GET", "POST"])
@admin_required
def edit_dataset(dataset_id: int):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM datasets WHERE id=%s LIMIT 1", (dataset_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        flash("Dataset entry not found.", "danger")
        return redirect(url_for("admin.datasets"))

    if request.method == "POST":
        text = (request.form.get("text") or "").strip()
        label = (request.form.get("label") or "").strip().lower()
        if not text or label not in ("real", "fake"):
            flash("Invalid input.", "danger")
            return redirect(url_for("admin.edit_dataset", dataset_id=dataset_id))

        cur = db.cursor()
        cur.execute(
            "UPDATE datasets SET text=%s, label=%s WHERE id=%s",
            (text, label, dataset_id),
        )
        db.commit()
        cur.close()
        flash("Dataset entry updated.", "success")
        return redirect(url_for("admin.datasets"))

    return render_template("admin_dataset_edit.html", row=row)


@admin_bp.route("/admin/retrain", methods=["POST"])
@admin_required
def retrain():
    # Export datasets into dataset/dataset.csv used by train_model.py
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT text, label FROM datasets ORDER BY created_at DESC LIMIT 50000")
    rows = cur.fetchall() or []
    cur.close()

    import pandas as pd
    from pathlib import Path

    dataset_path = Path(__file__).resolve().parents[1] / "dataset" / "dataset.csv"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([{"text": r["text"], "label": r["label"]} for r in rows])
    df.to_csv(dataset_path, index=False)

    # Train model
    import subprocess
    import sys
    
    try:
        subprocess.check_call([sys.executable, "train_model.py"], cwd=str(Path(__file__).resolve().parents[1]))
        flash("Model retrained successfully.", "success")
    except Exception:
        flash("Model retraining failed. Check server logs.", "danger")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/users")
@admin_required
def users():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username, email, role, is_active, created_at FROM users ORDER BY created_at DESC")
    rows = cur.fetchall() or []
    cur.close()
    return render_template("admin_users.html", rows=rows)


@admin_bp.route("/admin/users/toggle/<int:user_id>")
@admin_required
def toggle_user(user_id: int):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT is_active, role FROM users WHERE id=%s LIMIT 1", (user_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if row["role"] == "admin":
        flash("Cannot deactivate admin user.", "danger")
        return redirect(url_for("admin.users"))

    new_val = 0 if int(row["is_active"]) == 1 else 1
    cur2 = db.cursor()
    cur2.execute("UPDATE users SET is_active=%s WHERE id=%s", (new_val, user_id))
    db.commit()
    cur2.close()

    flash("User status updated.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/admin/predictions")
@admin_required
def predictions():
    db = get_db()
    cur = db.cursor(dictionary=True)

    page = max(int(request.args.get("page", "1") or 1), 1)
    per_page = 10
    offset = (page - 1) * per_page

    cur.execute("SELECT COUNT(*) AS cnt FROM prediction_history")
    total = (cur.fetchone() or {}).get("cnt", 0)

    cur.execute(
        "SELECT p.id, u.username, p.prediction_label, p.confidence, p.created_at, p.input_filename "
        "FROM prediction_history p JOIN users u ON u.id=p.user_id "
        "ORDER BY p.created_at DESC LIMIT %s OFFSET %s",
        (per_page, offset),
    )
    rows = cur.fetchall() or []
    cur.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template("admin_predictions.html", rows=rows, page=page, total_pages=total_pages, total=total)


@admin_bp.route("/admin/predictions/delete/<int:pred_id>")
@admin_required
def delete_prediction(pred_id: int):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM prediction_history WHERE id=%s", (pred_id,))
    db.commit()
    cur.close()
    flash("Prediction deleted.", "success")
    return redirect(url_for("admin.predictions"))


@admin_bp.route("/admin/reports/<unit>")
@admin_required
def reports_view(unit: str):
    unit = (unit or "daily").lower()
    if unit not in ("daily", "weekly", "monthly"):
        unit = "daily"

    db = get_db()

    from utils.reports import get_daily_reports, get_weekly_reports, get_monthly_reports

    label_breakdown = True
    limit = {"daily": 30, "weekly": 12, "monthly": 24}.get(unit, 30)

    if unit == "daily":
        rows = get_daily_reports(db, limit=limit, label_breakdown=label_breakdown)
    elif unit == "weekly":
        rows = get_weekly_reports(db, limit=limit, label_breakdown=label_breakdown)
    else:
        rows = get_monthly_reports(db, limit=limit, label_breakdown=label_breakdown)

    # rows are dicts from MySQL cursor
    return render_template(
        "reports.html",
        unit=unit,
        rows=rows,
        label_breakdown=label_breakdown,
    )


@admin_bp.route("/admin/reports/export/csv/<unit>")
@admin_required
def reports_export_csv(unit: str):
    unit = (unit or "daily").lower()
    if unit not in ("daily", "weekly", "monthly"):
        unit = "daily"

    db = get_db()
    from utils.reports import (
        get_daily_reports,
        get_weekly_reports,
        get_monthly_reports,
        export_reports_csv,
    )
    from config import Config
    from pathlib import Path
    from flask import redirect

    label_breakdown = True
    limit = {"daily": 30, "weekly": 12, "monthly": 24}.get(unit, 30)

    if unit == "daily":
        rows = get_daily_reports(db, limit=limit, label_breakdown=label_breakdown)
    elif unit == "weekly":
        rows = get_weekly_reports(db, limit=limit, label_breakdown=label_breakdown)
    else:
        rows = get_monthly_reports(db, limit=limit, label_breakdown=label_breakdown)

    export_dir = Path(Config.DATASET_FOLDER).parent / "reports_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"report_{unit}.csv"

    abs_path = export_reports_csv(rows, str(export_path))
    # Download path handling: redirect to the API export JSON endpoint is avoided.
    # For simple student assignment, redirect to reports page after export.
    return redirect(url_for("admin.reports_view", unit=unit))


@admin_bp.route("/admin/reports/export/pdf/<unit>")
@admin_required
def reports_export_pdf(unit: str):

    unit = (unit or "daily").lower()
    if unit not in ("daily", "weekly", "monthly"):
        unit = "daily"

    db = get_db()
    from utils.reports import (
        get_daily_reports,
        get_weekly_reports,
        get_monthly_reports,
    )
    from config import Config
    from pathlib import Path
    from flask import redirect

    label_breakdown = True
    limit = {"daily": 30, "weekly": 12, "monthly": 24}.get(unit, 30)

    if unit == "daily":
        rows = get_daily_reports(db, limit=limit, label_breakdown=label_breakdown)
    elif unit == "weekly":
        rows = get_weekly_reports(db, limit=limit, label_breakdown=label_breakdown)
    else:
        rows = get_monthly_reports(db, limit=limit, label_breakdown=label_breakdown)

    # Export a PDF if reportlab is installed; otherwise create a text fallback at the same .pdf path.

    export_dir = Path(Config.DATASET_FOLDER).parent / "reports_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"report_{unit}.pdf"

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(export_path), pagesize=letter)
        width, height = letter
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"Fake News Detection - {unit.title()} Report")
        y -= 25
        c.setFont("Helvetica", 10)

        # Table header
        c.drawString(50, y, "Bucket")
        c.drawString(160, y, "Label")
        c.drawString(270, y, "Count")
        y -= 15

        for r in rows:
            if y < 40:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(50, y, str(r.get("day")))
            c.drawString(160, y, str(r.get("prediction_label")))
            c.drawString(270, y, str(r.get("cnt")))
            y -= 12

        c.save()
    except Exception:
        # fallback: write plaintext to .pdf to avoid breaking route
        with open(str(export_path), "w", encoding="utf-8") as f:
            f.write(f"Fake News Detection - {unit.title()} Report\n\n")
            for r in rows:
                f.write(f"{r.get('day')}\t{r.get('prediction_label')}\t{r.get('cnt')}\n")

    flash("PDF report exported.", "success")
    return redirect(url_for("admin.reports_view", unit=unit))


