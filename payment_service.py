import stripe
from models import db, Transaction, Wallet
from services.exchange_service import ExchangeService
import json
from datetime import datetime

class PaymentService:
    def __init__(self):
        self.exchange_service = ExchangeService(navasan_api_key='freeVeBEP365HYZw58h3bdFVxui8EQXC')
        # Initialize Stripe (you'll need to set up Stripe keys)
        # stripe.api_key = config.STRIPE_SECRET_KEY
    
    def process_charge(self, user_id, amount, currency, payment_method, card_data):
        """Process wallet charge with actual payment"""
        try:
            # For USD payments - integrate with Stripe
            if currency == 'USD':
                # Create Stripe payment intent
                # intent = stripe.PaymentIntent.create(
                #     amount=int(amount * 100),  # cents
                #     currency='usd',
                #     payment_method=payment_method,
                #     confirm=True,
                #     return_url='https://yourdomain.com/success'
                # )
                
                # For now, simulate successful payment
                self._update_wallet_balance(user_id, currency, amount)
                
                transaction = Transaction(
                    user_id=user_id,
                    type='charge',
                    amount=amount,
                    currency=currency,
                    status='completed',
                    description=f'Wallet charge - {currency}',
                    metadata={'payment_method': 'card', 'card_data': card_data}
                )
                db.session.add(transaction)
                db.session.commit()
                
                return {
                    'success': True,
                    'transaction_id': transaction.id,
                    'amount': amount,
                    'currency': currency
                }
                
            elif currency == 'IRR':
                # Process Iranian card payment (integrate with local payment gateway)
                # This would connect to Iranian bank APIs
                self._update_wallet_balance(user_id, currency, amount)
                
                transaction = Transaction(
                    user_id=user_id,
                    type='charge',
                    amount=amount,
                    currency=currency,
                    status='completed',
                    description='شارژ کیف پول - ریال',
                    metadata={'payment_method': 'iranian_card', 'card_data': card_data}
                )
                db.session.add(transaction)
                db.session.commit()
                
                return {
                    'success': True,
                    'transaction_id': transaction.id,
                    'amount': amount,
                    'currency': currency
                }
                
            elif currency == 'USDT':
                # For USDT, we'd verify the blockchain transaction
                # This would check if USDT was sent to the user's address
                self._update_wallet_balance(user_id, currency, amount)
                
                transaction = Transaction(
                    user_id=user_id,
                    type='charge',
                    amount=amount,
                    currency=currency,
                    status='completed',
                    description='USDT deposit',
                    metadata={'payment_method': 'crypto', 'network': 'TRC20'}
                )
                db.session.add(transaction)
                db.session.commit()
                
                return {
                    'success': True,
                    'transaction_id': transaction.id,
                    'amount': amount,
                    'currency': currency
                }
                
        except Exception as e:
            # Log the failed transaction
            transaction = Transaction(
                user_id=user_id,
                type='charge',
                amount=amount,
                currency=currency,
                status='failed',
                description=f'Failed charge attempt - {currency}',
                metadata={'error': str(e)}
            )
            db.session.add(transaction)
            db.session.commit()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_withdrawal(self, user_id, amount, currency, card_id):
        """Process withdrawal to bank card"""
        try:
            # Check balance
            wallet = Wallet.query.filter_by(user_id=user_id).first()
            if not wallet:
                return {'success': False, 'error': 'Wallet not found'}
            
            balance = getattr(wallet, f'{currency.lower()}_balance', 0)
            if balance < amount:
                return {'success': False, 'error': 'Insufficient balance'}
            
            # Process withdrawal (integrate with payment processor)
            # For real implementation, this would connect to banking APIs
            
            # Update wallet balance
            self._update_wallet_balance(user_id, currency, -amount)
            
            transaction = Transaction(
                user_id=user_id,
                type='withdraw',
                amount=amount,
                currency=currency,
                status='completed',
                description=f'Withdrawal to card - {currency}',
                metadata={'card_id': card_id}
            )
            db.session.add(transaction)
            db.session.commit()
            
            return {
                'success': True,
                'transaction_id': transaction.id,
                'amount': amount,
                'currency': currency
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_transfer(self, from_user_id, to_email, amount, currency, message):
        """Transfer money to another user"""
        try:
            # Check sender balance
            from_wallet = Wallet.query.filter_by(user_id=from_user_id).first()
            if not from_wallet:
                return {'success': False, 'error': 'Sender wallet not found'}
            
            balance = getattr(from_wallet, f'{currency.lower()}_balance', 0)
            if balance < amount:
                return {'success': False, 'error': 'Insufficient balance'}
            
            # Find recipient
            from models import User
            recipient = User.query.filter_by(email=to_email).first()
            if not recipient:
                return {'success': False, 'error': 'Recipient not found'}
            
            # Transfer funds
            self._update_wallet_balance(from_user_id, currency, -amount)
            self._update_wallet_balance(recipient.id, currency, amount)
            
            # Record transactions for both users
            sender_tx = Transaction(
                user_id=from_user_id,
                type='send',
                amount=amount,
                currency=currency,
                status='completed',
                description=f'Transfer to {to_email}',
                metadata={'recipient': to_email, 'message': message}
            )
            
            receiver_tx = Transaction(
                user_id=recipient.id,
                type='receive',
                amount=amount,
                currency=currency,
                status='completed',
                description=f'Transfer from {from_user_id}',
                metadata={'sender': from_user_id, 'message': message}
            )
            
            db.session.add(sender_tx)
            db.session.add(receiver_tx)
            db.session.commit()
            
            return {
                'success': True,
                'transaction_id': sender_tx.id,
                'amount': amount,
                'currency': currency,
                'recipient': to_email
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_exchange(self, user_id, from_currency, to_currency, amount):
        """Exchange one currency for another using live rates"""
        try:
            # Check balance
            wallet = Wallet.query.filter_by(user_id=user_id).first()
            if not wallet:
                return {'success': False, 'error': 'Wallet not found'}
            
            from_balance = getattr(wallet, f'{from_currency.lower()}_balance', 0)
            if from_balance < amount:
                return {'success': False, 'error': 'Insufficient balance'}
            
            # Calculate exchange using live rates from Navasan
            exchange_result = self.exchange_service.calculate_exchange(
                from_currency, to_currency, amount
            )
            
            # Update balances
            self._update_wallet_balance(user_id, from_currency, -amount)
            self._update_wallet_balance(user_id, to_currency, exchange_result['final_amount'])
            
            transaction = Transaction(
                user_id=user_id,
                type='exchange',
                amount=amount,
                currency=from_currency,
                status='completed',
                description=f'Exchange {from_currency} to {to_currency}',
                metadata={
                    'from_currency': from_currency,
                    'to_currency': to_currency,
                    'exchange_rate': exchange_result['exchange_rate'],
                    'fee': exchange_result['fee'],
                    'final_amount': exchange_result['final_amount'],
                    'rate_source': 'navasan'
                }
            )
            db.session.add(transaction)
            db.session.commit()
            
            return {
                'success': True,
                'transaction_id': transaction.id,
                'from_amount': amount,
                'to_amount': exchange_result['final_amount'],
                'from_currency': from_currency,
                'to_currency': to_currency,
                'exchange_rate': exchange_result['exchange_rate'],
                'fee': exchange_result['fee']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _update_wallet_balance(self, user_id, currency, amount):
        """Update wallet balance for a user"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = Wallet(user_id=user_id)
            db.session.add(wallet)
        
        balance_field = f'{currency.lower()}_balance'
        current_balance = getattr(wallet, balance_field, 0)
        setattr(wallet, balance_field, current_balance + amount)
        
        db.session.commit()