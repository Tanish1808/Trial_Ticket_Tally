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

    // Universal Live User Modal for Email Availability Feedback
    window.showEmailUnavailableModal = function (options = {}) {
        const {
            actionTitle = 'Email Notification Notice',
            actionMessage = 'Your action was completed successfully.',
            noticeBody = 'Email notification could not be delivered on this deployment.',
            subText = 'Your updates remain securely saved in Ticket Tally and can be viewed in your in-app Notifications center.',
            buttonText = 'Continue',
            onClose = null
        } = options;

        let modalEl = document.getElementById('emailUnavailableModal');
        if (!modalEl) {
            modalEl = document.createElement('div');
            modalEl.className = 'modal fade';
            modalEl.id = 'emailUnavailableModal';
            modalEl.tabIndex = -1;
            modalEl.setAttribute('aria-labelledby', 'emailUnavailableModalLabel');
            modalEl.setAttribute('aria-hidden', 'true');
            modalEl.innerHTML = `
                <div class="modal-dialog modal-dialog-centered" style="max-width: 480px; margin: 1.5rem auto;">
                    <div class="modal-content border-0 shadow-lg" style="border-radius: 1rem; background: var(--surface, #ffffff); color: var(--text-primary, #111827); border: 1px solid var(--border, #e5e7eb) !important;">
                        <div class="modal-header border-bottom-0 pb-0 pt-4 px-4 d-flex justify-content-between align-items-center">
                            <div class="d-flex align-items-center gap-2">
                                <div class="d-inline-flex align-items-center justify-content-center flex-shrink-0" style="width: 40px; height: 40px; border-radius: 50%; background: rgba(245, 158, 11, 0.15); color: #d97706;">
                                    <i class="fas fa-envelope-open-text fa-lg"></i>
                                </div>
                                <h5 class="modal-title fw-bold mb-0" id="emailUnavailableModalLabel" style="font-size: 1.1rem; color: var(--text-primary, #111827);">Email Notification Notice</h5>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body py-3 px-4">
                            <div class="alert alert-success d-flex align-items-center gap-2 mb-3 py-2 px-3" style="border-radius: 0.5rem; font-size: 0.95rem; background: rgba(16, 185, 129, 0.12); color: #047857; border: 1px solid rgba(16, 185, 129, 0.25);">
                                <i class="fas fa-check-circle fs-5 flex-shrink-0"></i>
                                <span id="emailUnavailableSuccessText" class="fw-semibold"></span>
                            </div>
                            <p class="mb-2" id="emailUnavailableNoticeBody" style="font-size: 0.95rem; line-height: 1.5; color: var(--text-primary, #111827);"></p>
                            <p class="mb-0 text-muted" id="emailUnavailableSubText" style="font-size: 0.85rem; line-height: 1.4;"></p>
                        </div>
                        <div class="modal-footer border-top-0 pt-1 pb-4 px-4">
                            <button type="button" class="btn btn-primary-custom w-100 py-2 fw-semibold" data-bs-dismiss="modal" id="emailUnavailableDismissBtn" style="border-radius: 0.5rem;">
                                ${buttonText}
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modalEl);
        }

        const titleEl = modalEl.querySelector('#emailUnavailableModalLabel');
        const successEl = modalEl.querySelector('#emailUnavailableSuccessText');
        const noticeEl = modalEl.querySelector('#emailUnavailableNoticeBody');
        const subEl = modalEl.querySelector('#emailUnavailableSubText');
        const btnEl = modalEl.querySelector('#emailUnavailableDismissBtn');

        if (titleEl) titleEl.textContent = actionTitle;
        if (successEl) successEl.textContent = actionMessage;
        if (noticeEl) noticeEl.textContent = noticeBody;
        if (subEl) subEl.textContent = subText;
        if (btnEl) btnEl.textContent = buttonText;

        if (onClose) {
            const handleHidden = function () {
                modalEl.removeEventListener('hidden.bs.modal', handleHidden);
                onClose();
            };
            modalEl.addEventListener('hidden.bs.modal', handleHidden);
        }

        if (window.bootstrap && window.bootstrap.Modal) {
            const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
            modalInstance.show();
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initTheme();
            checkDemoMode();
        });
    } else {
        initTheme();
        checkDemoMode();
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
})();