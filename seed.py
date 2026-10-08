"""Load lab-only seed data. Refuses to run if the database already has users or products."""
import sys

from werkzeug.security import generate_password_hash

from db import DEFAULT_DB_PATH, connect, init_db

# Lab-only credentials. Documented in the README.
USERS = [
    ("admin", "admin@secureshop.test", "AdminLab#1", "admin"),
    ("alice", "alice@secureshop.test", "AliceLab#1", "user"),
    ("bob", "bob@secureshop.test", "BobLab#1", "user"),
]

PRODUCTS = [
    ("Trail Backpack", "35L waterproof hiking backpack.", 79.99, 25),
    ("Insulated Bottle", "750ml steel bottle, keeps drinks cold for 24h.", 24.50, 100),
    ("Wireless Earbuds", "Bluetooth 5.3 earbuds with charging case.", 59.00, 40),
    ("Desk Lamp", "LED lamp with adjustable colour temperature.", 32.75, 60),
    ("Mechanical Keyboard", "Tenkeyless keyboard with brown switches.", 89.90, 30),
    ("Running Shoes", "Lightweight road running shoes.", 110.00, 45),
    ("Yoga Mat", "6mm non-slip yoga mat.", 28.00, 80),
    ("Coffee Grinder", "Burr grinder with 15 grind settings.", 49.95, 35),
    ("Notebook Set", "Pack of three dotted notebooks.", 14.25, 150),
    ("USB-C Hub", "7-in-1 hub with HDMI and card reader.", 44.40, 55),
]

# username -> list of orders, each a list of (product name, quantity)
ORDERS = {
    "alice": [[("Trail Backpack", 1), ("Insulated Bottle", 2)], [("Notebook Set", 3)]],
    "bob": [[("Mechanical Keyboard", 1)], [("Running Shoes", 1), ("Yoga Mat", 1)]],
}


def seed(db_path=DEFAULT_DB_PATH):
    init_db(db_path)
    conn = connect(db_path)
    try:
        existing = conn.execute(
            "SELECT (SELECT COUNT(*) FROM users) + (SELECT COUNT(*) FROM products)"
        ).fetchone()[0]
        if existing:
            raise RuntimeError("Database is not empty; refusing to seed.")

        for username, email, password, role in USERS:
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (username, email, generate_password_hash(password), role),
            )
        conn.executemany(
            "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
            PRODUCTS,
        )

        for username, orders in ORDERS.items():
            user_id = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()["id"]
            for items in orders:
                lines = []
                for name, quantity in items:
                    product = conn.execute(
                        "SELECT id, price FROM products WHERE name = ?", (name,)
                    ).fetchone()
                    lines.append((product["id"], quantity, product["price"]))
                total = round(sum(q * p for _, q, p in lines), 2)
                order_id = conn.execute(
                    "INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total)
                ).lastrowid
                conn.executemany(
                    "INSERT INTO order_items (order_id, product_id, quantity, price)"
                    " VALUES (?, ?, ?, ?)",
                    [(order_id, pid, q, p) for pid, q, p in lines],
                )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        seed(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    print("Seeded.")
