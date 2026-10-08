import logging
import sqlite3
import time

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import connect
from security_log import log_event

auth_bp = Blueprint("auth", __name__)

MAX_FAILURES = 5
LOCKOUT_SECONDS = 300
# Compared against when the username is unknown, so both outcomes cost about the same time.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _recent_failures(key):
    """Failure timestamps for (ip, username) inside the lockout window, pruned in place."""
    table = current_app.extensions["login_failures"]
    cutoff = time.time() - LOCKOUT_SECONDS
    table[key] = [t for t in table.get(key, []) if t > cutoff]
    return table[key]


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
            (username, email, generate_password_hash(password)),
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
    key = (request.remote_addr, username.lower())
    failures = _recent_failures(key)
    if len(failures) >= MAX_FAILURES:
        log_event("login_locked_out", f"username={username!r}", logging.WARNING)
        return render_template("login.html", error="Too many failed attempts. Try again later."), 429

    conn = connect(current_app.config["DB_PATH"])
    try:
        # V1 fix: bound parameter. V5 fix: the password is checked against a salted hash.
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()

    stored = user["password"] if user else _DUMMY_HASH
    if not check_password_hash(stored, password) or user is None:
        failures.append(time.time())
        log_event("login_failed", f"username={username!r}", logging.WARNING)
        return render_template("login.html", error="Invalid username or password."), 401

    current_app.extensions["login_failures"].pop(key, None)
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    log_event("login_succeeded", f"username={username!r}")
    return redirect(url_for("shop.home"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    log_event("logout", "")
    session.clear()
    return redirect(url_for("shop.home"))
