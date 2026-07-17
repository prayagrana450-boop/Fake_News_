from __future__ import annotations

import re
from typing import Optional

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from config import Config
from database import get_db
from utils.security import check_password, hash_password
from utils.decorators import login_required


auth_bp = Blueprint("auth", __name__)


def _get_user_by_username(username: str):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s LIMIT 1", (username,))
    row = cur.fetchone()
    cur.close()
    return row


def _get_user_by_id(user_id: int):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username, email, role, is_active FROM users WHERE id=%s LIMIT 1", (user_id,))
    row = cur.fetchone()
    cur.close()
    return row


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.login"))

        user = _get_user_by_username(username)
        if not user or not user.get("is_active", 1):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.login"))

        if not check_password(user["password_hash"], password):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.login"))

        session["user_id"] = int(user["id"])
        session["username"] = user["username"]
        session["role"] = user["role"]

        # Admins must authenticate ONLY via admins table (/admin/login). 
        # Even if the users row contains role='admin', do not allow admin access.
        return redirect(url_for("dashboard.index"))


    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not username or not email or not password or not confirm:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
            flash("Username must be 3-30 chars and contain only letters, numbers, underscore.", "danger")
            return redirect(url_for("auth.register"))

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            flash("Invalid email.", "danger")
            return redirect(url_for("auth.register"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("auth.register"))

        if _get_user_by_username(username):
            flash("Username already exists.", "danger")
            return redirect(url_for("auth.register"))

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE email=%s LIMIT 1", (email,))
        exists = cur.fetchone()
        cur.close()
        if exists:
            flash("Email already exists.", "danger")
            return redirect(url_for("auth.register"))

        password_hash = hash_password(password)
        cur = db.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, role, is_active) VALUES (%s,%s,%s,'user',1)",
            (username, email, password_hash),
        )
        db.commit()
        cur.close()

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/profile")
@login_required
def profile():
    user = _get_user_by_id(session["user_id"])
    return render_template("profile.html", user=user)


@auth_bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()

    if not username or not email:
        flash("Username and email are required.", "danger")
        return redirect(url_for("auth.profile"))

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT id FROM users WHERE username=%s AND id<>%s LIMIT 1", (username, session["user_id"]))
    if cur.fetchone():
        cur.close()
        flash("Username already in use.", "danger")
        return redirect(url_for("auth.profile"))

    cur.execute("SELECT id FROM users WHERE email=%s AND id<>%s LIMIT 1", (email, session["user_id"]))
    if cur.fetchone():
        cur.close()
        flash("Email already in use.", "danger")
        return redirect(url_for("auth.profile"))

    cur.close()

    cur = db.cursor()
    cur.execute(
        "UPDATE users SET username=%s, email=%s WHERE id=%s",
        (username, email, session["user_id"]),
    )
    db.commit()
    cur.close()

    session["username"] = username
    flash("Profile updated.", "success")
    return redirect(url_for("auth.profile"))

