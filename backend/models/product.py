from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Product(db.Model):

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    category = db.Column(db.String(50), nullable=False)

    base_price = db.Column(db.Float, nullable=False)

    cost_price = db.Column(db.Float, nullable=False)

    minimum_price = db.Column(db.Float, nullable=False)

    stock = db.Column(db.Integer, nullable=False, default=0)

    inventory_age = db.Column(db.Integer, default=0)

    days_to_expiry = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<Product {self.name}>"