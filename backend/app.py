from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
import sys

# Add the current directory to Python path to import services
sys.path.append(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app)

# Import services
try:
    from services.exchange_service import ExchangeService
    from services.wallet_service import WalletService
    from services.payment_service import PaymentService
    print("✅ Successfully imported all services")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("⚠️  Running without additional services")

# Initialize services
exchange_service = ExchangeService()
wallet_service = WalletService()
payment_service = PaymentService()

# Simple JWT-like authentication (for demo purposes)
def create_token(user_id):
    return hashlib.sha256(f"{user_id}{secrets.token_hex(16)}".encode()).hexdigest()

def verify_token(token):
    # In a real app, you'd validate the token properly
    # For demo, we'll just check if it exists
    return bool(token and len(token) > 10)

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
    print("✅ Database initialized successfully")

# Exchange Service - Updated with better scraping
class ExchangeService:
    def get_current_rates(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get('https://www.tgju.org/profile/price_dollar_rl', 
                                  timeout=10, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Multiple strategies to find the price
            usd_to_irr = self.extract_price(soup)
            
            if not usd_to_irr:
                print("Could not extract price, using fallback")
                usd_to_irr = 1070000  # Current approximate rate
                
        except Exception as e:
            print(f"Error fetching rates: {e}")
            usd_to_irr = 1070000  # Current fallback rate
        
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
    
    def extract_price(self, soup):
        """Try multiple strategies to extract the USD price"""
        # Strategy 1: Look for the main price display
        price_selectors = [
            '[data-col="info.last_price"]',
            '.price',
            '.value',
            '.info-price',
            '#main > div > div > div > div.market-section > ul > li:nth-child(1) > span',
            'span.value',
            'div.value'
        ]
        
        for selector in price_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    price = self.clean_price(price_text)
                    if price and 100000 < price < 2000000:  # Reasonable range
                        print(f"Found price using selector '{selector}': {price}")
                        return price
            except Exception as e:
                continue
        
        # Strategy 2: Look for tables or specific structures
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                for i, cell in enumerate(cells):
                    if 'دلار' in cell.text or 'dollar' in cell.text.lower():
                        if i + 1 < len(cells):
                            price = self.clean_price(cells[i + 1].text)
                            if price:
                                return price
        
        # Strategy 3: Search for numeric values that look like prices
        import re
        text = soup.get_text()
        # Look for numbers with commas (Iranian format)
        price_patterns = [
            r'(\d{1,3}(?:,\d{3})*)',  # Numbers with commas
            r'(\d{6,7})',  # 6-7 digit numbers (current IRR range)
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                price = self.clean_price(match)
                if price and 1000000 < price < 1200000:  # Current expected range
                    print(f"Found price using regex: {price}")
                    return price
        
        return None
    
    def clean_price(self, price_text):
        """Clean and convert price text to float"""
        try:
            # Remove commas and convert to float
            cleaned = price_text.replace(',', '').strip()
            # Remove any non-numeric characters except decimal point
            cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '.')
            if cleaned:
                return float(cleaned)
        except Exception as e:
            print(f"Error cleaning price '{price_text}': {e}")
        return None

# Initialize database
init_db()

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
    return jsonify({"message": "PayMe Wallet API", "status": "Running", "version": "1.0"})

@app.route('/api/test')
def test_api():
    return jsonify({"message": "API is working!", "timestamp": datetime.utcnow().isoformat()})

@app.route('/api/test-services')
def test_services():
    try:
        rates = exchange_service.get_current_rates()
        return jsonify({
            'status': 'Services connected successfully',
            'exchange_rate': rates.get('USD_IRR', 'N/A'),
            'services': ['exchange', 'wallet', 'payment'],
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'Service connection failed: {str(e)}'}), 500

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

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    if not all([email, username, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    # Check if user already exists
    existing_user = conn.execute(
        'SELECT * FROM users WHERE email = ? OR username = ?', (email, username)
    ).fetchone()
    
    if existing_user:
        conn.close()
        return jsonify({'error': 'User already exists'}), 400
    
    # Create new user
    user_id = secrets.token_hex(16)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn.execute(
        'INSERT INTO users (id, email, username, password_hash, verified) VALUES (?, ?, ?, ?, ?)',
        (user_id, email, username, password_hash, True)  # Auto-verify for demo
    )
    
    # Create wallet
    wallet_id = secrets.token_hex(16)
    conn.execute(
        'INSERT INTO wallets (id, user_id) VALUES (?, ?)',
        (wallet_id, user_id)
    )
    
    conn.commit()
    conn.close()
    
    token = create_token(user_id)
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user_id,
            'email': email,
            'username': username
        }
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({'error': 'Missing email or password'}), 400
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE email = ?', (email,)
    ).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user['password_hash'] != password_hash:
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = create_token(user['id'])
    conn.close()
    
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'username': user['username']
        }
    })

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

@app.route('/api/payment/charge', methods=['POST'])
@require_auth
def charge_wallet():
    user_id = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    data = request.get_json()
    
    amount = data.get('amount')
    currency = data.get('currency')
    payment_method = data.get('payment_method', 'card')
    
    if not all([amount, currency]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Simulate payment processing
    conn = get_db_connection()
    
    # Update wallet balance
    wallet = conn.execute(
        'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
    ).fetchone()
    
    balance_field = f"{currency.lower()}_balance"
    
    if wallet:
        conn.execute(
            f'UPDATE wallets SET {balance_field} = {balance_field} + ? WHERE user_id = ?',
            (amount, user_id)
        )
    else:
        wallet_id = secrets.token_hex(16)
        conn.execute(
            f'INSERT INTO wallets (id, user_id, {balance_field}) VALUES (?, ?, ?)',
            (wallet_id, user_id, amount)
        )
    
    # Record transaction
    tx_id = secrets.token_hex(16)
    conn.execute(
        'INSERT INTO transactions (id, user_id, type, amount, currency, status, description, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (tx_id, user_id, 'charge', amount, currency, 'completed', f'Wallet charge - {currency}', json.dumps({
            'payment_method': payment_method
        }))
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'transaction_id': tx_id,
        'amount': amount,
        'currency': currency
    })

# Add more routes as needed...

if __name__ == '__main__':
    print("🚀 Starting PayMe Wallet API...")
    print("📍 API will be available at: http://localhost:5000")
    print("📊 Test services at: http://localhost:5000/api/test-services")
    print("🔗 Test API at: http://localhost:5000/api/test")
    app.run(debug=True, host='0.0.0.0', port=5000)