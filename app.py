from flask import Flask

HOST = "127.0.0.1"
PORT = 8080


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "SecureShop"

    return app


app = create_app()

if __name__ == "__main__":
    # Lab rule: bind to loopback only, never 0.0.0.0.
    app.run(host=HOST, port=PORT)
