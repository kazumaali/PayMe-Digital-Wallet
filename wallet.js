const API_BASE = 'http://127.0.0.1:5000/api';

// Load user balances from backend when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateBalances();
    loadExchangeRates();
    startLiveRatesUpdates(); // Optional: for real-time updates
});

function getAuthToken() {
    const token = localStorage.getItem('authToken');
    if (!token) {
        console.error('No authentication token found');
        // For testing, create a demo token
        const demoToken = 'demo-token-' + Math.random().toString(36).substr(2);
        localStorage.setItem('authToken', demoToken);
        return demoToken;
    }
    return token;
}

// Updated function to get balances from backend
async function updateBalances() {
    try {
        const token = getAuthToken();
        if (!token) {
            console.error('No authentication token found');
            return;
        }

        const response = await fetch(`${API_BASE}/wallet/balance`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const balances = await response.json();
        
        // Update the display with actual balances from backend
        document.getElementById('p1').textContent = `USD: $${balances.USD?.toFixed(2) || '0.00'}`;
        document.getElementById('p2').textContent = `USDT: ${balances.USDT?.toFixed(2) || '0.00'}`;
        document.getElementById('p3').textContent = `IRR: ${(balances.IRR || 0).toLocaleString()} ﷼`;
        
    } catch (error) {
        console.error('Error fetching balances:', error);
        // Fallback to localStorage if backend is unavailable
        fallbackToLocalStorage();
    }
}

// Get exchange rates for the chart and display
async function loadExchangeRates() {
    try {
        console.log('🔄 Fetching exchange rates...');
        const response = await fetch(`${API_BASE}/exchange-rates`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const rates = await response.json();
        console.log('✅ Exchange rates received:', rates);
        
        updateUSDPricesDisplay(rates);
        
    } catch (error) {
        console.error('❌ Error fetching exchange rates:', error);
        // Fallback to static rates
        const fallbackRates = {
            USD_IRR: 1070000,
            IRR_USD: 0.000000934579,
            timestamp: new Date().toISOString(),
            source: 'fallback'
        };
        updateUSDPricesDisplay(fallbackRates);
    }
}

// Update the USD Prices section with live rates
function updateUSDPricesDisplay(rates) {
    const usdPriceElement = document.getElementById('usdP');
    if (usdPriceElement) {
        const usdToIrr = rates.USD_IRR?.toLocaleString('en-US') || '1,070,000';
        const irrToUsd = (rates.IRR_USD * 100000)?.toFixed(7) || '0.09';
        const source = rates.source || 'live';
        
        usdPriceElement.innerHTML = `
            <strong>Current USD Prices (Live - ${source})</strong><br>
            <small>1 USD = ${usdToIrr} IRR</small><br>
            <small>100,000 IRR = $${irrToUsd} USD</small><br>
            <small style="color: #666;">Updated: ${new Date(rates.timestamp).toLocaleTimeString()}</small>
        `;
        
        console.log('💰 Exchange rates updated:', {
            'USD_IRR': rates.USD_IRR,
            'IRR_USD': rates.IRR_USD,
            'timestamp': rates.timestamp,
            'source': rates.source
        });
    }
}

// Optional: Update rates periodically
function startLiveRatesUpdates() {
    // Update rates every 5 minutes
    setInterval(loadExchangeRates, 5 * 60 * 1000);
}

// در wallet.js - آپدیت تابع fallback
function fallbackToLocalStorage() {
    try {
        const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
        const balances = currentUser.balances || { USD: 0, USDT: 0, IRR: 0 };
        
        // استفاده از مقادیر پیش‌فرض منطبق با backend
        document.getElementById('p1').textContent = `USD: $${(balances.USD || 0).toFixed(2)}`;
        document.getElementById('p2').textContent = `USDT: ${(balances.USDT || 0).toFixed(2)}`;
        document.getElementById('p3').textContent = `IRR: ${(balances.IRR || 0).toLocaleString()} ﷼`;
        
        console.log('⚠️ Using localStorage fallback balances');
    } catch (error) {
        console.error('Fallback also failed:', error);
        // مقادیر کاملاً پیش‌فرض
        document.getElementById('p1').textContent = 'USD: $0.00';
        document.getElementById('p2').textContent = 'USDT: 0.00';
        document.getElementById('p3').textContent = 'IRR: 0 ﷼';
    }
}

async function testConnection() {
    try {
        console.log('🔧 Testing connection to:', `${API_BASE}/debug-connection`);
        
        const response = await fetch(`${API_BASE}/debug-connection`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({ test: 'connection' })
        });

        console.log('📡 Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Connection successful:', data);
            return true;
        } else {
            console.error('❌ Server error:', response.status);
            showMessage('Server error: ' + response.status, 'red');
            return false;
        }
    } catch (error) {
        console.error('❌ Connection failed:', error);
        showMessage('Cannot connect to server. Please check if backend is running.', 'red');
        return false;
    }
}

// If you want to keep the original function name for compatibility, you can do:
// This ensures other parts of your code that call updateBalances() still work
window.updateBalances = updateBalances;
