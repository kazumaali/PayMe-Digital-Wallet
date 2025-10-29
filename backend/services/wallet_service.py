import hashlib
from models import db, Wallet, Card, User
import secrets

class WalletService:
    def generate_usdt_address(self, user_id):
        """Generate a unique USDT address for a user"""
        # In production, use a proper wallet generation service
        # This is a simplified version for demonstration
        base_string = f"{user_id}{secrets.token_hex(16)}"
        address = "0x" + hashlib.sha256(base_string.encode()).hexdigest()[:40]
        return address
    
    def get_usdt_address(self, user_id):
        """Get or generate USDT wallet address for user"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = Wallet(user_id=user_id)
            db.session.add(wallet)
        
        if not wallet.usdt_address:
            wallet.usdt_address = self.generate_usdt_address(user_id)
            db.session.commit()
        
        return wallet.usdt_address
    
    def get_balance(self, user_id):
        """Get user wallet balances"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = Wallet(user_id=user_id)
            db.session.add(wallet)
            db.session.commit()
        
        return {
            'USD': wallet.usd_balance,
            'USDT': wallet.usdt_balance,
            'IRR': wallet.irr_balance
        }
    
    def get_user_cards(self, user_id):
        """Get user's saved payment cards"""
        cards = Card.query.filter_by(user_id=user_id, is_active=True).all()
        return [
            {
                'id': card.id,
                'type': card.type,
                'last4': card.last4,
                'holder_name': card.holder_name,
                'currency': card.currency,
                'bank_name': card.bank_name
            }
            for card in cards
        ]
    
    def add_card(self, user_id, card_data):
        """Add a new payment card for user"""
        card = Card(
            user_id=user_id,
            type=card_data.get('type'),
            last4=card_data['number'][-4:],
            holder_name=card_data.get('holder_name'),
            expiry_month=card_data.get('expiry_month'),
            expiry_year=card_data.get('expiry_year'),
            currency=card_data.get('currency'),
            bank_name=card_data.get('bank_name'),
            card_number=card_data.get('number')  # In production, encrypt this
        )
        
        db.session.add(card)
        db.session.commit()
        
        return {
            'id': card.id,
            'type': card.type,
            'last4': card.last4,
            'currency': card.currency
        }
    
    def delete_card(self, user_id, card_id):
        """Soft delete a payment card"""
        card = Card.query.filter_by(id=card_id, user_id=user_id).first()
        if card:
            card.is_active = False
            db.session.commit()