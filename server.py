from flask import Flask, jsonify, request
from flask_cors import CORS
from database import Database
from datetime import datetime
import requests
import json
from wallet import WalletManager

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
            # مصدر 1: أسعار العملات الرقمية (Binance API)
            crypto_rates = self._get_crypto_rates()
            
            # مصدر 2: أسعار العملات التقليدية (يمكن إضافة مصادر أخرى)
            fiat_rates = self._get_fiat_rates()
            
            # دمج النتائج
            rates = {**crypto_rates, **fiat_rates}
            self.rates_cache = rates
            self.last_update = datetime.now()
            
            return rates
            
        except Exception as e:
            print(f"خطأ في جلب أسعار الصرف: {e}")
            # استخدام أسعار افتراضية إذا فشل الاتصال
            return self._get_fallback_rates()
    
    def _get_crypto_rates(self):
        """جلب أسعار العملات الرقمية من Binance"""
        try:
            # USDT to IRR (نستخدم سعر USDT to USDC كبديل ثم نحوله لريال)
            response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=USDTIRT')
            if response.status_code == 200:
                data = response.json()
                usdt_to_irr = float(data['price'])
            else:
                usdt_to_irr = 1000000  # سعر افتراضي
            
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
            print(f"خطأ في جلب أسعار العملات الرقمية: {e}")
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
        
    def _get_tgju_rates(self):
    """جلب أسعار الصرف من tgju.org"""
    try:
        # tgju.org يوفر API بسيط للأسعار
        response = requests.get('https://api.tgju.org/v1/data/sana/price_dollar_rl', timeout=10)
        if response.status_code == 200:
            data = response.json()
            # استخراج سعر الدولار من البيانات
            usd_to_irr = float(data['data']['price'])
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
        print(f"خطأ في جلب الأسعار من tgju.org: {e}")
        return self._get_fallback_rates()

    def _get_tgju_fallback(self):
    """مصدر بديل من tgju إذا فشل API الرئيسي"""
    try:
        # جلب من صفحة الويب الرئيسية كبديل
        response = requests.get('https://www.tgju.org/', timeout=10)
        # هنا يمكنك parse HTML لاستخراج السعر
        # هذا مثال بسيط - قد تحتاج لتعديله
        return 1000000  # سعر افتراضي
    except:
        return 1000000  # سعر افتراضي

# ثم عدل الدالة الرئيسية:
    def get_live_exchange_rates(self):
    """جلب أسعار الصرف الحية من مصادر مختلفة"""
    try:
        # الأولوية لـ tgju.org
        tgju_rates = self._get_tgju_rates()
        
        # إذا نجح tgju، استخدمه
        if tgju_rates.get('source') == 'tgju.org':
            rates = tgju_rates
        else:
            # إذا فشل، جرب المصادر الأخرى
            crypto_rates = self._get_crypto_rates()
            rates = {**crypto_rates}
        
        self.rates_cache = rates
        self.last_update = datetime.now()
        return rates
        
    except Exception as e:
        print(f"خطأ في جلب أسعار الصرف: {e}")
        return self._get_fallback_rates()

# إنشاء كائن خدمة أسعار الصرف
exchange_service = ExchangeRateService()

# Routes الموجودة سابقاً تبقى كما هي
@app.route('/api/user/create', methods=['POST'])
def create_user():
    """إنشاء مستخدم جديد"""
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"success": False, "message": "اسم المستخدم مطلوب"}), 400
    
    user_id = db.create_user(username)
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
def get_balance(user_id):
    """جلب أرصدة المستخدم"""
    balances = db.get_balance(user_id)
    return jsonify({
        "success": True,
        "balances": balances
    })

@app.route('/api/convert', methods=['POST'])
def convert_currency():
    """تحويل العملات مع التنفيذ الفعلي"""
    try:
        data = request.json
        print("📨 بيانات الاستقبال:", data)
        
        user_id = data.get('user_id')
        from_currency = data.get('from_currency')
        to_currency = data.get('to_currency')
        amount = data.get('amount')
        
        if not all([user_id, from_currency, to_currency, amount]):
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
        print("📊 جميع الأسعار:", rates_data['rates'] if rates_data['success'] else 'فشل')
        
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

if __name__ == '__main__':
    print("🎯 تم تشغيل خادم PayMe على http://localhost:5000")
    print("📊 قاعدة البيانات جاهزة")
    print("💱 خدمة أسعار الصرف الحية جاهزة")
    app.run(debug=True, port=5000)
    
    
# بعد تعريف db مباشرة أضف:
wallet_manager = WalletManager()

# أضف هذه الـ routes بعد دوال التحويل الحالية:

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