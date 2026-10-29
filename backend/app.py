import os

from flask import Flask, send_from_directory

from backend.config import Config

from backend.models.product import db
from backend.models.offer import Offer
from backend.models.bargaining_session import BargainingSession

from backend.routes.product_routes import product_bp
from backend.routes.offer_routes import offer_bp

from backend.routes.clearance_routes import clearance_bp
from backend.models.user import User
from backend.routes.auth_routes import auth_bp
from backend.services.security import init_auth


FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend"
)


def create_app():

    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path=""
    )

    app.config.from_object(Config)
    app.register_blueprint(offer_bp)
    app.register_blueprint(clearance_bp)
    app.config.from_object(Config)
    init_auth(app)
    app.register_blueprint(auth_bp)


    db.init_app(app)
    app.register_blueprint(product_bp)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)