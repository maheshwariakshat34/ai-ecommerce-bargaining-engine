from flask import Blueprint, request, jsonify


from backend.models.product import Product,db
from backend.models.bargaining_session import BargainingSession
from backend.models.offer import Offer
from backend.services.pricing_engine import calculate_pricing


offer_bp = Blueprint("offer_bp", __name__)


# --------------------------------------------------
# START BARGAINING SESSION
# --------------------------------------------------
@offer_bp.route("/api/bargaining/start", methods=["POST"])
def start_bargaining():
    data = request.get_json(silent=True) or {}

    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    try:
        product_id = int(product_id)
        quantity = int(quantity)
    except (TypeError, ValueError):
        return jsonify({
            "error": "product_id and quantity must be valid integers."
        }), 400

    if quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than zero."
        }), 400

    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({
            "error": "Product not found."
        }), 404

    if quantity > product.stock:
        return jsonify({
            "error": "Requested quantity exceeds available stock.",
            "available_stock": product.stock
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
# --------------------------------------------------
@offer_bp.route("/api/bargaining/offer", methods=["POST"])
def submit_offer():
    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    customer_offer = data.get("customer_offer")

    try:
        session_id = int(session_id)
        customer_offer = float(customer_offer)
    except (TypeError, ValueError):
        return jsonify({
            "error": "session_id and customer_offer are required and must be valid numbers."
        }), 400

    if customer_offer <= 0:
        return jsonify({
            "error": "Customer offer must be greater than zero."
        }), 400

    session = db.session.get(BargainingSession, session_id)

    if not session:
        return jsonify({
            "error": "Bargaining session not found."
        }), 404

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

    # Normal bargaining floor is the seller's minimum price.
    # During clearance, the price may go below that minimum,
    # but must not go below the total cost price.
    if clearance_total < normal_minimum_total:
        negotiation_floor = cost_total
    else:
        negotiation_floor = max(cost_total, normal_minimum_total)

    # The customer must never be charged above the calculated
    # target price just because they submitted a higher offer.
    target_price = round(max(bulk_price, negotiation_floor), 2)

    customer_offer = round(customer_offer, 2)

    # --------------------------------------------------
    # BARGAINING DECISION
    # --------------------------------------------------
    decision = None
    final_price = None
    counter_price = None
    response_message = ""

    is_final_round = current_round >= session.max_rounds

    if not is_final_round:

        # Offer meets the target: accept at the target price.
        if customer_offer >= target_price:
            decision = "ACCEPT"
            final_price = customer_offer
            response_message = (
                f"Offer accepted at your offered price of "
                f"{final_price:.2f}."
            )

        # Reasonable but lower offer: seller makes a counter-offer.
        elif customer_offer >= target_price * 0.80:
            decision = "COUNTER"

            counter_price = round(
                max(
                    negotiation_floor,
                    (customer_offer + target_price) / 2
                ),
                2
            )

            # Do not create a counter-price above the target.
            counter_price = min(counter_price, target_price)

            response_message = (
                f"Seller counter-offered at {counter_price:.2f}. "
                f"You may submit another offer."
            )

        # Extremely low offers are rejected.
        else:
            decision = "REJECT"
            response_message = (
                "Offer is too low. Please submit a more "
                "reasonable offer in the next round."
            )

    else:
        # ROUND 3: FINAL DECISION
        # No further negotiation after this round.
        if customer_offer >= target_price:
            decision = "ACCEPT"
            final_price = target_price
            response_message = (
                f"Final offer accepted at {final_price:.2f}."
            )

        elif customer_offer >= negotiation_floor:
            decision = "ACCEPT"
            final_price = customer_offer
            response_message = (
                f"Final offer accepted at {final_price:.2f}."
            )

        else:
            decision = "REJECT"
            response_message = (
                "Final offer rejected because it is below "
                "the minimum permitted price."
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

    db.session.commit()

    # --------------------------------------------------
    # API RESPONSE
    # --------------------------------------------------
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
            "nominal_bulk_discount_percent": pricing[
                "nominal_bulk_discount_percent"
            ],
            "nominal_bulk_discount_amount": pricing[
                "nominal_bulk_discount_amount"
            ],
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
        return jsonify({
            "error": "Bargaining session not found."
        }), 404

    product = db.session.get(Product, session.product_id)

    offers = (
        Offer.query
        .filter_by(session_id=session.id)
        .order_by(Offer.round_number.asc())
        .all()
    )

    history = []

    for offer in offers:
        history.append({
            "offer_id": offer.id,
            "round_number": offer.round_number,
            "customer_offer": offer.customer_offer,
            "quantity": offer.quantity,
            "seller_response": offer.seller_response,
            "counter_price": offer.counter_price,
            "final_price": offer.final_price
        })

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
