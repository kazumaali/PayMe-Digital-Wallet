# config.example.py
# Copy this file to config.py and fill in your actual values

import os

class Config:
    # Flask Configuration
    SECRET_KEY = 'your-secret-key-here'
    DEBUG = False
    TESTING = False
    
    # Database Configuration
    DATABASE_URL = 'sqlite:///wallet.db'  # For production, use PostgreSQL: postgresql://user:pass@localhost/dbname'
    
    # Payment Gateway Configuration
    STRIPE_SECRET_KEY = 'sk_test_your_stripe_secret_key'
    STRIPE_PUBLISHABLE_KEY = 'pk_test_your_stripe_publishable_key'
    
    # Crypto Configuration
    BLOCKCYPHER_API_KEY = 'your_blockcypher_api_key'
    COINBASE_API_KEY = 'your_coinbase_api_key'
    COINBASE_API_SECRET = 'your_coinbase_api_secret'
    
    # Exchange Rate API
    EXCHANGE_RATE_API_KEY = 'your_exchange_rate_api_key'
    
    # Bank Integration (for IRR)
    BANK_API_BASE_URL = 'https://api.your-bank.com'
    BANK_API_KEY = 'your_bank_api_key'
    BANK_API_SECRET = 'your_bank_api_secret'
    
    # Security
    JWT_SECRET_KEY = 'your-jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    
    # CORS
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']

class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE_URL = 'sqlite:///dev_wallet.db'

class ProductionConfig(Config):
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///wallet.db')
    
class TestingConfig(Config):
    TESTING = True
    DATABASE_URL = 'sqlite:///test_wallet.db'