from flask import Flask

from backend.config import Config

from backend.models.product import db
from backend.models.offer import Offer
from backend.models.bargaining_session import BargainingSession

from backend.routes.product_routes import product_bp
from backend.routes.offer_routes import offer_bp

from backend.routes.clearance_routes import clearance_bp


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)
    app.register_blueprint(offer_bp)
    app.register_blueprint(clearance_bp)


    db.init_app(app)
    app.register_blueprint(product_bp)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return "AI E-Commerce Bargaining Engine is running!"

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)