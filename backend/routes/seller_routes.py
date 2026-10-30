"""
Seller Dashboard API Routes
GET /api/seller/dashboard  — summary stats
GET /api/seller/deals      — all confirmed bargaining deals
GET /api/seller/orders     — all placed orders
"""

from flask import Blueprint, jsonify
from backend.services.security import admin_required
from backend.models.product import db
from backend.models.bargaining_session import BargainingSession
from backend.models.order import Order, OrderItem
from backend.models.user import User
from backend.models.product import Product
from sqlalchemy import func

seller_bp = Blueprint("seller", __name__, url_prefix="/api/seller")


# ── helper ──────────────────────────────────────────────────────────────────
def _user_info(user_id):
    if user_id is None:
        return {"name": "Guest", "email": "—"}
    u = db.session.get(User, user_id)
    if u:
        return {"name": u.name, "email": u.email}
    return {"name": f"User #{user_id}", "email": "—"}


# ── 1. Dashboard summary ─────────────────────────────────────────────────────
@seller_bp.get("/dashboard")
@admin_required
def dashboard():
    total_deals = BargainingSession.query.filter_by(status="CONFIRMED").count()
    active_sessions = BargainingSession.query.filter_by(status="ACTIVE").count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(func.sum(Order.total)).scalar() or 0.0

    # Revenue from bargained deals (final_price * quantity)
    deal_revenue = (
        db.session.query(
            func.sum(BargainingSession.final_price * BargainingSession.quantity)
        )
        .filter(BargainingSession.status == "CONFIRMED")
        .scalar()
        or 0.0
    )

    return jsonify({
        "total_deals":       total_deals,
        "active_sessions":   active_sessions,
        "total_orders":      total_orders,
        "total_revenue":     round(float(total_revenue), 2),
        "deal_revenue":      round(float(deal_revenue), 2),
    })


# ── 2. All confirmed bargaining deals ────────────────────────────────────────
@seller_bp.get("/deals")
@admin_required
def deals():
    sessions = (
        BargainingSession.query
        .filter_by(status="CONFIRMED")
        .order_by(BargainingSession.id.desc())
        .all()
    )

    result = []
    for s in sessions:
        product = db.session.get(Product, s.product_id)
        user = _user_info(s.user_id)
        result.append({
            "session_id":    s.id,
            "product_id":    s.product_id,
            "product_name":  product.name if product else f"Product #{s.product_id}",
            "quantity":      s.quantity,
            "final_price":   round(float(s.final_price or 0), 2),
            "total_value":   round(float((s.final_price or 0) * s.quantity), 2),
            "original_price": round(float(product.price if product else 0), 2),
            "saved":         round(float(((product.price if product else 0) - (s.final_price or 0)) * s.quantity), 2),
            "rounds_used":   s.current_round,
            "max_rounds":    s.max_rounds,
            "buyer_name":    user["name"],
            "buyer_email":   user["email"],
        })

    return jsonify(result)


# ── 3. All placed orders ──────────────────────────────────────────────────────
@seller_bp.get("/orders")
@admin_required
def orders():
    all_orders = (
        Order.query
        .order_by(Order.placed_at.desc())
        .all()
    )

    result = []
    for o in all_orders:
        user = _user_info(o.user_id)
        result.append({
            "order_id":    o.id,
            "buyer_name":  user["name"],
            "buyer_email": user["email"],
            "status":      o.status,
            "total":       round(float(o.total), 2),
            "placed_at":   o.placed_at.isoformat() if o.placed_at else None,
            "items":       [item.to_dict() for item in o.items],
        })

    return jsonify(result)
