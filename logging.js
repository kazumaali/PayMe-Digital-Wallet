const API_BASE = 'http://192.168.1.102:5000/api';

function getAuthToken() {
    return localStorage.getItem('authToken');
}

const username = document.getElementById('signupUsername');
const emailAdd = document.getElementById("emailAdd");
const CrPass = document.getElementById("CrPass");
const CrPass2 = document.getElementById("CrPass2");
const verification = document.getElementById("verification");
const hidden1 = document.getElementsByClassName("hidden1")[0];
const hidden2 = document.getElementsByClassName("hidden2")[0];
const hidden3 = document.getElementsByClassName("hidden3")[0];
const hidden4 = document.getElementsByClassName("hidden4")[0];
const hidden5 = document.getElementsByClassName("hidden5")[0];
const signupBtn = document.getElementById("signupBtn"); // Fixed typo: "ducument" to "document"

let emailVerificationCode = null;
let pendingUserData = null;

// Initialize EmailJS
function initEmailJS() {
    emailjs.init("d3oDpvpHsE4_0H-dq");
}

// Call initialization when page loads
document.addEventListener('DOMContentLoaded', function() {
    initEmailJS();
});

// Generate random verification code
function generateVerificationCode() {
    return Math.floor(100000 + Math.random() * 900000).toString();
}

// Send verification email
async function sendVerificationEmail(email, username) {
    try {
        const verificationCode = generateVerificationCode();
        
        const templateParams = {
            to_email: email,
            to_name: username,
            verification_code: verificationCode,
            website_name: "PayMe Digital Wallet",
            from_name: "Kazuma Ali"
        };

        const response = await emailjs.send(
            "service_t07qw3s",
            "template_z6biz19",
            templateParams
        );

        console.log('Verification email sent successfully:', response);
        return verificationCode;
    } catch (error) {
        console.error('Failed to send verification email:', error);
        throw new Error('Failed to send verification email. Please try again.');
    }
}

// Enhanced signup function with email verification
async function signUp() {
    const usernameValue = username.value.trim();
    const emailValue = emailAdd.value.trim().toLowerCase();
    const passwordValue = CrPass.value.trim();
    const confirmPasswordValue = CrPass2.value.trim();

    // Hide all error messages first
    hideAllErrors();

    // Validation
    if (!usernameValue || !emailValue || !passwordValue || !confirmPasswordValue) {
        showMessage('Please fill in all fields!', 'red');
        return;
    }

    if (usernameValue.length < 3) {
        showMessage('Username must be at least 3 characters long!', 'red');
        return;
    }

    if (passwordValue.length < 6) {
        showMessage('Password must be at least 6 characters long!', 'red');
        return;
    }

    if (!isValidEmail(emailValue)) {
        hidden1.style.display = 'block';
        return;
    }

    if (!isValidPassword(passwordValue)) {
        hidden2.style.display = 'block';
        return;
    }

    if (passwordValue !== confirmPasswordValue) {
        hidden3.style.display = 'block';
        return;
    }

    // Check if email already exists
    if (isEmailTaken(emailValue)) {
        hidden5.style.display = 'block';
        return;
    }

    // Check if username already exists
    if (isUsernameTaken(usernameValue)) {
        showMessage('This username is already taken!', 'red');
        return;
    }

    try {
        showMessage('Sending verification code...', 'blue');

        // Send verification email
        const verificationCode = await sendVerificationEmail(emailValue, usernameValue);

        // Store verification data
        emailVerificationCode = verificationCode;
        pendingUserData = {
            username: usernameValue,
            email: emailValue,
            password: hashPassword(passwordValue),
            profilePic: `https://api.dicebear.com/7.x/avataaars/svg?seed=${usernameValue}`,
            verified: false,
            createdAt: new Date().toISOString()
        };

        // Show verification section
        showVerificationSection();
        showMessage('Verification code sent to your email!', 'green');

    } catch (error) {
        showMessage(error.message, 'red');
    }
}

// Show verification input section
function showVerificationSection() {
    // Hide the signup form
    document.querySelector('.signup-form').style.display = 'none';
    document.querySelector('.signup-button').style.display = 'none';
    
    // Show verification input
    hidden4.style.display = 'block';
    document.getElementById('verification').focus();
}

// Verify email with code
function verifyEmail() {
    const enteredCode = document.getElementById('verification').value.trim();

    if (!enteredCode) {
        showMessage('Please enter the verification code!', 'red');
        return;
    }

    if (enteredCode === emailVerificationCode) {
        // Mark user as verified and save
        pendingUserData.verified = true;
        saveUser(pendingUserData);
        
        showMessage('Email verified successfully! Welcome!', 'green');
        
        localStorage.setItem('authToken', 'your-jwt-token-from-backend');
// The backend should return a JWT token upon successful verification

        // Redirect to wallet.html after successful verification
        setTimeout(() => {
            window.location.href = 'wallet.html';
        }, 2000);
        
        // Clear verification data
        emailVerificationCode = null;
        pendingUserData = null;

    } else {
        showMessage('Invalid verification code! Please try again.', 'red');
    }
}

// Utility functions
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidPassword(password) {
    // At least one lowercase, one uppercase, one number, one special character
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/;
    return passwordRegex.test(password) && password.length >= 6;
}

function hashPassword(password) {
    // Simple hash for demo purposes
    return btoa(password).split('').reverse().join('');
}

function showMessage(text, color) {
    // Create or update message element
    let message = document.getElementById('message');
    if (!message) {
        message = document.createElement('p');
        message.id = 'message';
        document.querySelector('section').appendChild(message);
    }
    message.textContent = text;
    message.style.color = color;
    message.style.display = 'block';
}

function hideAllErrors() {
    hidden1.style.display = 'none';
    hidden2.style.display = 'none';
    hidden3.style.display = 'none';
    hidden5.style.display = 'none';
}

// Enhanced user storage system
function saveUser(userData) {
    // Get existing users or initialize empty array
    const users = JSON.parse(localStorage.getItem('websiteUsers')) || [];
    
    // Add new user
    users.push(userData);
    
    // Save to localStorage
    localStorage.setItem('websiteUsers', JSON.stringify(users));
    
    // Set as current user
    localStorage.setItem('currentUser', JSON.stringify(userData));
    localStorage.setItem('userEmail', userData.email);
    localStorage.setItem('isLoggedIn', 'true');
}

// Check if email is already taken
function isEmailTaken(email) {
    const users = JSON.parse(localStorage.getItem('websiteUsers')) || [];
    return users.some(user => user.email === email && user.verified);
}

// Check if username is already taken
function isUsernameTaken(username) {
    const users = JSON.parse(localStorage.getItem('websiteUsers')) || [];
    return users.some(user => user.username === username && user.verified);
}

// Add event listener for Enter key in verification field
document.addEventListener('DOMContentLoaded', function() {
    const verificationField = document.getElementById('verification');
    if (verificationField) {
        verificationField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                verifyEmail();
            }
        });
    }
});