const API_BASE = 'http://192.168.1.102:5000/api';

function getAuthToken() {
    return localStorage.getItem('authToken');
}

let selectedCurrency = 'USD';
let userCards = [];
let currentBalance = { USD: 0, IRR: 0 };

async function loadUserData() {
    console.log('🔧 Withdraw page loaded, testing connection...');
    await testConnection();
    
    // بقیه کد...
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    
    // ابتدا از backend موجودی بگیرید
    await updateBalancesFromBackend();
    
    // سپس از localStorage به عنوان fallback استفاده کنید
    if (currentUser.balances) {
        currentBalance.USD = currentUser.balances.USD || 0;
        currentBalance.IRR = currentUser.balances.IRR || 0;
    }
    
    // Load user cards from localStorage
    userCards = JSON.parse(localStorage.getItem('userCards')) || [];
    
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
    
    // Add cards to dropdown with names if available
    filteredCards.forEach((card, index) => {
        const option = document.createElement('option');
        option.value = index;
        const cardName = card.name ? ` - ${card.name}` : '';
        option.textContent = `${card.type} - ****${card.number.slice(-4)}${cardName}`;
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
    const filteredCards = userCards.filter(c => c.currency === selectedCurrency);
    const card = filteredCards[cardIndex];
    
    if (card) {
        const cardName = card.name ? ` - ${card.name}` : '';
        previewCardType.textContent = (card.type || 'Credit Card') + cardName;
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

async function requestWithdrawalOTP() {
    const cardSelect = document.getElementById('cardSelect');
    const amountInput = document.getElementById('amount');
    const amount = parseFloat(amountInput.value);
    
    if (cardSelect.value === '') {
        showMessage('لطفا یک کارت انتخاب کنید!', 'error');
        return;
    }
    
    if (!amount || amount <= 0) {
        showMessage('لطفا مبلغ برداشت را وارد کنید!', 'error');
        return;
    }
    
    // تست اتصال اول
    const isConnected = await testConnection();
    if (!isConnected) {
        return;
    }
    
    const cardIndex = parseInt(cardSelect.value);
    const filteredCards = userCards.filter(c => c.currency === selectedCurrency);
    const card = filteredCards[cardIndex];
    
    showMessage('در حال ارسال رمز پویا...', 'success');
    
    try {
        console.log('📤 Sending withdrawal OTP request for card:', card.number);
        
        const response = await fetch('${API_BASE}/payment/request-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                card_number: card.number,
                card_last4: card.last4
            })
        });

        console.log('📥 Response status:', response.status);
        const data = await response.json();
        console.log('📥 Response data:', data);
        
        if (data.success) {
            showMessage('✅ رمز پویا ارسال شد. لطفا پیامک خود را چک کنید.', 'success');
            document.getElementById('otpSection').style.display = 'block';
            document.getElementById('withdrawalOtp').focus();
        } else {
            showMessage('❌ ' + data.error, 'error');
        }
    } catch (error) {
        console.error('❌ Error requesting OTP:', error);
        showMessage('خطا در ارتباط با سرور. لطفا دوباره تلاش کنید.', 'error');
    }
}

async function processWithdrawal() {
    const amountInput = document.getElementById('amount');
    const cardSelect = document.getElementById('cardSelect');
    const otpInput = document.getElementById('withdrawalOtp');
    const amount = parseFloat(amountInput.value);
    const otp = otpInput.value;
    
    if (!amount || amount <= 0) {
        showMessage('لطفا مبلغ برداشت را وارد کنید!', 'error');
        return;
    }
    
    if (!otp) {
        showMessage('لطفا رمز پویا را وارد کنید!', 'error');
        return;
    }
    
    const cardIndex = parseInt(cardSelect.value);
    const filteredCards = userCards.filter(c => c.currency === selectedCurrency);
    const card = filteredCards[cardIndex];
    
    showMessage('در حال پردازش درخواست برداشت...', 'success');
    
    try {
        const response = await fetch('${API_BASE}/payment/withdraw', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                amount: amount,
                currency: selectedCurrency,
                otp_code: otp,
                card_number: card.number  // ✅ ارسال شماره کارت
            })
        });

        const data = await response.json();
        
        if (data.success) {
            showMessage(`✅ برداشت موفق! مبلغ ${amount.toLocaleString()} ${selectedCurrency} از حساب شما کسر شد.`, 'success');
            
            // به‌روزرسانی موجودی
            await updateBalancesFromBackend();
            document.getElementById('otpSection').style.display = 'none';
            otpInput.value = '';
            amountInput.value = '';
            
            // به‌روزرسانی موجودی نمایش داده شده
            updateWithdrawalInfo();
            
        } else {
            showMessage('❌ خطا در برداشت: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error processing withdrawal:', error);
        showMessage('خطا در ارتباط با سرور', 'error');
    }
}

async function updateBalancesFromBackend() {
    try {
        const response = await fetch(`${API_BASE}/wallet/balance`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const balances = await response.json();
            currentBalance.USD = balances.USD || 0;
            currentBalance.IRR = balances.IRR || 0;
            
            // به‌روزرسانی localStorage
            const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
            currentUser.balances = balances;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
        }
    } catch (error) {
        console.error('Error updating balances from backend:', error);
    }
}

async function testConnection() {
    try {
        const response = await fetch(`${API_BASE}/test`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Connection to server successful:', data);
            return true;
        } else {
            console.error('❌ Server response not OK:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ Connection to server failed:', error);
        showMessage('اتصال به سرور برقرار نیست. لطفا از روشن بودن سرور اطمینان حاصل کنید.', 'error');
        return false;
    }
}