// Powers the "Theme Preview" buttons inside the site menu dropdown
// (see the .theme-preview block in base.html). Lets a visitor try a
// different color scheme and has the site remember their choice.

(function () {
    const defaultTheme = 'blueprint-light';
    // The key used to save the choice in the browser's localStorage, so the
    // theme is still applied the next time this visitor comes back.
    const storageKey = 'peerslateTheme';
    const themeButtons = document.querySelectorAll('[data-theme-option]');

    // Switches the color scheme by changing a data-theme attribute on
    // <body> — style.css has CSS variable overrides for each theme name
    // (e.g. data-theme="modern-blue") that this attribute switches between.
    function applyTheme(themeName) {
        document.body.dataset.theme = themeName;
        localStorage.setItem(storageKey, themeName);

        // Highlight whichever theme button matches the current choice.
        themeButtons.forEach(function (button) {
            const isActive = button.dataset.themeOption === themeName;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    }

    // Restore the visitor's last choice on page load (falls back to the
    // site's default theme for a first-time visitor).
    // Guard: only trust the saved name if a matching theme button still
    // exists — a visitor might have a removed theme (e.g. the old
    // "slate-light") saved in localStorage, which would otherwise leave
    // the site with no matching CSS variable block.
    const savedTheme = localStorage.getItem(storageKey);
    const savedThemeExists = Array.prototype.some.call(
        themeButtons,
        function (button) { return button.dataset.themeOption === savedTheme; }
    );
    applyTheme(savedThemeExists ? savedTheme : defaultTheme);

    themeButtons.forEach(function (button) {
        button.addEventListener('click', function (event) {
            // Stops the click from bubbling up and immediately closing the
            // site-menu dropdown (see the click-outside-closes-it listener
            // for #site-menu-dropdown in base.html).
            event.stopPropagation();
            applyTheme(button.dataset.themeOption);
        });
    });
})();
