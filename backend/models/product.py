from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Product(db.Model):

    __tablename__ = "products"

    # -----------------------------------------
    # BASIC PRODUCT INFORMATION
    # -----------------------------------------

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False
    )


    # -----------------------------------------
    # PRICING
    # -----------------------------------------

    base_price = db.Column(
        db.Float,
        nullable=False
    )

    cost_price = db.Column(
        db.Float,
        nullable=False
    )

    # Minimum price for NORMAL bargaining
    minimum_price = db.Column(
        db.Float,
        nullable=False
    )


    # -----------------------------------------
    # INVENTORY
    # -----------------------------------------

    stock = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    inventory_age = db.Column(
        db.Integer,
        default=0
    )


    # -----------------------------------------
    # EXPIRY
    # -----------------------------------------

    # Nullable because electronics/clothing
    # may not have expiry.

    days_to_expiry = db.Column(
        db.Integer,
        nullable=True
    )


    # -----------------------------------------
    # SALES DATA
    # -----------------------------------------

    # Number of units sold in last 7 days

    sales_last_7_days = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )


    # Number of units sold in last 30 days

    sales_last_30_days = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )


    # -----------------------------------------
    # DEMAND
    # -----------------------------------------

    # HIGH / MEDIUM / LOW

    demand_level = db.Column(
        db.String(20),
        nullable=False,
        default="MEDIUM"
    )


    # -----------------------------------------
    # CONVERT PRODUCT TO JSON
    # -----------------------------------------

    def to_dict(self):

        return {

            "id": self.id,

            "name": self.name,

            "category": self.category,

            "base_price": self.base_price,

            "cost_price": self.cost_price,

            "minimum_price": self.minimum_price,

            "stock": self.stock,

            "inventory_age": self.inventory_age,

            "days_to_expiry": self.days_to_expiry,

            "sales_last_7_days": (
                self.sales_last_7_days
            ),

            "sales_last_30_days": (
                self.sales_last_30_days
            ),

            "demand_level": (
                self.demand_level
            )
        }