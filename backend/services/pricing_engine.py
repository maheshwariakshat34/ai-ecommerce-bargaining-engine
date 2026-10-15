from backend.services.clearance_engine import calculate_clearance_price


def calculate_bulk_discount(quantity, unit_price):
    if quantity >= 10:
        discount_percent = 8
    elif quantity >= 5:
        discount_percent = 5
    elif quantity >= 3:
        discount_percent = 3
    else:
        discount_percent = 0

    base_total = unit_price * quantity
    discount_amount = base_total * discount_percent / 100
    discounted_total = base_total - discount_amount

    return {
        "discount_percent": discount_percent,
        "discount_amount": round(discount_amount, 2),
        "discounted_total": round(discounted_total, 2)
    }


def calculate_pricing(product, quantity):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    clearance = calculate_clearance_price(product)

    base_total = product.base_price * quantity
    clearance_unit_price = clearance["clearance_price"]
    clearance_total = clearance_unit_price * quantity
    cost_total = product.cost_price * quantity

    bulk = calculate_bulk_discount(
        quantity,
        clearance_unit_price
    )

    # Protect the seller's total product cost.
    final_bulk_price = max(
        bulk["discounted_total"],
        cost_total
    )

    # Report the discount actually applied after cost protection.
    actual_discount_amount = max(
        0,
        round(clearance_total - final_bulk_price, 2)
    )

    actual_discount_percent = (
        round((actual_discount_amount / clearance_total) * 100, 2)
        if clearance_total > 0
        else 0
    )

    return {
        "base_total": round(base_total, 2),
        "clearance_unit_price": round(clearance_unit_price, 2),
        "clearance_total": round(clearance_total, 2),

        # Actual discount after cost protection
        "bulk_discount_percent": actual_discount_percent,
        "bulk_discount_amount": actual_discount_amount,

        # Original bulk tier, useful for transparency
        "nominal_bulk_discount_percent": bulk["discount_percent"],
        "nominal_bulk_discount_amount": bulk["discount_amount"],

        "bulk_price": round(final_bulk_price, 2),
        "negotiation_price": round(final_bulk_price, 2),

        "normal_minimum_total": round(
            product.minimum_price * quantity, 2
        ),
        "cost_total": round(cost_total, 2),

        "clearance_level": clearance["clearance_level"],
        "pressure_score": clearance["pressure_score"],
        "clearance_reasons": clearance["reasons"],

        "cost_price_reached": final_bulk_price <= cost_total
    }
