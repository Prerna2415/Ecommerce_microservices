from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    idempotency_key = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'idempotency_key',
            name='uq_order_user_idempotency'
        ),
    )