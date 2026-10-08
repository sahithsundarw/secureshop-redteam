import sqlite3
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from db import connect

account_bp = Blueprint("account", __name__)

MAX_QUANTITY = 1000


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def _conn():
    """One connection per request, closed on teardown."""
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


@account_bp.teardown_app_request
def _close_conn(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def _cart_lines(user_id):
    return _conn().execute(
        "SELECT c.id, c.quantity, p.id AS product_id, p.name, p.price, p.stock,"
        " c.quantity * p.price AS subtotal"
        " FROM cart_items c JOIN products p ON p.id = c.product_id"
        " WHERE c.user_id = ? ORDER BY c.id",
        (user_id,),
    ).fetchall()


def _render_cart(error=None, status=200):
    lines = _cart_lines(session["user_id"])
    total = round(sum(line["subtotal"] for line in lines), 2)
    return render_template("cart.html", lines=lines, total=total, error=error), status


@account_bp.route("/cart")
@login_required
def cart():
    return _render_cart()


@account_bp.route("/cart/add", methods=["POST"])
@login_required
def cart_add():
    try:
        product_id = int(request.form.get("product_id", ""))
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        abort(400)
    if not 1 <= quantity <= MAX_QUANTITY:
        abort(400)

    conn = _conn()
    if conn.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone() is None:
        abort(404)
    existing = conn.execute(
        "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
        (session["user_id"], product_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE cart_items SET quantity = quantity + ? WHERE id = ?", (quantity, existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (session["user_id"], product_id, quantity),
        )
    conn.commit()
    return redirect(url_for("account.cart"))


@account_bp.route("/cart/remove", methods=["POST"])
@login_required
def cart_remove():
    try:
        item_id = int(request.form.get("item_id", ""))
    except ValueError:
        abort(400)
    conn = _conn()
    conn.execute(
        "DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, session["user_id"])
    )
    conn.commit()
    return redirect(url_for("account.cart"))


@account_bp.route("/cart/checkout", methods=["POST"])
@login_required
def checkout():
    user_id = session["user_id"]
    conn = _conn()
    # Take the write lock before reading so the stock check and the writes are one unit.
    conn.execute("BEGIN IMMEDIATE")
    lines = _cart_lines(user_id)
    if not lines:
        conn.rollback()
        return _render_cart("Your cart is empty.", 400)
    short = [line["name"] for line in lines if line["quantity"] > line["stock"]]
    if short:
        conn.rollback()
        return _render_cart("Not enough stock for: " + ", ".join(short), 409)

    total = round(sum(line["subtotal"] for line in lines), 2)
    order_id = conn.execute(
        "INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total)
    ).lastrowid
    for line in lines:
        updated = conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (line["quantity"], line["product_id"], line["quantity"]),
        )
        if updated.rowcount != 1:
            conn.rollback()
            return _render_cart("Not enough stock for: " + line["name"], 409)
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
            (order_id, line["product_id"], line["quantity"], line["price"]),
        )
    conn.executemany(
        "DELETE FROM cart_items WHERE id = ? AND user_id = ?",
        [(line["id"], user_id) for line in lines],
    )
    conn.commit()
    return redirect(url_for("account.order_detail", order_id=order_id))


@account_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = _conn()
    user_id = session["user_id"]
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            return _render_profile("Email is required.", 400)
        try:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
            conn.commit()
        except sqlite3.IntegrityError:
            return _render_profile("Email already in use.", 409)
        return redirect(url_for("account.profile"))
    return _render_profile()


def _render_profile(error=None, status=200):
    user = _conn().execute(
        "SELECT username, email FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    return render_template("profile.html", user=user, error=error), status


@account_bp.route("/orders")
@login_required
def orders():
    rows = _conn().execute(
        "SELECT id, total, created_at FROM orders WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("orders.html", orders=rows)


@account_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    conn = _conn()
    order = conn.execute(
        "SELECT id, total, created_at FROM orders WHERE id = ? AND user_id = ?",
        (order_id, session["user_id"]),
    ).fetchone()
    if order is None:
        abort(404)
    items = conn.execute(
        "SELECT p.name, oi.quantity, oi.price, oi.quantity * oi.price AS subtotal"
        " FROM order_items oi JOIN products p ON p.id = oi.product_id"
        " WHERE oi.order_id = ? ORDER BY oi.id",
        (order_id,),
    ).fetchall()
    return render_template("order.html", order=order, items=items)
