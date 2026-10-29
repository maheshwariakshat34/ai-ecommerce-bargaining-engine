import math
import re
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.models.product import Product, db
from backend.services.security import admin_required, has_admin_key, is_admin
from backend.services.clearance_engine import calculate_clearance_price


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


# a web link, or a file inside the frontend folder; no spaces or quotes
IMAGE_URL_PATTERN = re.compile(r"^(https?://|/|images/)[^\s\"'<>]+$")


def _image_url(value):
    """Photo link or None. Only http(s) links and local image paths are allowed."""
    if value is None or str(value).strip() == "":
        return None

    value = str(value).strip()

    if len(value) > 500 or not IMAGE_URL_PATTERN.match(value):
        raise ValueError(
            "image_url must be a link starting with http:// or https://, "
            "or a path like images/photo.jpg (no spaces)."
        )

    return value


def _expiry_date(d):
    """
    Expiry as a date. Accepts expiry_date ("YYYY-MM-DD") or, for older
    clients, days_to_expiry (number of days from today). Empty = no expiry.
    """
    raw = d.get("expiry_date")

    if isinstance(raw, date):
        return raw

    if raw not in (None, ""):
        try:
            return date.fromisoformat(str(raw).strip())
        except ValueError:
            raise ValueError("expiry_date must be a date like 2026-12-31.")

    days = d.get("days_to_expiry")

    if days in (None, ""):
        return None

    days = _int(days, "days_to_expiry", -36500)

    if days > 36500:
        raise ValueError("days_to_expiry is too large.")

    return date.today() + timedelta(days=days)


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

    if clean["sales_last_7_days"] > clean["sales_last_30_days"]:
        raise ValueError("sales_last_7_days cannot be greater than sales_last_30_days.")

    clean["expiry_date"] = _expiry_date(d)

    demand = str(d.get("demand_level") or "MEDIUM").upper()
    if demand not in VALID_DEMAND:
        raise ValueError("demand_level must be LOW, MEDIUM or HIGH.")
    clean["demand_level"] = demand

    clean["seasonal_factor"] = _num(
        d.get("seasonal_factor", 0), "seasonal_factor", -10**6
    )

    clean["image_url"] = _image_url(d.get("image_url"))
    return clean


def public_product(p):
    """What a customer may see. No cost, minimum price or sales data."""
    clearance = calculate_clearance_price(p)

    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "base_price": p.base_price,
        # current selling price per item (after any clearance discount)
        "price": clearance["clearance_price"],
        "discount_percent": clearance["discount_percent"],
        "stock": p.stock,
        # days left (None = no expiry); lets the shop show "Expires in 5 days"
        "days_to_expiry": p.days_to_expiry,
        "image_url": p.image_url
    }


@product_bp.route("/api/products", methods=["GET"])
def get_products():
    products = Product.query.all()

    # The shop always gets the customer view. The full list (cost, expired items)
    # is only for the seller dashboard (?view=admin) or tools using the admin key.
    if has_admin_key() or (request.args.get("view") == "admin" and is_admin()):
        return jsonify([p.to_dict() for p in products])

    # Customers do not see expired products
    visible = [
        item for item in products
        if item.days_to_expiry is None or item.days_to_expiry > 0
    ]

    return jsonify([public_product(item) for item in visible])


@product_bp.route("/api/products", methods=["POST"])
@admin_required
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
@admin_required
def update_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"message": "Request body must be valid JSON."}), 400

    fields = [
        "name", "category", "base_price", "cost_price", "minimum_price",
        "stock", "inventory_age", "expiry_date", "sales_last_7_days",
        "sales_last_30_days", "demand_level", "seasonal_factor", "image_url"
    ]

    # Merge existing values with updates, then validate the final result
    merged = {f: getattr(product, f) for f in fields}
    merged.update({f: data[f] for f in fields if f in data})

    # older clients may still send days_to_expiry (days from today)
    if "days_to_expiry" in data and "expiry_date" not in data:
        merged["expiry_date"] = None
        merged["days_to_expiry"] = data["days_to_expiry"]

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
@admin_required
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