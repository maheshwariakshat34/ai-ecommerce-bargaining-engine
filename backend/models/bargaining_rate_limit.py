from datetime import datetime
from backend.models.product import db


class BargainingRateLimit(db.Model):

    __tablename__ = "bargaining_rate_limits"

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "product_id", "date",
            name="uq_rate_limit_user_product_day",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    session_count = db.Column(db.Integer, nullable=False, default=0)
    last_session_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
