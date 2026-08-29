/* ==========================================================================
   Theme Toggle & Dark Mode Management
   ========================================================================== */

(function () {
    'use strict';

    // Get theme from localStorage or default to light
    const getTheme = () => {
        try {
            return localStorage.getItem('ticket-tally-theme') || 'light';
        } catch (e) {
            return 'light';
        }
    };

    // Apply saved theme immediately on script evaluation to eliminate render flash
    const applyImmediateTheme = () => {
        const theme = getTheme();
        document.documentElement.setAttribute('data-theme', theme);
    };
    applyImmediateTheme();

    // Set theme in localStorage and apply to document
    const setTheme = (theme) => {
        try {
            localStorage.setItem('ticket-tally-theme', theme);
        } catch (e) {}
        document.documentElement.setAttribute('data-theme', theme);
        updateThemeIcon(theme);
    };

    // Update the icon based on current theme for all toggle buttons on page
    const updateThemeIcon = (theme) => {
        const toggleButtons = document.querySelectorAll('#darkModeToggle, .theme-toggle');
        toggleButtons.forEach((toggleBtn) => {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                if (theme === 'dark') {
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-sun');
                    toggleBtn.setAttribute('title', 'Switch to Light Mode');
                    toggleBtn.setAttribute('aria-label', 'Switch to Light Mode');
                } else {
                    icon.classList.remove('fa-sun');
                    icon.classList.add('fa-moon');
                    toggleBtn.setAttribute('title', 'Switch to Dark Mode');
                    toggleBtn.setAttribute('aria-label', 'Switch to Dark Mode');
                }
            }
        });
    };

    // Toggle theme
    const toggleTheme = () => {
        const currentTheme = getTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    };

    // Initialize theme and attach listeners on DOM load
    const initTheme = () => {
        const savedTheme = getTheme();
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcon(savedTheme);

        // Add event listener to all toggle buttons on the page
        const toggleButtons = document.querySelectorAll('#darkModeToggle, .theme-toggle');
        toggleButtons.forEach((toggleBtn) => {
            toggleBtn.removeEventListener('click', toggleTheme);
            toggleBtn.addEventListener('click', toggleTheme);
        });
    };

    // Exit Demo Mode
    const exitDemoMode = () => {
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        localStorage.removeItem('access_token');

        sessionStorage.removeItem('user');
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('access_token');

        window.location.href = '/';
    };
    window.exitDemoMode = exitDemoMode;

    // Check for Demo User and Show Banner
    const checkDemoMode = () => {
        const userStr = sessionStorage.getItem('user') || localStorage.getItem('user');
        if (!userStr) return;

        try {
            const user = JSON.parse(userStr);
            if (user.email === 'demo@tickettally.com') {
                // 0. Apply Demo Mode Styling
                document.body.classList.add('demo-mode');

                // Inject Demo CSS (Removed Watermark, Added Sidebar Logout Hide)
                const style = document.createElement('style');
                style.innerHTML = `
                    .demo-mode .navbar {
                        border-bottom: 2px solid #ff9800 !important;
                    }
                    /* Hide Sidebar Logout Button in Demo Mode */
                    .demo-mode .sidebar-footer .logout-btn {
                        display: none !important;
                    }
                `;
                document.head.appendChild(style);

                // Dashboard Specific Logic: Add "Exit Dashboard" Button
                if (window.location.pathname.includes('/dashboard') || document.querySelector('.header-actions')) {
                    const headerActions = document.querySelector('.header-actions');
                    if (headerActions) {
                        // Check if button already exists to prevent duplicates
                        if (!document.getElementById('demoExitBtn')) {
                            const exitBtn = document.createElement('button');
                            exitBtn.id = 'demoExitBtn';
                            exitBtn.className = 'btn btn-outline-danger me-2';
                            exitBtn.setAttribute('title', 'Exit Demo Dashboard');
                            exitBtn.setAttribute('aria-label', 'Exit Demo Dashboard');
                            exitBtn.innerHTML = '<i class="fas fa-sign-out-alt me-md-2"></i><span class="d-none d-md-inline">Exit Dashboard</span>';
                            exitBtn.onclick = () => logout(); // calls global logout() from auth.js which handles demo exit

                            // Insert at the beginning of actions
                            headerActions.insertBefore(exitBtn, headerActions.firstChild);
                        }
                    }
                }

                // Modify Logout Button to be Exit Demo (Global)
                const logoutBtn = document.querySelector('a[href="/logout"], button[onclick="logout()"]');
                if (logoutBtn) {
                    logoutBtn.innerHTML = '<i class="fas fa-sign-out-alt me-2"></i>Exit Demo';
                    logoutBtn.removeAttribute('href');
                    logoutBtn.onclick = (e) => {
                        e.preventDefault();
                        exitDemoMode();
                    };
                    logoutBtn.classList.remove('text-danger');
                    logoutBtn.classList.add('text-warning');
                }

                // Landing Page Specific Logic
                if (window.location.pathname === '/') {
                    // 1. Change "See Demo" to "Preview Dashboard"
                    const seeDemoBtn = document.querySelector('button[onclick="openDemoModal()"], button[onclick="loginAsDemo()"]');
                    if (seeDemoBtn) {
                        seeDemoBtn.innerHTML = '<i class="fas fa-tachometer-alt me-2"></i>Preview Dashboard';
                        seeDemoBtn.onclick = (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            window.location.href = '/dashboard/employee';
                        };
                        seeDemoBtn.classList.remove('btn-outline-custom');
                        seeDemoBtn.classList.add('btn-primary-custom');
                    }

                    // 2. Restrict other actions (Login, Signup, etc.)
                    const restrictedSelectors = [
                        'a[href="/login"]',
                        'a[href="/signup"]',
                        'a[href^="/dashboard"]' // catch other dashboard links if any
                    ];

                    restrictedSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            // Skip if it's the preview button we just modified
                            if (el === seeDemoBtn) return;

                            el.onclick = (e) => {
                                e.preventDefault();
                                const modal = new bootstrap.Modal(document.getElementById('restrictedActionModal'));
                                modal.show();
                            };
                        });
                    });
                }

                // 1. Show Banner
                if (!document.getElementById('demo-banner')) {
                    const banner = document.createElement('div');
                    banner.id = 'demo-banner';
                    banner.style.cssText = `
                        position: fixed;
                        bottom: 0;
                        left: 0;
                        width: 100%;
                        background-color: #ff9800;
                        color: white;
                        text-align: center;
                        padding: 10px 20px;
                        z-index: 9999;
                        font-weight: bold;
                        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    `;
                    banner.innerHTML = `
                        <div style="flex-grow: 1; text-align: center;">
                            <i class="fas fa-eye me-2"></i> You are viewing a Read-Only Demo. Actions are disabled.
                        </div>
                        <button onclick="exitDemoMode()" class="btn btn-sm btn-light text-warning fw-bold" style="white-space: nowrap;">
                            <i class="fas fa-sign-out-alt me-1"></i> Exit Demo
                        </button>
                    `;
                    document.body.appendChild(banner);

                    // Adjust body padding to prevent banner from covering content
                    document.body.style.paddingBottom = '60px';
                }
            }
        } catch (e) {
            console.error('Error checking demo mode', e);
        }
    };

    // Check Email Availability Status on Deployment
    const checkEmailStatus = () => {
        fetch('/api/v1/auth/config')
            .then(res => res.json())
            .then(data => {
                if (data && data.email_delivery_enabled === false) {
                    displayEmailDisabledNotice();
                }
            })
            .catch(() => {});
    };

    const displayEmailDisabledNotice = () => {
        if (document.getElementById('emailDeliveryStatusNotice')) return;

        const headerActions = document.querySelector('.header-actions, .navbar-nav, .d-flex.align-items-center.gap-3');
        if (headerActions) {
            const badge = document.createElement('div');
            badge.id = 'emailDeliveryStatusNotice';
            badge.className = 'badge d-inline-flex align-items-center gap-1 px-2 py-1';
            badge.style.cssText = 'background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 9999px; font-weight: 600; font-size: 0.75rem; cursor: pointer;';
            badge.setAttribute('title', 'Email notifications are unavailable on this deployment. In-app notifications remain active.');
            badge.setAttribute('aria-label', 'Email notifications unavailable. In-app notifications active.');
            badge.innerHTML = '<i class="fas fa-bell me-1"></i><span>In-App Notifications Only</span>';
            badge.onclick = () => {
                alert('Email notifications are unavailable on this cloud deployment. Ticket Tally provides in-app notifications for all ticket updates and assignments.');
            };
            headerActions.prepend(badge);
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initTheme();
            checkDemoMode();
            checkEmailStatus();
        });
    } else {
        initTheme();
        checkDemoMode();
        checkEmailStatus();
    }

    // Expose theme functions globally
    window.ThemeManager = {
        getTheme,
        setTheme,
        toggleTheme
    };

    // Make exitDemoMode global for onclick handlers
    window.exitDemoMode = exitDemoMode;
    window.checkDemoMode = checkDemoMode;
    window.checkEmailStatus = checkEmailStatus;
})();