const API_BASE = 'http://localhost:5000/api';

function getAuthToken() {
    return localStorage.getItem('authToken');
}

// Exchange rates (for demonstration)
        const exchangeRates = {
            USD: { USDT: 1.00, IRR: 42000 },
            USDT: { USD: 1.00, IRR: 42000 },
            IRR: { USD: 0.0000238, USDT: 0.0000238 }
        };
        
        const exchangeFee = 0.005; // 0.5%
        
        function updateBalances() {
            const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
            const balances = currentUser.balances || { USD: 0, USDT: 0, IRR: 0 };
            
            document.getElementById('balanceUSD').textContent = `USD: $${balances.USD.toFixed(2)}`;
            document.getElementById('balanceUSDT').textContent = `USDT: ${balances.USDT.toFixed(2)}`;
            document.getElementById('balanceIRR').textContent = `IRR: ${balances.IRR.toLocaleString()} ﷼`;
        }
        
        function calculateExchange() {
            const fromAmount = parseFloat(document.getElementById('fromAmount').value) || 0;
            const fromCurrency = document.getElementById('fromCurrency').value;
            const toCurrency = document.getElementById('toCurrency').value;
            
            if (fromAmount <= 0) {
                document.getElementById('toAmount').value = '';
                return;
            }
            
            // Get exchange rate
            const rate = exchangeRates[fromCurrency][toCurrency];
            
            // Calculate amount after fee
            const amountAfterFee = fromAmount * (1 - exchangeFee);
            const toAmount = amountAfterFee * rate;
            
            document.getElementById('toAmount').value = toAmount.toFixed(2);
            
            // Update rate display
            document.getElementById('rateDisplay').textContent = 
                `1 ${fromCurrency} = ${rate.toLocaleString()} ${toCurrency}`;
        }
        
        function executeExchange() {
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
                    rate: exchangeRates[fromCurrency][toCurrency],
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
        
        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            updateBalances();
            
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