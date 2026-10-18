import math

from flask import Blueprint, request, jsonify

from backend.models.product import Product, db
from backend.models.bargaining_session import BargainingSession
from backend.models.offer import Offer
from backend.services.pricing_engine import calculate_pricing
from backend.services.bargaining_service import (
    process_offer,
    get_last_counter,
)
from backend.services.ai_negotiator import understand_message, write_reply
from backend.services.security import is_admin


offer_bp = Blueprint("offer_bp", __name__)


def _to_int(value):
    if isinstance(value, bool):
        raise ValueError("Invalid integer")
    return int(value)


# --------------------------------------------------
# START BARGAINING SESSION
# --------------------------------------------------
@offer_bp.route("/api/bargaining/start", methods=["POST"])
def start_bargaining():
    data = request.get_json(silent=True) or {}

    try:
        product_id = _to_int(data.get("product_id"))
        quantity = _to_int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({
            "error": "product_id and quantity must be valid integers."
        }), 400

    if quantity <= 0:
        return jsonify({"error": "Quantity must be greater than zero."}), 400

    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"error": "Product not found."}), 404

    available_stock = product.stock or 0

    if quantity > available_stock:
        return jsonify({
            "error": "Requested quantity exceeds available stock.",
            "available_stock": available_stock
        }), 400

    session = BargainingSession(
        product_id=product.id,
        quantity=quantity,
        current_round=1,
        max_rounds=3,
        status="ACTIVE"
    )

    db.session.add(session)
    db.session.commit()

    return jsonify({
        "message": "Bargaining session started successfully.",
        "session": session.to_dict(),
        "product": {
            "id": product.id,
            "name": product.name,
            "base_price": product.base_price,
            "quantity": quantity
        }
    }), 201


# --------------------------------------------------
# SUBMIT CUSTOMER OFFER (number, TOTAL price)
# --------------------------------------------------
@offer_bp.route("/api/bargaining/offer", methods=["POST"])
def submit_offer():
    data = request.get_json(silent=True) or {}

    try:
        session_id = _to_int(data.get("session_id"))
        customer_offer = float(data.get("customer_offer"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "session_id and customer_offer are required and must be valid numbers."
        }), 400

    if not math.isfinite(customer_offer) or customer_offer <= 0:
        return jsonify({
            "error": "Customer offer must be a finite number greater than zero."
        }), 400

    payload, status = process_offer(session_id, customer_offer)

    # Customers must never see cost, floor or target price
    if not is_admin():
        payload.pop("pricing", None)

    return jsonify(payload), status


# --------------------------------------------------
# AI CHAT (natural language: English / Hindi / Hinglish)
# --------------------------------------------------
@offer_bp.route("/api/bargaining/chat", methods=["POST"])
def bargaining_chat():
    data = request.get_json(silent=True) or {}

    try:
        session_id = _to_int(data.get("session_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "session_id must be a valid integer."}), 400

    message = str(data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "message is required."}), 400

    if len(message) > 500:
        return jsonify({"error": "message is too long (max 500 characters)."}), 400

    session = db.session.get(BargainingSession, session_id)

    if not session:
        return jsonify({"error": "Bargaining session not found."}), 404

    product = db.session.get(Product, session.product_id)

    if not product:
        return jsonify({"error": "Product not found."}), 404

    # 1. NLP: understand the customer message
    parsed = understand_message(message)

    base_ctx = {
        "product_name": product.name,
        "quantity": session.quantity,
        "round": session.current_round,
        "max_rounds": session.max_rounds,
    }

    # Session already finished
    if session.status != "ACTIVE":
        ctx = {**base_ctx, "type": "SESSION_ENDED"}
        return jsonify({
            "reply": write_reply(ctx, message),
            "session_status": session.status,
            "final_price": session.final_price,
            "understood": parsed
        }), 200

    # 2. Work out the TOTAL offer amount (rule engine works on totals)
    customer_offer = None

    if parsed["intent"] == "OFFER":
        amount = parsed["amount"]
        customer_offer = (
            amount if parsed["amount_type"] == "total"
            else amount * session.quantity
        )

    elif parsed["intent"] == "ACCEPT_COUNTER":
        customer_offer = get_last_counter(session.id)

        if customer_offer is None:
            ctx = {**base_ctx, "type": "NO_COUNTER"}
            return jsonify({
                "reply": write_reply(ctx, message),
                "session_status": session.status,
                "understood": parsed
            }), 200

    # 3a. Not an offer (question / other): answer, do not use up a round
    if customer_offer is None:
        try:
            asking_price = calculate_pricing(
                product, session.quantity
            )["clearance_total"]
        except (ValueError, TypeError, AttributeError):
            asking_price = product.base_price * session.quantity

        ctx = {**base_ctx, "type": "INFO", "asking_price": asking_price}
        return jsonify({
            "reply": write_reply(ctx, message),
            "session_status": session.status,
            "understood": parsed
        }), 200

    # 3b. Offer: rule engine decides
    if not math.isfinite(customer_offer) or customer_offer <= 0:
        return jsonify({"error": "Could not understand a valid price."}), 400

    result, status = process_offer(session.id, customer_offer)

    if status != 200:
        return jsonify(result), status

    # 4. NLP: word the decision (LLM only sees safe facts)
    ctx = {
        **base_ctx,
        "round": result["round_number"],
        "decision": result["decision"],
        "customer_offer": result["customer_offer"],
        "counter_price": result["counter_price"],
        "final_price": result["final_price"],
        "session_status": result["session_status"],
        "rounds_left": result["max_rounds"] - result["round_number"],
    }

    return jsonify({
        "reply": write_reply(ctx, message),
        "decision": result["decision"],
        "customer_offer": result["customer_offer"],
        "counter_price": result["counter_price"],
        "final_price": result["final_price"],
        "round_number": result["round_number"],
        "max_rounds": result["max_rounds"],
        "session_status": result["session_status"],
        "understood": parsed
    }), 200


def _session_product(product):
    if not product:
        return None

    data = {
        "id": product.id,
        "name": product.name,
        "base_price": product.base_price,
        "stock": product.stock
    }

    # Cost and minimum price: admin only
    if is_admin():
        data["cost_price"] = product.cost_price
        data["minimum_price"] = product.minimum_price

    return data


# --------------------------------------------------
# GET BARGAINING SESSION AND HISTORY
# --------------------------------------------------
@offer_bp.route("/api/bargaining/session/<int:session_id>", methods=["GET"])
def get_bargaining_session(session_id):
    session = db.session.get(BargainingSession, session_id)

    if not session:
        return jsonify({"error": "Bargaining session not found."}), 404

    product = db.session.get(Product, session.product_id)

    offers = (
        Offer.query
        .filter_by(session_id=session.id)
        .order_by(Offer.round_number.asc())
        .all()
    )

    history = [{
        "offer_id": o.id,
        "round_number": o.round_number,
        "customer_offer": o.customer_offer,
        "quantity": o.quantity,
        "seller_response": o.seller_response,
        "counter_price": o.counter_price,
        "final_price": o.final_price
    } for o in offers]

    return jsonify({
        "session": session.to_dict(),
        "product": _session_product(product),
        "bargaining_history": history
    }), 200