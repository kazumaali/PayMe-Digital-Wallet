import sqlite3
import json
from datetime import datetime, timedelta
import hashlib
import secrets

class Database:
    def __init__(self, db_name='wallet.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """إنشاء الجداول الأساسية مع تحديثات الأمان"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # تحديث جدول المستخدمين لإضافة كلمات المرور
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                is_verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول جلسات المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_token TEXT UNIQUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # جدول محاولات تسجيل الدخول
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                ip_address TEXT,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success INTEGER DEFAULT 0
            )
        ''')
        
        # جدول الأرصدة (موجود سابقاً)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER,
                currency TEXT NOT NULL,
                amount REAL DEFAULT 0,
                PRIMARY KEY (user_id, currency),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # جدول المعاملات (موجود سابقاً)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                from_currency TEXT,
                to_currency TEXT,
                amount REAL,
                recipient TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # جدول طلبات السحب (موجود سابقاً)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                currency TEXT,
                card_number TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # في init_database أضف:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info', -- 'info', 'success', 'warning', 'error'
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password, salt=None):
        """تشفير كلمة المرور باستخدام salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex()
        return password_hash, salt
    
    def verify_password(self, password, password_hash, salt):
        """التحقق من كلمة المرور"""
        test_hash, _ = self.hash_password(password, salt)
        return test_hash == password_hash
    
    def create_user(self, username, password, email=None, phone=None):
        """إنشاء مستخدم جديد مع كلمة مرور مشفرة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # تشفير كلمة المرور
            password_hash, salt = self.hash_password(password)
            
            cursor.execute(
                'INSERT INTO users (username, password_hash, salt, email, phone) VALUES (?, ?, ?, ?, ?)',
                (username, password_hash, salt, email, phone)
            )
            user_id = cursor.lastrowid
            
            # إنشاء أرصدة ابتدائية
            currencies = ['USD', 'IRR', 'USDT']
            for currency in currencies:
                initial_balance = 1000 if currency == 'USD' else 0
                cursor.execute(
                    'INSERT INTO balances (user_id, currency, amount) VALUES (?, ?, ?)',
                    (user_id, currency, initial_balance)
                )
            
            conn.commit()
            return user_id
        except sqlite3.IntegrityError as e:
            print(f"❌ خطأ في إنشاء المستخدم: {e}")
            return None
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {e}")
            return None
        finally:
            conn.close()
    
    # دالة التوافق مع النظام القديم
    def create_user_legacy(self, username):
        """إنشاء مستخدم بدون كلمة مرور (للتتوافق مع النظام القديم)"""
        return self.create_user(username, "default_password")
    
    def authenticate_user(self, username, password):
        """المصادقة على المستخدم"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, password_hash, salt FROM users WHERE username = ?',
            (username,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user and self.verify_password(password, user[1], user[2]):
            return user[0]  # user_id
        return None
    
    def create_session(self, user_id, expires_hours=24):
        """إنشاء جلسة مستخدم"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        cursor.execute(
            'INSERT INTO user_sessions (user_id, session_token, expires_at) VALUES (?, ?, ?)',
            (user_id, session_token, expires_at)
        )
        
        conn.commit()
        conn.close()
        return session_token
    
    def validate_session(self, session_token):
        """التحقق من صحة الجلسة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT user_id, expires_at FROM user_sessions WHERE session_token = ? AND expires_at > ?',
            (session_token, datetime.now())
        )
        session = cursor.fetchone()
        conn.close()
        
        if session:
            return session[0]  # user_id
        return None
    
    def get_user_by_id(self, user_id):
        """جلب بيانات المستخدم"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, username, email, phone, created_at FROM users WHERE id = ?',
            (user_id,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'phone': user[3],
                'created_at': user[4]
            }
        return None
    
    # الدوال الحالية (للتوافق)
    def get_balance(self, user_id):
        """جلب أرصدة المستخدم"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT currency, amount FROM balances WHERE user_id = ?', 
            (user_id,)
        )
        balances = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        return balances

    def create_notification(self, user_id, title, message, type='info'):
        """إنشاء إشعار جديد"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, ?)',
            (user_id, title, message, type)
        )
        conn.commit()
        conn.close()

    def get_unread_notifications(self, user_id):
        """جلب الإشعارات غير المقروءة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, title, message, type, created_at FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC',
            (user_id,)
        )
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'id': row[0],
                'title': row[1],
                'message': row[2],
                'type': row[3],
                'date': row[4]
            })
        
        conn.close()
        return notifications

    def mark_notification_read(self, notification_id):
        """تحديد إشعار كمقروء"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE notifications SET is_read = 1 WHERE id = ?',
            (notification_id,)
        )
        conn.commit()
        conn.close()

# اختبار قاعدة البيانات المحدثة
if __name__ == '__main__':
    db = Database()
    
    # اختبار إنشاء مستخدم جديد
    user_id = db.create_user("test_user_secure", "secure_password123", "test@example.com", "123456789")
    if user_id:
        print(f"✅ تم إنشاء المستخدم الآمن برقم: {user_id}")
        
        # اختبار المصادقة
        auth_user = db.authenticate_user("test_user_secure", "secure_password123")
        if auth_user:
            print(f"✅ المصادقة ناجحة للمستخدم: {auth_user}")
            
            # اختبار الجلسة
            session = db.create_session(auth_user)
            print(f"✅ تم إنشاء الجلسة: {session}")
            
            # اختبار التحقق من الجلسة
            valid_user = db.validate_session(session)
            if valid_user:
                print(f"✅ الجلسة صالحة للمستخدم: {valid_user}")
            else:
                print("❌ الجلسة غير صالحة")
        else:
            print("❌ فشل المصادقة")
    else:
        print("❌ فشل إنشاء المستخدم")
    
    # اختبار التوافق مع النظام القديم
    balances = db.get_balance(1)
    print(f"📊 الأرصدة: {balances}")