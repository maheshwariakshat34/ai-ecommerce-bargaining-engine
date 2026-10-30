from datetime import datetime, timezone
from backend.models.product import db


class CartItem(db.Model):
    """One bargained item sitting in the user's cart before placing the order."""

    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=True
    )

    # Snapshot fields so the cart stays correct even if the product changes
    product_name     = db.Column(db.String(200), nullable=False)
    quantity         = db.Column(db.Integer,     nullable=False)
    price_per_unit   = db.Column(db.Float,       nullable=False)   # bargained price
    original_price   = db.Column(db.Float,       nullable=False)   # list price at deal time

    session_id = db.Column(db.Integer, nullable=True)   # reference to BargainingSession
    added_at   = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        saved = round((self.original_price - self.price_per_unit) * self.quantity, 2)
        return {
            "id":             self.id,
            "product_id":     self.product_id,
            "product_name":   self.product_name,
            "quantity":       self.quantity,
            "price_per_unit": self.price_per_unit,
            "original_price": self.original_price,
            "total":          round(self.price_per_unit * self.quantity, 2),
            "saved":          max(saved, 0),
            "session_id":     self.session_id,
            "added_at":       self.added_at.isoformat(),
        }
