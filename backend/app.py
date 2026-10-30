import os

from flask import Flask, send_from_directory

from backend.config import Config

from backend.models.product import db
from backend.models.offer import Offer
from backend.models.bargaining_session import BargainingSession
from backend.models.cart import CartItem
from backend.models.order import Order, OrderItem

from backend.routes.product_routes import product_bp
from backend.routes.offer_routes import offer_bp
from backend.routes.clearance_routes import clearance_bp
from backend.routes.cart_routes import cart_bp
from backend.routes.seller_routes import seller_bp
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
    init_auth(app)
    db.init_app(app)

    # Bargaining routes  — /api/bargaining/start | /offer | /chat | /confirm | /session/<id>
    app.register_blueprint(offer_bp)

    # Clearance routes   — /api/clearance/<id>
    app.register_blueprint(clearance_bp)

    # Auth routes        — /api/auth/register | /login | /logout | /me
    app.register_blueprint(auth_bp)

    # Product routes     — /api/products  (GET, POST, PUT, DELETE)
    app.register_blueprint(product_bp)

    # Cart & Order routes — /api/cart | /api/orders
    app.register_blueprint(cart_bp)

    # Seller Dashboard routes
    app.register_blueprint(seller_bp)

    with app.app_context():
        db.create_all()

    # ---------- Page routes (clean URLs, no .html in the browser) ----------
    @app.route("/")
    def home():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/bargain")
    def bargain():
        return send_from_directory(FRONTEND_DIR, "bargain.html")

    @app.route("/login")
    def login_page():
        return send_from_directory(FRONTEND_DIR, "login.html")

    @app.route("/admin")
    def admin():
        return send_from_directory(FRONTEND_DIR, "admin.html")


    @app.route("/seller")
    def seller_dashboard():
        return send_from_directory(FRONTEND_DIR, "seller.html")

    @app.route("/orders")
    def orders_page():
        return send_from_directory(FRONTEND_DIR, "orders.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)