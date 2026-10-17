import math

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.models.product import Product, db


product_bp = Blueprint("product", __name__)

VALID_DEMAND = {"LOW", "MEDIUM", "HIGH"}


def _num(value, name, minimum=0):
    """Convert to a finite float >= minimum, or raise ValueError."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number.")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.")
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{name} must be a valid number >= {minimum}.")
    return number


def _int(value, name, minimum=0):
    number = _num(value, name, minimum)
    if number != int(number):
        raise ValueError(f"{name} must be a whole number.")
    return int(number)


def validate_product_data(d):
    """Validate a full set of product fields (already merged for PUT)."""
    clean = {}
    clean["name"] = str(d.get("name") or "").strip()
    clean["category"] = str(d.get("category") or "").strip()
    if not clean["name"] or not clean["category"]:
        raise ValueError("name and category are required.")

    clean["base_price"] = _num(d.get("base_price"), "base_price", 0.01)
    clean["cost_price"] = _num(d.get("cost_price"), "cost_price", 0)
    clean["minimum_price"] = _num(d.get("minimum_price"), "minimum_price", 0)

    # Business rule: cost <= minimum <= base
    if not (clean["cost_price"] <= clean["minimum_price"] <= clean["base_price"]):
        raise ValueError(
            "Prices must satisfy: cost_price <= minimum_price <= base_price."
        )

    clean["stock"] = _int(d.get("stock"), "stock", 0)
    clean["inventory_age"] = _int(d.get("inventory_age", 0), "inventory_age", 0)
    clean["sales_last_7_days"] = _int(
        d.get("sales_last_7_days", 0), "sales_last_7_days", 0
    )
    clean["sales_last_30_days"] = _int(
        d.get("sales_last_30_days", 0), "sales_last_30_days", 0
    )

    expiry = d.get("days_to_expiry")
    clean["days_to_expiry"] = (
        None if expiry is None else _int(expiry, "days_to_expiry", -10**6)
    )

    demand = str(d.get("demand_level") or "MEDIUM").upper()
    if demand not in VALID_DEMAND:
        raise ValueError("demand_level must be LOW, MEDIUM or HIGH.")
    clean["demand_level"] = demand

    clean["seasonal_factor"] = _num(
        d.get("seasonal_factor", 0), "seasonal_factor", -10**6
    )
    return clean


@product_bp.route("/api/products", methods=["GET"])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


@product_bp.route("/api/products", methods=["POST"])
def add_product():
    data = request.get_json(silent=True)  # FIX: None body no longer crashes

    if not isinstance(data, dict):
        return jsonify({"message": "Request body must be valid JSON."}), 400

    try:
        clean = validate_product_data(data)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400

    product = Product(**clean)

    try:
        db.session.add(product)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Could not save product."}), 500

    return jsonify({
        "message": "Product added successfully",
        "product": product.to_dict()
    }), 201


@product_bp.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"message": "Request body must be valid JSON."}), 400

    fields = [
        "name", "category", "base_price", "cost_price", "minimum_price",
        "stock", "inventory_age", "days_to_expiry", "sales_last_7_days",
        "sales_last_30_days", "demand_level", "seasonal_factor"
    ]

    # Merge existing values with updates, then validate the final result
    merged = {f: getattr(product, f) for f in fields}
    merged.update({f: data[f] for f in fields if f in data})

    try:
        clean = validate_product_data(merged)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400

    for key, value in clean.items():
        setattr(product, key, value)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Could not update product."}), 500

    return jsonify({
        "message": "Product updated successfully",
        "product": product.to_dict()
    })


@product_bp.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    try:
        db.session.delete(product)
        db.session.commit()
    except IntegrityError:
        # FIX: product still referenced by bargaining sessions / offers
        db.session.rollback()
        return jsonify({
            "message": "Cannot delete product: it has bargaining sessions or offers."
        }), 409

    return jsonify({"message": "Product deleted successfully"})