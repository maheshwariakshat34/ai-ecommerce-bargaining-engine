"""
Core bargaining logic, shared by /api/bargaining/offer and /api/bargaining/chat.
The rule engine (not the AI) decides every price.
"""

from sqlalchemy.exc import IntegrityError

from backend.models.product import Product, db
from backend.models.bargaining_session import BargainingSession
from backend.models.offer import Offer
from backend.services.pricing_engine import calculate_pricing

# In clearance mode the floor is the cost price. Keep a small margin above it
# so that a final-round deal never happens at exactly zero profit.
SAFETY_MARGIN = 0.02


def get_last_counter(session_id):
    """Return the seller's most recent counter price in this session, or None."""
    last = (
        Offer.query
        .filter(Offer.session_id == session_id,
                Offer.counter_price.isnot(None))
        .order_by(Offer.round_number.desc())
        .first()
    )
    return last.counter_price if last else None


def process_offer(session_id, customer_offer):
    """
    customer_offer = TOTAL price for the whole quantity.
    Returns (payload_dict, http_status).
    """
    session = db.session.get(
        BargainingSession, session_id, with_for_update=True
    )

    if not session:
        return {"error": "Bargaining session not found."}, 404

    if session.status != "ACTIVE":
        return {
            "error": "This bargaining session is no longer active.",
            "session_status": session.status,
            "final_price": session.final_price
        }, 400

    product = db.session.get(Product, session.product_id)

    if not product:
        return {
            "error": "Product associated with this session was not found."
        }, 404

    if product.days_to_expiry is not None and product.days_to_expiry <= 0:
        return {"error": "This product has expired and cannot be sold."}, 400

    quantity = session.quantity
    current_round = session.current_round

    if quantity > (product.stock or 0):
        return {
            "error": "Requested quantity exceeds available stock.",
            "available_stock": product.stock or 0
        }, 400

    try:
        pricing = calculate_pricing(product, quantity)
    except (ValueError, TypeError, AttributeError) as error:
        return {
            "error": "Unable to calculate product pricing.",
            "details": str(error)
        }, 400

    clearance_total = float(pricing["clearance_total"])
    bulk_price = float(pricing["bulk_price"])
    cost_total = float(pricing["cost_total"])
    normal_minimum_total = float(pricing["normal_minimum_total"])

    if clearance_total < normal_minimum_total:
        # clearance mode: floor is cost plus a small margin (never above the list price)
        negotiation_floor = min(cost_total * (1 + SAFETY_MARGIN), clearance_total)
    else:
        negotiation_floor = max(cost_total, normal_minimum_total)

    target_price = round(max(bulk_price, negotiation_floor), 2)
    customer_offer = round(customer_offer, 2)

    previous_counter = get_last_counter(session.id)

    decision = None
    final_price = None
    counter_price = None
    message = ""

    is_final_round = current_round >= session.max_rounds

    accept_price = None

    if customer_offer >= target_price:
        accept_price = target_price
    elif previous_counter is not None and customer_offer >= previous_counter:
        accept_price = previous_counter
    elif is_final_round and customer_offer >= negotiation_floor:
        accept_price = customer_offer

    if accept_price is not None:
        decision = "ACCEPT"
        final_price = round(accept_price, 2)
        message = f"Offer accepted at {final_price:.2f}."

    elif is_final_round:
        decision = "REJECT"
        message = (
            "Final offer rejected because it is below "
            "the minimum permitted price."
        )

    elif customer_offer >= target_price * 0.80:
        decision = "COUNTER"

        # Start from the seller's last price (target first, then the previous counter)
        # so the seller moves towards the customer every round.
        reference = previous_counter if previous_counter is not None else target_price
        counter_price = max(negotiation_floor, (customer_offer + reference) / 2)
        counter_price = round(min(counter_price, reference), 2)
        message = (
            f"Seller counter-offered at {counter_price:.2f}. "
            f"You may submit another offer."
        )

    else:
        decision = "REJECT"
        message = (
            "Offer is too low. Please submit a more "
            "reasonable offer in the next round."
        )

    db.session.add(Offer(
        product_id=product.id,
        session_id=session.id,
        customer_offer=customer_offer,
        quantity=quantity,
        round_number=current_round,
        seller_response=decision,
        final_price=final_price,
        counter_price=counter_price
    ))

    if decision == "ACCEPT":
        session.status = "ACCEPTED"
        session.final_price = final_price

        # Deal done: reduce stock and record the sale in ONE atomic update,
        # so two simultaneous deals can never sell the same last units.
        updated = Product.query.filter(
            Product.id == product.id,
            Product.stock >= quantity
        ).update({
            Product.stock: Product.stock - quantity,
            Product.sales_last_7_days: Product.sales_last_7_days + quantity,
            Product.sales_last_30_days: Product.sales_last_30_days + quantity,
        }, synchronize_session=False)

        if updated == 0:
            db.session.rollback()
            return {
                "error": "Stock changed while the deal was being made. Please try again."
            }, 409

    elif is_final_round:
        session.status = "CLOSED"
    else:
        session.current_round += 1

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {
            "error": "This round was already submitted. Please retry."
        }, 409
    except Exception:
        db.session.rollback()
        return {"error": "Could not save the offer."}, 500

    return {
        "message": message,
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
    }, 200