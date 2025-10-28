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
    document.body.setAttribute('data-audience-mode', savedMode);
    modeButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === savedMode);
    });

    // Add click handlers
    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            document.body.setAttribute('data-audience-mode', mode);
            localStorage.setItem('audienceMode', mode);

            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            console.log(`Switched to ${mode} mode`);
        });
    });
}
