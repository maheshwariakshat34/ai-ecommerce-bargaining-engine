from flask import Flask

from backend.config import Config
from backend.models.product import db


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return "AI E-Commerce Bargaining Engine is running!"

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)