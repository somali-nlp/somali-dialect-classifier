/**
 * Animations Module
 * Count-up animations and visual effects
 */

/**
 * Animate count-up effect on elements with data-count attribute
 * Uses requestAnimationFrame for smooth 60fps animations
 */
export function animateCountUp() {
    const elements = document.querySelectorAll('[data-count]');
    elements.forEach(el => {
        const target = parseFloat(el.dataset.count);
        const suffix = el.dataset.suffix || '';
        const duration = 2000;
        const start = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            const current = Math.floor(target * eased);

            el.textContent = current.toLocaleString() + suffix;

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.textContent = target.toLocaleString() + suffix;
            }
        }

        requestAnimationFrame(update);
    });

    // Animate source cards
    const sourceValues = document.querySelectorAll('.source-metric-value[data-value]');
    sourceValues.forEach(el => {
        const target = parseInt(el.dataset.value);
        const duration = 2000;
        const start = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(target * eased);

            el.textContent = current.toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.textContent = target.toLocaleString();
            }
        }

        requestAnimationFrame(update);
    });
}
