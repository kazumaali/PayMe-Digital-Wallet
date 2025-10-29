from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app)

# Simple JWT-like authentication (for demo purposes)
def create_token(user_id):
    return hashlib.sha256(f"{user_id}{secrets.token_hex(16)}".encode()).hexdigest()

def verify_token(token):
    # In a real app, you'd validate the token properly
    return True

def get_user_from_token(token):
    # Simple demo implementation
    # In production, use proper JWT decoding
    return token

# Database setup
def init_db():
    conn = sqlite3.connect('wallet.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Wallet table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            usd_balance REAL DEFAULT 0.0,
            usdt_balance REAL DEFAULT 0.0,
            irr_balance REAL DEFAULT 0.0,
            usdt_address TEXT UNIQUE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            last4 TEXT NOT NULL,
            holder_name TEXT,
            expiry_month INTEGER,
            expiry_year INTEGER,
            currency TEXT NOT NULL,
            bank_name TEXT,
            card_number TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            description TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Exchange Service
class ExchangeService:
    def get_current_rates(self):
        try:
            response = requests.get('https://www.tgju.org/profile/price_dollar_rl', timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find the price (this might need adjustment based on the actual page structure)
            price_element = soup.find('span', {'class': 'value'}) or soup.find('div', {'class': 'price'})
            if price_element:
                price_text = price_element.text.strip().replace(',', '')
                usd_to_irr = float(price_text)
            else:
                usd_to_irr = 42000  # Fallback
                
        except Exception as e:
            print(f"Error fetching rates: {e}")
            usd_to_irr = 42000  # Fallback rate
        
        rates = {
            'USD_IRR': usd_to_irr,
            'IRR_USD': 1 / usd_to_irr,
            'USD_USDT': 1.0,
            'USDT_USD': 1.0,
            'USDT_IRR': usd_to_irr,
            'IRR_USDT': 1 / usd_to_irr,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return rates

# Initialize database
init_db()
exchange_service = ExchangeService()

# Helper functions for database operations
def get_db_connection():
    conn = sqlite3.connect('wallet.db')
    conn.row_factory = sqlite3.Row
    return conn

# Authentication middleware
def require_auth(f):
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or not verify_token(token):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# Routes
@app.route('/')
def hello():
    return jsonify({"message": "PayMe Wallet API", "status": "Running"})
    
    
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

@app.route('/api/exchange-rates', methods=['GET'])
def get_exchange_rates():
    rates = exchange_service.get_current_rates()
    return jsonify(rates)

@app.route('/api/wallet/balance', methods=['GET'])
@require_auth
def get_balance():
    user_id = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    
    conn = get_db_connection()
    wallet = conn.execute(
        'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
    ).fetchone()
    
    if not wallet:
        # Create wallet if it doesn't exist
        wallet_id = secrets.token_hex(16)
        conn.execute(
            'INSERT INTO wallets (id, user_id) VALUES (?, ?)',
            (wallet_id, user_id)
        )
        conn.commit()
        wallet = conn.execute(
            'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
        ).fetchone()
    
    balance = {
        'USD': wallet['usd_balance'] or 0.0,
        'USDT': wallet['usdt_balance'] or 0.0,
        'IRR': wallet['irr_balance'] or 0.0
    }
    
    conn.close()
    return jsonify(balance)

@app.route('/api/wallet/usdt/address', methods=['GET'])
@require_auth
def get_usdt_address():
    user_id = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    
    conn = get_db_connection()
    wallet = conn.execute(
        'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
    ).fetchone()
    
    if not wallet or not wallet['usdt_address']:
        # Generate new USDT address
        usdt_address = "0x" + hashlib.sha256(f"{user_id}{secrets.token_hex(16)}".encode()).hexdigest()[:40]
        
        if not wallet:
            wallet_id = secrets.token_hex(16)
            conn.execute(
                'INSERT INTO wallets (id, user_id, usdt_address) VALUES (?, ?, ?)',
                (wallet_id, user_id, usdt_address)
            )
        else:
            conn.execute(
                'UPDATE wallets SET usdt_address = ? WHERE user_id = ?',
                (usdt_address, user_id)
            )
        
        conn.commit()
    else:
        usdt_address = wallet['usdt_address']
    
    conn.close()
    return jsonify({'usdt_address': usdt_address})

@app.route('/api/payment/send', methods=['POST'])
@require_auth
def send_money():
    user_id = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    data = request.get_json()
    
    amount = data.get('amount')
    currency = data.get('currency')
    recipient_email = data.get('recipient_email')
    message = data.get('message', '')
    
    if not all([amount, currency, recipient_email]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    # Check sender balance
    sender_wallet = conn.execute(
        'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
    ).fetchone()
    
    balance_field = f"{currency.lower()}_balance"
    current_balance = sender_wallet[balance_field] or 0.0
    
    if current_balance < amount:
        conn.close()
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # Find recipient
    recipient = conn.execute(
        'SELECT * FROM users WHERE email = ?', (recipient_email,)
    ).fetchone()
    
    if not recipient:
        conn.close()
        return jsonify({'error': 'Recipient not found'}), 404
    
    # Update balances
    conn.execute(
        f'UPDATE wallets SET {balance_field} = {balance_field} - ? WHERE user_id = ?',
        (amount, user_id)
    )
    
    recipient_wallet = conn.execute(
        'SELECT * FROM wallets WHERE user_id = ?', (recipient['id'],)
    ).fetchone()
    
    if recipient_wallet:
        conn.execute(
            f'UPDATE wallets SET {balance_field} = {balance_field} + ? WHERE user_id = ?',
            (amount, recipient['id'])
        )
    else:
        wallet_id = secrets.token_hex(16)
        conn.execute(
            f'INSERT INTO wallets (id, user_id, {balance_field}) VALUES (?, ?, ?)',
            (wallet_id, recipient['id'], amount)
        )
    
    # Record transactions
    tx_id = secrets.token_hex(16)
    conn.execute(
        'INSERT INTO transactions (id, user_id, type, amount, currency, status, description, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (tx_id, user_id, 'send', amount, currency, 'completed', f'Transfer to {recipient_email}', json.dumps({
            'recipient': recipient_email,
            'message': message
        }))
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'transaction_id': tx_id,
        'amount': amount,
        'currency': currency,
        'recipient': recipient_email
    })

# Add more routes as needed...

if __name__ == '__main__':
    print("Starting PayMe Wallet API...")
    print("API will be available at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)