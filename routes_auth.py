import hashlib
import sqlite3

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from db import connect

auth_bp = Blueprint("auth", __name__)


def _weak_hash(password):
    # VULNERABLE (V5, A07 Authentication Failures): unsalted MD5 password storage.
    return hashlib.md5(password.encode()).hexdigest()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", error=None)

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    if not username or not email or not password:
        return render_template("register.html", error="All fields are required."), 400

    conn = connect(current_app.config["DB_PATH"])
    try:
        conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
            (username, email, _weak_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Username or email already taken."), 409
    finally:
        conn.close()
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    conn = connect(current_app.config["DB_PATH"])
    try:
        # VULNERABLE (V1, A03 Injection): credentials are concatenated into the SQL string.
        user = conn.execute(
            f"SELECT * FROM users WHERE username = '{username}'"
            f" AND password = '{_weak_hash(password)}'"
        ).fetchone()
    finally:
        conn.close()

    # VULNERABLE (V5): no lockout or throttling after repeated failures.
    # VULNERABLE (V8, A09 Logging Failures): failed and successful logins are not logged.
    if user is None:
        return render_template("login.html", error="Invalid username or password."), 401

    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    return redirect(url_for("shop.home"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("shop.home"))
