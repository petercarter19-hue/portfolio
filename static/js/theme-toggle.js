/* Dark theme toggle (PS-THEME-001, Monochrome & Signal Gold).
   The anti-flash inline script in base.html already applies a stored "dark"
   preference before this file loads; this file only owns the click handler
   and keeping the switch's visual state in sync. */
(function () {
    /* Dark theme pause (owner direction, 2026-08-03). The shells emit
       data-ps-dark-theme on <html> only while PEERSLATE_DARK_THEME_ENABLED is
       true. Without it this file does nothing, so a theme switch left in or
       re-added to any template cannot put the site into dark. Restoring the
       theme is a single flag flip; delete nothing here. */
    if (!document.documentElement.hasAttribute('data-ps-dark-theme')) return;

    var STORAGE_KEY = 'ps-theme';
    var toggles = Array.prototype.slice.call(document.querySelectorAll('[data-theme-toggle-proxy]'));
    var headerToggle = document.getElementById('theme-toggle');
    if (headerToggle) toggles.unshift(headerToggle);
    if (!toggles.length) return;

    function isDark() {
        return document.body.getAttribute('data-theme') === 'dark';
    }

    function syncSwitch() {
        toggles.forEach(function (toggle) {
            toggle.setAttribute('aria-checked', isDark() ? 'true' : 'false');
        });
    }

    toggles.forEach(function (toggle) {
        toggle.addEventListener('click', function () {
            var next = isDark() ? 'modern-blue' : 'dark';
            document.body.setAttribute('data-theme', next);
            try {
                window.localStorage.setItem(STORAGE_KEY, next === 'dark' ? 'dark' : 'light');
            } catch (e) { /* localStorage unavailable — theme still applies for this page view */ }
            syncSwitch();
        });
    });

    syncSwitch();
})();
