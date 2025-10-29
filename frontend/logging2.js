function login() {
            const email = document.getElementById("emailInput").value.trim().toLowerCase();
            const password = document.getElementById("passwordInput").value;
            const message = document.getElementById("loginMessage");

            // Clear previous messages
            message.style.display = 'none';
            message.className = '';

            if (!email || !password) {
                showLoginMessage('Please fill in both email and password!', 'error');
                return;
            }

            // Special case for admin email
            if (email === "kazumasatou20021423@gmail.com") {
                let userData = JSON.parse(localStorage.getItem('currentUser'));
                
                if (!userData) {
                    userData = {
                        username: "Kazumaali",
                        email: email,
                        profilePic: 'kazuma.png',
                        verified: true
                    };
                    localStorage.setItem('currentUser', JSON.stringify(userData));
                }
                
                localStorage.setItem('userEmail', email);
                localStorage.setItem('isLoggedIn', 'true');
                
                showLoginMessage('Admin login successful! Redirecting...', 'success');
                
                // Redirect to wallet.html
                setTimeout(() => {
                    window.location.href = 'wallet.html';
                }, 1500);
                return;
            }

            // Get users from localStorage
            const users = JSON.parse(localStorage.getItem('websiteUsers')) || [];
            const user = users.find(u => u.email === email);

            if (!user) {
                showLoginMessage('No account found with this email!', 'error');
                return;
            }

            // Check if user is verified
            if (!user.verified) {
                showLoginMessage('Please verify your email before logging in!', 'error');
                return;
            }

            // Password verification
            if (user.password !== hashPassword(password)) {
                showLoginMessage('Invalid password!', 'error');
                return;
            }

            // Successful login
            localStorage.setItem('currentUser', JSON.stringify(user));
            localStorage.setItem('userEmail', user.email);
            localStorage.setItem('isLoggedIn', 'true');
            
            showLoginMessage('Login successful! Redirecting...', 'success');
            
            // Redirect to wallet.html
            setTimeout(() => {
                window.location.href = 'wallet.html';
            }, 1500);
        }

        // Password hash function (must match the one in logging.js)
        function hashPassword(password) {
            // Simple hash for demo purposes - same as in logging.js
            return btoa(password).split('').reverse().join('');
        }

        // Show login message
        function showLoginMessage(text, type) {
            const message = document.getElementById('loginMessage');
            message.textContent = text;
            message.style.display = 'block';
            
            switch(type) {
                case 'success':
                    message.className = 'message-success';
                    break;
                case 'error':
                    message.className = 'message-error';
                    break;
                case 'info':
                    message.className = 'message-info';
                    break;
            }
        }

        // Allow login on Enter key press
        document.addEventListener('DOMContentLoaded', function() {
            const emailInput = document.getElementById('emailInput');
            const passwordInput = document.getElementById('passwordInput');
            
            emailInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    login();
                }
            });
            
            passwordInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    login();
                }
            });
        });

        // Check if user is already logged in (optional - shows message but doesn't redirect)
    document.addEventListener('DOMContentLoaded', function() {
        const isLoggedIn = localStorage.getItem('isLoggedIn');
        const currentUser = JSON.parse(localStorage.getItem('currentUser'));
    
        if (isLoggedIn === 'true' && currentUser) {
            showLoginMessage('You are already logged in! You can proceed to wallet or log out.', 'info');
        }
    });