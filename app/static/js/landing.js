/* ==========================================================================
   Landing Page Interactions
   ========================================================================== */

(function () {
    'use strict';

    // Smooth scrolling for anchor links
    const initSmoothScroll = () => {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');

                // Skip if it's just "#"
                if (href === '#') {
                    e.preventDefault();
                    return;
                }

                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    const navHeight = document.querySelector('.navbar').offsetHeight;
                    const targetPosition = target.offsetTop - navHeight;

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });
    };

    // Navbar scroll effect
    const initNavbarScroll = () => {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;

        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.style.boxShadow = 'var(--shadow-md)';
            } else {
                navbar.style.boxShadow = 'none';
            }
        });
    };

    // Intersection Observer for fade-in animations
    const initScrollAnimations = () => {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Observe feature cards
        document.querySelectorAll('.feature-card').forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            observer.observe(card);
        });

        // Observe process steps
        document.querySelectorAll('.step-content').forEach((step, index) => {
            step.style.opacity = '0';
            step.style.transform = 'translateY(30px)';
            step.style.transition = `opacity 0.6s ease ${index * 0.15}s, transform 0.6s ease ${index * 0.15}s`;
            observer.observe(step);
        });
    };

    // Active nav link based on scroll position
    const initActiveNavLink = () => {
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-link[href^="#"]');

        window.addEventListener('scroll', () => {
            let current = '';
            const scrollPosition = window.scrollY + 100;

            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                const sectionHeight = section.clientHeight;

                if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                    current = section.getAttribute('id');
                }
            });

            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${current}`) {
                    link.classList.add('active');
                }
            });
        });
    };

    // Initialize all functions when DOM is ready
    const init = () => {
        initSmoothScroll();
        initNavbarScroll();
        initScrollAnimations();
        initActiveNavLink();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

function openDemoModal() {
    try {
        console.log('Opening demo modal...');
        const modalEl = document.getElementById('demoInfoModal');
        if (!modalEl) {
            alert('Error: Demo Modal element not found!');
            return;
        }
        if (typeof bootstrap === 'undefined') {
            alert('Error: Bootstrap is not loaded!');
            return;
        }
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } catch (e) {
        alert('Error showing modal: ' + e.message);
        console.error(e);
    }
}

async function loginAsDemo() {
    try {
        // Target the button inside the modal
        const btn = document.querySelector('#demoInfoModal button[onclick="loginAsDemo()"]');
        let originalText = 'Enter Demo Mode';
        if (btn) {
            originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
            btn.disabled = true;
        }

        const response = await fetch('/api/v1/auth/demo-login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            // Use Session Storage for Demo (Temporary Session)
            sessionStorage.setItem('token', data.access_token); // auth.js checks 'token'
            sessionStorage.setItem('access_token', data.access_token);
            sessionStorage.setItem('user', JSON.stringify(data.user));

            // Clear any local storage to avoid conflicts
            localStorage.removeItem('token');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');

            // Clear any local storage to avoid conflicts
            localStorage.removeItem('token');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');

            // Reload to apply Demo Mode UI on Landing Page
            window.location.reload();
        } else {
            alert('Failed to login as demo user: ' + (data.error || 'Unknown error'));
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred during demo login.');
        const btn = document.querySelector('#demoInfoModal button[onclick="loginAsDemo()"]');
        if (btn) {
            btn.innerHTML = 'Enter Demo Mode';
            btn.disabled = false;
        }
    }
}