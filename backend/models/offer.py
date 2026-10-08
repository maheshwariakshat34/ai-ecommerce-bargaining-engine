from backend.models.product import db


class Offer(db.Model):

    __tablename__ = "offers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("bargaining_sessions.id"),
        nullable=False
    )

    customer_offer = db.Column(
        db.Float,
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    round_number = db.Column(
        db.Integer,
        nullable=False
    )

    seller_response = db.Column(
        db.String(20),
        nullable=False
    )

    final_price = db.Column(
        db.Float,
        nullable=True
    )

    counter_price = db.Column(
        db.Float,
        nullable=True
    )

    def to_dict(self):

        return {
            "id": self.id,
            "product_id": self.product_id,
            "session_id": self.session_id,
            "customer_offer": self.customer_offer,
            "quantity": self.quantity,
            "round_number": self.round_number,
            "seller_response": self.seller_response,
            "final_price": self.final_price,
            "counter_price": self.counter_price
        }