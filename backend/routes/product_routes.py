from flask import Blueprint, jsonify, request

from backend.models.product import Product
from backend.models.product import db


product_bp = Blueprint("product", __name__)


@product_bp.route("/api/products", methods=["GET"])
def get_products():

    products = Product.query.all()

    return jsonify([
        product.to_dict()
        for product in products
    ])


@product_bp.route("/api/products", methods=["POST"])
def add_product():

    data = request.get_json()

    product = Product(
        name=data["name"],
        category=data["category"],
        base_price=data["base_price"],
        cost_price=data["cost_price"],
        minimum_price=data["minimum_price"],
        stock=data["stock"],
        inventory_age=data.get("inventory_age", 0),
        days_to_expiry=data.get("days_to_expiry"),
        sales_last_7_days = data.get("sales_last_7_days", 0),
        sales_last_30_days = data.get("sales_last_30_days", 0),
        demand_level = data.get("demand_level", "MEDIUM"),
        seasonal_factor = data.get("seasonal_factor", 0)
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        "message": "Product added successfully",
        "product": product.to_dict()
    }), 201

@product_bp.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):

    product = Product.query.get(product_id)

    if not product:
        return jsonify({
            "message": "Product not found"
        }), 404

    data = request.get_json()

    product.name = data.get("name", product.name)
    product.category = data.get("category", product.category)
    product.base_price = data.get("base_price", product.base_price)
    product.cost_price = data.get("cost_price", product.cost_price)
    product.minimum_price = data.get(
        "minimum_price",
        product.minimum_price
    )
    product.stock = data.get("stock", product.stock)
    product.inventory_age = data.get(
        "inventory_age",
        product.inventory_age
    )
    product.days_to_expiry = data.get(
        "days_to_expiry",
        product.days_to_expiry
    )
    product.sales_last_7_days = data.get(
        "sales_last_7_days",
        product.sales_last_7_days
    )

    product.sales_last_30_days = data.get(
        "sales_last_30_days",
        product.sales_last_30_days
    )

    product.demand_level = data.get(
        "demand_level",
        product.demand_level
    )

    product.seasonal_factor = data.get(
        "seasonal_factor",
        product.seasonal_factor
    )

    db.session.commit()

    return jsonify({
        "message": "Product updated successfully",
        "product": product.to_dict()
    })

@product_bp.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):

    product = Product.query.get(product_id)

    if not product:
        return jsonify({
            "message": "Product not found"
        }), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({
        "message": "Product deleted successfully"
    })