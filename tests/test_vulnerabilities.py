"""Demonstrations that the planted weaknesses V1-V8 are present on the vulnerable build.

Lab use only: every payload targets the local test database. Ticket 09 fixes each weakness and
inverts these assertions.
"""
import hashlib
import logging
import re
import sqlite3
from pathlib import Path

import pytest

import seed
from app import create_app
from db import connect

pytestmark = pytest.mark.vulnerability
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "test.db"
    seed.seed(path)
    return path


@pytest.fixture()
def app(db_path):
    return create_app(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username="alice", password="AliceLab#1"):
    return client.post("/login", data={"username": username, "password": password})


def test_v1_search_sql_injection_returns_user_rows(client):
    payload = "zzz%' UNION SELECT id, username, password, 1.0, 1 FROM users --"
    response = client.get("/search", query_string={"q": payload})
    assert response.status_code == 200
    assert b"alice@" not in response.data  # sanity: emails are not selected
    assert b"alice" in response.data and b"bob" in response.data


def test_v1_login_sql_injection_bypasses_password(client):
    response = login(client, "admin'--", "wrong")
    assert response.status_code == 302
    assert b"Admin" in client.get("/").data


def test_v2_search_term_reflected_unescaped(client):
    response = client.get("/search", query_string={"q": "<script>alert(1)</script>"})
    assert b"<script>alert(1)</script>" in response.data


def test_v3_user_can_read_another_users_order(client, db_path):
    conn = connect(db_path)
    bob_order = conn.execute(
        "SELECT o.id FROM orders o JOIN users u ON u.id = o.user_id WHERE u.username = 'bob'"
    ).fetchone()["id"]
    conn.close()
    login(client)
    response = client.get(f"/orders/{bob_order}")
    assert response.status_code == 200
    assert b"Mechanical Keyboard" in response.data


def test_v4_anonymous_reaches_admin_pages(client):
    assert client.get("/admin").status_code == 200
    assert b"alice@secureshop.test" in client.get("/admin/users").data


def test_v4_ordinary_user_reaches_admin_pages(client):
    login(client)
    assert client.get("/admin/products").status_code == 200


def test_v5_passwords_stored_as_unsalted_md5(db_path):
    conn = connect(db_path)
    stored = conn.execute("SELECT password FROM users WHERE username = 'alice'").fetchone()[0]
    conn.close()
    assert stored == hashlib.md5(b"AliceLab#1").hexdigest()


def test_v5_session_cookie_forgeable_with_known_key(app, client):
    forged = app.session_interface.get_signing_serializer(app).dumps(
        {"user_id": 1, "role": "admin"}
    )
    # Werkzeug 2.0.3 signature: set_cookie(server_name, key, value). A raw Cookie header is
    # overwritten by the client's cookie jar.
    client.set_cookie("localhost", "session", forged)
    page = client.get("/profile")
    assert page.status_code == 200
    assert b"admin" in page.data
    assert app.config["SECRET_KEY"] == "secret"


def test_v5_no_lockout_after_repeated_failures(client):
    for _ in range(15):
        assert login(client, "alice", "wrong").status_code == 401
    assert login(client).status_code == 302


def test_v6_debug_on_and_errors_are_not_handled(app, client):
    assert app.debug is True
    with pytest.raises(sqlite3.OperationalError):
        client.get("/search", query_string={"q": "x' OR"})


def test_v6_security_headers_absent(client):
    headers = client.get("/").headers
    for name in (
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
    ):
        assert name not in headers


def test_v6_session_cookie_has_permissive_flags(client):
    cookie = login(client).headers.get("Set-Cookie", "")
    assert "session=" in cookie
    assert "HttpOnly" not in cookie
    assert "SameSite" not in cookie


def test_v7_outdated_components_pinned_and_vendored():
    pins = (ROOT / "requirements.txt").read_text(encoding="utf-8-sig")
    assert re.search(r"^Flask==2\.0\.3$", pins, re.M)
    assert re.search(r"^Werkzeug==2\.0\.3$", pins, re.M)
    jquery = ROOT / "static" / "vendor" / "jquery-1.12.4.min.js"
    assert "jQuery v1.12.4" in jquery.read_text(encoding="utf-8")


def test_v7_pages_load_the_old_jquery(client):
    assert b"vendor/jquery-1.12.4.min.js" in client.get("/").data


def test_v8_failed_login_and_admin_action_leave_no_log_entry(client, caplog):
    with caplog.at_level(logging.DEBUG):
        login(client, "alice", "wrong")
        login(client, "admin", "AdminLab#1")
        client.post("/admin/products/9999/delete")
    assert caplog.records == []
