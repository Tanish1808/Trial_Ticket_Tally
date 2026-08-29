/* ==========================================================================
   Authentication Utilities
   ========================================================================== */

// Get current user from storage (Session first, then Local)
function getCurrentUser() {
    const sessionUser = sessionStorage.getItem('user');
    if (sessionUser) return JSON.parse(sessionUser);

    const localUser = localStorage.getItem('user');
    return localUser ? JSON.parse(localUser) : null;
}

// Get auth token (Session first, then Local)
function getAuthToken() {
    return sessionStorage.getItem('token') || localStorage.getItem('token');
}

// Check if user is logged in
function isAuthenticated() {
    return getCurrentUser() !== null && getAuthToken() !== null;
}

// Logout user
function logout() {
    const user = getCurrentUser();
    const isDemo = user && user.email === 'demo@tickettally.com';

    if (isDemo) {
        // Redirect to Landing Page but KEEP session to maintain Demo Mode
        window.location.href = '/';
        return;
    }

    // Normal Logout
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');

    sessionStorage.removeItem('user');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('access_token');

    window.location.href = '/login';
}

// Protect page (require authentication)
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// Check user role
function hasRole(role) {
    const user = getCurrentUser();
    return user && user.role === role;
}

// Redirect to appropriate dashboard based on role
function redirectToDashboard() {
    const user = getCurrentUser();
    if (!user) {
        window.location.href = '/login';
        return;
    }

    // Role check logic matching backend UserRole enum
    switch (user.role) {
        case 'admin':
            window.location.href = '/dashboard/admin';
            break;
        case 'it_staff':
        case 'it-staff':
        case 'it_support':
            window.location.href = '/dashboard/it-staff';
            break;
        case 'employee':
        default:
            window.location.href = '/dashboard/employee';
            break;
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Format time
function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Generate random ticket ID
function generateTicketId() {
    const prefix = 'TKT';
    const randomNum = Math.floor(10000 + Math.random() * 90000);
    return `${prefix}-${randomNum}`;
}

// Calculate time ago
function timeAgo(dateString) {
    if (!dateString) return 'Unknown';
    // Append 'Z' to treat as UTC if no timezone offset is present
    if (!dateString.endsWith('Z') && !dateString.includes('+')) dateString += 'Z';

    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) return interval + " year" + (interval === 1 ? "" : "s") + " ago";
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) return interval + " month" + (interval === 1 ? "" : "s") + " ago";
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) return interval + " day" + (interval === 1 ? "" : "s") + " ago";
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) return interval + " hr" + (interval === 1 ? "" : "s") + " ago";
    interval = Math.floor(seconds / 60);
    if (interval >= 1) return interval + " min" + (interval === 1 ? "" : "s") + " ago";
    return Math.floor(seconds) + " seconds ago";
}

// Handle Forgot Password Submission
document.addEventListener('DOMContentLoaded', function () {
    console.log('Auth.js loaded');
    const forgotForm = document.getElementById('forgotPasswordForm');
    if (forgotForm) {
        console.log('Forgot form found, attaching listener');
        forgotForm.addEventListener('submit', async function (e) {
            console.log('Forgot form submitted');
            e.preventDefault();
            const btn = forgotForm.querySelector('button[type="submit"]');
            const email = document.getElementById('forgotEmail').value;

            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending...';

            try {
                const response = await fetch('/api/v1/auth/forgot-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });

                let data = {};
                try {
                    data = await response.json();
                } catch (_) {
                    data = {};
                }

                if (response.ok) {
                    showToast(data.message || 'If an account exists with this email, a password reset link has been sent.', 'success');
                    forgotForm.reset();
                } else if (response.status === 429) {
                    const rateLimitMsg = data.error || 'Too many password reset attempts. Please wait a minute before trying again.';
                    showToast(rateLimitMsg, 'warning');
                } else if (response.status === 400) {
                    showToast(data.error || 'Please provide a valid email address.', 'error');
                } else if (response.status >= 500) {
                    showToast('Server error encountered. Please try again later.', 'error');
                } else {
                    showToast(data.error || 'Failed to send reset link. Please check your email and try again.', 'error');
                }
            } catch (e) {
                console.error("Forgot password error", e);
                showToast('Unable to connect to server. Please check your network and try again.', 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    }

    // Handle Reset Password Submission
    const resetForm = document.getElementById('resetPasswordForm');
    if (resetForm) {
        resetForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const btn = resetForm.querySelector('button[type="submit"]');
            const token = document.getElementById('resetToken').value;
            const password = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;

            if (password !== confirmPassword) {
                showToast('Passwords do not match', 'error');
                return;
            }

            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Resetting...';

            try {
                const response = await fetch('/api/v1/auth/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token, new_password: password })
                });

                let data = {};
                try {
                    data = await response.json();
                } catch (_) {
                    data = {};
                }

                if (response.ok) {
                    showToast(data.message || 'Password reset successfully.', 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else if (response.status === 429) {
                    const rateLimitMsg = data.error || 'Too many password reset attempts. Please wait a minute before trying again.';
                    showToast(rateLimitMsg, 'warning');
                } else if (response.status === 400) {
                    showToast(data.error || 'Invalid or expired reset token.', 'error');
                } else if (response.status >= 500) {
                    showToast('Server error encountered. Please try again later.', 'error');
                } else {
                    showToast(data.error || 'Failed to reset password. Please try again.', 'error');
                }
            } catch (e) {
                console.error("Reset password error", e);
                showToast('Unable to connect to server. Please check your network and try again.', 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    }
});

// Toast Helper (Duplicate of profile.js simple toast, or use Bootstrap toast if available on page)
// Login/Forgot pages use Bootstrap toast in HTML, so we need to trigger it.
function showToast(message, type = 'info') {
    const toastEl = document.getElementById('liveToast');
    const toastBody = document.getElementById('toastMessage');

    if (toastEl && toastBody) {
        toastBody.textContent = message;
        let bgClass = 'text-bg-primary';
        if (type === 'error' || type === 'danger') {
            bgClass = 'text-bg-danger';
        } else if (type === 'warning') {
            bgClass = 'text-bg-warning';
        } else if (type === 'success') {
            bgClass = 'text-bg-success';
        }
        toastEl.className = `toast align-items-center ${bgClass} border-0`;

        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    } else {
        alert(message);
    }
}