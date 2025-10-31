# backend/services/exchange_service.py
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re

class ExchangeService:
    def __init__(self, navasan_api_key='freeVeBEP365HYZw58h3bdFVxui8EQXC'):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.navasan_api_key = navasan_api_key
        self.navasan_base_url = 'https://api.navasan.tech/v1/'
    
    def get_current_rates(self):
        """Get current exchange rates from Navasan API"""
        cache_key = 'exchange_rates'
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return cached_data
        
        try:
            print("🌐 Fetching live exchange rates from Navasan API...")
            
            # Try Navasan API first
            navasan_rates = self.get_navasan_rates()
            if navasan_rates:
                print("✅ Successfully fetched rates from Navasan API")
                self.cache[cache_key] = (navasan_rates, datetime.now())
                return navasan_rates
            
            # Fallback to web scraping if Navasan fails
            print("⚠️ Navasan API failed, falling back to web scraping...")
            scraped_rates = self.get_rates_from_web_scraping()
            self.cache[cache_key] = (scraped_rates, datetime.now())
            return scraped_rates
                
        except Exception as e:
            print(f"❌ Error fetching rates: {e}")
            return self.get_fallback_rates()
    
    def get_navasan_rates(self):
        """Get rates from Navasan API"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            # Navasan API endpoint for live rates
            response = requests.get(
                f'{self.navasan_base_url}latest',
                params={'api_key': self.navasan_api_key, 'items': 'usd,usdt,eur'},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_navasan_data(data)
            else:
                print(f"Navasan API returned status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error calling Navasan API: {e}")
            return None
    
    def parse_navasan_data(self, data):
        """Parse Navasan API response"""
        try:
            # Extract rates from Navasan response
            usd_to_irr = float(data.get('usd', {}).get('value', 1070000))
            usdt_to_irr = float(data.get('usdt', {}).get('value', 1070000))
            
            # If USDT rate is not available, use USD rate as approximation
            if usdt_to_irr == 1070000:  # Default value means not found
                usdt_to_irr = usd_to_irr
            
            rates = {
                'USD_IRR': usd_to_irr,
                'IRR_USD': 1 / usd_to_irr,
                'USD_USDT': 1.0,
                'USDT_USD': 1.0,
                'USDT_IRR': usdt_to_irr,
                'IRR_USDT': 1 / usdt_to_irr,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'navasan'
            }
            
            print(f"💰 Navasan Rates - USD: {usd_to_irr:,.0f} IRR, USDT: {usdt_to_irr:,.0f} IRR")
            return rates
            
        except Exception as e:
            print(f"Error parsing Navasan data: {e}")
            return None
    
    def get_rates_from_web_scraping(self):
        """Fallback to web scraping if API fails"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Try tgju.org as fallback
            response = requests.get(
                'https://www.tgju.org/profile/price_dollar_rl',
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for price in various selectors
            price_selectors = [
                '[data-col="info.last_price"]',
                '.price',
                '.value',
                '.info-price'
            ]
            
            for selector in price_selectors:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text().strip()
                    price = self.clean_price(price_text)
                    if price and 500000 < price < 2000000:
                        usd_to_irr = price
                        usdt_to_irr = price  # Assume same as USD for fallback
                        
                        rates = {
                            'USD_IRR': float(usd_to_irr),
                            'IRR_USD': 1 / float(usd_to_irr),
                            'USD_USDT': 1.0,
                            'USDT_USD': 1.0,
                            'USDT_IRR': float(usdt_to_irr),
                            'IRR_USDT': 1 / float(usdt_to_irr),
                            'timestamp': datetime.utcnow().isoformat(),
                            'source': 'tgju_fallback'
                        }
                        
                        print(f"✅ Fallback Rates - USD: {usd_to_irr:,.0f} IRR")
                        return rates
            
            return self.get_fallback_rates()
            
        except Exception as e:
            print(f"Web scraping failed: {e}")
            return self.get_fallback_rates()
    
    def get_fallback_rates(self):
        """Return fallback rates when all methods fail"""
        usd_to_irr = 1070000  # Current approximate rate
        usdt_to_irr = 1070000
        
        rates = {
            'USD_IRR': float(usd_to_irr),
            'IRR_USD': 1 / float(usd_to_irr),
            'USD_USDT': 1.0,
            'USDT_USD': 1.0,
            'USDT_IRR': float(usdt_to_irr),
            'IRR_USDT': 1 / float(usdt_to_irr),
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'fallback'
        }
        
        print("⚠️ Using fallback rates")
        return rates
    
    def clean_price(self, price_text):
        """Clean and convert price text to float"""
        try:
            # Remove commas (Iranian format uses commas as thousand separators)
            cleaned = price_text.replace(',', '').strip()
            
            # Remove any non-numeric characters except decimal point
            cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '.')
            
            # Remove multiple decimal points
            if '.' in cleaned:
                parts = cleaned.split('.')
                if len(parts) > 2:
                    cleaned = parts[0] + '.' + ''.join(parts[1:])
            
            if cleaned:
                price = float(cleaned)
                # Validate that it's a reasonable exchange rate
                if 500000 < price < 2000000:
                    return price
        except Exception as e:
            print(f"Error cleaning price '{price_text}': {e}")
        
        return None
    
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