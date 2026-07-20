/* Dark theme toggle (PS-THEME-001, Monochrome & Signal Gold).
   The anti-flash inline script in base.html already applies a stored "dark"
   preference before this file loads; this file only owns the click handler
   and keeping the switch's visual state in sync. */
(function () {
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
