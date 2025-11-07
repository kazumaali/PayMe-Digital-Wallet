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

function updateBalance() {
    const currency = document.getElementById('currency').value;
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    const balances = currentUser.balances || { USD: 0, USDT: 0, IRR: 0 };
    
    const symbol = currency === 'USD' ? '$' : currency === 'IRR' ? '﷼ ' : '';
    document.getElementById('availableBalance').textContent = 
        `${symbol}${balances[currency]?.toLocaleString()}`;
}

function sendMoney() {
    const currency = document.getElementById('currency').value;
    const amount = parseFloat(document.getElementById('amount').value);
    const message = document.getElementById('message').value;
    const recipientEmail = document.getElementById('recipientEmail').value;
    
    // Validation
    if (!amount || amount <= 0) {
        showMessage('Please enter a valid amount!', 'red');
        return;
    }
    
    if (!recipientEmail) {
        showMessage('Please enter recipient email!', 'red');
        return;
    }
    
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    const balances = currentUser.balances || { USD: 0, USDT: 0, IRR: 0 };
    
    if (amount > balances[currency]) {
        showMessage('Insufficient balance!', 'red');
        return;
    }
    
    // Process transaction
    showMessage('Processing transaction...', 'blue');
    
    setTimeout(() => {
        // Update sender balance
        balances[currency] -= amount;
        currentUser.balances = balances;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        // Save transaction history
        const transactions = JSON.parse(localStorage.getItem('transactions')) || [];
        transactions.push({
            type: 'send',
            currency: currency,
            amount: amount,
            recipient: recipientEmail,
            message: message,
            date: new Date().toISOString(),
            status: 'completed'
        });
        localStorage.setItem('transactions', JSON.stringify(transactions));
        
        showMessage(`Successfully sent ${getCurrencySymbol(currency)}${amount.toLocaleString()} to ${recipientEmail}`, 'green');
        
        // Clear form
        document.getElementById('amount').value = '';
        document.getElementById('message').value = '';
        document.getElementById('recipientEmail').value = '';
        updateBalance();
    }, 1500);
}

function getCurrencySymbol(currency) {
    return currency === 'USD' ? '$' : currency === 'IRR' ? '﷼ ' : '';
}

function showMessage(text, color) {
    const message = document.getElementById('sendMessage');
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
document.addEventListener('DOMContentLoaded', function() {
    updateBalance();
});