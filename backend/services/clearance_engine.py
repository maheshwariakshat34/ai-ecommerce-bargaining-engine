def calculate_clearance_price(product):

    base_price = product.base_price
    cost_price = product.cost_price

    stock = product.stock or 0
    inventory_age = product.inventory_age or 0

    demand = (
        product.demand_level or "MEDIUM"
    ).upper()

    sales_last_7_days = (
        product.sales_last_7_days or 0
    )

    sales_last_30_days = (
        product.sales_last_30_days or 0
    )

    days_to_expiry = product.days_to_expiry

    # -----------------------------------------
    # 1. INVENTORY PRESSURE
    # -----------------------------------------
    # More stock = more clearance pressure

    inventory_pressure = min(
        stock / 50,
        1
    )


    # -----------------------------------------
    # 2. AGE PRESSURE
    # -----------------------------------------
    # Older inventory = more pressure

    age_pressure = min(
        inventory_age / 180,
        1
    )


    # -----------------------------------------
    # 3. DEMAND PRESSURE
    # -----------------------------------------

    demand_map = {
        "HIGH": 0.0,
        "MEDIUM": 0.5,
        "LOW": 1.0
    }

    demand_pressure = demand_map.get(
        demand,
        0.5
    )


    # -----------------------------------------
    # 4. SALES VELOCITY
    # -----------------------------------------

    sales_velocity_7d = (
        sales_last_7_days / 7
    )

    sales_velocity_30d = (
        sales_last_30_days / 30
    )

    # Recent sales get higher importance

    sales_velocity = (
        sales_velocity_7d * 0.6
        + sales_velocity_30d * 0.4
    )


    # Lower sales velocity = higher pressure

    velocity_pressure = max(
        0,
        min(
            1 - (sales_velocity / 5),
            1
        )
    )


    # -----------------------------------------
    # 5. EXPIRY PRESSURE
    # -----------------------------------------

    if days_to_expiry is None:

        # Products such as electronics
        # may not have an expiry date.

        expiry_pressure = 0

    else:

        expiry_pressure = max(
            0,
            min(
                (60 - days_to_expiry) / 60,
                1
            )
        )


    # -----------------------------------------
    # 6. TOTAL CLEARANCE PRESSURE
    # -----------------------------------------

    pressure_score = (

        inventory_pressure * 0.25

        + age_pressure * 0.20

        + demand_pressure * 0.20

        + velocity_pressure * 0.20

        + expiry_pressure * 0.15

    )

    pressure_score = min(
        max(
            pressure_score,
            0
        ),
        1
    )


    # -----------------------------------------
    # 7. DYNAMIC DISCOUNT
    # -----------------------------------------
    #
    # Maximum theoretical discount = 100%
    #
    # But cost_price protection below
    # prevents selling below actual cost.
    #
    # Therefore the actual discount depends
    # completely on the pressure score.
    #

    discount_percent = (
        pressure_score * 100
    )

    discount_percent = round(
        discount_percent,
        2
    )


    # -----------------------------------------
    # 8. CALCULATED CLEARANCE PRICE
    # -----------------------------------------

    discount_amount = (
        base_price
        * discount_percent
        / 100
    )

    calculated_price = (
        base_price
        - discount_amount
    )


    # -----------------------------------------
    # 9. ACTUAL COST PRICE PROTECTION
    # -----------------------------------------
    #
    # Clearance can go below minimum_price,
    # but NEVER below actual cost_price.
    #

    clearance_price = max(
        calculated_price,
        cost_price
    )

    clearance_price = round(
        clearance_price,
        2
    )


    # -----------------------------------------
    # 10. ACTUAL DISCOUNT
    # -----------------------------------------

    if base_price > 0:

        actual_discount = (
            (
                (base_price - clearance_price)
                / base_price
            )
            * 100
        )

    else:

        actual_discount = 0


    actual_discount = round(
        actual_discount,
        2
    )


    # -----------------------------------------
    # 11. CLEARANCE LEVEL
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
    # 12. REASONS
    # -----------------------------------------

    reasons = []


    if inventory_pressure >= 0.6:

        reasons.append(
            "High inventory level"
        )


    if age_pressure >= 0.6:

        reasons.append(
            "Aging inventory"
        )


    if demand_pressure >= 0.8:

        reasons.append(
            "Low demand"
        )


    if velocity_pressure >= 0.6:

        reasons.append(
            "Slow sales velocity"
        )


    if expiry_pressure >= 0.5:

        reasons.append(
            "Expiry urgency"
        )


    if not reasons:

        reasons.append(
            "Healthy inventory conditions"
        )


    # -----------------------------------------
    # 13. COST PRICE REACHED
    # -----------------------------------------

    cost_price_reached = (
        clearance_price <= cost_price
    )


    # -----------------------------------------
    # 14. FINAL RESPONSE
    # -----------------------------------------

    return {

        "base_price": base_price,

        "cost_price": cost_price,

        "minimum_price": product.minimum_price,

        "clearance_price": clearance_price,

        "discount_percent": actual_discount,

        "clearance_level": clearance_level,

        "pressure_score": round(
            pressure_score,
            3
        ),

        "inventory_pressure": round(
            inventory_pressure,
            3
        ),

        "age_pressure": round(
            age_pressure,
            3
        ),

        "demand_pressure": round(
            demand_pressure,
            3
        ),

        "velocity_pressure": round(
            velocity_pressure,
            3
        ),

        "expiry_pressure": round(
            expiry_pressure,
            3
        ),

        "sales_velocity": round(
            sales_velocity,
            3
        ),

        "cost_price_reached": cost_price_reached,

        "reasons": reasons
    }