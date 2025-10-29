let selectedCurrency = 'USD';
let userCards = [];
let currentBalance = { USD: 0, IRR: 0 };

function loadUserData() {
    // Load current user data
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    
    // Load user balances
    const users = JSON.parse(localStorage.getItem('users')) || [];
    const userData = users.find(u => u.email === currentUser.email) || {};
    currentBalance.USD = userData.balanceUSD || 0;
    currentBalance.IRR = userData.balanceIRR || 0;
    
    // Load user cards
    userCards = userData.cards || [];
    
    updateWithdrawalInfo();
}

function updateWithdrawalInfo() {
    selectedCurrency = document.getElementById('currency').value;
    
    // Update balance display
    const balanceElement = document.getElementById('availableBalance');
    if (selectedCurrency === 'USD') {
        balanceElement.textContent = `$${currentBalance.USD.toFixed(2)}`;
    } else {
        balanceElement.textContent = `${currentBalance.IRR.toLocaleString()} ﷼`;
    }
    
    // Update cards dropdown
    updateCardsDropdown();
    
    // Reset amount and validation
    document.getElementById('amount').value = '';
    validateAmount();
}

function updateCardsDropdown() {
    const cardSelect = document.getElementById('cardSelect');
    const cardPreview = document.getElementById('cardPreview');
    const noCardsMessage = document.getElementById('noCardsMessage');
    
    // Clear previous options
    cardSelect.innerHTML = '<option value="">-- Choose a card --</option>';
    
    // Filter cards by currency
    const filteredCards = userCards.filter(card => card.currency === selectedCurrency);
    
    if (filteredCards.length === 0) {
        cardSelect.style.display = 'none';
        cardPreview.style.display = 'none';
        noCardsMessage.style.display = 'block';
        return;
    }
    
    cardSelect.style.display = 'block';
    noCardsMessage.style.display = 'none';
    
    // Add cards to dropdown
    filteredCards.forEach((card, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${card.type} - ****${card.number.slice(-4)}`;
        cardSelect.appendChild(option);
    });
    
    // Show first card by default
    if (filteredCards.length > 0) {
        cardSelect.value = '0';
        showCardPreview();
    }
}

function showCardPreview() {
    const cardSelect = document.getElementById('cardSelect');
    const cardPreview = document.getElementById('cardPreview');
    const previewCardType = document.getElementById('previewCardType');
    const previewCardNumber = document.getElementById('previewCardNumber');
    const previewCardBank = document.getElementById('previewCardBank');
    
    if (cardSelect.value === '') {
        cardPreview.style.display = 'none';
        return;
    }
    
    const cardIndex = parseInt(cardSelect.value);
    const card = userCards.filter(c => c.currency === selectedCurrency)[cardIndex];
    
    if (card) {
        previewCardType.textContent = card.type || 'Credit Card';
        previewCardNumber.textContent = `**** **** **** ${card.number.slice(-4)}`;
        previewCardBank.textContent = card.bank || 'Bank';
        cardPreview.style.display = 'block';
    }
}

function validateAmount() {
    const amountInput = document.getElementById('amount');
    const withdrawBtn = document.getElementById('withdrawBtn');
    const amount = parseFloat(amountInput.value) || 0;
    const balance = selectedCurrency === 'USD' ? currentBalance.USD : currentBalance.IRR;
    
    // Calculate fee
    const fee = calculateFee(amount);
    const netAmount = amount - fee;
    
    if (amount <= 0) {
        withdrawBtn.disabled = true;
        return;
    }
    
    if (netAmount <= 0) {
        showMessage('Amount too small after fees', 'error');
        withdrawBtn.disabled = true;
        return;
    }
    
    if (amount > balance) {
        showMessage('Insufficient balance', 'error');
        withdrawBtn.disabled = true;
        return;
    }
    
    if (document.getElementById('cardSelect').value === '') {
        withdrawBtn.disabled = true;
        return;
    }
    
    withdrawBtn.disabled = false;
}

function calculateFee(amount) {
    const feePercentage = 0.01; // 1%
    let fee = amount * feePercentage;
    
    // Minimum fee
    if (selectedCurrency === 'USD') {
        fee = Math.max(fee, 1);
    } else {
        fee = Math.max(fee, 50000);
    }
    
    return fee;
}

function processWithdrawal() {
    const amountInput = document.getElementById('amount');
    const cardSelect = document.getElementById('cardSelect');
    const amount = parseFloat(amountInput.value);
    const balance = selectedCurrency === 'USD' ? currentBalance.USD : currentBalance.IRR;
    
    if (amount <= 0 || amount > balance) {
        showMessage('Invalid amount', 'error');
        return;
    }
    
    if (cardSelect.value === '') {
        showMessage('Please select a card', 'error');
        return;
    }
    
    // Calculate fee and net amount
    const fee = calculateFee(amount);
    const netAmount = amount - fee;
    
    // Update user balance
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    const users = JSON.parse(localStorage.getItem('users')) || [];
    const userIndex = users.findIndex(u => u.email === currentUser.email);
    
    if (userIndex !== -1) {
        if (selectedCurrency === 'USD') {
            users[userIndex].balanceUSD -= amount;
            currentBalance.USD -= amount;
        } else {
            users[userIndex].balanceIRR -= amount;
            currentBalance.IRR -= amount;
        }
        
        // Save updated data
        localStorage.setItem('users', JSON.stringify(users));
        
        // Show success message
        const currencySymbol = selectedCurrency === 'USD' ? '$' : '﷼';
        showMessage(
            `Success! $${amount.toFixed(2)} withdrawn to your card. Net amount after $${fee.toFixed(2)} fee: ${currencySymbol}${netAmount.toFixed(2)}. Funds will arrive in 1-3 business days.`,
            'success'
        );
        
        // Reset form
        amountInput.value = '';
        updateWithdrawalInfo();
        document.getElementById('withdrawBtn').disabled = true;
        
        // Update wallet page balance if it's open
        if (typeof updateWalletBalance === 'function') {
            updateWalletBalance();
        }
    } else {
        showMessage('User not found', 'error');
    }
}

function showMessage(text, type) {
    const message = document.getElementById('message');
    message.textContent = text;
    
    if (type === 'success') {
        message.style.color = '#065f46';
        message.style.backgroundColor = '#d1fae5';
        message.style.border = '1px solid #a7f3d0';
    } else {
        message.style.color = '#991b1b';
        message.style.backgroundColor = '#fef2f2';
        message.style.border = '1px solid #fecaca';
    }
    
    message.style.display = 'block';
    
    setTimeout(() => {
        message.style.display = 'none';
    }, 5000);
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadUserData();
});