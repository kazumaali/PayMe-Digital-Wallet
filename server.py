from flask import Flask, jsonify, request
from flask_cors import CORS
from database import Database
from datetime import datetime
import requests
import sqlite3
from wallet import WalletManager
from functools import wraps

app = Flask(__name__)
CORS(app)

# تحقق مما إذا كان ملف database.py موجود
try:
    db = Database()
    print("✅ قاعدة البيانات متصلة بنجاح")
except Exception as e:
    print(f"❌ خطأ في قاعدة البيانات: {e}")
    db = None

# Route أساسي للتأكد من أن الخادم يعمل
@app.route('/')
def home():
    return jsonify({
        "message": "مرحباً بك في نظام PayMe!",
        "status": "يعمل",
        "available_endpoints": [
            "/api/balance/1",
            "/api/exchange-rate", 
            "/api/user/create"
        ]
    })

@app.route('/test')
def test():
    return "✅ الخادم يعمل بشكل صحيح!"

class ExchangeRateService:
    def __init__(self):
        self.rates_cache = {}
        self.last_update = None
    
    def get_live_exchange_rates(self):
        """جلب أسعار الصرف الحية من مصادر مختلفة"""
        try:
            # الأولوية لـ tgju.org
            tgju_rates = self._get_tgju_rates()
            
            # إذا نجح tgju، استخدمه
            if tgju_rates and tgju_rates.get('source') == 'tgju.org':
                rates = tgju_rates
                print("✅ استخدام أسعار tgju.org")
            else:
                # إذا فشل، جرب المصادر الأخرى
                crypto_rates = self._get_crypto_rates()
                rates = crypto_rates
                print("✅ استخدام أسعار احتياطية")
            
            self.rates_cache = rates
            self.last_update = datetime.now()
            return rates
            
        except Exception as e:
            print(f"❌ خطأ في جلب أسعار الصرف: {e}")
            return self._get_fallback_rates()
    
    def _get_tgju_rates(self):
        """جلب أسعار الصرف من tgju.org"""
        try:
            # tgju.org يوفر API بسيط للأسعار
            response = requests.get('https://api.tgju.org/v1/data/sana/price_dollar_rl', timeout=10)
            if response.status_code == 200:
                data = response.json()
                # استخراج سعر الدولار من البيانات
                usd_to_irr = float(data['data']['price'])
                print(f"✅ سعر الدولار من tgju: {usd_to_irr}")
            else:
                # إذا فشل المصدر الرئيسي، جرب مصدراً بديلاً من tgju
                usd_to_irr = self._get_tgju_fallback()
        
            return {
                "USD_TO_IRR": usd_to_irr,
                "IRR_TO_USD": 1 / usd_to_irr,
                "USD_TO_USDT": 1,
                "USDT_TO_USD": 1,
                "USDT_TO_IRR": usd_to_irr,
                "IRR_TO_USDT": 1 / usd_to_irr,
                "source": "tgju.org",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"❌ خطأ في جلب الأسعار من tgju.org: {e}")
            return None

    def _get_tgju_fallback(self):
        """مصدر بديل من tgju إذا فشل API الرئيسي"""
        try:
            # جلب من صفحة الويب الرئيسية كبديل
            response = requests.get('https://www.tgju.org/', timeout=10)
            # هنا يمكنك parse HTML لاستخراج السعر
            # هذا مثال بسيط - قد تحتاج لتعديله
            return 1000000  # سعر افتراضي أكثر واقعية
        except:
            return 1000000  # سعر افتراضي
    
    def _get_crypto_rates(self):
        """جلب أسعار العملات الرقمية من Binance"""
        try:
            # USDT to IRR
            response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=USDTIRT', timeout=10)
            if response.status_code == 200:
                data = response.json()
                usdt_to_irr = float(data['price'])
                print(f"✅ سعر USDT من Binance: {usdt_to_irr}")
            else:
                usdt_to_irr = 1000000 # سعر افتراضي
            
            # USD to USDT (عادة ≈ 1)
            usd_to_usdt = 1.0
            
            # حساب الأسعار الأخرى بناءً على ذلك
            return {
                "USD_TO_IRR": usdt_to_irr,
                "IRR_TO_USD": 1 / usdt_to_irr,
                "USD_TO_USDT": usd_to_usdt,
                "USDT_TO_USD": 1 / usd_to_usdt,
                "USDT_TO_IRR": usdt_to_irr,
                "IRR_TO_USDT": 1 / usdt_to_irr,
                "source": "binance",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ خطأ في جلب أسعار العملات الرقمية: {e}")
            return self._get_fallback_rates()
    
    def _get_fiat_rates(self):
        """جلب أسعار العملات التقليدية (يمكن إضافة مصادر أخرى لاحقاً)"""
        # حالياً نستخدم نفس أسعار العملات الرقمية
        return {}
    
    def _get_fallback_rates(self):
        """أسعار افتراضية إذا فشل الاتصال بالإنترنت"""
        return {
            "USD_TO_IRR": 1000000,
            "IRR_TO_USD": 0.000001,
            "USD_TO_USDT": 1,
            "USDT_TO_USD": 1,
            "USDT_TO_IRR": 1000000,
            "IRR_TO_USDT": 0.000001,
            "source": "fallback",
            "timestamp": datetime.now().isoformat()
        }

# إنشاء كائن خدمة أسعار الصرف
exchange_service = ExchangeRateService()

# إنشاء كائن إدارة المحفظة
try:
    wallet_manager = WalletManager()
    print("✅ نظام المحفظة جاهز")
except Exception as e:
    print(f"❌ خطأ في تحميل نظام المحفظة: {e}")
    wallet_manager = None

# دالة decorator للتحقق من المصادقة
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"success": False, "message": "غير مصرح بالوصول"}), 401
        
        user_id = db.validate_session(session_token)
        if not user_id:
            return jsonify({"success": False, "message": "الجلسة منتهية"}), 401
        
        return f(user_id, *args, **kwargs)
    return decorated_function

# Routes المصادقة
@app.route('/api/auth/register', methods=['POST'])
def register():
    """تسجيل مستخدم جديد"""
    data = request.json
    print("📝 بيانات التسجيل:", data)
    
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    phone = data.get('phone')
    
    if not all([username, password]):
        return jsonify({"success": False, "message": "اسم المستخدم وكلمة المرور مطلوبان"}), 400
    
    if len(password) < 6:
        return jsonify({"success": False, "message": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}), 400
    
    user_id = db.create_user(username, password, email, phone)
    if user_id:
        # إنشاء جلسة تلقائية بعد التسجيل
        session_token = db.create_session(user_id)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "session_token": session_token,
            "message": "تم إنشاء الحساب بنجاح"
        })
    else:
        return jsonify({
            "success": False,
            "message": "اسم المستخدم موجود مسبقاً"
        }), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """تسجيل الدخول"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return jsonify({"success": False, "message": "بيانات ناقصة"}), 400
    
    user_id = db.authenticate_user(username, password)
    if user_id:
        session_token = db.create_session(user_id)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "session_token": session_token,
            "message": "تم تسجيل الدخول بنجاح"
        })
    else:
        return jsonify({
            "success": False,
            "message": "اسم المستخدم أو كلمة المرور غير صحيحة"
        }), 401

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout(user_id):
    """تسجيل الخروج"""
    session_token = request.headers.get('Authorization')
    conn = sqlite3.connect('wallet.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "تم تسجيل الخروج بنجاح"})

# Routes المحفظة (محمية بالمصادقة)
@app.route('/api/balance', methods=['GET'])
@login_required
def get_balance_protected(user_id):
    """جلب أرصدة المستخدم (محمي)"""
    try:
        balances = db.get_balance(user_id)
        return jsonify({
            "success": True,
            "balances": balances
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"خطأ في جلب الأرصدة: {str(e)}"
        }), 500

@app.route('/api/convert', methods=['POST'])
@login_required
def convert_currency_protected(user_id):
    """تحويل العملات (محمي)"""
    try:
        data = request.json
        print("📨 بيانات الاستقبال:", data)
        
        from_currency = data.get('from_currency')
        to_currency = data.get('to_currency')
        amount = data.get('amount')
        
        if not all([from_currency, to_currency, amount]):
            return jsonify({
                "success": False, 
                "message": "بيانات ناقصة"
            }), 400
        
        # جلب أرصدة المستخدم الحالية
        balances = db.get_balance(user_id)
        print("💰 الأرصدة الحالية:", balances)
        
        # التحقق من وجود رصيد كافي
        if from_currency not in balances or balances[from_currency] < amount:
            return jsonify({
                "success": False,
                "message": f"رصيد غير كافي في {from_currency}. الرصيد المتاح: {balances.get(from_currency, 0)}"
            }), 400
        
        # جلب سعر الصرف
        rates_response = get_exchange_rate()
        rates_data = rates_response.get_json()
        rate_key = f"{from_currency}_TO_{to_currency}"
        
        print("🔍 مفتاح السعر المطلوب:", rate_key)
        
        if not rates_data['success'] or rate_key not in rates_data['rates']:
            return jsonify({
                "success": False,
                "message": f"خطأ في سعر الصرف: {rate_key} غير متوفر"
            }), 400
        
        rate = rates_data['rates'][rate_key]
        converted_amount = amount * rate
        
        print("🔄 تفاصيل التحويل:", {
            'من': f"{amount} {from_currency}",
            'إلى': f"{converted_amount} {to_currency}", 
            'السعر': rate
        })
        
        # تنفيذ التحويل في قاعدة البيانات
        conn = sqlite3.connect('wallet.db')
        cursor = conn.cursor()
        
        # خصم من العملة المصدر
        cursor.execute(
            'UPDATE balances SET amount = amount - ? WHERE user_id = ? AND currency = ?',
            (amount, user_id, from_currency)
        )
        
        # إضافة للعملة الهدف
        cursor.execute(
            'UPDATE balances SET amount = amount + ? WHERE user_id = ? AND currency = ?',
            (converted_amount, user_id, to_currency)
        )
        
        # تسجيل المعاملة
        cursor.execute(
            '''INSERT INTO transactions 
               (user_id, type, from_currency, to_currency, amount, status) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, 'exchange', from_currency, to_currency, amount, 'completed')
        )
        
        conn.commit()
        conn.close()
        
        print("✅ التحويل تم بنجاح")
        
        return jsonify({
            "success": True,
            "message": "تم التحويل بنجاح",
            "conversion": {
                "from": from_currency,
                "to": to_currency,
                "original_amount": amount,
                "converted_amount": converted_amount,
                "rate": rate
            }
        })
        
    except Exception as e:
        print(f"❌ خطأ في التحويل: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": f"خطأ داخلي: {str(e)}"
        }), 500

@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications(user_id):
    """جلب الإشعارات"""
    try:
        notifications = db.get_unread_notifications(user_id)
        return jsonify({
            "success": True,
            "notifications": notifications
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"خطأ في جلب الإشعارات: {str(e)}"
        }), 500

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(user_id, notification_id):
    """تحديد إشعار كمقروء"""
    try:
        db.mark_notification_read(notification_id)
        return jsonify({
            "success": True,
            "message": "تم تحديد الإشعار كمقروء"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"خطأ في تحديث الإشعار: {str(e)}"
        }), 500

# Routes العامة (بدون مصادقة)
@app.route('/api/exchange-rate', methods=['GET'])
def get_exchange_rate():
    """جلب أسعار الصرف الحية"""
    rates = exchange_service.get_live_exchange_rates()
    return jsonify({
        "success": True, 
        "rates": rates,
        "last_update": exchange_service.last_update.isoformat() if exchange_service.last_update else None
    })

@app.route('/api/exchange-rate/cached', methods=['GET'])
def get_cached_exchange_rate():
    """جلب أسعار الصرف المخزنة (أسرع)"""
    if not exchange_service.rates_cache:
        exchange_service.get_live_exchange_rates()
    
    return jsonify({
        "success": True, 
        "rates": exchange_service.rates_cache,
        "last_update": exchange_service.last_update.isoformat() if exchange_service.last_update else None
    })

# Routes التوافق مع النظام القديم (سيتم إزالتها لاحقاً)
@app.route('/api/user/create', methods=['POST'])
def create_user_legacy():
    """إنشاء مستخدم جديد (للتوافق مع النظام القديم)"""
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"success": False, "message": "اسم المستخدم مطلوب"}), 400
    
    # استخدام النظام القديم بدون كلمة مرور
    user_id = db.create_user_legacy(username)
    if user_id:
        return jsonify({
            "success": True, 
            "user_id": user_id,
            "message": "تم إنشاء المستخدم بنجاح"
        })
    else:
        return jsonify({
            "success": False, 
            "message": "اسم المستخدم موجود مسبقاً"
        }), 400

@app.route('/api/balance/<int:user_id>', methods=['GET'])
def get_balance_legacy(user_id):
    """جلب أرصدة المستخدم (للتوافق مع النظام القديم)"""
    try:
        balances = db.get_balance(user_id)
        return jsonify({
            "success": True,
            "balances": balances
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"خطأ في جلب الأرصدة: {str(e)}"
        }), 500

# Routes الإرسال والاستقبال (للتوافق مع النظام القديم)
@app.route('/api/send', methods=['POST'])
def send_money():
    """إرسال أموال لمستخدم آخر"""
    try:
        data = request.json
        print("📤 بيانات الإرسال:", data)
        
        from_user_id = data.get('from_user_id')
        to_user_id = data.get('to_user_id')  # يمكن أن يكون null إذا كان عنوان خارجي
        amount = data.get('amount')
        currency = data.get('currency')
        recipient_address = data.get('recipient_address')
        
        if not all([from_user_id, amount, currency, recipient_address]):
            return jsonify({
                "success": False, 
                "message": "بيانات ناقصة"
            }), 400
        
        # تنفيذ الإرسال
        result = wallet_manager.send_money(from_user_id, to_user_id, amount, currency, recipient_address)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ خطأ في الإرسال: {e}")
        return jsonify({
            "success": False,
            "message": f"خطأ داخلي: {str(e)}"
        }), 500

@app.route('/api/transactions/<int:user_id>', methods=['GET'])
def get_transactions(user_id):
    """جلب سجل المعاملات"""
    try:
        transactions = wallet_manager.get_transaction_history(user_id)
        return jsonify({
            "success": True,
            "transactions": transactions
        })
    except Exception as e:
        print(f"❌ خطأ في جلب المعاملات: {e}")
        return jsonify({
            "success": False,
            "message": f"خطأ في جلب المعاملات: {str(e)}"
        }), 500

@app.route('/api/user/exists', methods=['POST'])
def check_user_exists():
    """التحقق من وجود مستخدم"""
    data = request.json
    username = data.get('username')
    
    conn = sqlite3.connect('wallet.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return jsonify({"success": True, "user_id": user[0]})
    else:
        return jsonify({"success": False, "message": "المستخدم غير موجود"})

# Routes السحب (للتوافق مع النظام القديم)
@app.route('/api/withdraw', methods=['POST'])
def process_withdrawal():
    """معالجة طلبات السحب للبطاقات البنكية"""
    try:
        data = request.json
        print("💳 بيانات السحب:", data)
        
        user_id = data.get('user_id')
        amount = data.get('amount')
        currency = data.get('currency')
        card_number = data.get('card_number')
        
        if not all([user_id, amount, currency, card_number]):
            return jsonify({
                "success": False, 
                "message": "بيانات ناقصة"
            }), 400
        
        # جلب أرصدة المستخدم
        balances = db.get_balance(user_id)
        
        # حساب العمولة (1%)
        fee = amount * 0.01
        total_amount = amount + fee
        
        # التحقق من الرصيد الكافي
        if currency not in balances or balances[currency] < total_amount:
            return jsonify({
                "success": False,
                "message": f"رصيد غير كافي. الرصيد المتاح: {balances.get(currency, 0)} {currency}"
            }), 400
        
        # التحقق من رقم البطاقة
        clean_card = card_number.replace(' ', '')
        if not clean_card.startswith('6') or len(clean_card) != 16:
            return jsonify({
                "success": False,
                "message": "رقم البطاقة غير صحيح. يجب أن يكون 16 رقماً ويبدأ بـ 6"
            }), 400
        
        # تنفيذ السحب في قاعدة البيانات
        conn = sqlite3.connect('wallet.db')
        cursor = conn.cursor()
        
        # خصم المبلغ + العمولة
        cursor.execute(
            'UPDATE balances SET amount = amount - ? WHERE user_id = ? AND currency = ?',
            (total_amount, user_id, currency)
        )
        
        # تسجيل معاملة السحب
        cursor.execute(
            '''INSERT INTO transactions 
               (user_id, type, from_currency, amount, recipient, status) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, 'withdraw', currency, amount, f"Card: {clean_card[-4:]}", 'pending')
        )
        
        conn.commit()
        conn.close()
        
        print("✅ طلب السحب مسجل بنجاح")
        
        return jsonify({
            "success": True,
            "message": "تم تقديم طلب السحب بنجاح",
            "withdrawal": {
                "amount": amount,
                "fee": fee,
                "total": total_amount,
                "currency": currency,
                "card_last_digits": clean_card[-4:],
                "estimated_time": "24 ساعة"
            }
        })
        
    except Exception as e:
        print(f"❌ خطأ في السحب: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": f"خطأ داخلي: {str(e)}"
        }), 500

@app.route('/api/withdrawal-history/<int:user_id>', methods=['GET'])
def get_withdrawal_history(user_id):
    """جلب سجل طلبات السحب"""
    try:
        conn = sqlite3.connect('wallet.db')
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT type, from_currency, amount, recipient, status, created_at 
               FROM transactions WHERE user_id = ? AND type = 'withdraw'
               ORDER BY created_at DESC''',
            (user_id,)
        )
        
        withdrawals = []
        for row in cursor.fetchall():
            withdrawals.append({
                'type': row[0],
                'currency': row[1],
                'amount': row[2],
                'recipient': row[3],
                'status': row[4],
                'date': row[5]
            })
        
        conn.close()
        
        return jsonify({
            "success": True,
            "withdrawals": withdrawals
        })
        
    except Exception as e:
        print(f"❌ خطأ في جلب سجل السحب: {e}")
        return jsonify({
            "success": False,
            "message": f"خطأ في جلب السجل: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("🎯 تم تشغيل خادم PayMe على http://localhost:5000")
    print("📊 قاعدة البيانات جاهزة")
    print("💱 خدمة أسعار الصرف الحية جاهزة")
    app.run(debug=True, port=5000)