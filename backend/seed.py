from backend.app import app
from backend.models.product import db, Product


products = [

    # -----------------------------------------
    # 1. HIGH DEMAND ELECTRONICS
    # -----------------------------------------

    Product(
        name="Wireless Headphones",
        category="Electronics",

        base_price=2000,
        cost_price=1300,
        minimum_price=1600,

        stock=8,
        inventory_age=20,

        days_to_expiry=None,

        sales_last_7_days=12,
        sales_last_30_days=45,

        demand_level="HIGH"
    ),


    # -----------------------------------------
    # 2. OLD + SLOW ELECTRONICS
    # -----------------------------------------

    Product(
        name="Smart Watch",
        category="Electronics",

        base_price=5000,
        cost_price=3500,
        minimum_price=4200,

        stock=10,
        inventory_age=120,

        days_to_expiry=None,

        sales_last_7_days=1,
        sales_last_30_days=4,

        demand_level="LOW"
    ),


    # -----------------------------------------
    # 3. MEDIUM DEMAND FOOTWEAR
    # -----------------------------------------

    Product(
        name="Sports Shoes",
        category="Footwear",

        base_price=3000,
        cost_price=2100,
        minimum_price=2500,

        stock=15,
        inventory_age=70,

        days_to_expiry=None,

        sales_last_7_days=4,
        sales_last_30_days=16,

        demand_level="MEDIUM"
    ),


    # -----------------------------------------
    # 4. OLD + HIGH STOCK CLOTHING
    # -----------------------------------------

    Product(
        name="Cotton T-Shirt",
        category="Clothing",

        base_price=1000,
        cost_price=600,
        minimum_price=750,

        stock=30,
        inventory_age=120,

        days_to_expiry=None,

        sales_last_7_days=1,
        sales_last_30_days=5,

        demand_level="LOW"
    ),


    # -----------------------------------------
    # 5. NEAR EXPIRY FOOD
    # -----------------------------------------

    Product(
        name="Protein Bar",
        category="Food",

        base_price=500,
        cost_price=300,
        minimum_price=380,

        stock=50,
        inventory_age=90,

        days_to_expiry=20,

        sales_last_7_days=2,
        sales_last_30_days=8,

        demand_level="LOW"
    )
]


with app.app_context():

    db.create_all()

    db.session.add_all(products)

    db.session.commit()

    print(
        "Products inserted successfully!"
    )