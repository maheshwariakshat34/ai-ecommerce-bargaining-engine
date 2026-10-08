from flask import Blueprint, jsonify

from backend.models.product import Product

from backend.services.clearance_engine import (
    calculate_clearance_price
)


clearance_bp = Blueprint(
    "clearance",
    __name__
)


@clearance_bp.route(
    "/api/clearance/<int:product_id>",
    methods=["GET"]
)
def get_clearance_price(product_id):

    # Find product
    product = Product.query.get(product_id)

    # Product not found
    if not product:
        return jsonify({
            "message": "Product not found"
        }), 404

    # Calculate dynamic clearance price
    clearance = calculate_clearance_price(
        product
    )

    # Return result
    return jsonify({

        "product_id": product.id,

        "product_name": product.name,

        "category": product.category,

        "stock": product.stock,

        "inventory_age": product.inventory_age,

        "days_to_expiry": product.days_to_expiry,

        "clearance": clearance

    }), 200