# backend/services/sms_service.py
import random
import time
import hashlib
import hmac
from cryptography.fernet import Fernet
import base64
import sqlite3
from datetime import datetime, timedelta

# در sms_service.py - رفع مشکل indentation و منطق

class SimulatedSMSService:
    def __init__(self, db_path='sms_service.db'):
        self.db_path = db_path
        self._init_database()
        self.otp_storage = {}
        self.failed_attempts = {}
        
        # کلید رمزنگاری
        self.cipher_key = base64.b64encode(hashlib.sha256(b'payme-wallet-secret-key').digest())
        self.cipher = Fernet(self.cipher_key)
    
    def _init_database(self):
        """ایجاد دیتابیس برای ذخیره پیامک‌ها"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sms_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                message TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                status TEXT DEFAULT 'sent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def send_otp(self, card_number, card_last4):
        """ارسال رمز پویا بر اساس شماره کارت"""
        try:
            # تولید رمز پویا
            otp = str(random.randint(100000, 999999))
            
            # ساخت متن پیامک
            message = f"""
🔐 PayMe Wallet
📱 رمز پویا: {otp}
💳 برای کارت: ****{card_last4}
⏰ اعتبار: 5 دقیقه
🌐 payme.ir
            """.strip()
            
            # ذخیره در دیتابیس با کلید شماره کارت
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sms_messages (phone_number, message, otp_code) VALUES (?, ?, ?)',
                (f"card_{card_last4}", message, otp)
            )
            conn.commit()
            conn.close()
            
            # ذخیره در حافظه برای تأیید - با کلید شماره کارت
            self.otp_storage[card_number] = {
                'otp': hashlib.sha256(otp.encode()).hexdigest(),
                'expires_at': time.time() + 300,  # 5 دقیقه
                'attempts': 0,
                'card_last4': card_last4
            }
            
            # نمایش در کنسول (برای تست)
            print("=" * 50)
            print("📱 **پیامک شبیه‌سازی شده**")
            print(f"💳 برای کارت: ****{card_last4}")
            print(f"📨 رمز پویا: {otp}")
            print("=" * 50)
            
            return True, 'رمز پویا با موفقیت ارسال شد'
            
        except Exception as e:
            print(f"❌ خطا در ارسال OTP: {e}")
            return False, 'خطای سیستمی در ارسال پیامک'

    def verify_otp(self, card_number, entered_otp):
        """بررسی رمز پویا بر اساس شماره کارت"""
        try:
            if card_number not in self.otp_storage:
                return False, 'رمز پویا یافت نشد. لطفاً مجدداً درخواست کنید.'
            
            otp_data = self.otp_storage[card_number]
            
            # بررسی انقضا
            if time.time() > otp_data['expires_at']:
                del self.otp_storage[card_number]
                return False, 'رمز پویا منقضی شده است'
            
            # بررسی تعداد تلاش
            if otp_data['attempts'] >= 3:
                del self.otp_storage[card_number]
                return False, 'تعداد تلاش‌ها بیش از حد مجاز است'
            
            # بررسی رمز
            entered_hash = hashlib.sha256(entered_otp.encode()).hexdigest()
            if hmac.compare_digest(otp_data['otp'], entered_hash):
                del self.otp_storage[card_number]
                return True, 'رمز پویا تأیید شد'
            else:
                otp_data['attempts'] += 1
                remaining_attempts = 3 - otp_data['attempts']
                return False, f'رمز پویا نادرست است. تلاش‌های باقیمانده: {remaining_attempts}'
                
        except Exception as e:
            print(f"❌ خطا در بررسی OTP: {e}")
            return False, 'خطای سیستمی در بررسی رمز پویا'

# نمونه سرویس
sms_service = SimulatedSMSService()