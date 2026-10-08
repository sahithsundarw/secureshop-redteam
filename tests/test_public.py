import subprocess
import sys
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
def client(db_path):
    return create_app(db_path).test_client()


def test_seed_data_shape(db_path):
    conn = connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] == 1
        users_with_orders = conn.execute(
            "SELECT COUNT(DISTINCT o.user_id) FROM orders o JOIN users u ON u.id = o.user_id"
            " WHERE u.role = 'user'"
        ).fetchone()[0]
        assert users_with_orders >= 2
    finally:
        conn.close()


def test_seed_refuses_non_empty_database(db_path):
    with pytest.raises(RuntimeError):
        seed.seed(db_path)


def test_seed_script_exits_nonzero_on_non_empty_database(db_path):
    result = subprocess.run(
        [sys.executable, "seed.py", str(db_path)], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "not empty" in result.stderr


def test_home_lists_products(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to SecureShop" in response.data
    assert b"Trail Backpack" in response.data


def test_product_listing_shows_all(client):
    response = client.get("/products")
    assert response.status_code == 200
    assert response.data.count(b'class="price"') == 10


def test_product_detail(client):
    response = client.get("/products/1")
    assert response.status_code == 200
    assert b"Trail Backpack" in response.data
    assert b"79.99" in response.data


def test_unknown_product_returns_404_page(client):
    response = client.get("/products/9999")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_search_returns_matching_products(client):
    response = client.get("/search?q=keyboard")
    assert response.status_code == 200
    assert b"Mechanical Keyboard" in response.data
    assert b"Yoga Mat" not in response.data


def test_search_without_match(client):
    response = client.get("/search?q=zzzz")
    assert response.status_code == 200
    assert b"No products found" in response.data


def test_register_then_login_then_logout(client):
    response = client.post(
        "/register", data={"username": "carol", "email": "carol@x.test", "password": "pw12345"}
    )
    assert response.status_code == 302

    response = client.post("/login", data={"username": "carol", "password": "pw12345"})
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" in sess

    response = client.post("/logout")
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_register_duplicate_username_rejected(client):
    response = client.post(
        "/register", data={"username": "alice", "email": "new@x.test", "password": "pw12345"}
    )
    assert response.status_code == 409
    assert b"already taken" in response.data


def test_register_missing_fields_rejected(client):
    response = client.post("/register", data={"username": "dave"})
    assert response.status_code == 400


def test_login_seed_user(client):
    response = client.post("/login", data={"username": "alice", "password": "AliceLab#1"})
    assert response.status_code == 302


def test_wrong_password_rejected(client):
    response = client.post("/login", data={"username": "alice", "password": "wrong"})
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_unknown_user_rejected(client):
    response = client.post("/login", data={"username": "nobody", "password": "x"})
    assert response.status_code == 401
