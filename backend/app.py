from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import os
import sys
import re
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
from sms_service import sms_service

# Add the current directory to Python path to import services
sys.path.append(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app, origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080", "http://127.0.0.1:8080"], supports_credentials=True)

# Import services
try:
    from services.exchange_service import ExchangeService
    from services.wallet_service import WalletService
    from services.payment_service import PaymentService
    print("✅ Successfully imported all services")
    
    # Initialize services with your Navasan API key
    exchange_service = ExchangeService(navasan_api_key='freeVeBEP365HYZw58h3bdFVxui8EQXC')
    wallet_service = WalletService()
    payment_service = PaymentService()
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("⚠️  Running with built-in exchange service only")
    
    # Simplified service implementation
class ExchangeService:
    def __init__(self, navasan_api_key='freeVeBEP365HYZw58h3bdFVxui8EQXC'):
        self.navasan_api_key = navasan_api_key
        self.cache = {}
        self.cache_timeout = 300

    def get_current_rates(self):
        cache_key = 'exchange_rates'
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return cached_data
        
        try:
            # Your existing rate fetching logic here
            usd_to_irr = 1070000
            rates = {
                'USD_IRR': float(usd_to_irr),
                'IRR_USD': 1 / float(usd_to_irr),
                'USD_USDT': 1.0,
                'USDT_USD': 1.0,
                'USDT_IRR': float(usd_to_irr),
                'IRR_USDT': 1 / float(usd_to_irr),
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'static'
            }
            
            self.cache[cache_key] = (rates, datetime.now())
            return rates
            
        except Exception as e:
            print(f"Error getting rates: {e}")
            # Fallback rates
            return {
                'USD_IRR': 1070000,
                'IRR_USD': 0.000000934579,
                'USD_USDT': 1.0,
                'USDT_USD': 1.0,
                'USDT_IRR': 1070000,
                'IRR_USDT': 0.000000934579,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'fallback'
            }

# Initialize services
exchange_service = ExchangeService()

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
    try:
        print("🔄 Fetching exchange rates...")
        rates = exchange_service.get_current_rates()
        print(f"✅ Rates fetched: 1 USD = {rates['USD_IRR']:,.0f} IRR")
        return jsonify(rates)
    except Exception as e:
        print(f"❌ Error in exchange-rates endpoint: {e}")
        # Return fallback rates
        fallback_rates = {
            'USD_IRR': 1070000,
            'IRR_USD': 0.000000934579,
            'USD_USDT': 1.0,
            'USDT_USD': 1.0,
            'USDT_IRR': 1070000,
            'IRR_USDT': 0.000000934579,
            'timestamp': datetime.utcnow().isoformat(),
            'note': 'Using fallback rates due to error',
            'source': 'fallback'
        }
        return jsonify(fallback_rates)

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
    
# در app.py - آپدیت routeهای OTP
@app.route('/api/payment/request-otp', methods=['POST'])
@require_auth
def request_otp():
    """درخواست ارسال رمز پویا بر اساس کارت"""
    try:
        data = request.get_json()
        card_number = data.get('card_number')
        card_last4 = data.get('card_last4')
        
        if not all([card_number, card_last4]):
            return jsonify({
                'success': False, 
                'error': 'لطفا اطلاعات کارت را وارد کنید'
            }), 400
        
        # ارسال OTP - فقط بر اساس شماره کارت
        success, message = sms_service.send_otp(card_number, card_last4)
        
        if success:
            return jsonify({
                'success': True, 
                'message': message
            })
        else:
            return jsonify({
                'success': False, 
                'error': message
            }), 400
            
    except Exception as e:
        print(f"❌ خطا در درخواست OTP: {e}")
        return jsonify({
            'success': False,
            'error': 'خطای سرور در ارسال رمز پویا'
        }), 500

@app.route('/api/payment/verify-otp', methods=['POST'])
@require_auth
def verify_otp():
    """بررسی رمز پویا بر اساس کارت"""
    try:
        data = request.get_json()
        card_number = data.get('card_number')
        otp_code = data.get('otp_code')
        
        if not all([card_number, otp_code]):
            return jsonify({
                'success': False, 
                'error': 'لطفا اطلاعات کارت و رمز پویا را وارد کنید'
            }), 400
        
        # بررسی OTP
        is_valid, message = sms_service.verify_otp(card_number, otp_code)
        
        if is_valid:
            return jsonify({
                'success': True, 
                'message': message
            })
        else:
            return jsonify({
                'success': False, 
                'error': message
            }), 400
            
    except Exception as e:
        print(f"❌ خطا در بررسی OTP: {e}")
        return jsonify({
            'success': False,
            'error': 'خطای سرور در بررسی رمز پویا'
        }), 500

# در app.py - آپدیت endpointهای پرداخت

@app.route('/api/payment/process-irr', methods=['POST'])
@require_auth
def process_irr_payment():
    """پردازش پرداخت ریالی"""
    user_id = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    data = request.get_json()
    
    amount = data.get('amount')
    otp_code = data.get('otp_code')
    card_number = data.get('card_number')  # ✅ تغییر از phone_number به card_number
    
    if not all([amount, otp_code, card_number]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # بررسی رمز پویا - با card_number
    is_valid, otp_message = sms_service.verify_otp(card_number, otp_code)
    if not is_valid:
        return jsonify({'success': False, 'error': otp_message}), 400
    
    # پردازش پرداخت
    try:
        conn = get_db_connection()
        
        # افزایش موجودی
        wallet = conn.execute(
            'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
        ).fetchone()
        
        if wallet:
            conn.execute(
                'UPDATE wallets SET irr_balance = irr_balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
        else:
            wallet_id = secrets.token_hex(16)
            conn.execute(
                'INSERT INTO wallets (id, user_id, irr_balance) VALUES (?, ?, ?)',
                (wallet_id, user_id, amount)
            )
        
        # ثبت تراکنش
        tx_id = secrets.token_hex(16)
        conn.execute(
            'INSERT INTO transactions (id, user_id, type, amount, currency, status, description, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (tx_id, user_id, 'charge', amount, 'IRR', 'completed', 'شارژ کیف پول - ریال', json.dumps({
                'payment_method': 'iranian_card',
                'otp_verified': True,
                'card_number': card_number[-4:]  # فقط 4 رقم آخر
            }))
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'transaction_id': tx_id,
            'amount': amount,
            'currency': 'IRR'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/payment/withdraw', methods=['POST'])
@require_auth
def process_withdrawal():
    """پردازش برداشت از حساب"""
    user_id = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    data = request.get_json()
    
    amount = data.get('amount')
    currency = data.get('currency')
    otp_code = data.get('otp_code')
    card_number = data.get('card_number')  # ✅ تغییر از phone_number به card_number
    
    if not all([amount, currency, otp_code, card_number]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # بررسی رمز پویا - با card_number
    is_valid, otp_message = sms_service.verify_otp(card_number, otp_code)
    if not is_valid:
        return jsonify({'success': False, 'error': otp_message}), 400
    
    # پردازش برداشت
    try:
        conn = get_db_connection()
        
        # بررسی موجودی
        wallet = conn.execute(
            'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
        ).fetchone()
        
        if not wallet:
            return jsonify({'success': False, 'error': 'کیف پول یافت نشد'}), 404
        
        balance_field = f"{currency.lower()}_balance"
        current_balance = wallet[balance_field] or 0.0
        
        if current_balance < amount:
            return jsonify({'success': False, 'error': 'موجودی کافی نیست'}), 400
        
        # کسر از موجودی
        conn.execute(
            f'UPDATE wallets SET {balance_field} = {balance_field} - ? WHERE user_id = ?',
            (amount, user_id)
        )
        
        # ثبت تراکنش
        tx_id = secrets.token_hex(16)
        conn.execute(
            'INSERT INTO transactions (id, user_id, type, amount, currency, status, description, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (tx_id, user_id, 'withdraw', amount, currency, 'completed', f'برداشت به کارت - {currency}', json.dumps({
                'payment_method': 'card_withdrawal',
                'otp_verified': True,
                'card_number': card_number[-4:]  # فقط 4 رقم آخر
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
# در app.py - اضافه کردن endpoint جدید

@app.route('/api/wallet/withdraw/check-balance', methods=['POST'])
@require_auth
def check_withdrawal_balance():
    """بررسی موجودی برای برداشت"""
    user_id = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    data = request.get_json()
    
    amount = data.get('amount')
    currency = data.get('currency')
    
    if not all([amount, currency]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    wallet = conn.execute(
        'SELECT * FROM wallets WHERE user_id = ?', (user_id,)
    ).fetchone()
    
    if not wallet:
        return jsonify({'success': False, 'error': 'Wallet not found'}), 404
    
    balance_field = f"{currency.lower()}_balance"
    current_balance = wallet[balance_field] or 0.0
    
    conn.close()
    
    if current_balance < amount:
        return jsonify({
            'success': False, 
            'error': 'موجودی کافی نیست',
            'current_balance': current_balance,
            'requested_amount': amount
        })
    
    # محاسبه کارمزد
    fee_percentage = 0.01  # 1%
    fee = amount * fee_percentage
    
    if currency == 'USD':
        fee = max(fee, 1.0)  # حداقل 1 دلار
    else:  # IRR
        fee = max(fee, 50000)  # حداقل 50,000 ریال
    
    net_amount = amount - fee
    
    return jsonify({
        'success': True,
        'current_balance': current_balance,
        'fee': fee,
        'net_amount': net_amount,
        'currency': currency
    })
    
@app.route('/api/debug-connection', methods=['GET', 'POST'])
def debug_connection():
    print("🔧 Debug connection called")
    print("📧 Headers:", dict(request.headers))
    print("📦 Method:", request.method)
    
    if request.method == 'POST':
        print("📝 POST Data:", request.get_json())
    
    return jsonify({
        'status': 'connected',
        'message': 'Server is responding',
        'timestamp': datetime.utcnow().isoformat(),
        'your_ip': request.remote_addr,
        'method': request.method
    })

# در انتهای فایل app.py این خط را تغییر دهید:
if __name__ == '__main__':
    print("🚀 Starting PayMe Wallet API...")
    print("📍 API will be available at: http://localhost:5000")
    print("📊 Test services at: http://localhost:5000/api/test-services")
    print("🔗 Test API at: http://localhost:5000/api/test")
    print("💱 Test exchange rates at: http://localhost:5000/api/exchange-rates")
    app.run(debug=True, host='127.0.0.1', port=5000)  # تغییر به 127.0.0.1