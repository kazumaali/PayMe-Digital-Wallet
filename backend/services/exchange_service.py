import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

class ExchangeService:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    def get_current_rates(self):
        """Get current exchange rates from tgju.org"""
        cache_key = 'exchange_rates'
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return cached_data
        
        try:
            # Scrape from tgju.org
            response = requests.get('https://www.tgju.org/profile/price_dollar_rl')
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the price element (this selector might need adjustment)
            price_element = soup.find('span', {'class': 'value'})
            usd_to_irr = float(price_element.text.replace(',', '')) if price_element else 42000
            
            rates = {
                'USD_IRR': usd_to_irr,
                'IRR_USD': 1 / usd_to_irr,
                'USD_USDT': 1.0,
                'USDT_USD': 1.0,
                'USDT_IRR': usd_to_irr,
                'IRR_USDT': 1 / usd_to_irr,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.cache[cache_key] = (rates, datetime.now())
            return rates
            
        except Exception as e:
            # Fallback rates
            return {
                'USD_IRR': 42000,
                'IRR_USD': 0.0000238,
                'USD_USDT': 1.0,
                'USDT_USD': 1.0,
                'USDT_IRR': 42000,
                'IRR_USDT': 0.0000238,
                'timestamp': datetime.utcnow().isoformat(),
                'note': 'Using fallback rates'
            }
    
    def get_rate(self, base_currency):
        """Get exchange rate for specific base currency"""
        rates = self.get_current_rates()
        
        if base_currency == 'USD':
            return {
                'USDT': rates['USD_USDT'],
                'IRR': rates['USD_IRR']
            }
        elif base_currency == 'USDT':
            return {
                'USD': rates['USDT_USD'],
                'IRR': rates['USDT_IRR']
            }
        elif base_currency == 'IRR':
            return {
                'USD': rates['IRR_USD'],
                'USDT': rates['IRR_USDT']
            }
        else:
            raise ValueError(f"Unsupported base currency: {base_currency}")
    
    def calculate_exchange(self, from_currency, to_currency, amount):
        """Calculate exchange between currencies"""
        rates = self.get_current_rates()
        rate_key = f"{from_currency}_{to_currency}"
        
        if rate_key not in rates:
            raise ValueError(f"Unsupported currency pair: {from_currency} to {to_currency}")
        
        rate = rates[rate_key]
        converted_amount = amount * rate
        
        # Apply exchange fee (0.5%)
        fee = converted_amount * 0.005
        final_amount = converted_amount - fee
        
        return {
            'original_amount': amount,
            'converted_amount': converted_amount,
            'final_amount': final_amount,
            'exchange_rate': rate,
            'fee': fee,
            'from_currency': from_currency,
            'to_currency': to_currency
        }