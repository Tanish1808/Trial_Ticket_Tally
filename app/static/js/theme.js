/* ==========================================================================
   Theme Toggle & Dark Mode Management
   ========================================================================== */

(function() {
    'use strict';
    
    // Get theme from localStorage or default to light
    const getTheme = () => {
        return localStorage.getItem('ticket-tally-theme') || 'light';
    };
    
    // Set theme in localStorage and apply to document
    const setTheme = (theme) => {
        localStorage.setItem('ticket-tally-theme', theme);
        document.documentElement.setAttribute('data-theme', theme);
        updateThemeIcon(theme);
    };
    
    // Update the icon based on current theme
    const updateThemeIcon = (theme) => {
        const toggleBtn = document.getElementById('darkModeToggle');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                if (theme === 'dark') {
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-sun');
                } else {
                    icon.classList.remove('fa-sun');
                    icon.classList.add('fa-moon');
                }
            }
        }
    };
    
    // Toggle theme
    const toggleTheme = () => {
        const currentTheme = getTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    };
    
    // Initialize theme on page load
    const initTheme = () => {
        const savedTheme = getTheme();
        setTheme(savedTheme);
        
        // Add event listener to toggle button
        const toggleBtn = document.getElementById('darkModeToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
    
    // Expose theme functions globally
    window.ThemeManager = {
        getTheme,
        setTheme,
        toggleTheme
    };
})();