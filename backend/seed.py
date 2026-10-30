import os
import re
import sys
from datetime import date, timedelta

from sqlalchemy import inspect

from backend.app import app
from backend.models.product import db, Product
from backend.models.user import User


# Photos: put a file named like the product in frontend/images/ and run
# python seed.py --reset. Example: "Wireless Headphones" -> wireless-headphones.jpg
# (jpg, jpeg, png or webp). python seed.py --names prints every file name.
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "images")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def local_image(name):
    for ext in ("jpg", "jpeg", "png", "webp"):
        if os.path.exists(os.path.join(IMAGE_DIR, slug(name) + "." + ext)):
            return "images/" + slug(name) + "." + ext
    return None


def P(name, category, base, cost, minimum, stock, age, expiry_in_days,
      s7, s30, demand, season=0.0, image=None):
    return dict(
        name=name, category=category,
        base_price=base, cost_price=cost, minimum_price=minimum,
        stock=stock, inventory_age=age,
        expiry_date=(
            None if expiry_in_days is None
            else date.today() + timedelta(days=expiry_in_days)
        ),
        sales_last_7_days=s7, sales_last_30_days=s30,
        demand_level=demand, seasonal_factor=season,
        image_url=local_image(name) or image,
    )


PRODUCTS = [

    # ================= ELECTRONICS =================
    # Hot seller, low stock -> no discount
    P("Wireless Headphones", "Electronics", 2000, 1300, 1600, 8, 20, None, 12, 45, "HIGH"),
    # Old + slow -> medium clearance
    P("Smart Watch", "Electronics", 5000, 3500, 4200, 10, 120, None, 1, 4, "LOW"),
    # Healthy, steady seller
    P("Bluetooth Speaker", "Electronics", 3500, 2200, 2800, 14, 35, None, 9, 36, "HIGH"),
    # Dead stock: no sales at all in 30 days
    P("Old Model Tablet", "Electronics", 15000, 11000, 12500, 12, 175, None, 0, 0, "LOW"),
    # Good stock level, bulk-friendly
    P("USB-C Cable (1m)", "Electronics", 400, 150, 220, 120, 40, None, 25, 100, "MEDIUM"),
    # Sales slowing down: 30-day average high, last week very low
    P("Power Bank 10000mAh", "Electronics", 1800, 1100, 1400, 25, 80, None, 2, 20, "MEDIUM"),

    # ================= FOOTWEAR =================
    P("Sports Shoes", "Footwear", 3000, 2100, 2500, 15, 70, None, 4, 16, "MEDIUM"),
    # Seasonal leftover, very old
    P("Winter Boots", "Footwear", 4500, 3000, 3600, 22, 160, None, 1, 6, "LOW", -0.3),
    # New arrival, strong sales
    P("Running Shoes Pro", "Footwear", 5500, 3800, 4600, 9, 12, None, 10, 28, "HIGH"),
    P("Flip Flops", "Footwear", 500, 220, 320, 60, 55, None, 8, 30, "MEDIUM"),

    # ================= CLOTHING =================
    # Old + high stock
    P("Cotton T-Shirt", "Clothing", 1000, 600, 750, 30, 120, None, 1, 5, "LOW"),
    P("Denim Jeans", "Clothing", 2200, 1300, 1700, 20, 30, None, 7, 26, "HIGH"),
    # Out-of-season, huge stock
    P("Woolen Sweater", "Clothing", 2500, 1500, 1900, 40, 150, None, 1, 4, "LOW", -0.4),
    P("Hooded Jacket", "Clothing", 3200, 1900, 2400, 18, 65, None, 3, 14, "MEDIUM"),
    # Bulk friendly basic
    P("Cotton Socks (pair)", "Clothing", 200, 80, 120, 150, 90, None, 10, 45, "MEDIUM"),

    # ================= FOOD (EXPIRY) =================
    # Expires in 20 days, slow seller
    P("Protein Bar", "Food", 500, 300, 380, 50, 90, 20, 2, 8, "LOW"),
    # Expires in 5 days -> deep clearance
    P("Fresh Orange Juice", "Food", 120, 70, 90, 60, 14, 5, 10, 40, "MEDIUM"),
    # Plenty of shelf life -> no expiry pressure
    P("Basmati Rice 5kg", "Food", 750, 520, 600, 40, 25, 300, 8, 32, "HIGH"),
    # Expires in 3 days, lots of stock -> deepest clearance
    P("Cream Biscuits", "Food", 60, 35, 45, 200, 40, 10, 15, 60, "MEDIUM"),
    # Moderate expiry window
    P("Green Tea (100 bags)", "Food", 450, 280, 340, 35, 60, 45, 3, 12, "MEDIUM"),

    # ================= HOME & KITCHEN =================
    P("Non-stick Pan", "Home & Kitchen", 1500, 900, 1150, 16, 50, None, 5, 20, "MEDIUM"),
    P("Electric Kettle", "Home & Kitchen", 1800, 1100, 1400, 12, 100, None, 2, 9, "LOW"),
    P("LED Desk Lamp", "Home & Kitchen", 900, 500, 650, 45, 140, None, 2, 8, "LOW"),

    # ================= BEAUTY =================
    # 40 days left, slow seller -> mild discount
    P("Face Moisturizer", "Beauty", 650, 350, 450, 28, 85, 40, 3, 14, "MEDIUM"),
    P("Shampoo 500ml", "Beauty", 400, 220, 290, 70, 30, 200, 12, 48, "HIGH"),

    # ================= SPORTS & STATIONERY =================
    P("Yoga Mat", "Sports", 1200, 650, 850, 25, 75, None, 3, 15, "MEDIUM"),
    P("Cricket Bat", "Sports", 3800, 2400, 3000, 8, 110, None, 1, 5, "LOW"),
    P("Notebook (pack of 5)", "Stationery", 350, 180, 240, 100, 20, None, 20, 80, "HIGH"),

    # ================= EXPIRY TEST CASES =================

    P("Fresh Bread Loaf", "Food", 80, 40, 55, 25, 2, 5, 8, 30, "MEDIUM"),

    P("Expired Yogurt Cup", "Food", 60, 30, 40, 18, 30, 6, 4, 20, "MEDIUM"),
]


def ensure_seller():
    """Creates the seller (admin) account if it does not exist yet."""
    email = (os.getenv("ADMIN_EMAIL") or "seller@smartshop.com").strip().lower()
    password = os.getenv("ADMIN_PASSWORD")

    if User.query.filter_by(email=email).first():
        print(f"Seller account already exists: {email}")
        return

    seller = User(name="Seller", email=email, role="admin")
    seller.set_password(password or "seller123")
    db.session.add(seller)
    db.session.commit()

    print(f"Seller account created: {email}")
    if not password:
        print("WARNING: it uses the default password 'seller123'. "
              "Put ADMIN_PASSWORD=... in your .env file and run  python seed.py --reset  to change it.")


def seed(reset=False):
    with app.app_context():

        if reset:
            db.session.remove()
            db.drop_all()
            db.create_all()
            print("Tables rebuilt (old products, sessions, offers and users removed).")
        else:
            db.create_all()

            columns = {c["name"] for c in inspect(db.engine).get_columns("products")}
            if not {"expiry_date", "image_url"} <= columns:
                print("Your database is from an older version (missing expiry_date or image_url).")
                print("Run:  python seed.py --reset")
                return

        existing = {name for (name,) in db.session.query(Product.name).all()}
        added = 0

        for data in PRODUCTS:
            if data["name"] in existing:
                continue
            assert data["cost_price"] <= data["minimum_price"] <= data["base_price"], \
                f"Bad price order for {data['name']}"
            db.session.add(Product(**data))
            added += 1

        db.session.commit()
        print(f"{added} products added, {len(PRODUCTS) - added} already existed.")

        ensure_seller()


if __name__ == "__main__":
    if "--names" in sys.argv:
        for item in PRODUCTS:
            print(slug(item["name"]) + ".jpg")
    else:
        seed(reset="--reset" in sys.argv)
