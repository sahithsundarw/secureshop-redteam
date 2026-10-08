"""Proofs that each planted weakness V1-V8 is fixed. These replace test_vulnerabilities.py, which
demonstrates the same flaws on the v1-vulnerable tag; each assertion here is the inverse of one there."""
import logging
import re
from pathlib import Path

import pytest

import seed
from app import create_app
from db import connect

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


def test_v1_search_injection_returns_no_user_rows(client):
    payload = "zzz%' UNION SELECT id, username, password, 1.0, 1 FROM users --"
    page = client.get("/search", query_string={"q": payload})
    assert page.status_code == 200
    assert b"bob" not in page.data and b"alice" not in page.data


def test_v1_search_still_finds_real_products(client):
    assert b"Desk Lamp" in client.get("/search", query_string={"q": "lamp"}).data


def test_v1_login_injection_no_longer_bypasses_password(client):
    assert login(client, "admin'--", "wrong").status_code == 401


def test_v2_search_term_is_escaped(client):
    page = client.get("/search", query_string={"q": "<script>alert(1)</script>"})
    assert b"<script>alert(1)</script>" not in page.data
    assert b"&lt;script&gt;" in page.data


def test_v3_user_cannot_read_another_users_order(client, db_path):
    conn = connect(db_path)
    bob_order = conn.execute(
        "SELECT o.id FROM orders o JOIN users u ON u.id = o.user_id WHERE u.username = 'bob'"
    ).fetchone()["id"]
    conn.close()
    login(client)
    response = client.get(f"/orders/{bob_order}")
    assert response.status_code == 404
    assert b"Mechanical Keyboard" not in response.data


@pytest.mark.parametrize("path", ["/admin", "/admin/users", "/admin/products"])
def test_v4_anonymous_and_user_are_kept_out_of_admin(client, path):
    assert client.get(path).status_code == 302
    login(client)
    assert client.get(path).status_code == 403


def test_v4_admin_still_reaches_admin(client):
    login(client, "admin", "AdminLab#1")
    assert client.get("/admin/users").status_code == 200


def test_v5_passwords_are_salted_hashes(db_path):
    conn = connect(db_path)
    stored = [r[0] for r in conn.execute("SELECT password FROM users")]
    conn.close()
    assert len(set(stored)) == 3
    assert all(s.startswith(("scrypt:", "pbkdf2:")) for s in stored)
    assert "AliceLab#1" not in "".join(stored)


def test_v5_secret_key_is_not_the_old_guessable_one(app):
    assert app.config["SECRET_KEY"] != "secret"
    assert len(app.config["SECRET_KEY"]) >= 32


def test_v5_forged_session_with_old_key_is_rejected(app, client):
    from itsdangerous import URLSafeTimedSerializer
    import hashlib
    forged = URLSafeTimedSerializer(
        "secret", salt="cookie-session", serializer=app.session_interface.serializer,
        signer_kwargs={"key_derivation": "hmac", "digest_method": hashlib.sha1},
    ).dumps({"user_id": 1, "role": "admin"})
    client.set_cookie("session", forged, domain="localhost")
    assert client.get("/admin/users").status_code == 302


def test_v5_lockout_after_repeated_failures(client):
    for _ in range(5):
        assert login(client, "alice", "wrong").status_code == 401
    assert login(client).status_code == 429  # even the right password is refused while locked


def test_v5_failures_for_one_user_do_not_lock_another(client):
    for _ in range(5):
        login(client, "alice", "wrong")
    assert login(client, "bob", "BobLab#1").status_code == 302


def test_v6_debug_off_and_errors_are_generic(app):
    assert app.debug is False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    page = app.test_client().get("/boom")
    assert page.status_code == 500
    assert b"secret internal detail" not in page.data and b"Traceback" not in page.data


def test_v6_security_headers_present(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"


def test_v6_session_cookie_flags(client):
    cookie = login(client).headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_v7_components_upgraded_and_jquery_removed():
    pins = (ROOT / "requirements.txt").read_text(encoding="utf-8-sig")
    assert re.search(r"^Flask==3\.1\.3$", pins, re.M)
    assert re.search(r"^Werkzeug==3\.1\.9$", pins, re.M)
    assert not (ROOT / "static" / "vendor" / "jquery-1.12.4.min.js").exists()


def test_v7_pages_no_longer_load_jquery(client):
    assert b"jquery" not in client.get("/").data.lower()


def test_v8_security_events_are_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="secureshop.security"):
        login(client, "alice", "wrong")
        login(client, "admin", "AdminLab#1")
        client.post("/admin/products/9999/delete")
        client.post("/admin/products/new", data={
            "name": "Log Test", "description": "d", "price": "1", "stock": "1"})
    text = caplog.text
    assert "event=login_failed" in text and "username='alice'" in text
    assert "event=login_succeeded" in text
    assert "event=admin_action" in text


def test_v8_access_denial_is_logged(client, caplog):
    login(client)
    with caplog.at_level(logging.INFO, logger="secureshop.security"):
        client.get("/admin")
    assert "event=access_denied" in caplog.text


def test_v8_log_file_is_written(app, client):
    login(client, "alice", "wrong")
    for handler in logging.getLogger("secureshop.security").handlers:
        handler.flush()
    assert "event=login_failed" in Path(app.config["LOG_PATH"]).read_text(encoding="utf-8")
