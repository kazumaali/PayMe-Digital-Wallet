const API_BASE = 'http://localhost:5000/api';

function getAuthToken() {
    return localStorage.getItem('authToken');
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

function updateCardsDropdown() {
    cardsSelect.innerHTML = '<option value="">-- Please choose --</option>';
    userCards.forEach((card, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${card.type} - ****${card.last4} (${card.currency})`;
        cardsSelect.appendChild(option);
    });
}

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
    document.getElementById('newCardNumber').value = '';
    document.getElementById('newExpiryDate').value = '';
    document.getElementById('newCvv').value = '';
    document.getElementById('newCardHolder').value = '';
    document.getElementById('newExpiryDateIRR').value = '';
    document.getElementById('newCvv2').value = '';
}

function hideAddCardForm() {
    addCardForm.style.display = 'none';
}

function addNewCard() {
    const currency = currencySelect.value;
    const cardNumber = document.getElementById('newCardNumber').value.replace(/\s/g, '');

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
            type: 'Visa/MasterCard',
            last4: cardNumber.slice(-4),
            number: cardNumber,
            expiry: expiryDate,
            cvv: cvv,
            holder: cardHolder,
            currency: currency
        };
    } else if (currency === 'IRR') {
        const expiryDate = document.getElementById('newExpiryDateIRR').value;
        const cvv2 = document.getElementById('newCvv2').value;

        if (!expiryDate || !cvv2) {
            showMessage('Please fill all card details!', 'red');
            return;
        }

        newCard = {
            type: 'Iranian Bank Card',
            last4: cardNumber.slice(-4),
            number: cardNumber,
            expiry: expiryDate,
            cvv2: cvv2,
            currency: currency
        };
    }
    
    userCards.push(newCard);
    localStorage.setItem('userCards', JSON.stringify(userCards));
    updateCardsDropdown();
    hideAddCardForm();
    showMessage('New card added successfully!', 'green');
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

function requestDynamicCode() {
    // Simulate requesting dynamic code from bank
    showMessage('درخواست رمز پویا ارسال شد. لطفا منتظر پیامک باشید...', 'blue');
    
    // Simulate receiving dynamic code after 3 seconds
    setTimeout(() => {
        // Generate a random 6-digit code
        const dynamicCode = Math.floor(100000 + Math.random() * 900000).toString();
        document.getElementById('irrDynamicCode').value = dynamicCode;
        showMessage(`رمز پویا دریافت شد: ${dynamicCode}`, 'green');
    }, 3000);
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

function processIRRPayment() {
    const amount = parseFloat(document.getElementById('amount').value);
    const dynamicCode = document.getElementById('irrDynamicCode').value;
    
    if (!amount || amount <= 0) {
        showMessage('Please enter a valid amount!', 'red');
        return;
    }
    
    if (!dynamicCode) {
        showMessage('Please enter رمز پویا!', 'red');
        return;
    }
    
    // For saved cards, we already have the card details
    // For new cards, validate the card fields
    if (!selectedCard) {
        const cvv2 = document.getElementById('irrCvv2').value;
        const expiryDate = document.getElementById('irrExpiryDate').value;
        const cardNumber = document.getElementById('irrCardNumber').value;
        
        if (!cvv2 || !expiryDate || !cardNumber) {
            showMessage('Please fill all card details!', 'red');
            return;
        }
    }

    // Simulate payment processing
    showMessage('Processing IRR payment...', 'blue');
    
    setTimeout(() => {
        updateBalance('IRR', amount);
        showMessage(`Successfully charged ${amount.toLocaleString()} ﷼ to your wallet!`, 'green');
        
        // Redirect to wallet after success
        setTimeout(() => {
            window.location.href = 'wallet.html';
        }, 2000);
    }, 2000);
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