from backend.models.product import db


class BargainingSession(db.Model):

    __tablename__ = "bargaining_sessions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # BUG 15 FIX: tie session to the user who created it so other users
    # cannot submit offers or confirm deals on someone else's session.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True   # nullable so existing rows and guest sessions still work
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

    # BUG 4/8 FIX: tracks whether a CONFIRM is pending so process_offer()
    # can block new offers until the customer confirms or the session closes.
    confirming = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    def to_dict(self):

        return {
            "id": self.id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "quantity": self.quantity,
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "status": self.status,
            "final_price": self.final_price,
            "confirming": self.confirming
        }