from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db

admin_login_bp = Blueprint("admin_login", __name__)


# -------------------------
# Admin Registration
# -------------------------
@admin_login_bp.route("/admin/register", methods=["GET", "POST"])
def admin_register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("admin_register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("admin_register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("admin_register.html")

        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute(
            "SELECT id FROM admins WHERE email=%s",
            (email,)
        )

        if cur.fetchone():
            cur.close()
            flash("Email already exists.", "danger")
            return render_template("admin_register.html")

        password_hash = generate_password_hash(password)

        cur.execute(
            """
            INSERT INTO admins (username, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (username, email, password_hash),
        )

        db.commit()
        cur.close()

        flash("Admin registered successfully. Please login.", "success")
        return redirect(url_for("admin_login.admin_login"))

    return render_template("admin_register.html")

# -------------------------
# Admin Login
# -------------------------
@admin_login_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("is_admin"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("admin_login.html")

        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute(
            """
            SELECT id, username, email, password_hash
            FROM admins
            WHERE email=%s
            LIMIT 1
            """,
            (email,),
        )

        admin = cur.fetchone()
        cur.close()

        if admin is None:
            flash("Invalid email or password.", "danger")
            return render_template("admin_login.html")

        if not check_password_hash(admin["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("admin_login.html")

        session.clear()

        session["admin_id"] = admin["id"]
        session["admin_name"] = admin["username"]
        session["is_admin"] = True

        flash("Welcome Admin!", "success")

        return redirect(url_for("admin.dashboard"))

    return render_template("admin_login.html")


# -------------------------
# Admin Logout
# -------------------------
@admin_login_bp.route("/admin/logout")
def admin_logout():

    session.clear()

    flash("Logged out successfully.", "success")

    return redirect(url_for("admin_login.admin_login"))


# -------------------------
# Dashboard Redirect
# -------------------------
@admin_login_bp.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("is_admin"):
        flash("Please login first.", "danger")
        return redirect(url_for("admin_login.admin_login"))

    return redirect(url_for("admin.dashboard"))