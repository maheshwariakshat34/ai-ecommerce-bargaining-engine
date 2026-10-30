from datetime import datetime, timezone
from backend.models.product import db


class Order(db.Model):
    """A placed order (cart converted to order)."""

    __tablename__ = "orders"

    id       = db.Column(db.Integer,   primary_key=True)
    user_id  = db.Column(db.Integer,   db.ForeignKey("users.id"), nullable=False, index=True)
    status   = db.Column(db.String(20), nullable=False, default="PLACED")
    total    = db.Column(db.Float,      nullable=False)
    placed_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    items = db.relationship("OrderItem", backref="order", lazy=True,
                            cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":        self.id,
            "user_id":   self.user_id,
            "status":    self.status,
            "total":     self.total,
            "placed_at": self.placed_at.isoformat(),
            "items":     [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    """One line item inside an Order."""

    __tablename__ = "order_items"

    id             = db.Column(db.Integer,    primary_key=True)
    order_id       = db.Column(db.Integer,    db.ForeignKey("orders.id"), nullable=False)
    product_id     = db.Column(db.Integer,    nullable=True)
    product_name   = db.Column(db.String(200), nullable=False)
    quantity       = db.Column(db.Integer,    nullable=False)
    price_per_unit = db.Column(db.Float,      nullable=False)
    original_price = db.Column(db.Float,      nullable=False)

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
        }
