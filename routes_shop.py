from flask import Blueprint, abort, current_app, render_template, request

from db import connect

shop_bp = Blueprint("shop", __name__)


def _query(sql, params=()):
    conn = connect(current_app.config["DB_PATH"])
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


@shop_bp.route("/")
def home():
    featured = _query("SELECT * FROM products ORDER BY id LIMIT 4")
    return render_template("home.html", products=featured)


@shop_bp.route("/products")
def products():
    return render_template("products.html", products=_query("SELECT * FROM products ORDER BY id"))


@shop_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    rows = _query("SELECT * FROM products WHERE id = ?", (product_id,))
    if not rows:
        abort(404)
    return render_template("product.html", product=rows[0])


@shop_bp.route("/search")
def search():
    term = request.args.get("q", "").strip()
    results = []
    if term:
        like = f"%{term}%"
        results = _query(
            "SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY id",
            (like, like),
        )
    return render_template("search.html", term=term, products=results)
