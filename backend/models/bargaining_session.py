from datetime import datetime, timedelta
from backend.models.product import db


class BargainingSession(db.Model):

    __tablename__ = "bargaining_sessions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )


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


    # can block new offers until the customer confirms or the session closes.
    confirming = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_activity_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

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
            "confirming": self.confirming,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
