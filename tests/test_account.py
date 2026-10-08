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
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 302


@pytest.fixture()
def alice(client):
    login(client, "alice", "AliceLab#1")
    return client


def rows(db_path, sql, params=()):
    conn = connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def order_ids(db_path, username):
    return [
        r["id"]
        for r in rows(
            db_path,
            "SELECT o.id FROM orders o JOIN users u ON u.id = o.user_id WHERE u.username = ?"
            " ORDER BY o.id",
            (username,),
        )
    ]


# --- anonymous access redirects to login ---------------------------------------------------


@pytest.mark.parametrize("path", ["/cart", "/profile", "/orders", "/orders/1"])
def test_anonymous_get_redirects_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize(
    "path,data",
    [
        ("/cart/add", {"product_id": 1}),
        ("/cart/remove", {"item_id": 1}),
        ("/cart/checkout", {}),
        ("/profile", {"email": "x@y.test"}),
    ],
)
def test_anonymous_post_redirects_to_login(client, path, data):
    response = client.post(path, data=data)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# --- cart ----------------------------------------------------------------------------------


def test_add_and_view_cart(alice):
    response = alice.post("/cart/add", data={"product_id": 1, "quantity": 2})
    assert response.status_code == 302
    page = alice.get("/cart")
    assert page.status_code == 200
    assert b"Trail Backpack" in page.data
    assert b"159.98" in page.data


def test_adding_same_product_twice_merges_quantity(alice, db_path):
    alice.post("/cart/add", data={"product_id": 1, "quantity": 1})
    alice.post("/cart/add", data={"product_id": 1, "quantity": 2})
    items = rows(db_path, "SELECT quantity FROM cart_items WHERE product_id = 1")
    assert [i["quantity"] for i in items] == [3]


def test_add_unknown_product_returns_404(alice):
    assert alice.post("/cart/add", data={"product_id": 9999}).status_code == 404


def test_add_invalid_quantity_returns_400(alice):
    assert alice.post("/cart/add", data={"product_id": 1, "quantity": 0}).status_code == 400
    assert alice.post("/cart/add", data={"product_id": 1, "quantity": "x"}).status_code == 400


def test_remove_cart_item(alice, db_path):
    alice.post("/cart/add", data={"product_id": 1})
    item_id = rows(db_path, "SELECT id FROM cart_items")[0]["id"]
    assert alice.post("/cart/remove", data={"item_id": item_id}).status_code == 302
    assert rows(db_path, "SELECT id FROM cart_items") == []


def test_cannot_remove_another_users_cart_item(client, db_path):
    login(client, "bob", "BobLab#1")
    client.post("/cart/add", data={"product_id": 2})
    bob_item = rows(db_path, "SELECT id FROM cart_items")[0]["id"]
    client.post("/logout")
    login(client, "alice", "AliceLab#1")
    client.post("/cart/remove", data={"item_id": bob_item})
    assert len(rows(db_path, "SELECT id FROM cart_items")) == 1


def test_cart_is_per_user(client):
    login(client, "alice", "AliceLab#1")
    client.post("/cart/add", data={"product_id": 1})
    client.post("/logout")
    login(client, "bob", "BobLab#1")
    assert b"Trail Backpack" not in client.get("/cart").data


# --- checkout ------------------------------------------------------------------------------


def test_checkout_creates_order_and_empties_cart(alice, db_path):
    before = order_ids(db_path, "alice")
    alice.post("/cart/add", data={"product_id": 1, "quantity": 2})
    alice.post("/cart/add", data={"product_id": 2, "quantity": 1})
    response = alice.post("/cart/checkout")
    assert response.status_code == 302

    new_ids = [i for i in order_ids(db_path, "alice") if i not in before]
    assert len(new_ids) == 1
    order = rows(db_path, "SELECT * FROM orders WHERE id = ?", (new_ids[0],))[0]
    assert order["total"] == pytest.approx(2 * 79.99 + 24.50)
    items = rows(db_path, "SELECT * FROM order_items WHERE order_id = ?", (new_ids[0],))
    assert sorted((i["product_id"], i["quantity"], i["price"]) for i in items) == [
        (1, 2, 79.99),
        (2, 1, 24.50),
    ]
    assert rows(db_path, "SELECT id FROM cart_items") == []
    assert rows(db_path, "SELECT stock FROM products WHERE id = 1")[0]["stock"] == 23


def test_checkout_empty_cart_creates_no_order(alice, db_path):
    before = order_ids(db_path, "alice")
    response = alice.post("/cart/checkout")
    assert response.status_code == 400
    assert order_ids(db_path, "alice") == before


def test_checkout_rejects_quantity_over_stock(alice, db_path):
    before = order_ids(db_path, "alice")
    alice.post("/cart/add", data={"product_id": 1, "quantity": 26})
    response = alice.post("/cart/checkout")
    assert response.status_code == 409
    assert order_ids(db_path, "alice") == before
    assert rows(db_path, "SELECT stock FROM products WHERE id = 1")[0]["stock"] == 25
    assert len(rows(db_path, "SELECT id FROM cart_items")) == 1


# --- profile -------------------------------------------------------------------------------


def test_profile_shows_own_details(alice):
    page = alice.get("/profile")
    assert page.status_code == 200
    assert b"alice" in page.data
    assert b"alice@secureshop.test" in page.data


def test_profile_updates_email(alice, db_path):
    response = alice.post("/profile", data={"email": "alice2@secureshop.test"})
    assert response.status_code == 302
    row = rows(db_path, "SELECT email, username, role FROM users WHERE username = 'alice'")[0]
    assert (row["email"], row["role"]) == ("alice2@secureshop.test", "user")


def test_profile_ignores_role_field(alice, db_path):
    alice.post("/profile", data={"email": "alice@secureshop.test", "role": "admin"})
    assert rows(db_path, "SELECT role FROM users WHERE username = 'alice'")[0]["role"] == "user"


def test_profile_rejects_blank_email(alice):
    assert alice.post("/profile", data={"email": "  "}).status_code == 400


def test_profile_rejects_email_taken_by_another_user(alice):
    response = alice.post("/profile", data={"email": "bob@secureshop.test"})
    assert response.status_code == 409


# --- order history -------------------------------------------------------------------------


def test_seeded_users_have_distinct_orders(db_path):
    alice_ids, bob_ids = order_ids(db_path, "alice"), order_ids(db_path, "bob")
    assert alice_ids and bob_ids
    assert not set(alice_ids) & set(bob_ids)


def test_order_list_shows_only_own_orders(alice, db_path):
    page = alice.get("/orders")
    assert page.status_code == 200
    for oid in order_ids(db_path, "alice"):
        assert f"/orders/{oid}".encode() in page.data
    for oid in order_ids(db_path, "bob"):
        assert f"/orders/{oid}\"".encode() not in page.data


def test_order_detail_shows_items(alice, db_path):
    oid = order_ids(db_path, "alice")[0]
    page = alice.get(f"/orders/{oid}")
    assert page.status_code == 200
    assert b"Trail Backpack" in page.data
    assert b"Insulated Bottle" in page.data


def test_order_detail_unknown_id_returns_404(alice):
    assert alice.get("/orders/9999").status_code == 404


@pytest.mark.xfail(strict=True, reason="V3 planted in ticket 06; ticket 09 removes this marker")
def test_order_detail_of_another_user_returns_404(alice, db_path):
    bob_order = order_ids(db_path, "bob")[0]
    assert alice.get(f"/orders/{bob_order}").status_code == 404


# --- review follow-up: atomic checkout and quantity bound ----------------------------------


@pytest.mark.parametrize("quantity", ["1001", str(2**63)])
def test_add_oversized_quantity_returns_400(alice, quantity):
    response = alice.post("/cart/add", data={"product_id": 1, "quantity": quantity})
    assert response.status_code == 400


def test_second_checkout_cannot_drive_stock_negative(client, db_path):
    login(client, "alice", "AliceLab#1")
    client.post("/cart/add", data={"product_id": 1, "quantity": 20})
    assert client.post("/cart/checkout").status_code == 302
    client.post("/logout")
    login(client, "bob", "BobLab#1")
    client.post("/cart/add", data={"product_id": 1, "quantity": 20})
    before = order_ids(db_path, "bob")
    assert client.post("/cart/checkout").status_code == 409
    assert order_ids(db_path, "bob") == before
    assert rows(db_path, "SELECT stock FROM products WHERE id = 1")[0]["stock"] == 5


def test_checkout_stock_guard_holds_against_stale_cart_read(alice, db_path, monkeypatch):
    """Simulates the check-then-write race: the cart read reports more stock than exists."""
    import routes_account

    real = routes_account._cart_lines
    monkeypatch.setattr(
        routes_account,
        "_cart_lines",
        lambda user_id: [{**dict(r), "stock": 999} for r in real(user_id)],
    )
    alice.post("/cart/add", data={"product_id": 1, "quantity": 26})
    before = order_ids(db_path, "alice")
    assert alice.post("/cart/checkout").status_code == 409
    assert order_ids(db_path, "alice") == before
    assert rows(db_path, "SELECT stock FROM products WHERE id = 1")[0]["stock"] == 25
    assert len(rows(db_path, "SELECT id FROM cart_items")) == 1
