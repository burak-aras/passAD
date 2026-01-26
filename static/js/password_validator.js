/**
 * Password Validator - Client-side validation and strength indicator
 */

document.addEventListener('DOMContentLoaded', function() {
    const newPasswordInput = document.getElementById('new_password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const submitBtn = document.getElementById('submitBtn');
    const passwordStrength = document.getElementById('passwordStrength');
    const strengthBar = document.getElementById('strengthBar');
    const strengthText = document.getElementById('strengthText');
    
    // Password requirements
    const requirements = {
        length: { regex: /.{8,}/, element: document.getElementById('req-length') },
        uppercase: { regex: /[A-Z]/, element: document.getElementById('req-uppercase') },
        lowercase: { regex: /[a-z]/, element: document.getElementById('req-lowercase') },
        digit: { regex: /[0-9]/, element: document.getElementById('req-digit') }
    };
    
    // Validate password on input
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            const password = this.value;
            
            if (password.length > 0) {
                passwordStrength.style.display = 'block';
                validatePassword(password);
                calculateStrength(password);
            } else {
                passwordStrength.style.display = 'none';
                resetRequirements();
            }
            
            // Check if passwords match
            checkPasswordMatch();
        });
    }
    
    // Check password match on confirm input
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    }
    
    /**
     * Validate password against requirements
     */
    function validatePassword(password) {
        let allValid = true;
        
        for (const [key, requirement] of Object.entries(requirements)) {
            const isValid = requirement.regex.test(password);
            
            if (isValid) {
                requirement.element.classList.add('valid');
            } else {
                requirement.element.classList.remove('valid');
                allValid = false;
            }
        }
        
        return allValid;
    }
    
    /**
     * Calculate password strength
     */
    function calculateStrength(password) {
        let strength = 0;
        
        // Length check
        if (password.length >= 8) strength += 25;
        if (password.length >= 12) strength += 15;
        
        // Character variety
        if (/[a-z]/.test(password)) strength += 15;
        if (/[A-Z]/.test(password)) strength += 15;
        if (/[0-9]/.test(password)) strength += 15;
        if (/[^a-zA-Z0-9]/.test(password)) strength += 15;
        
        // Update strength bar
        strengthBar.style.width = strength + '%';
        
        // Set color and text based on strength
        if (strength < 40) {
            strengthBar.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
            strengthText.textContent = 'Zayıf şifre';
            strengthText.style.color = '#ef4444';
        } else if (strength < 70) {
            strengthBar.style.background = 'linear-gradient(90deg, #f59e0b, #d97706)';
            strengthText.textContent = 'Orta güçte şifre';
            strengthText.style.color = '#f59e0b';
        } else {
            strengthBar.style.background = 'linear-gradient(90deg, #10b981, #059669)';
            strengthText.textContent = 'Güçlü şifre';
            strengthText.style.color = '#10b981';
        }
    }
    
    /**
     * Check if passwords match
     */
    function checkPasswordMatch() {
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        const confirmFeedback = document.getElementById('confirmFeedback');
        
        if (confirmPassword.length > 0) {
            if (newPassword === confirmPassword) {
                confirmPasswordInput.classList.remove('is-invalid');
                confirmPasswordInput.classList.add('is-valid');
                confirmFeedback.style.display = 'none';
            } else {
                confirmPasswordInput.classList.remove('is-valid');
                confirmPasswordInput.classList.add('is-invalid');
                confirmFeedback.style.display = 'block';
            }
        } else {
            confirmPasswordInput.classList.remove('is-valid', 'is-invalid');
            confirmFeedback.style.display = 'none';
        }
    }
    
    /**
     * Reset all requirements
     */
    function resetRequirements() {
        for (const requirement of Object.values(requirements)) {
            requirement.element.classList.remove('valid');
        }
    }
    
    /**
     * Form submission validation
     */
    const form = document.getElementById('passwordForm');
    if (form) {
        form.addEventListener('submit', function(event) {
            const newPassword = newPasswordInput.value;
            const confirmPassword = confirmPasswordInput.value;
            
            // Validate password requirements
            if (!validatePassword(newPassword)) {
                event.preventDefault();
                alert('Lütfen şifre gereksinimlerini karşılayın!');
                return false;
            }
            
            // Check if passwords match
            if (newPassword !== confirmPassword) {
                event.preventDefault();
                alert('Şifreler eşleşmiyor!');
                confirmPasswordInput.focus();
                return false;
            }
            
            // Add loading state to button
            submitBtn.classList.add('loading');
            submitBtn.disabled = true;
            
            return true;
        });
    }
});
