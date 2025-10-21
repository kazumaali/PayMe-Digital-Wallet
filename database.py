import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name='wallet.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """إنشاء الجداول الأساسية"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول الأرصدة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER,
                currency TEXT NOT NULL,
                amount REAL DEFAULT 0,
                PRIMARY KEY (user_id, currency),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # جدول المعاملات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL, -- 'send', 'receive', 'exchange', 'withdraw'
                from_currency TEXT,
                to_currency TEXT,
                amount REAL,
                recipient TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, username):
        """إنشاء مستخدم جديد"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
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
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
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

# اختبار قاعدة البيانات
if __name__ == '__main__':
    db = Database()
    user_id = db.create_user("test_user")
    print(f"تم إنشاء المستخدم برقم: {user_id}")
    balances = db.get_balance(user_id)
    print(f"الأرصدة: {balances}")