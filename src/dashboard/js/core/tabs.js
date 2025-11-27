/**
 * Tab Navigation Module
 * Handles tab switching and URL hash management
 */

/**
 * Initialize tab navigation system
 * Sets up click handlers and hash-based routing
 */
export function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;

            // Update buttons
            tabButtons.forEach(btn => {
                btn.classList.remove('active');
                btn.setAttribute('aria-selected', 'false');
            });
            button.classList.add('active');
            button.setAttribute('aria-selected', 'true');

            // Update content
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${targetTab}-panel`).classList.add('active');

            // Update URL hash
            window.location.hash = targetTab;
        });
    });

    // Handle initial hash
    const hash = window.location.hash.slice(1);
    if (hash && ['overview', 'sources', 'quality', 'pipeline', 'reports'].includes(hash)) {
        const button = document.querySelector(`[data-tab="${hash}"]`);
        if (button) button.click();
    }
}
