# kavenegar_verify_service.py
import requests
import random
import time
import hashlib
import hmac
from cryptography.fernet import Fernet
import base64

class KavehNegharVerifyService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://api.kavenegar.com/v1'
    
    def send_otp(self, phone_number, card_last4, otp):
        """ارسال رمز پویا با سرویس اعتبارسنجی کاوه نگار"""
        try:
            # فرمت‌دهی شماره تلفن (حذف صفر اول)
            if phone_number.startswith('0'):
                phone_number = phone_number[1:]
            
            # استفاده از سرویس verify/lookup
            url = f"{self.base_url}/{self.api_key}/verify/lookup.json"
            
            # پارامترهای ارسال
            payload = {
                'receptor': phone_number,
                'token': otp,           # رمز پویا
                'token2': card_last4,   # ۴ رقم آخر کارت
                'token3': '5',          # زمان انقضا (دقیقه)
                'template': 'payme-verify'  # نام تمپلیت - می‌تونی تغییر بدی
            }
            
            print(f"🔧 ارسال درخواست به کاوه نگار...")
            print(f"   شماره: {phone_number}")
            print(f"   OTP: {otp}")
            print(f"   کارت: ****{card_last4}")
            
            response = requests.post(url, data=payload, timeout=15)
            
            print(f"🔧 وضعیت پاسخ: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                return_status = result['return']['status']
                
                if return_status == 200:
                    print("✅ پیامک با موفقیت ارسال شد")
                    return True
                else:
                    error_msg = result['return']['message']
                    print(f"❌ خطا از کاوه نگار: {error_msg}")
                    
                    # راهنمایی برای خطاهای رایج
                    if "template" in error_msg.lower():
                        print("💡 راهنما: نیاز به ایجاد تمپلیت در بخش اعتبارسنجی")
                    elif "receptor" in error_msg.lower():
                        print("💡 راهنما: شماره موبایل معتبر نیست")
                    elif "api" in error_msg.lower():
                        print("💡 راهنما: API Key معتبر نیست")
                    
                    return False
            else:
                print(f"❌ خطای HTTP: {response.status_code}")
                print(f"❌ متن خطا: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ timeout در ارسال پیامک")
            return False
        except requests.exceptions.ConnectionError:
            print("❌ خطای اتصال به کاوه نگار")
            return False
        except Exception as e:
            print(f"❌ خطای ناشناخته: {str(e)}")
            return False

class SecureOTPService:
    def __init__(self, api_key):
        self.sms_service = KavehNegharVerifyService(api_key)
        self.otp_storage = {}
        self.failed_attempts = {}
        
        # کلید رمزنگاری
        self.cipher_key = base64.b64encode(hashlib.sha256(b'payme-wallet-secret-key').digest())
        self.cipher = Fernet(self.cipher_key)
    
    def _encrypt_phone(self, phone_number):
        return self.cipher.encrypt(phone_number.encode()).decode()
    
    def validate_phone_number(self, phone):
        """اعتبارسنجی شماره موبایل ایرانی"""
        import re
        pattern = r'^09[0-9]{9}$'
        if not re.match(pattern, phone):
            return False, 'شماره موبایل معتبر نیست'
        return True, 'شماره معتبر است'
    
    def send_otp(self, phone_number, card_last4):
        """ارسال رمز پویا"""
        try:
            # اعتبارسنجی شماره
            is_valid, validation_msg = self.validate_phone_number(phone_number)
            if not is_valid:
                return False, validation_msg
            
            # تولید رمز پویا
            otp = str(random.randint(100000, 999999))
            
            print(f"🔧 شروع ارسال OTP...")
            success = self.sms_service.send_otp(phone_number, card_last4, otp)
            
            if success:
                # ذخیره اطلاعات
                encrypted_phone = self._encrypt_phone(phone_number)
                self.otp_storage[encrypted_phone] = {
                    'otp': hashlib.sha256(otp.encode()).hexdigest(),
                    'expires_at': time.time() + 300,  # 5 دقیقه
                    'attempts': 0,
                    'card_last4': card_last4
                }
                
                print(f"📱 OTP {otp} برای {phone_number} ارسال شد")
                return True, 'رمز پویا با موفقیت ارسال شد'
            else:
                return False, 'خطا در ارسال پیامک. لطفاً مجدداً تلاش کنید.'
                
        except Exception as e:
            print(f"❌ خطا در ارسال OTP: {e}")
            return False, 'خطای سیستمی در ارسال پیامک'
    
    def verify_otp(self, phone_number, entered_otp):
        """بررسی رمز پویا"""
        try:
            is_valid, _ = self.validate_phone_number(phone_number)
            if not is_valid:
                return False, 'شماره موبایل معتبر نیست'
            
            encrypted_phone = self._encrypt_phone(phone_number)
            
            if encrypted_phone not in self.otp_storage:
                return False, 'رمز پویا یافت نشد. لطفاً مجدداً درخواست کنید.'
            
            otp_data = self.otp_storage[encrypted_phone]
            
            # بررسی انقضا
            if time.time() > otp_data['expires_at']:
                del self.otp_storage[encrypted_phone]
                return False, 'رمز پویا منقضی شده است'
            
            # بررسی تعداد تلاش
            if otp_data['attempts'] >= 3:
                del self.otp_storage[encrypted_phone]
                return False, 'تعداد تلاش‌ها بیش از حد مجاز است'
            
            # بررسی رمز
            entered_hash = hashlib.sha256(entered_otp.encode()).hexdigest()
            if hmac.compare_digest(otp_data['otp'], entered_hash):
                del self.otp_storage[encrypted_phone]
                return True, 'رمز پویا تأیید شد'
            else:
                otp_data['attempts'] += 1
                remaining_attempts = 3 - otp_data['attempts']
                return False, f'رمز پویا نادرست است. تلاش‌های باقیمانده: {remaining_attempts}'
                
        except Exception as e:
            print(f"❌ خطا در بررسی OTP: {e}")
            return False, 'خطای سیستمی در بررسی رمز پویا'

# نمونه سرویس با API Key تو
sms_service = SecureOTPService(api_key='YOUR_API_KEY_HERE')