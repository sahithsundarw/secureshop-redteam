from functools import wraps

from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for

from db import connect
from routes_account import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def _run(sql, params=(), commit=False):
    """Run one statement on a short-lived connection; return (rows, rowcount)."""
    conn = connect(current_app.config["DB_PATH"])
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        if commit:
            conn.commit()
        return rows, cur.rowcount
    finally:
        conn.close()


def _get_product(product_id):
    rows, _ = _run("SELECT * FROM products WHERE id = ?", (product_id,))
    if not rows:
        abort(404)
    return rows[0]


def _parse_product_form(form):
    """Return (values, error). values is (name, description, price, stock) when valid."""
    name = form.get("name", "").strip()
    description = form.get("description", "").strip()
    if not name or not description:
        return None, "Name and description are required."
    try:
        price = float(form.get("price", ""))
        stock = int(form.get("stock", ""))
    except ValueError:
        return None, "Price must be a number and stock a whole number."
    if not (0 <= price < 1e9) or not (0 <= stock < 10**9):
        return None, "Price and stock must be zero or more."
    return (name, description, round(price, 2), stock), None


@admin_bp.route("")
@admin_required
def index():
    return render_template("admin/index.html")


@admin_bp.route("/products")
@admin_required
def products():
    rows, _ = _run("SELECT * FROM products ORDER BY id")
    return render_template("admin/products.html", products=rows, error=request.args.get("error"))


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    if request.method == "GET":
        return render_template("admin/product_form.html", product=None, error=None)
    values, error = _parse_product_form(request.form)
    if error:
        return render_template("admin/product_form.html", product=request.form, error=error), 400
    _run(
        "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
        values,
        commit=True,
    )
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = _get_product(product_id)
    if request.method == "GET":
        return render_template("admin/product_form.html", product=product, error=None)
    values, error = _parse_product_form(request.form)
    if error:
        return render_template("admin/product_form.html", product=request.form, error=error), 400
    _run(
        "UPDATE products SET name = ?, description = ?, price = ?, stock = ? WHERE id = ?",
        (*values, product_id),
        commit=True,
    )
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    product = _get_product(product_id)
    conn = connect(current_app.config["DB_PATH"])
    try:
        # SQLite does not enforce foreign keys by default, so check order references explicitly.
        # Order history must stay intact; carts are just cleared of the product.
        if conn.execute(
            "SELECT 1 FROM order_items WHERE product_id = ?", (product_id,)
        ).fetchone():
            rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
            message = f"{product['name']} is part of existing orders and cannot be deleted."
            return render_template("admin/products.html", products=rows, error=message), 409
        conn.execute("DELETE FROM cart_items WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("admin.products"))


@admin_bp.route("/users")
@admin_required
def users():
    rows, _ = _run("SELECT id, username, email, role FROM users ORDER BY id")
    return render_template("admin/users.html", users=rows)
