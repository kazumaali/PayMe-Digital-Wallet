from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    wallet = db.relationship('Wallet', backref='user', lazy=True, uselist=False)
    cards = db.relationship('Card', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Wallet(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    usd_balance = db.Column(db.Float, default=0.0)
    usdt_balance = db.Column(db.Float, default=0.0)
    irr_balance = db.Column(db.Float, default=0.0)
    usdt_address = db.Column(db.String(255), unique=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Card(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'visa', 'mastercard', 'iranian_bank'
    last4 = db.Column(db.String(4), nullable=False)
    holder_name = db.Column(db.String(100))
    expiry_month = db.Column(db.Integer)
    expiry_year = db.Column(db.Integer)
    currency = db.Column(db.String(3), nullable=False)  # USD, IRR
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For Iranian cards
    bank_name = db.Column(db.String(50))
    card_number = db.Column(db.String(16))  # encrypted in production

class Transaction(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # charge, withdraw, send, receive, exchange
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    description = db.Column(db.Text)
    metadata = db.Column(db.JSON)  # Additional data like recipient, card info, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For exchanges
    from_currency = db.Column(db.String(3))
    to_currency = db.Column(db.String(3))
    exchange_rate = db.Column(db.Float)