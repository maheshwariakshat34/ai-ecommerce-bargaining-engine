import math

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from backend.models.product import Product, db
from backend.models.bargaining_session import BargainingSession
from backend.models.offer import Offer
from backend.services.pricing_engine import calculate_pricing


offer_bp = Blueprint("offer_bp", __name__)


def _to_int(value):
    # bool is a subclass of int (True -> 1), so reject it explicitly
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

    available_stock = product.stock or 0  # FIX: stock may be None

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
# SUBMIT CUSTOMER OFFER
# NOTE: customer_offer is the TOTAL price for the whole quantity.
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

    # FIX: float("nan") and float("inf") pass `<= 0` checks
    if not math.isfinite(customer_offer) or customer_offer <= 0:
        return jsonify({
            "error": "Customer offer must be a finite number greater than zero."
        }), 400

    # FIX: lock the row so two concurrent offers can't both use the same round
    session = db.session.get(
        BargainingSession, session_id, with_for_update=True
    )

    if not session:
        return jsonify({"error": "Bargaining session not found."}), 404

    if session.status != "ACTIVE":
        return jsonify({
            "error": "This bargaining session is no longer active.",
            "session_status": session.status,
            "final_price": session.final_price
        }), 400

    product = db.session.get(Product, session.product_id)

    if not product:
        return jsonify({
            "error": "Product associated with this session was not found."
        }), 404

    quantity = session.quantity
    current_round = session.current_round

    # FIX: stock may have changed since the session started
    if quantity > (product.stock or 0):
        return jsonify({
            "error": "Requested quantity exceeds available stock.",
            "available_stock": product.stock or 0
        }), 400

    # --------------------------------------------------
    # CALCULATE PRICING
    # --------------------------------------------------
    try:
        pricing = calculate_pricing(product, quantity)
    except (ValueError, TypeError, AttributeError) as error:
        return jsonify({
            "error": "Unable to calculate product pricing.",
            "details": str(error)
        }), 400

    clearance_total = float(pricing["clearance_total"])
    bulk_price = float(pricing["bulk_price"])
    cost_total = float(pricing["cost_total"])
    normal_minimum_total = float(pricing["normal_minimum_total"])

    if clearance_total < normal_minimum_total:
        negotiation_floor = cost_total
    else:
        negotiation_floor = max(cost_total, normal_minimum_total)

    target_price = round(max(bulk_price, negotiation_floor), 2)
    customer_offer = round(customer_offer, 2)

    # FIX: previous seller counter must be binding
    last_counter_offer = (
        Offer.query
        .filter(Offer.session_id == session.id,
                Offer.counter_price.isnot(None))
        .order_by(Offer.round_number.desc())
        .first()
    )
    previous_counter = (
        last_counter_offer.counter_price if last_counter_offer else None
    )

    # --------------------------------------------------
    # BARGAINING DECISION
    # --------------------------------------------------
    decision = None
    final_price = None
    counter_price = None
    response_message = ""

    is_final_round = current_round >= session.max_rounds

    # Work out whether the offer is acceptable and at what price.
    accept_price = None

    if customer_offer >= target_price:
        # FIX: charge the target price, never more than it
        # (previously rounds 1-2 charged the higher customer offer)
        accept_price = target_price

    elif previous_counter is not None and customer_offer >= previous_counter:
        # FIX: seller honours their own earlier counter-offer
        accept_price = previous_counter

    elif is_final_round and customer_offer >= negotiation_floor:
        accept_price = customer_offer

    if accept_price is not None:
        decision = "ACCEPT"
        final_price = round(accept_price, 2)
        response_message = f"Offer accepted at {final_price:.2f}."

    elif is_final_round:
        decision = "REJECT"
        response_message = (
            "Final offer rejected because it is below "
            "the minimum permitted price."
        )

    elif customer_offer >= target_price * 0.80:
        decision = "COUNTER"

        counter_price = max(
            negotiation_floor,
            (customer_offer + target_price) / 2
        )
        counter_price = min(counter_price, target_price)

        # FIX: seller must not raise the price versus the earlier counter
        if previous_counter is not None:
            counter_price = min(counter_price, previous_counter)

        counter_price = round(counter_price, 2)

        response_message = (
            f"Seller counter-offered at {counter_price:.2f}. "
            f"You may submit another offer."
        )

    else:
        decision = "REJECT"
        response_message = (
            "Offer is too low. Please submit a more "
            "reasonable offer in the next round."
        )

    # --------------------------------------------------
    # SAVE OFFER HISTORY
    # --------------------------------------------------
    offer = Offer(
        product_id=product.id,
        session_id=session.id,
        customer_offer=customer_offer,
        quantity=quantity,
        round_number=current_round,
        seller_response=decision,
        final_price=final_price,
        counter_price=counter_price
    )

    db.session.add(offer)

    # --------------------------------------------------
    # UPDATE SESSION STATUS
    # --------------------------------------------------
    if decision == "ACCEPT":
        session.status = "ACCEPTED"
        session.final_price = final_price
    elif is_final_round:
        session.status = "CLOSED"
    else:
        session.current_round += 1

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "This round was already submitted. Please retry."
        }), 409
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Could not save the offer."}), 500

    return jsonify({
        "message": response_message,
        "session_id": session.id,
        "product_id": product.id,
        "product_name": product.name,
        "quantity": quantity,
        "round_number": current_round,
        "max_rounds": session.max_rounds,
        "decision": decision,
        "customer_offer": customer_offer,
        "counter_price": counter_price,
        "final_price": final_price,
        "session_status": session.status,
        "pricing": {
            "base_total": pricing["base_total"],
            "clearance_unit_price": pricing["clearance_unit_price"],
            "clearance_total": pricing["clearance_total"],
            "clearance_level": pricing["clearance_level"],
            "pressure_score": pricing["pressure_score"],
            "clearance_reasons": pricing["clearance_reasons"],
            "bulk_discount_percent": pricing["bulk_discount_percent"],
            "bulk_discount_amount": pricing["bulk_discount_amount"],
            "nominal_bulk_discount_percent":
                pricing["nominal_bulk_discount_percent"],
            "nominal_bulk_discount_amount":
                pricing["nominal_bulk_discount_amount"],
            "bulk_price": pricing["bulk_price"],
            "negotiation_price": pricing["negotiation_price"],
            "normal_minimum_total": pricing["normal_minimum_total"],
            "cost_total": pricing["cost_total"],
            "cost_price_reached": pricing["cost_price_reached"],
            "negotiation_floor": round(negotiation_floor, 2),
            "target_price": target_price
        }
    }), 200


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
        "product": {
            "id": product.id,
            "name": product.name,
            "base_price": product.base_price,
            "cost_price": product.cost_price,
            "minimum_price": product.minimum_price,
            "stock": product.stock
        } if product else None,
        "bargaining_history": history
    }), 200