/**
 * Audience Mode Module
 * Toggles between Story and Analyst viewing modes
 */

/**
 * Initialize audience mode toggle functionality
 * Manages localStorage persistence and mode switching
 */
export function initAudienceMode() {
    const modeButtons = document.querySelectorAll('.mode-toggle-btn');
    const savedMode = localStorage.getItem('audienceMode') || 'story';

    // Set initial mode
    applyMode(savedMode);
    modeButtons.forEach(btn => {
        const isActive = btn.dataset.mode === savedMode;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-pressed', isActive.toString());
    });

    // Add click handlers
    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            applyMode(mode);
            localStorage.setItem('audienceMode', mode);

            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            modeButtons.forEach(b => b.setAttribute('aria-pressed', (b === btn).toString()));

            console.log(`Switched to ${mode} mode`);
        });
    });

    function applyMode(mode) {
        document.body.setAttribute('data-audience-mode', mode);
        document.querySelectorAll('[data-show-in]').forEach(element => {
            const attribute = element.getAttribute('data-show-in') || '';
            const targets = attribute.split(/[\s,]+/).filter(Boolean);
            const isVisible = targets.includes(mode);

            element.setAttribute('aria-hidden', (!isVisible).toString());
        });
    }
}
