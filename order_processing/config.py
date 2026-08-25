import os

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///orders.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_secret_key')
PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:9002')
