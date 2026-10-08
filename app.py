import os
import secrets

from flask import Flask, render_template

import db
from routes_account import account_bp
from routes_auth import auth_bp
from routes_shop import shop_bp

HOST = "127.0.0.1"
PORT = 8080


def create_app(db_path=None):
    app = Flask(__name__)
    # Set SECRET_KEY to keep sessions across restarts; otherwise a random per-process key is used.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["DB_PATH"] = db_path or db.DEFAULT_DB_PATH
    db.init_db(app.config["DB_PATH"])

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("error.html", code=500, message="Something went wrong."), 500

    return app


app = create_app()

if __name__ == "__main__":
    # Lab rule: bind to loopback only, never 0.0.0.0.
    app.run(host=HOST, port=PORT)
