# backend/services/exchange_service.py
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re

class ExchangeService:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    def get_current_rates(self):
        """Get current exchange rates from tgju.org with improved scraping"""
        cache_key = 'exchange_rates'
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return cached_data
        
        try:
            print("🌐 Fetching live exchange rates from tgju.org...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # Try multiple URLs and methods
            usd_to_irr = self.try_multiple_sources(headers)
            
            if not usd_to_irr:
                print("❌ Could not extract price from any source, using fallback")
                usd_to_irr = 1070000  # Current approximate rate
            
            print(f"✅ Current USD to IRR rate: {usd_to_irr:,.0f}")
                
        except Exception as e:
            print(f"❌ Error fetching rates: {e}")
            usd_to_irr = 1070000  # Current fallback rate
        
        rates = {
            'USD_IRR': float(usd_to_irr),
            'IRR_USD': 1 / float(usd_to_irr),
            'USD_USDT': 1.0,
            'USDT_USD': 1.0,
            'USDT_IRR': float(usd_to_irr),
            'IRR_USDT': 1 / float(usd_to_irr),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.cache[cache_key] = (rates, datetime.now())
        return rates
    
    def try_multiple_sources(self, headers):
        """Try multiple methods to get the USD price"""
        methods = [
            self.scrape_tgju_direct,
            self.scrape_tgju_api,
            self.scrape_alternative_site
        ]
        
        for method in methods:
            try:
                rate = method(headers)
                if rate and 500000 < rate < 2000000:  # Reasonable range
                    print(f"✅ Success with {method.__name__}: {rate:,.0f}")
                    return rate
            except Exception as e:
                print(f"❌ {method.__name__} failed: {e}")
                continue
        
        return None
    
    def scrape_tgju_direct(self, headers):
        """Direct scraping from tgju.org"""
        response = requests.get(
            'https://www.tgju.org/profile/price_dollar_rl',
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Look for the main price in various selectors
        price_selectors = [
            '[data-col="info.last_price"]',
            '.price',
            '.value',
            '.info-price',
            'span.value',
            'div.value',
            '.market-price',
            '[itemprop="price"]'
        ]
        
        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get_text().strip()
                price = self.clean_price(price_text)
                if price:
                    return price
        
        # Method 2: Look for specific data attributes
        data_elements = soup.find_all(attrs={"data-col": "info.last_price"})
        for element in data_elements:
            price_text = element.get_text().strip()
            price = self.clean_price(price_text)
            if price:
                return price
        
        # Method 3: Search for numeric patterns in the entire page
        text = soup.get_text()
        price_patterns = [
            r'(\d{1,3}(?:,\d{3})+,?\d*)',  # Numbers with Iranian commas
            r'(\d{6,7})',  # 6-7 digit numbers
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                price = self.clean_price(match)
                if price and 1000000 < price < 1200000:  # Current expected range
                    return price
        
        return None
    
    def scrape_tgju_api(self, headers):
        """Try to find API endpoints or JSON data"""
        try:
            # Sometimes tgju has API-like endpoints
            api_response = requests.get(
                'https://api.tgju.org/v1/data/sana/json',
                headers=headers,
                timeout=5
            )
            if api_response.status_code == 200:
                data = api_response.json()
                # Look for USD price in the response
                for key, value in data.items():
                    if 'price_dollar' in key.lower() and 'p' in value:
                        price = self.clean_price(str(value['p']))
                        if price:
                            return price
        except:
            pass
        
        try:
            # Another potential API endpoint
            api_response = requests.get(
                'https://www.tgju.org/ajax/price.json',
                headers=headers,
                timeout=5
            )
            if api_response.status_code == 200:
                data = api_response.json()
                # Parse the JSON response for USD price
                usd_price = data.get('price_dollar_rl', {}).get('price')
                if usd_price:
                    return self.clean_price(str(usd_price))
        except:
            pass
        
        return None
    
    def scrape_alternative_site(self, headers):
        """Fallback to alternative sites"""
        try:
            response = requests.get(
                'https://www.tgju.org/',
                headers=headers,
                timeout=10
            )
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for USD price in the main page
            usd_indicators = ['دلار', 'dollar', 'USD', 'price_dollar']
            
            for indicator in usd_indicators:
                elements = soup.find_all(string=re.compile(indicator, re.IGNORECASE))
                for element in elements:
                    parent = element.parent
                    if parent:
                        # Look for numbers near the indicator
                        text = parent.get_text()
                        price_pattern = r'(\d{1,3}(?:,\d{3})+,?\d*)'
                        matches = re.findall(price_pattern, text)
                        for match in matches:
                            price = self.clean_price(match)
                            if price and 1000000 < price < 1200000:
                                return price
        except:
            pass
        
        return None
    
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