from sqlalchemy.exc import IntegrityError
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from models import db, Order
from config import PRODUCT_SERVICE_URL
import requests

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)

jwt = JWTManager(app)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    user_id = get_jwt_identity()

    # Every order request must contain an idempotency key.
    idempotency_key = request.headers.get('Idempotency-Key')

    if not idempotency_key:
        return jsonify({
            'message': 'Idempotency-Key header is required'
        }), 400

    # Check whether this request has already been processed.
    existing_order = Order.query.filter_by(
        idempotency_key=idempotency_key
    ).first()

    if existing_order:
        return jsonify({
            'id': existing_order.id,
            'status': existing_order.status,
            'message': 'Order already exists'
        }), 200

    data = request.json

    if not data or 'product_id' not in data or 'quantity' not in data:
        return jsonify({
            'message': 'product_id and quantity are required'
        }), 400

    product_id = data['product_id']
    quantity = data['quantity']

    if quantity <= 0:
        return jsonify({
            'message': 'Quantity must be greater than zero'
        }), 400

    # Get the JWT token from the current request.
    authorization_header = request.headers.get('Authorization')

    if not authorization_header:
        return jsonify({
            'message': 'Authorization header is required'
        }), 401

    access_token = authorization_header.split(' ')[1]
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Get product information from Product Management service.
    product_response = requests.get(
        f'{PRODUCT_SERVICE_URL}/products/{product_id}',
        headers=headers
    )

    if product_response.status_code != 200:
        return jsonify({
            'message': 'Product not found'
        }), 404

    product = product_response.json()

    # Check whether enough stock is available.
    if product['quantity'] < quantity:
        return jsonify({
            'message': 'Insufficient stock'
        }), 400

    # Create the order.
    new_order = Order(
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
        idempotency_key=idempotency_key
    )

    db.session.add(new_order)

    try:
        db.session.commit()
    except IntegrityError:
        # Another request with the same idempotency key
        # was processed concurrently.
        db.session.rollback()

        existing_order = Order.query.filter_by(
            user_id=user_id,
            idempotency_key=idempotency_key
        ).first()

        if existing_order:
            return jsonify({
                'id': existing_order.id,
                'status': existing_order.status,
                'message': 'Order already exists'
            }), 200

        return jsonify({
            'message': 'Unable to create order'
        }), 500

    # Update the product stock.
    updated_stock = product['quantity'] - quantity

    product_update_response = requests.put(
        f'{PRODUCT_SERVICE_URL}/products/{product_id}',
        json={'quantity': updated_stock},
        headers=headers
    )

    if product_update_response.status_code != 200:
        return jsonify({
            'message': 'Order created but product stock could not be updated'
        }), 500

    return jsonify({
        'id': new_order.id,
        'status': new_order.status
    }), 201

@app.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    user_id = get_jwt_identity()
    orders = Order.query.filter_by(user_id=user_id).all()
    return jsonify([{'id': order.id, 'product_id': order.product_id, 'quantity': order.quantity, 'status': order.status} for order in orders]), 200

if __name__ == '__main__':
    app.run(debug=True, port=5002)
