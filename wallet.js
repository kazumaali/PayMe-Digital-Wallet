        // Load user balances when page loads
document.addEventListener('DOMContentLoaded', function() {
            updateBalances();
        });

        function updateBalances() {
            const currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
            
            // Get balances or initialize if they don't exist
            const balances = currentUser.balances || {
                USD: 0,
                USDT: 0,
                IRR: 0
            };
            
            // Update display
            document.getElementById('p1').textContent = `USD: $${balances.USD.toFixed(2)}`;
            document.getElementById('p2').textContent = `USDT: ${balances.USDT.toFixed(2)}`;
            document.getElementById('p3').textContent = `IRR: ${balances.IRR.toLocaleString()} ﷼`;
            
            // Update current user data
            currentUser.balances = balances;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
        }