/**
 * Accessibility Module
 * Smooth scrolling, keyboard navigation, and scroll spy
 */

/**
 * Initialize smooth scrolling for anchor links
 * Handles offset for sticky navigation
 */
export function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');

            e.preventDefault();
            const targetTab = this.dataset.tabTarget;
            if (targetTab) {
                const tabButton = document.querySelector(`.tab-button[data-tab="${targetTab}"]`);
                if (tabButton) tabButton.click();
            }

            if (this.hasAttribute('data-dashboard-link')) {
                const overviewButton = document.querySelector('.tab-button[data-tab="overview"]');
                if (overviewButton) overviewButton.click();
            }

            const modeTarget = this.dataset.modeTarget;
            if (modeTarget) {
                const modeButton = document.querySelector(`.mode-toggle-btn[data-mode="${modeTarget}"]`);
                if (modeButton && !modeButton.classList.contains('active')) {
                    modeButton.click();
                }
            }

            if (href === '#') {
                return;
            }

            const target = document.querySelector(href);
            if (target) {
                // Get navbar height for offset
                const navHeight = document.querySelector('.global-nav')?.offsetHeight || 72;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;

                // Smooth scroll with custom easing
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });

                // Add visual feedback to the arrow icon if it's the dashboard button
                if (this.id === 'view-dashboard-btn') {
                    const icon = this.querySelector('.hero-cta-icon');
                    if (icon) {
                        icon.style.animation = 'none';
                        setTimeout(() => {
                            icon.style.animation = 'bounceArrow 0.6s ease-in-out';
                        }, 10);
                    }
                }
            }
        });
    });

    // Special handling for the View Dashboard button
    const viewDashboardBtn = document.getElementById('view-dashboard-btn');
    if (viewDashboardBtn) {
        // Add pulse animation to the arrow icon on page load
        setTimeout(() => {
            const icon = viewDashboardBtn.querySelector('.hero-cta-icon');
            if (icon) {
                icon.style.animation = 'pulseArrow 2s ease-in-out infinite';
            }
        }, 1000);
    }
}

// Add CSS animation for pulsing arrow (injected via JS)
const style = document.createElement('style');
style.textContent = `
    @keyframes pulseArrow {
        0%, 100% { transform: translateY(0); opacity: 1; }
        50% { transform: translateY(4px); opacity: 0.7; }
    }
`;
document.head.appendChild(style);

/**
 * Initialize keyboard navigation for interactive elements
 */
export function initKeyboardNav() {
    const stages = document.querySelectorAll('.lifecycle-stage');
    stages.forEach(stage => {
        stage.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                // Could open modal or show details
                console.log('Stage clicked:', stage.querySelector('.lifecycle-stage-name').textContent);
            }
        });
    });
}

/**
 * Initialize scroll spy for active navigation highlighting
 */
export function initScrollSpy() {
    const sections = document.querySelectorAll('section[id], main[id], nav[id]');
    const navLinks = document.querySelectorAll('.nav-link');

    // Height of sticky header for offset
    const navHeight = document.querySelector('.global-nav')?.offsetHeight || 0;

    function updateActiveLink() {
        let currentSection = '';

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const scrollPosition = window.scrollY + navHeight + 100; // Offset for better UX

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                currentSection = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href');
            if (href === `#${currentSection}`) {
                link.classList.add('active');
            }
        });
    }

    // Update on scroll with throttling for performance
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                updateActiveLink();
                ticking = false;
            });
            ticking = true;
        }
    });

    // Initial update
    updateActiveLink();
}

/**
 * Initialize mobile navigation menu toggle
 */
export function initMobileMenu() {
    const toggleButton = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (!toggleButton || !navLinks) {
        return;
    }

    const closeMenu = () => {
        navLinks.classList.remove('is-open');
        toggleButton.setAttribute('aria-expanded', 'false');
        toggleButton.setAttribute('aria-label', 'Open mobile menu');
    };

    toggleButton.addEventListener('click', () => {
        const isOpen = navLinks.classList.toggle('is-open');
        toggleButton.setAttribute('aria-expanded', String(isOpen));
        toggleButton.setAttribute('aria-label', isOpen ? 'Close mobile menu' : 'Open mobile menu');

        if (isOpen) {
            toggleButton.focus();
        }
    });

    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            if (navLinks.classList.contains('is-open')) {
                closeMenu();
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && navLinks.classList.contains('is-open')) {
            closeMenu();
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && navLinks.classList.contains('is-open')) {
            closeMenu();
        }
    });
}
