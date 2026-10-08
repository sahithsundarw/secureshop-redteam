import pytest

import seed
from app import create_app
from db import connect


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "test.db"
    seed.seed(path)
    return path


@pytest.fixture()
def client(db_path):
    return create_app(db_path).test_client()


def login(client, username, password):
    assert client.post("/login", data={"username": username, "password": password}).status_code == 302


@pytest.fixture()
def admin(client):
    login(client, "admin", "AdminLab#1")
    return client


def rows(db_path, sql, params=()):
    conn = connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def product_by_name(db_path, name):
    found = rows(db_path, "SELECT * FROM products WHERE name = ?", (name,))
    return found[0] if found else None


GOOD = {"name": "Water Filter", "description": "Pitcher filter.", "price": "19.99", "stock": "12"}


def test_admin_can_open_dashboard(admin):
    response = admin.get("/admin")
    assert response.status_code == 200
    assert b"Admin" in response.data


def test_admin_nav_visible_to_admin_only(client):
    login(client, "alice", "AliceLab#1")
    assert b"/admin" not in client.get("/").data
    client.post("/logout")
    login(client, "admin", "AdminLab#1")
    assert b'href="/admin"' in client.get("/").data


def test_admin_product_list(admin):
    page = admin.get("/admin/products")
    assert page.status_code == 200
    assert b"Trail Backpack" in page.data


def test_create_product_shows_in_catalogue(admin, db_path):
    assert admin.get("/admin/products/new").status_code == 200
    response = admin.post("/admin/products/new", data=GOOD)
    assert response.status_code == 302
    assert product_by_name(db_path, "Water Filter")["stock"] == 12
    assert b"Water Filter" in admin.get("/products").data


@pytest.mark.parametrize(
    "override",
    [
        {"name": ""},
        {"description": ""},
        {"price": "abc"},
        {"price": "-1"},
        {"stock": "1.5"},
        {"stock": "-3"},
    ],
)
def test_create_product_rejects_bad_input(admin, db_path, override):
    response = admin.post("/admin/products/new", data={**GOOD, **override})
    assert response.status_code == 400
    assert product_by_name(db_path, "Water Filter") is None


def test_edit_product_updates_catalogue(admin, db_path):
    assert admin.get("/admin/products/1/edit").status_code == 200
    data = {"name": "Trail Backpack XL", "description": "Bigger.", "price": "99.50", "stock": "5"}
    assert admin.post("/admin/products/1/edit", data=data).status_code == 302
    row = rows(db_path, "SELECT * FROM products WHERE id = 1")[0]
    assert (row["name"], row["price"], row["stock"]) == ("Trail Backpack XL", 99.5, 5)
    assert b"Trail Backpack XL" in admin.get("/products").data


def test_edit_unknown_product_returns_404(admin):
    assert admin.get("/admin/products/9999/edit").status_code == 404
    assert admin.post("/admin/products/9999/edit", data=GOOD).status_code == 404


def test_delete_unreferenced_product(admin, db_path):
    admin.post("/admin/products/new", data=GOOD)
    pid = product_by_name(db_path, "Water Filter")["id"]
    assert admin.post(f"/admin/products/{pid}/delete").status_code == 302
    assert product_by_name(db_path, "Water Filter") is None
    assert b"Water Filter" not in admin.get("/products").data


def test_delete_product_in_orders_is_refused(admin, db_path):
    response = admin.post("/admin/products/1/delete")  # Trail Backpack is in alice's order
    assert response.status_code == 409
    assert rows(db_path, "SELECT id FROM products WHERE id = 1")


def test_delete_unknown_product_returns_404(admin):
    assert admin.post("/admin/products/9999/delete").status_code == 404


def test_user_listing(admin):
    page = admin.get("/admin/users")
    assert page.status_code == 200
    for expected in (b"alice", b"alice@secureshop.test", b"bob", b"admin", b"user"):
        assert expected in page.data


def test_user_listing_never_shows_password_hashes(admin):
    assert b"pbkdf2" not in admin.get("/admin/users").data
    assert b"scrypt" not in admin.get("/admin/users").data


# Role enforcement (V4 fix).

ADMIN_PAGES = ["/admin", "/admin/products", "/admin/products/new", "/admin/users"]




@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_anonymous_is_redirected_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_non_admin_is_forbidden(client, path):
    login(client, "alice", "AliceLab#1")
    assert client.get(path).status_code == 403


def test_non_admin_cannot_change_products(client, db_path):
    login(client, "alice", "AliceLab#1")
    assert client.post("/admin/products/new", data=GOOD).status_code == 403
    assert client.post("/admin/products/1/delete").status_code == 403
    assert product_by_name(db_path, "Water Filter") is None


def test_delete_product_only_in_a_cart_removes_cart_rows(admin, client, db_path):
    admin.post("/admin/products/new", data=GOOD)
    pid = product_by_name(db_path, "Water Filter")["id"]
    conn = connect(db_path)
    conn.execute("INSERT INTO cart_items (user_id, product_id, quantity) VALUES (2, ?, 1)", (pid,))
    conn.commit()
    conn.close()
    assert admin.post(f"/admin/products/{pid}/delete").status_code == 302
    assert product_by_name(db_path, "Water Filter") is None
    assert rows(db_path, "SELECT id FROM cart_items WHERE product_id = ?", (pid,)) == []
