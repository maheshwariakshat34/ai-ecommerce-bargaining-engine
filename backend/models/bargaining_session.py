from backend.models.product import db


class BargainingSession(db.Model):

    __tablename__ = "bargaining_sessions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    current_round = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    max_rounds = db.Column(
        db.Integer,
        nullable=False,
        default=3
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="ACTIVE"
    )

    final_price = db.Column(
        db.Float,
        nullable=True
    )

    def to_dict(self):

        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "status": self.status,
            "final_price": self.final_price,
            "sales_last_7_days": self.sales_last_7_days,
            "sales_last_30_days": self.sales_last_30_days,
            "demand_level": self.demand_level,
            "seasonal_factor": self.seasonal_factor
        }