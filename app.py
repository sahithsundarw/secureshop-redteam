import os

from flask import Flask, render_template

import db
from routes_account import account_bp
from routes_admin import admin_bp
from routes_auth import auth_bp
from routes_shop import shop_bp

HOST = "127.0.0.1"
PORT = 8080


def create_app(db_path=None):
    app = Flask(__name__)
    # VULNERABLE (V5, A07): hard-coded guessable signing key lets anyone forge a session cookie.
    app.config["SECRET_KEY"] = "secret"
    # VULNERABLE (V6, A05 Security Misconfiguration): debug on, and session cookie without
    # HttpOnly (SameSite is left unset as well).
    app.config["DEBUG"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = False
    app.config["DB_PATH"] = db_path or os.environ.get("SECURESHOP_DB") or db.DEFAULT_DB_PATH
    db.init_db(app.config["DB_PATH"])

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="Page not found."), 404

    # VULNERABLE (V6): no generic 500 handler and no security headers (CSP, X-Frame-Options,
    # X-Content-Type-Options, Referrer-Policy), so errors surface stack traces.

    return app


app = create_app()

if __name__ == "__main__":
    # Lab rule: bind to loopback only, never 0.0.0.0.
    app.run(host=HOST, port=PORT, use_reloader=False)
