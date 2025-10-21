import sqlite3
from datetime import datetime

class WalletManager:
    def __init__(self, db_name='wallet.db'):
        self.db_name = db_name
    
    def send_money(self, from_user_id, to_user_id, amount, currency, recipient_address):
        """إرسال أموال من مستخدم إلى آخر"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # التحقق من رصيد المرسل
            cursor.execute(
                'SELECT amount FROM balances WHERE user_id = ? AND currency = ?',
                (from_user_id, currency)
            )
            sender_balance = cursor.fetchone()
            
            if not sender_balance or sender_balance[0] < amount:
                return {"success": False, "message": "رصيد غير كافي"}
            
            # خصم من المرسل
            cursor.execute(
                'UPDATE balances SET amount = amount - ? WHERE user_id = ? AND currency = ?',
                (amount, from_user_id, currency)
            )
            
            # إضافة للمستلم (إذا كان المستلم موجوداً في نظامنا)
            if to_user_id:
                cursor.execute(
                    'UPDATE balances SET amount = amount + ? WHERE user_id = ? AND currency = ?',
                    (amount, to_user_id, currency)
                )
            
            # تسجيل المعاملة
            cursor.execute(
                '''INSERT INTO transactions 
                   (user_id, type, from_currency, amount, recipient, status) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (from_user_id, 'send', currency, amount, recipient_address, 'completed')
            )
            
            conn.commit()
            return {"success": True, "message": "تم الإرسال بنجاح"}
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "message": f"خطأ في الإرسال: {str(e)}"}
        finally:
            conn.close()
    
    def get_transaction_history(self, user_id):
        """جلب سجل المعاملات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT type, from_currency, to_currency, amount, recipient, status, created_at 
               FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 10''',
            (user_id,)
        )
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                'type': row[0],
                'from_currency': row[1],
                'to_currency': row[2],
                'amount': row[3],
                'recipient': row[4],
                'status': row[5],
                'date': row[6]
            })
        
        conn.close()
        return transactions

# اختبار النظام
if __name__ == '__main__':
    wallet = WalletManager()
    print("✅ نظام المحفظة جاهز")