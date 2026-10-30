"""
Dynamic clearance engine (real-world style markdown pricing).

Rules:
1. Stock is measured as "days of cover" (stock / daily sales), not raw units.
2. Sales trend matters: recent 7-day rate vs 30-day average.
3. No discount while pressure is below CLEARANCE_THRESHOLD (healthy stock).
4. Discount grows with pressure but is capped at MAX_DISCOUNT_PERCENT.
5. Expiry sets a minimum pressure that grows smoothly as the date gets
   closer (0 at 60 days left, 1 on the expiry day).
6. Price never goes below cost_price and never above base_price.
"""

import math

MAX_DISCOUNT_PERCENT = 50      # hard cap on clearance discount
CLEARANCE_THRESHOLD = 0.20     # below this pressure -> no discount

COVER_OK_DAYS = 30             # <= 30 days of stock is healthy
COVER_BAD_DAYS = 120           # >= 120 days of stock is max pressure
AGE_MAX_DAYS = 180
EXPIRY_WINDOW_DAYS = 60


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(value, high))


def _round_price(value):
    """Round UP to a clean shop price: whole rupee under Rs 100, else next Rs 5."""
    step = 1 if value < 100 else 5
    return math.ceil(round(value, 2) / step) * step


def calculate_clearance_price(product):

    base_price = float(product.base_price or 0)
    cost_price = float(product.cost_price or 0)
    minimum_price = float(product.minimum_price or 0)

    stock = max(product.stock or 0, 0)
    inventory_age = max(product.inventory_age or 0, 0)
    demand = (product.demand_level or "MEDIUM").upper()
    sales_7d = max(product.sales_last_7_days or 0, 0)
    sales_30d = max(product.sales_last_30_days or 0, 0)
    days_to_expiry = product.days_to_expiry

    # BUG 6 FIX: 0-stock items cannot be sold; return list price with no discount
    if stock == 0:
        return {
            "base_price": base_price,
            "cost_price": cost_price,
            "minimum_price": minimum_price,
            "clearance_price": base_price,
            "discount_percent": 0.0,
            "clearance_level": "NORMAL",
            "pressure_score": 0.0,
            "inventory_pressure": 0.0,
            "age_pressure": 0.0,
            "demand_pressure": 0.0,
            "velocity_pressure": 0.0,
            "expiry_pressure": 0.0,
            "sales_velocity": 0.0,
            "days_of_cover": 0.0,
            "cost_price_reached": False,
            "reasons": ["Out of stock"],
        }

    # SALES VELOCITY (units/day)

    recent_rate = sales_7d / 7
    average_rate = sales_30d / 30

    sales_velocity = recent_rate * 0.6 + average_rate * 0.4


    # 1. INVENTORY PRESSURE (days of cover)

    if sales_velocity > 0:
        days_of_cover = stock / sales_velocity
    else:
        days_of_cover = 999 if stock > 0 else 0

    inventory_pressure = _clamp(
        (days_of_cover - COVER_OK_DAYS)
        / (COVER_BAD_DAYS - COVER_OK_DAYS)
    )


    # 2. AGE PRESSURE

    age_pressure = _clamp(inventory_age / AGE_MAX_DAYS)

    # -----------------------------------------
    # 3. DEMAND PRESSURE
    # -----------------------------------------
    demand_pressure = {
        "HIGH": 0.0,
        "MEDIUM": 0.5,
        "LOW": 1.0
    }.get(demand, 0.5)

    # -----------------------------------------
    # 4. SALES TREND PRESSURE
    # -----------------------------------------
    # Recent sales slower than the 30-day average = slowing demand.
    if average_rate > 0:
        velocity_pressure = _clamp(1 - recent_rate / average_rate)
    else:
        # No sales at all in 30 days
        velocity_pressure = 1.0 if stock > 0 else 0.0

    # -----------------------------------------
    # 5. EXPIRY PRESSURE
    # -----------------------------------------
    if days_to_expiry is None:
        expiry_pressure = 0.0
    else:
        expiry_pressure = _clamp(
            (EXPIRY_WINDOW_DAYS - days_to_expiry) / EXPIRY_WINDOW_DAYS
        )

    # -----------------------------------------
    # 6. TOTAL PRESSURE
    # -----------------------------------------
    pressure_score = (
        inventory_pressure * 0.25
        + age_pressure * 0.20
        + demand_pressure * 0.15
        + velocity_pressure * 0.20
        + expiry_pressure * 0.20
    )

    # Stock that is close to its expiry date must move, whatever the other
    # signals say. The minimum rises a little every day, so the price keeps
    # falling as the date gets closer instead of stopping at one level.
    pressure_score = max(pressure_score, expiry_pressure)

    pressure_score = _clamp(pressure_score)

    # -----------------------------------------
    # 7. DISCOUNT (thresholded + capped)
    # -----------------------------------------
    if pressure_score < CLEARANCE_THRESHOLD:
        discount_percent = 0.0
    else:
        scaled = (
            (pressure_score - CLEARANCE_THRESHOLD)
            / (1 - CLEARANCE_THRESHOLD)
        )
        discount_percent = min(
            scaled * MAX_DISCOUNT_PERCENT,
            MAX_DISCOUNT_PERCENT
        )

    calculated_price = base_price * (1 - discount_percent / 100)

    # -----------------------------------------
    # 8. COST PROTECTION (never below cost, never above base)
    # -----------------------------------------
    clearance_price = round(
        min(max(_round_price(calculated_price), cost_price), base_price), 2
    )

    actual_discount = (
        round((base_price - clearance_price) / base_price * 100, 2)
        if base_price > 0 else 0
    )

    # -----------------------------------------
    # 9. CLEARANCE LEVEL
    # -----------------------------------------
    if pressure_score >= 0.80:
        clearance_level = "EXTREME"
    elif pressure_score >= 0.60:
        clearance_level = "URGENT"
    elif pressure_score >= 0.40:
        clearance_level = "HIGH"
    elif pressure_score >= 0.20:
        clearance_level = "MEDIUM"
    else:
        clearance_level = "NORMAL"

    # -----------------------------------------
    # 10. REASONS
    # -----------------------------------------
    reasons = []

    if inventory_pressure >= 0.5:
        reasons.append(
            f"Overstock: about {round(days_of_cover)} days of stock"
            if days_of_cover < 999 else "Overstock: no recent sales"
        )
    if age_pressure >= 0.6:
        reasons.append("Aging inventory")
    if demand_pressure >= 0.8:
        reasons.append("Low demand")
    if velocity_pressure >= 0.5:
        reasons.append("Sales are slowing down")
    if expiry_pressure >= 0.5:
        reasons.append("Expiry urgency")
    if not reasons:
        reasons.append("Healthy inventory conditions")

    return {
        "base_price": base_price,
        "cost_price": cost_price,
        "minimum_price": minimum_price,
        "clearance_price": clearance_price,
        "discount_percent": actual_discount,
        "clearance_level": clearance_level,
        "pressure_score": round(pressure_score, 3),
        "inventory_pressure": round(inventory_pressure, 3),
        "age_pressure": round(age_pressure, 3),
        "demand_pressure": round(demand_pressure, 3),
        "velocity_pressure": round(velocity_pressure, 3),
        "expiry_pressure": round(expiry_pressure, 3),
        "sales_velocity": round(sales_velocity, 3),
        "days_of_cover": round(days_of_cover, 1),
        "cost_price_reached": clearance_price <= cost_price,
        "reasons": reasons
    }