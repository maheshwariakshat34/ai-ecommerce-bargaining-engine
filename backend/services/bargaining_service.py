"""
Core bargaining logic, shared by /api/bargaining/offer and /api/bargaining/chat.
The rule engine (not the AI) decides every price.
"""

import math
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from backend.models.product import Product, db
from backend.models.bargaining_session import BargainingSession
from backend.models.offer import Offer
from backend.models.bargaining_rate_limit import BargainingRateLimit
from backend.services.pricing_engine import calculate_pricing
from backend.services.clearance_engine import calculate_dynamic_floor

# Final round: the customer must cover this share of the gap between the
# negotiation floor and the seller's last price (last counter, or target if
# there was none). 0 = accept anything above the floor (old behaviour),
# 1 = the customer must meet the seller's last price.
FINAL_ROUND_ACCEPT_SHARE = 0.5


def is_session_expired(session):
    """Return True if the session is no longer usable."""
    if session.status != "ACTIVE":
        return True
    if session.expires_at is None:
        return False
    return datetime.utcnow() > session.expires_at


def refresh_session_activity(session):
    """Extend expiry after any valid customer action."""
    timeout = current_app.config.get("BARGAINING_SESSION_TIMEOUT_MINUTES", 15)
    now = datetime.utcnow()
    session.last_activity_at = now
    session.expires_at = now + timedelta(minutes=timeout)
    return session


def expire_session(session):
    """Mark an active session as expired."""
    session.status = "EXPIRED"
    session.last_activity_at = datetime.utcnow()
    return session


def check_rate_limit(user_id, product_id):
    """
    Return (allowed: bool, message: str).
    Skipped for guests (user_id is None).
    Enforces daily session count + cooling-off between sessions.
    """
    if user_id is None:
        return True, ""
    today = datetime.utcnow().date()
    max_sessions = current_app.config.get("RATE_LIMIT_SESSIONS_PER_DAY", 3)
    cooling_off = current_app.config.get("COOLING_OFF_MINUTES", 10)
    record = BargainingRateLimit.query.filter_by(
        user_id=user_id,
        product_id=product_id,
        date=today,
    ).first()
    if record is None:
        return True, ""
    if record.session_count >= max_sessions:
        return False, (
            f"You have already bargained {max_sessions} times on this product today. "
            "Please try again tomorrow."
        )
    if record.last_session_at:
        elapsed = (datetime.utcnow() - record.last_session_at).total_seconds() / 60
        if elapsed < cooling_off:
            remaining = int(cooling_off - elapsed) + 1
            return False, f"Please wait {remaining} minute(s) before starting a new session."
    return True, ""


def record_session_start(user_id, product_id):
    """Increment today's session counter for this user+product. Skipped for guests."""
    if user_id is None:
        return
    today = datetime.utcnow().date()
    record = BargainingRateLimit.query.filter_by(
        user_id=user_id,
        product_id=product_id,
        date=today,
    ).first()
    if record is None:
        record = BargainingRateLimit(
            user_id=user_id,
            product_id=product_id,
            date=today,
            session_count=1,
            last_session_at=datetime.utcnow(),
        )
        db.session.add(record)
    else:
        record.session_count += 1
        record.last_session_at = datetime.utcnow()
    db.session.commit()


def get_last_counter_offer(session_id):
    """Return the Offer row that holds the seller's most recent price, or None."""
    return (
        Offer.query
        .filter(Offer.session_id == session_id,
                Offer.counter_price.isnot(None))
        .order_by(Offer.round_number.desc())
        .first()
    )


def get_last_counter(session_id):
    """Return the seller's most recent counter price in this session, or None."""
    last = get_last_counter_offer(session_id)
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


    if session.confirming:
        waiting = get_last_counter_offer(session.id)
        return {
            "error": "A price is waiting for your confirmation. "
                     "Please confirm the deal.",
            "awaiting_confirmation": True,
            "pending_price": waiting.counter_price if waiting else None,
            "session_status": session.status
        }, 409

    if current_round > session.max_rounds:

        # Block it cleanly rather than letting an extra free offer through.
        return {
            "error": "No more rounds available. This negotiation has ended.",
            "session_status": session.status,
        }, 409

    if current_round >= session.max_rounds:
        waiting = get_last_counter_offer(session.id)

        if waiting is not None:
            return {
                "error": "A price is waiting for your confirmation. "
                         "Please confirm the deal.",
                "awaiting_confirmation": True,
                "pending_price": waiting.counter_price,
                "session_status": session.status
            }, 409

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

    # Phase 2: dynamic floor — scales with clearance pressure so a heavily
    # discounted product floors lower than a healthy-stock one.
    pressure = pricing["pressure_score"]
    floor_unit = calculate_dynamic_floor(product, pressure)
    dynamic_floor_total = floor_unit * quantity

    if clearance_total < normal_minimum_total:
        # Clearance mode: use dynamic floor, but never above the clearance price
        negotiation_floor = min(dynamic_floor_total, clearance_total)
    else:
        negotiation_floor = max(dynamic_floor_total, normal_minimum_total)

    target_price = round(max(bulk_price, negotiation_floor), 2)
    customer_offer = round(customer_offer, 2)

    previous_counter = get_last_counter(session.id)

    decision = None
    final_price = None
    counter_price = None
    message = ""

    is_final_round = current_round >= session.max_rounds

    # Seller's last stated price, and the lowest offer we take in the final round
    last_price = previous_counter if previous_counter is not None else target_price
    last_price = max(last_price, negotiation_floor)
    # BUG 7 FIX: explicitly clamp final_round_min to negotiation_floor
    final_round_min = max(
        round(negotiation_floor + FINAL_ROUND_ACCEPT_SHARE * (last_price - negotiation_floor), 2),
        negotiation_floor
    )

    accept_price = None
    is_final_counter = False   # Phase 2: signals this is the absolute floor offer

    # The seller's own standing price comes first, so a customer is never asked
    # to pay more than a price the seller already offered.
    if previous_counter is not None and customer_offer >= previous_counter:
        accept_price = previous_counter
    elif customer_offer >= target_price:
        accept_price = target_price
    elif is_final_round and customer_offer >= final_round_min:
        accept_price = customer_offer

    if accept_price is not None:
        # The price is agreed, but the deal is NOT made yet. It becomes final
        # only when the customer confirms it (see confirm_deal below).
        decision = "CONFIRM"
        counter_price = round(accept_price, 2)
        message = (
            f"{counter_price:.2f} is acceptable. "
            f"Waiting for the customer to confirm the deal."
        )

    elif is_final_round:
        # Phase 2 fix: instead of a hard REJECT on the final round, counter at
        # exactly the dynamic floor so the buyer always gets one last clear price.
        decision = "COUNTER"
        counter_price = round(negotiation_floor, 2)
        is_final_counter = True
        message = (
            f"This is our absolute final price: {counter_price:.2f}. "
            "We cannot go any lower."
        )

    elif customer_offer >= target_price * 0.80:
        decision = "COUNTER"

        # Start from the seller's last price (target first, then the previous counter)
        # so the seller moves towards the customer every round.
        reference = previous_counter if previous_counter is not None else target_price

        reference = round(float(reference), 2)
        counter_price = max(negotiation_floor, (customer_offer + reference) / 2)
        # Whole rupees, rounded up, so the customer sees a clean number
        counter_price = math.ceil(counter_price)
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
        # a price waiting for confirmation is stored as a counter price
        seller_response="COUNTER" if decision == "CONFIRM" else decision,
        final_price=final_price,
        counter_price=counter_price
    ))

    if decision == "CONFIRM":
        # Nothing is sold yet. Set confirming=True so no new offer can bypass

        session.confirming = True
        if not is_final_round:
            session.current_round += 1
    elif is_final_round and is_final_counter:
        # Phase 2: bot countered at floor on final round — set confirming so the
        # buyer can only accept or walk away; session stays ACTIVE for confirmation.
        session.confirming = True
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
        "awaiting_confirmation": decision == "CONFIRM",
        "pending_price": counter_price if decision == "CONFIRM" else None,
        "is_final_offer": is_final_counter,
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
            "normal_minimum_total": pricing["normal_minimum_total"],
            "cost_total": pricing["cost_total"],
            "cost_price_reached": pricing["cost_price_reached"],
            "negotiation_floor": round(negotiation_floor, 2),
            "target_price": target_price
        }
    }, 200


def confirm_deal(session_id):
    """
    The customer confirms the seller's last price. ONLY here is the deal made:
    the session is closed as ACCEPTED, and stock and sales are updated.
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

    offer = get_last_counter_offer(session.id)

    if offer is None:
        return {
            "error": "There is no price to confirm yet. Please make an offer first."
        }, 400

    quantity = session.quantity
    price = round(float(offer.counter_price), 2)

    try:
        pricing = calculate_pricing(product, quantity)
    except (ValueError, TypeError, AttributeError) as error:
        return {
            "error": "Unable to calculate product pricing.",
            "details": str(error)
        }, 400

    # Safety net: never sell below cost, even if the price changed since it was offered
    if price < float(pricing["cost_total"]) - 0.005:
        return {
            "error": "This price is no longer available. Please make a new offer."
        }, 409

    offer.seller_response = "ACCEPT"
    offer.final_price = price

    session.status = "ACCEPTED"
    session.final_price = price
    session.confirming = False   # BUG 4 FIX: clear the pending-confirm flag

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

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return {"error": "Could not save the deal."}, 500

    return {
        "message": f"Deal confirmed at {price:.2f}.",
        "confirmed": True,
        "session_id": session.id,
        "product_id": product.id,
        "product_name": product.name,
        "quantity": quantity,
        "round_number": offer.round_number,
        "max_rounds": session.max_rounds,
        "decision": "ACCEPT",
        "customer_offer": price,
        "counter_price": price,
        "final_price": price,
        "session_status": session.status
    }, 200