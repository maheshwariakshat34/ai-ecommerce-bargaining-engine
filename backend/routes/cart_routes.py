"""Cart & Order routes.

GET  /api/cart              — current user's cart items
DELETE /api/cart/<item_id>  — remove one item from cart
POST /api/orders/place      — convert cart → placed order
GET  /api/orders            — current user's order history
"""

from flask import Blueprint, jsonify

from backend.models.product import db
from backend.models.cart import CartItem
from backend.models.order import Order, OrderItem
from backend.services.security import bargaining_login_required, current_user

cart_bp = Blueprint("cart_bp", __name__)


# ------------------------------------------------------------------
# CART
# ------------------------------------------------------------------

@cart_bp.route("/api/cart", methods=["GET"])
@bargaining_login_required
def get_cart():
    user  = current_user()
    items = CartItem.query.filter_by(user_id=user.id).order_by(CartItem.added_at.asc()).all()

    total       = round(sum(i.price_per_unit * i.quantity for i in items), 2)
    total_saved = round(sum(max(i.original_price - i.price_per_unit, 0) * i.quantity for i in items), 2)

    return jsonify({
        "items":       [i.to_dict() for i in items],
        "count":       len(items),
        "total":       total,
        "total_saved": total_saved,
    }), 200


@cart_bp.route("/api/cart/<int:item_id>", methods=["DELETE"])
@bargaining_login_required
def remove_from_cart(item_id):
    user = current_user()
    item = CartItem.query.filter_by(id=item_id, user_id=user.id).first()

    if not item:
        return jsonify({"error": "Cart item not found."}), 404

    db.session.delete(item)
    db.session.commit()

    # Return updated count
    remaining = CartItem.query.filter_by(user_id=user.id).count()
    return jsonify({"message": "Item removed from cart.", "count": remaining}), 200


# ------------------------------------------------------------------
# ORDERS
# ------------------------------------------------------------------

@cart_bp.route("/api/orders/place", methods=["POST"])
@bargaining_login_required
def place_order():
    user  = current_user()
    items = CartItem.query.filter_by(user_id=user.id).all()

    if not items:
        return jsonify({"error": "Your cart is empty."}), 400

    total = round(sum(i.price_per_unit * i.quantity for i in items), 2)

    order = Order(user_id=user.id, status="PLACED", total=total)
    db.session.add(order)
    db.session.flush()   # get order.id before adding children

    for item in items:
        order_item = OrderItem(
            order_id       = order.id,
            product_id     = item.product_id,
            product_name   = item.product_name,
            quantity       = item.quantity,
            price_per_unit = item.price_per_unit,
            original_price = item.original_price,
        )
        db.session.add(order_item)
        db.session.delete(item)   # clear from cart

    db.session.commit()

    return jsonify({
        "message": "Order placed successfully!",
        "order":   order.to_dict(),
    }), 201


@cart_bp.route("/api/orders", methods=["GET"])
@bargaining_login_required
def get_orders():
    user   = current_user()
    orders = (
        Order.query
        .filter_by(user_id=user.id)
        .order_by(Order.placed_at.desc())
        .all()
    )
    return jsonify({"orders": [o.to_dict() for o in orders]}), 200
