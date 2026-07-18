from __future__ import annotations

import os
import uuid

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from config import Config
from database import get_db
from predict import get_predictor

from utils.decorators import login_required
from utils.files import allowed_file, secure_filename


prediction_bp = Blueprint("prediction", __name__)


@prediction_bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict_ui():
    if request.method == "POST":
        text = (request.form.get("text") or "").strip()
        input_filename = None
        input_type = "TEXT"

        # File upload support
        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            # Accept TXT/CSV/JSON only
            allowed = set(Config.ALLOWED_EXTENSIONS)

            if not allowed_file(uploaded.filename, tuple(allowed)):
                flash("Invalid file type. Upload .txt/.csv/.json/.pdf only.", "danger")
                return redirect(url_for("prediction.predict_ui"))

            fname = secure_filename(uploaded.filename)
            ext = os.path.splitext(fname)[1].lower()
            new_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(Config.UPLOAD_FOLDER, new_name)
            uploaded.save(save_path)
            input_filename = new_name

            input_type = ext.lstrip(".").upper()

            # Attempt to extract text

            try:
                file_text = open(save_path, "r", encoding="utf-8", errors="ignore").read()
                # If csv, try naive extraction: first column
                if ext == ".csv":
                    lines = [l.strip() for l in file_text.splitlines() if l.strip()]
                    if lines:
                        # Drop header if it contains 'label'
                        if any("label" in lines[0].lower() for _ in [0]):
                            lines = lines[1:]
                        text = lines[0] if lines else text
                elif ext == ".json":
                    import json

                    obj = json.loads(file_text)
                    if isinstance(obj, dict) and "text" in obj:
                        text = str(obj["text"])
                    elif isinstance(obj, list) and obj:
                        text = str(obj[0].get("text") or obj[0].get("body") or obj[0])
                else:
                    text = file_text
            except Exception:
                flash("Failed to read uploaded file.", "danger")
                return redirect(url_for("prediction.predict_ui"))




            # Persist input_type for result page
            if not input_type:
                input_type = "TEXT"
            else:
                # Ensure input_type is available for both file and manual predictions
                input_type = input_type if input_type else "TEXT"






        if not text:

            flash("Please provide text or upload a file.", "danger")
            return redirect(url_for("prediction.predict_ui"))

        import logging
        import traceback

        try:
            predictor = get_predictor()
            result = predictor.predict(text)

            # Save prediction history with confidence
            # (Use extracted text as input_text; store input_filename as uploaded name)
            # Note: existing DB schema is respected (no new tables/routes).
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO prediction_history (user_id, input_text, input_filename, prediction_label, confidence) VALUES (%s,%s,%s,%s,%s)",
                (
                    session["user_id"],
                    text,
                    input_filename,
                    result["prediction_label"],
                    result["confidence"],
                ),
            )
            db.commit()
            cur.close()

            return render_template(
                "prediction_result.html",
                result=result,
                input_text_preview=text[:800],
                input_filename=input_filename,
                input_type=input_type if uploaded and uploaded.filename else "TEXT",
            )

        except Exception as e:
            # Full traceback logging (Render-friendly)
            tb = traceback.format_exc()
            logging.getLogger(__name__).error("Prediction failed: %s\n%s", e, tb)
            print("[ERROR] Prediction failed:")
            print(tb)

            flash("Prediction failed on the server. Please try again.", "danger")
            return redirect(url_for("prediction.predict_ui"))


    return render_template("prediction.html")


@prediction_bp.route("/history")
@login_required
def history():
    db = get_db()
    cur = db.cursor(dictionary=True)

    page = max(int(request.args.get("page", "1") or 1), 1)
    per_page = 10
    offset = (page - 1) * per_page

    cur.execute(
        "SELECT COUNT(*) AS cnt FROM prediction_history WHERE user_id=%s",
        (session["user_id"],),
    )
    total = cur.fetchone()["cnt"]

    cur.execute(
        "SELECT id, prediction_label, confidence, created_at, input_filename, input_text FROM prediction_history "
        "WHERE user_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (session["user_id"], per_page, offset),
    )
    rows = cur.fetchall() or []
    cur.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "prediction_history.html",
        rows=rows,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@prediction_bp.route("/history/delete/<int:pred_id>")
@login_required
def delete_history(pred_id: int):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "DELETE FROM prediction_history WHERE id=%s AND user_id=%s",
        (pred_id, session["user_id"]),
    )
    db.commit()
    cur.close()
    flash("Prediction deleted.", "success")
    return redirect(url_for("prediction.history"))

