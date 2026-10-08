import os
import secrets

from flask import Flask, render_template

import db
from routes_account import account_bp
from routes_admin import admin_bp
from routes_auth import auth_bp
from routes_shop import shop_bp
from security_log import init_logging

HOST = "127.0.0.1"
PORT = 8080


def create_app(db_path=None):
    app = Flask(__name__)
    # V5 fix: the signing key comes from the environment, with a random per-process fallback
    # (sessions then reset on restart, which is acceptable for a lab).
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    # V6 fix: debug off; cookie flags set. Secure is on only when served over HTTPS
    # (SECURESHOP_HTTPS=1), because the lab runs on plain http://127.0.0.1.
    app.config["DEBUG"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SECURESHOP_HTTPS") == "1"
    app.config["LOG_PATH"] = os.environ.get("SECURESHOP_LOG") or db.DEFAULT_DB_PATH.parent.parent / "logs" / "security.log"
    app.extensions["login_failures"] = {}
    init_logging(app)
    app.config["DB_PATH"] = db_path or os.environ.get("SECURESHOP_DB") or db.DEFAULT_DB_PATH
    db.init_db(app.config["DB_PATH"])

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, message="You do not have access to this page."), 403

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("error.html", code=500, message="Something went wrong."), 500

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app


app = create_app()

if __name__ == "__main__":
    # Lab rule: bind to loopback only, never 0.0.0.0.
    app.run(host=HOST, port=PORT, use_reloader=False)
