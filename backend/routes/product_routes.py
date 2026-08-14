from flask import Blueprint, jsonify

from backend.models.product import Product

product_bp = Blueprint("product", __name__)


@product_bp.route("/api/products", methods=["GET"])
def get_products():

    products = Product.query.all()

    return jsonify([
        product.to_dict()
        for product in products
    ])