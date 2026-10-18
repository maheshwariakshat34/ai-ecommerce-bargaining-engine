from flask import Blueprint, jsonify

from backend.models.product import Product, db
from backend.services.clearance_engine import calculate_clearance_price
from backend.services.security import admin_required


clearance_bp = Blueprint("clearance", __name__)


# Admin only: the clearance data contains cost price and internal pressure scores.
@clearance_bp.route("/api/clearance/<int:product_id>", methods=["GET"])
@admin_required
def get_clearance_price(product_id):

    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    clearance = calculate_clearance_price(product)

    return jsonify({
        "product_id": product.id,
        "product_name": product.name,
        "category": product.category,
        "stock": product.stock,
        "inventory_age": product.inventory_age,
        "days_to_expiry": product.days_to_expiry,
        "clearance": clearance
    }), 200