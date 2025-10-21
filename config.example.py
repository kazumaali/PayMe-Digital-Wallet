# config.example.py - انسخ هذا كـ config.py واملأ بياناتك

DATABASE_CONFIG = {
    'name': 'YOUR_DATABASE_NAME',
    'path': './backend/'
}

EXCHANGE_RATE_SOURCES = {
    'tgju': 'https://api.tgju.org/',
    'binance': 'https://api.binance.com/'
}

# إعدادات التطبيق
DEBUG = True
SECRET_KEY = 'generate-secure-random-key-here'

# إعدادات البنوك (لا تضع معلومات حقيقية)
BANK_CONFIG = {
    'supported_banks': ['Bank Melli', 'Bank Saderat'],
    'withdrawal_fee': 0.01
}
