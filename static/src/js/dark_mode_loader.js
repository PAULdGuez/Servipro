/** @odoo-module **/

// Apply dark mode class on page load if preference is saved
const isDark = localStorage.getItem('pest_dark_mode') === 'true';
if (isDark) {
    // Wait for DOM to be ready, then apply to action manager
    const observer = new MutationObserver((mutations, obs) => {
        const actionManager = document.querySelector('.o_action_manager');
        if (actionManager) {
            actionManager.classList.add('pest_dark_mode');
            obs.disconnect();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Fallback: try immediately
    const am = document.querySelector('.o_action_manager');
    if (am) am.classList.add('pest_dark_mode');
}
