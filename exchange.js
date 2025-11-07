const API_BASE = 'http://127.0.0.1:5000/api';

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

let currentRates = {
    USD: { USDT: 1.00, IRR: 1070000 },
    USDT: { USD: 1.00, IRR: 1070000 },
    IRR: { USD: 0.000000934579, USDT: 0.000000934579 }
};

const exchangeFee = 0.005; // 0.5%

// Load current exchange rates from backend
async function loadExchangeRates() {
    try {
        const response = await fetch(`${API_BASE}/exchange-rates`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const rates = await response.json();
        
        // Update current rates with live data
        currentRates = {
            USD: { 
                USDT: rates.USD_USDT || 1.00, 
                IRR: rates.USD_IRR || 1070000 
            },
            USDT: { 
                USD: rates.USDT_USD || 1.00, 
                IRR: rates.USDT_IRR || 1070000 
            },
            IRR: { 
                USD: rates.IRR_USD || 0.000000934579, 
                USDT: rates.IRR_USDT || 0.000000934579 
            }
        };
        
        console.log('💰 Live exchange rates loaded:', currentRates);
        return rates;
        
    } catch (error) {
        console.error('Error fetching exchange rates:', error);
        // Keep using the default rates
        return currentRates;
    }
}

function updateBalances() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    const balances = currentUser.balances || { USD: 0, USDT: 0, IRR: 0 };
    
    document.getElementById('balanceUSD').textContent = `USD: $${balances.USD.toFixed(2)}`;
    document.getElementById('balanceUSDT').textContent = `USDT: ${balances.USDT.toFixed(2)}`;
    document.getElementById('balanceIRR').textContent = `IRR: ${balances.IRR.toLocaleString()} ﷼`;
}

async function calculateExchange() {
    const fromAmount = parseFloat(document.getElementById('fromAmount').value) || 0;
    const fromCurrency = document.getElementById('fromCurrency').value;
    const toCurrency = document.getElementById('toCurrency').value;
    
    if (fromAmount <= 0) {
        document.getElementById('toAmount').value = '';
        return;
    }
    
    // Ensure we have the latest rates
    await loadExchangeRates();
    
    // Get exchange rate
    const rate = currentRates[fromCurrency][toCurrency];
    
    if (!rate) {
        showMessage('Exchange rate not available for this pair', 'red');
        return;
    }
    
    // Calculate amount after fee
    const amountAfterFee = fromAmount * (1 - exchangeFee);
    const toAmount = amountAfterFee * rate;
    
    document.getElementById('toAmount').value = toAmount.toFixed(2);
    
    // Update rate display
    document.getElementById('rateDisplay').textContent = 
        `1 ${fromCurrency} = ${rate.toLocaleString()} ${toCurrency}`;
}

async function executeExchange() {
    const fromAmount = parseFloat(document.getElementById('fromAmount').value);
    const fromCurrency = document.getElementById('fromCurrency').value;
    const toCurrency = document.getElementById('toCurrency').value;
    const toAmount = parseFloat(document.getElementById('toAmount').value);
    
    // Validation
    if (!fromAmount || fromAmount <= 0) {
        showMessage('Please enter a valid amount!', 'red');
        return;
    }
    
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    const balances = currentUser.balances || { USD: 0, USDT: 0, IRR: 0 };
    
    // Check balance
    if (fromAmount > balances[fromCurrency]) {
        showMessage('Insufficient balance!', 'red');
        return;
    }
    
    // Ensure we have latest rates
    await loadExchangeRates();
    const rate = currentRates[fromCurrency][toCurrency];
    
    if (!rate) {
        showMessage('Exchange rate not available', 'red');
        return;
    }
    
    // Process exchange
    showMessage('Processing exchange...', 'blue');
    
    setTimeout(() => {
        // Update balances
        balances[fromCurrency] -= fromAmount;
        balances[toCurrency] += toAmount;
        
        // Save updated balances
        currentUser.balances = balances;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        // Save transaction
        const transactions = JSON.parse(localStorage.getItem('transactions')) || [];
        transactions.push({
            type: 'exchange',
            fromCurrency: fromCurrency,
            fromAmount: fromAmount,
            toCurrency: toCurrency,
            toAmount: toAmount,
            rate: rate,
            fee: fromAmount * exchangeFee,
            date: new Date().toISOString(),
            status: 'completed'
        });
        localStorage.setItem('transactions', JSON.stringify(transactions));
        
        showMessage(`Successfully exchanged ${fromAmount} ${fromCurrency} to ${toAmount.toFixed(2)} ${toCurrency}`, 'green');
        
        // Update UI
        updateBalances();
        document.getElementById('fromAmount').value = '';
        document.getElementById('toAmount').value = '';
    }, 1500);
}

function showMessage(text, color) {
    const message = document.getElementById('exchangeMessage');
    message.textContent = text;
    message.style.color = color === 'green' ? '#155724' : color === 'red' ? '#721c24' : '#0c5460';
    message.style.backgroundColor = color === 'green' ? '#d4edda' : 
                                  color === 'red' ? '#f8d7da' : '#d1ecf1';
    message.style.border = `1px solid ${color === 'green' ? '#c3e6cb' : 
                                  color === 'red' ? '#f5c6cb' : '#bee5eb'}`;
    message.style.display = 'block';
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

// Initialize page
document.addEventListener('DOMContentLoaded', async function() {
    updateBalances();
    
    // Load exchange rates on page load
    await loadExchangeRates();
    
    // Set up currency pairs to avoid same currency
    document.getElementById('fromCurrency').addEventListener('change', function() {
        const fromCurrency = this.value;
        const toSelect = document.getElementById('toCurrency');
        
        // Remove current options
        toSelect.innerHTML = '';
        
        // Add options excluding the selected from currency
        ['USD', 'USDT', 'IRR'].forEach(currency => {
            if (currency !== fromCurrency) {
                const option = document.createElement('option');
                option.value = currency;
                option.textContent = currency;
                toSelect.appendChild(option);
            }
        });
        
        calculateExchange();
    });
    
    // Trigger initial setup
    document.getElementById('fromCurrency').dispatchEvent(new Event('change'));
});