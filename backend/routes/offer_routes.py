from flask import Blueprint, jsonify, request

from backend.models.product import Product, db
from backend.models.offer import Offer
from backend.models.bargaining_session import BargainingSession


offer_bp = Blueprint("offer", __name__)


# --------------------------------------------------
# BULK DISCOUNT
# --------------------------------------------------

def calculate_bulk_discount(quantity, base_price):

    if quantity >= 10:
        discount_percent = 8

    elif quantity >= 5:
        discount_percent = 5

    elif quantity >= 3:
        discount_percent = 3

    else:
        discount_percent = 0

    base_total = base_price * quantity

    discount_amount = (
        base_total * discount_percent / 100
    )

    discounted_total = (
        base_total - discount_amount
    )

    return (
        discount_percent,
        round(discount_amount, 2),
        round(discounted_total, 2)
    )


# --------------------------------------------------
# CREATE BARGAINING SESSION
# --------------------------------------------------

@offer_bp.route("/api/bargaining/start", methods=["POST"])
def start_bargaining():

    data = request.get_json()

    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if product_id is None:
        return jsonify({
            "message": "product_id is required"
        }), 400

    product = Product.query.get(product_id)

    if not product:
        return jsonify({
            "message": "Product not found"
        }), 404

    if quantity <= 0:
        return jsonify({
            "message": "Quantity must be greater than 0"
        }), 400

    if quantity > product.stock:
        return jsonify({
            "message": "Not enough stock available"
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
        "message": "Bargaining session started",
        "session": session.to_dict()
    }), 201


# --------------------------------------------------
# MAKE OFFER
# --------------------------------------------------

@offer_bp.route("/api/bargaining/offer", methods=["POST"])
def make_offer():

    data = request.get_json()

    session_id = data.get("session_id")
    customer_offer = data.get("customer_offer")

    if session_id is None or customer_offer is None:

        return jsonify({
            "message": "session_id and customer_offer are required"
        }), 400

    # --------------------------------------------------
    # FIND SESSION
    # --------------------------------------------------

    session = BargainingSession.query.get(session_id)

    if not session:

        return jsonify({
            "message": "Bargaining session not found"
        }), 404

    # --------------------------------------------------
    # CHECK SESSION STATUS
    # --------------------------------------------------

    if session.status != "ACTIVE":

        return jsonify({
            "message": "This bargaining session is already closed",
            "status": session.status
        }), 400

    # --------------------------------------------------
    # CHECK ROUND
    # --------------------------------------------------

    current_round = session.current_round

    if current_round > session.max_rounds:

        session.status = "EXPIRED"

        db.session.commit()

        return jsonify({
            "message": "Maximum bargaining rounds reached"
        }), 400

    # --------------------------------------------------
    # PRODUCT
    # --------------------------------------------------

    product = Product.query.get(session.product_id)

    if not product:

        return jsonify({
            "message": "Product not found"
        }), 404

    quantity = session.quantity

    # --------------------------------------------------
    # PRICE CALCULATIONS
    # --------------------------------------------------

    base_total = (
        product.base_price * quantity
    )

    minimum_total = (
        product.minimum_price * quantity
    )

    (
        bulk_discount_percent,
        bulk_discount_amount,
        bulk_price
    ) = calculate_bulk_discount(
        quantity,
        product.base_price
    )

    # Never go below seller minimum

    bulk_price = max(
        bulk_price,
        minimum_total
    )

    bulk_price = round(
        bulk_price,
        2
    )

    # --------------------------------------------------
    # BARGAINING DECISION
    # --------------------------------------------------

    decision = None
    final_price = None
    counter_price = None

    # ==================================================
    # ROUND 1
    # ==================================================

    if current_round == 1:

        # Very good offer
        if customer_offer >= bulk_price:

            decision = "ACCEPT"

            final_price = customer_offer

        # Reasonable offer
        elif customer_offer >= minimum_total * 0.90:

            decision = "COUNTER"

            # Conservative first counter
            negotiation_gap = (
                bulk_price - minimum_total
            )

            counter_price = (
                bulk_price
                - negotiation_gap * 0.25
            )

            counter_price = max(
                counter_price,
                minimum_total
            )

            counter_price = round(
                counter_price,
                2
            )

        else:

            decision = "REJECT"

    # ==================================================
    # ROUND 2
    # ==================================================

    elif current_round == 2:

        # Good offer
        if customer_offer >= bulk_price * 0.97:

            decision = "ACCEPT"

            final_price = customer_offer

        # Near minimum
        elif customer_offer >= minimum_total * 0.92:

            decision = "COUNTER"

            negotiation_gap = (
                bulk_price - minimum_total
            )

            counter_price = (
                minimum_total
                + negotiation_gap * 0.35
            )

            counter_price = max(
                counter_price,
                minimum_total
            )

            counter_price = round(
                counter_price,
                2
            )

        else:

            decision = "REJECT"

    # ==================================================
    # ROUND 3 - FINAL ROUND
    # ==================================================

    elif current_round == 3:

        # Seller's FINAL FIXED PRICE
        final_counter_price = max(
            minimum_total,
            round(
                minimum_total
                + (
                    (bulk_price - minimum_total)
                    * 0.50
                ),
                2
            )
        )

        # Customer meets final price
        if customer_offer >= final_counter_price:

            decision = "ACCEPT"

            final_price = final_counter_price

        else:

            decision = "COUNTER"

            counter_price = final_counter_price

    # --------------------------------------------------
    # SAVE OFFER
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
    # SESSION UPDATE
    # --------------------------------------------------

    if decision == "ACCEPT":

        session.status = "ACCEPTED"
        session.final_price = final_price

    elif current_round >= session.max_rounds:

        # After the final round, negotiation is closed
        session.status = "CLOSED"

    elif decision == "REJECT":

        # Reject only the current offer.
        # Allow the customer to make a better offer.
        session.current_round += 1

    else:

        # COUNTER
        # Move to the next round
        session.current_round += 1

    db.session.commit()

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return jsonify({

        "message": "Offer processed successfully",

        "session_id": session.id,

        "product": product.name,

        "quantity": quantity,

        "round": current_round,

        "max_rounds": session.max_rounds,

        "base_total": base_total,

        "bulk_discount_percent": bulk_discount_percent,

        "bulk_discount_amount": bulk_discount_amount,

        "bulk_price": bulk_price,

        "minimum_total": minimum_total,

        "customer_offer": customer_offer,

        "decision": decision,

        "counter_price": counter_price,

        "final_price": final_price,

        "session_status": session.status

    }), 201


# --------------------------------------------------
# GET BARGAINING HISTORY
# --------------------------------------------------

@offer_bp.route("/api/bargaining/session/<int:session_id>", methods=["GET"])
def get_bargaining_history(session_id):

    session = BargainingSession.query.get(session_id)

    if not session:
        return jsonify({
            "message": "Bargaining session not found"
        }), 404

    product = Product.query.get(session.product_id)

    offers = Offer.query.filter_by(
        session_id=session.id
    ).order_by(
        Offer.round_number.asc()
    ).all()

    return jsonify({

        "session": session.to_dict(),

        "product": product.to_dict()
        if product else None,

        "bargaining_history": [
            offer.to_dict()
            for offer in offers
        ]

    }), 200