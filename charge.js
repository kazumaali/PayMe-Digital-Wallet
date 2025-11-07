const API_BASE = 'http://127.0.0.1:5000/api';

function getAuthToken() {
    const token = localStorage.getItem('authToken');
    if (!token) {
        console.error('No authentication token found');
        // redirect to login
        window.location.href = 'login.html';
        return null;
    }
    return token;
}

const currencySelect = document.getElementById('currency');
const cardSelection = document.getElementById('cardSelection');
const amountSection = document.getElementById('amountSection');
const cardsSelect = document.getElementById('cards');
const addCardForm = document.getElementById('addCardForm');
const usdCardFields = document.getElementById('usdCardFields');
const irrCardFields = document.getElementById('irrCardFields');
const irrNewCardFields = document.getElementById('irrNewCardFields');
const irrSavedCardInfo = document.getElementById('irrSavedCardInfo');
const selectedCardDisplay = document.getElementById('selectedCardDisplay');

// Initialize user cards
let userCards = JSON.parse(localStorage.getItem('userCards')) || [];
let selectedCard = null;

updateCardsDropdown();

currencySelect.addEventListener('change', function() {
    const currency = this.value;
    hideAllPaymentSections();
    cardSelection.style.display = 'none';
    amountSection.style.display = 'none';
    addCardForm.style.display = 'none';
    resetIRRForm();
    
    if (currency === 'USD' || currency === 'IRR') {
        cardSelection.style.display = 'block';
        amountSection.style.display = 'block';
        
        if (currency === 'USD') {
            document.getElementById('usdPayment').style.display = 'block';
        } else if (currency === 'IRR') {
            document.getElementById('irrPayment').style.display = 'block';
        }
    } else if (currency === 'USDT') {
        amountSection.style.display = 'block';
        document.getElementById('usdtPayment').style.display = 'block';
        generateUSDTAddress();
    }
});

// Add event listener for card selection
cardsSelect.addEventListener('change', function() {
    const selectedIndex = this.value;
    if (selectedIndex === '') {
        selectedCard = null;
        resetIRRForm();
        return;
    }
    
    selectedCard = userCards[selectedIndex];
    
    if (currencySelect.value === 'IRR' && selectedCard.currency === 'IRR') {
        // Auto-fill IRR card details and hide input fields
        showSavedIRRCard();
    }
});

function hideAllPaymentSections() {
    document.getElementById('usdPayment').style.display = 'none';
    document.getElementById('irrPayment').style.display = 'none';
    document.getElementById('usdtPayment').style.display = 'none';
    addCardForm.style.display = 'none';
}

// Update the updateCardsDropdown function
function updateCardsDropdown() {
    cardsSelect.innerHTML = '<option value="">-- Please choose --</option>';
    userCards.forEach((card, index) => {
        const option = document.createElement('option');
        option.value = index;
        const cardName = card.name ? ` (${card.name})` : '';
        option.textContent = `${card.type} - ****${card.last4}${cardName} (${card.currency})`;
        cardsSelect.appendChild(option);
    });
    
    // Update saved cards list
    updateSavedCardsList();
}

// Add new function to display saved cards with delete option
function updateSavedCardsList() {
    const savedCardsList = document.getElementById('savedCardsList');
    const savedCardsSection = document.getElementById('savedCardsSection');
    
    if (userCards.length === 0) {
        savedCardsSection.style.display = 'none';
        return;
    }
    
    savedCardsSection.style.display = 'block';
    savedCardsList.innerHTML = '';
    
    userCards.forEach((card, index) => {
        const cardElement = document.createElement('div');
        cardElement.className = 'saved-card';
        cardElement.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin: 8px 0;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        `;
        
        const cardName = card.name ? ` (${card.name})` : '';
        cardElement.innerHTML = `
            <div>
                <strong>${card.type} - ****${card.last4}${cardName}</strong>
                <br>
                <small>Currency: ${card.currency}</small>
            </div>
            <button onclick="deleteCard(${index})" style="
                background: #dc3545;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            ">Delete</button>
        `;
        
        savedCardsList.appendChild(cardElement);
    });
}

// Update showAddCardForm to clear card name field
function showAddCardForm() {
    const currency = currencySelect.value;
    if (!currency) {
        showMessage('Please select a currency first!', 'red');
        return;
    }
    
    addCardForm.style.display = 'block';
    
    // Show appropriate fields based on currency
    if (currency === 'USD') {
        usdCardFields.style.display = 'block';
        irrCardFields.style.display = 'none';
    } else if (currency === 'IRR') {
        usdCardFields.style.display = 'none';
        irrCardFields.style.display = 'block';
    }
    
    // Clear form
    document.getElementById('cardName').value = '';
    document.getElementById('newCardNumber').value = '';
    document.getElementById('newExpiryDate').value = '';
    document.getElementById('newCvv').value = '';
    document.getElementById('newCardHolder').value = '';
    document.getElementById('newExpiryDateIRR').value = '';
    document.getElementById('newCvv2').value = '';
    
    document.getElementById('cardPhone').value = '';
}

function hideAddCardForm() {
    addCardForm.style.display = 'none';
}

// Update addNewCard function to include card name
function addNewCard() {
    const currency = currencySelect.value;
    const cardNumber = document.getElementById('newCardNumber').value.replace(/\s/g, '');
    const cardName = document.getElementById('cardName').value.trim();
    let phoneNumber = '';
    if (currency === 'IRR') {
        if (!phoneNumber || phoneNumber.length !== 11 || !phoneNumber.startsWith('09')) {
            showMessage('لطفا شماره موبایل صحیح را وارد کنید', 'red');
            return;
        }
    }

    // Validation
    if (!cardNumber || cardNumber.length < 16) {
        showMessage('Please enter a valid card number!', 'red');
        return;
    }

    let newCard;
    
    if (currency === 'USD') {
        const expiryDate = document.getElementById('newExpiryDate').value;
        const cvv = document.getElementById('newCvv').value;
        const cardHolder = document.getElementById('newCardHolder').value;

        if (!expiryDate || !cvv || !cardHolder) {
            showMessage('Please fill all card details!', 'red');
            return;
        }

        newCard = {
            name: cardName,
            type: 'Visa/MasterCard',
            last4: cardNumber.slice(-4),
            number: cardNumber,
            expiry: expiryDate,
            cvv: cvv,
            holder: cardHolder,
            currency: currency,
            bank: 'International Bank'
        };
    } else if (currency === 'IRR') {
        const expiryDate = document.getElementById('newExpiryDateIRR').value;
        const cvv2 = document.getElementById('newCvv2').value;

        if (!expiryDate || !cvv2) {
            showMessage('Please fill all card details!', 'red');
            return;
        }

        newCard = {
            name: cardName,
            type: 'Iranian Bank Card',
            last4: cardNumber.slice(-4),
            number: cardNumber,
            expiry: expiryDate,
            cvv2: cvv2,
            currency: currency,
            bank: 'Iranian Bank',
            phone: phoneNumber
        };
    }
    
    userCards.push(newCard);
    localStorage.setItem('userCards', JSON.stringify(userCards));
    updateCardsDropdown();
    hideAddCardForm();
    showMessage('New card added successfully!', 'green');
}

// Add delete card function
function deleteCard(index) {
    if (confirm('Are you sure you want to delete this card?')) {
        userCards.splice(index, 1);
        localStorage.setItem('userCards', JSON.stringify(userCards));
        updateCardsDropdown();
        showMessage('Card deleted successfully!', 'green');
    }
}

function showSavedIRRCard() {
    if (selectedCard && selectedCard.currency === 'IRR') {
        // Hide the input fields for new card
        irrNewCardFields.style.display = 'none';
        
        // Show the saved card info
        irrSavedCardInfo.style.display = 'block';
        selectedCardDisplay.textContent = `${selectedCard.type} - ****${selectedCard.last4}`;
        
        // Auto-fill the hidden fields with saved card data
        document.getElementById('irrBank').value = 'melli'; // Default bank
        document.getElementById('irrCardNumber').value = selectedCard.number;
        document.getElementById('irrExpiryDate').value = selectedCard.expiry;
        document.getElementById('irrCvv2').value = selectedCard.cvv2;
    }
}

function resetIRRForm() {
    // Show all input fields
    irrNewCardFields.style.display = 'block';
    irrSavedCardInfo.style.display = 'none';
    
    // Clear all fields
    document.getElementById('irrBank').value = '';
    document.getElementById('irrCardNumber').value = '';
    document.getElementById('irrExpiryDate').value = '';
    document.getElementById('irrCvv2').value = '';
    document.getElementById('irrDynamicCode').value = '';
    
    selectedCard = null;
}

async function requestDynamicCode() {
    if (!selectedCard) {
        showMessage('لطفا ابتدا یک کارت انتخاب کنید!', 'red');
        return;
    }

    // تست اتصال اول
    const isConnected = await testConnection();
    if (!isConnected) {
        return;
    }

    showMessage('در حال ارسال رمز پویا...', 'blue');
    
    try {
        console.log('📤 Sending OTP request for card:', selectedCard.number);
        
        const response = await fetch(`${API_BASE}/payment/request-otp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                card_number: selectedCard.number,
                card_last4: selectedCard.last4
            })
        });

        console.log('📥 Response status:', response.status);
        
        const data = await response.json();
        console.log('📥 Response data:', data);
        
        if (data.success) {
            showMessage('✅ رمز پویا ارسال شد. لطفا پیامک خود را چک کنید.', 'green');
            document.getElementById('irrDynamicCode').disabled = false;
            document.getElementById('irrDynamicCode').focus();
        } else {
            showMessage('❌ ' + data.error, 'red');
        }
    } catch (error) {
        console.error('❌ Error in OTP request:', error);
        showMessage('خطا در ارتباط با سرور. لطفا دوباره تلاش کنید.', 'red');
    }
}

async function requestWithdrawalOTP() {
    const cardSelect = document.getElementById('cardSelect');
    if (cardSelect.value === '') {
        showMessage('لطفا یک کارت انتخاب کنید!', 'error');
        return;
    }
    
    const cardIndex = parseInt(cardSelect.value);
    const filteredCards = userCards.filter(c => c.currency === selectedCurrency);
    const card = filteredCards[cardIndex];
    
    showMessage('درخواست رمز پویا ارسال شد...', 'success');
    
    try {
        const response = await fetch(`${API_BASE}/payment/request-otp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                card_number: card.number,  // فقط شماره کارت
                card_last4: card.last4     // فقط 4 رقم آخر
            })
        });

        const data = await response.json();
        
        if (data.success) {
            showMessage('رمز پویا به شماره موبایل مرتبط با کارت شما ارسال شد.', 'success');
            document.getElementById('otpSection').style.display = 'block';
            document.getElementById('withdrawalOtp').focus();
        } else {
            showMessage('خطا در ارسال رمز پویا: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error requesting OTP:', error);
        showMessage('خطا در ارتباط با سرور', 'error');
    }
}

function processUSDPayment() {
    const amount = parseFloat(document.getElementById('amount').value);
    const selectedCardIndex = cardsSelect.value;
    
    if (!amount || amount <= 0) {
        showMessage('Please enter a valid amount!', 'red');
        return;
    }
    
    if (!selectedCardIndex) {
        showMessage('Please select a card!', 'red');
        return;
    }

    // Simulate payment processing
    showMessage('Processing USD payment...', 'blue');
    
    setTimeout(() => {
        updateBalance('USD', amount);
        showMessage(`Successfully charged $${amount.toFixed(2)} to your wallet!`, 'green');
        
        // Redirect to wallet after success
        setTimeout(() => {
            window.location.href = 'wallet.html';
        }, 2000);
    }, 2000);
}

async function processIRRPayment() {
    const amount = parseFloat(document.getElementById('amount').value);
    const dynamicCode = document.getElementById('irrDynamicCode').value;
    
    if (!amount || amount <= 0) {
        showMessage('Please enter a valid amount!', 'red');
        return;
    }
    
    if (!dynamicCode) {
        showMessage('لطفا رمز پویا را وارد کنید!', 'red');
        return;
    }
    
    // تست اتصال اول
    const isConnected = await testConnection();
    if (!isConnected) {
        return;
    }
    
    showMessage('در حال پردازش پرداخت...', 'blue');
    
    try {
        // اگر کارت انتخاب شده، از شماره کارت استفاده کن
        const cardNumber = selectedCard ? selectedCard.number : document.getElementById('irrCardNumber').value;
        
        console.log('📤 Sending IRR payment request:', { amount, cardNumber });
        
        const response = await fetch(`${API_BASE}/payment/process-irr`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                amount: amount,
                otp_code: dynamicCode,
                card_number: cardNumber  // ✅ فقط card_number ارسال می‌شود
            })
        });

        console.log('📥 Response status:', response.status);
        const data = await response.json();
        console.log('📥 Response data:', data);
        
        if (data.success) {
            // به‌روزرسانی موجودی از backend
            await updateBalancesFromBackend();
            showMessage(`✅ پرداخت موفق! مبلغ ${amount.toLocaleString()} ﷼ به کیف پول شما اضافه شد!`, 'green');
            
            setTimeout(() => {
                window.location.href = 'wallet.html';
            }, 2000);
        } else {
            showMessage('❌ خطا در پرداخت: ' + data.error, 'red');
        }
    } catch (error) {
        console.error('❌ Error processing payment:', error);
        showMessage('خطا در ارتباط با سرور. لطفا دوباره تلاش کنید.', 'red');
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
            // به‌روزرسانی localStorage با داده‌های backend
            const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
            currentUser.balances = balances;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
        }
    } catch (error) {
        console.error('Error updating balances from backend:', error);
    }
}

function generateUSDTAddress() {
    // Generate a unique USDT address for the user
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    if (!currentUser.usdtAddress) {
        // Generate a mock USDT address (in real app, this would come from backend)
        const chars = '0123456789abcdef';
        let address = '0x';
        for (let i = 0; i < 40; i++) {
            address += chars[Math.floor(Math.random() * chars.length)];
        }
        currentUser.usdtAddress = address;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
    }
    document.getElementById('usdtAddress').textContent = currentUser.usdtAddress;
}

function simulateUSDTPayment() {
    const amount = parseFloat(document.getElementById('amount').value);
    if (!amount || amount <= 0) {
        showMessage('Please enter a valid amount!', 'red');
        return;
    }
    
    showMessage('Processing USDT payment...', 'blue');
    
    setTimeout(() => {
        updateBalance('USDT', amount);
        showMessage(`Successfully charged ${amount.toFixed(2)} USDT to your wallet!`, 'green');
        
        // Redirect to wallet after success
        setTimeout(() => {
            window.location.href = 'wallet.html';
        }, 2000);
    }, 2000);
}

function updateBalance(currency, amount) {
    const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    if (!currentUser.balances) {
        currentUser.balances = { USD: 0, USDT: 0, IRR: 0 };
    }
    
    currentUser.balances[currency] += amount;
    localStorage.setItem('currentUser', JSON.stringify(currentUser));
}

function showMessage(text, color) {
    const message = document.getElementById('message');
    message.textContent = text;
    message.style.color = color;
    message.style.backgroundColor = color === 'green' ? '#d4edda' : 
                                  color === 'red' ? '#f8d7da' : 
                                  color === 'blue' ? '#d1ecf1' : '#fff3cd';
    message.style.border = `1px solid ${color === 'green' ? '#c3e6cb' : 
                                  color === 'red' ? '#f5c6cb' : 
                                  color === 'blue' ? '#bee5eb' : '#ffeaa7'}`;
    message.style.display = 'block';
}

async function testConnection() {
    try {
        const response = await fetch(`${API_BASE}/test`);
        if (response.ok) {
            console.log('✅ Connection to server successful');
            return true;
        }
    } catch (error) {
        console.error('❌ Connection failed:', error);
        showMessage('سرور در دسترس نیست. لطفا بعدا تلاش کنید.', 'red');
        return false;
    }
}

// Format card number input
document.getElementById('newCardNumber')?.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    let formattedValue = value.match(/.{1,4}/g)?.join(' ');
    if (formattedValue) {
        e.target.value = formattedValue;
    }
});

document.getElementById('cardNumber')?.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    let formattedValue = value.match(/.{1,4}/g)?.join(' ');
    if (formattedValue) {
        e.target.value = formattedValue;
    }
});

document.getElementById('irrCardNumber')?.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    let formattedValue = value.match(/.{1,4}/g)?.join(' ');
    if (formattedValue) {
        e.target.value = formattedValue;
    }
});

// Format expiry date input
document.getElementById('newExpiryDate')?.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 2) {
        e.target.value = value.slice(0, 2) + '/' + value.slice(2, 4);
    }
});

document.getElementById('newExpiryDateIRR')?.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 2) {
        e.target.value = value.slice(0, 2) + '/' + value.slice(2, 4);
    }
});

document.getElementById('irrExpiryDate')?.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 2) {
        e.target.value = value.slice(0, 2) + '/' + value.slice(2, 4);
    }
});

document.getElementById('expiryDate')?.addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 2) {
        e.target.value = value.slice(0, 2) + '/' + value.slice(2, 4);
    }
});

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Charge page loaded, testing connection...');
    testConnection();
});