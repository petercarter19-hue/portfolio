// Slate theme selector and profile-tab helpers.
// This stays browser-only: it never reads environment variables or secrets.

(function () {
    const defaultTheme = 'modern-blue';
    const storageKey = 'peerslateTheme';
    const themeButtons = document.querySelectorAll('[data-theme-option]');
    const profileTabLinks = document.querySelectorAll('.profile-tab[href*="#"]');
    const allProfileTabs = document.querySelectorAll('.profile-tab');

    // The four NEW slate themes get the platform slate treatment (stone
    // texture, restyled hero/cards/buttons). The four ORIGINAL themes
    // (command-gold, modern-blue, blueprint-light, secure-green) must look
    // exactly as they did before, so all that new styling is gated in
    // style.css behind body[data-slate="on"] — which we only set here for
    // the slate themes.
    // modern-blue (the mockup theme) is slate-family WITHOUT the stone
    // photo — platform layout + paper grain, never the rock slabs.
    // paper-slate ("White Slate") is its stone-photo twin.
    const slateThemes = ['light-slate', 'light-blue-slate', 'gray-slate', 'sage-slate', 'paper-slate', 'modern-blue'];

    // The two DARK slate themes go further: they use a real slate
    // photograph for the page and give every card/button/strip its own
    // raised stone-slab surface. style.css keys that treatment off
    // body[data-slate-photo="on"].
    // modern-blue rides the photo pipeline too, but with a near-opaque
    // white wash: flat white mockup cards over the faintest texture.
    const photoSlateThemes = ['gray-slate', 'sage-slate', 'light-slate', 'light-blue-slate', 'paper-slate', 'modern-blue'];

    function applyTheme(themeName) {
        document.body.dataset.theme = themeName;
        document.body.dataset.slate = slateThemes.indexOf(themeName) !== -1 ? 'on' : 'off';
        document.body.dataset.slatePhoto = photoSlateThemes.indexOf(themeName) !== -1 ? 'on' : 'off';
        localStorage.setItem(storageKey, themeName);

        themeButtons.forEach(function (button) {
            const isActive = button.dataset.themeOption === themeName;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    }

    const savedTheme = localStorage.getItem(storageKey);
    const savedThemeExists = Array.prototype.some.call(
        themeButtons,
        function (button) { return button.dataset.themeOption === savedTheme; }
    );

    applyTheme(savedThemeExists ? savedTheme : defaultTheme);

    themeButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            applyTheme(button.dataset.themeOption);
        });
    });

    // ---- Theme dropdown (mockup header) ----
    // The swatches live inside a panel behind a "Theme" button now.
    const themeMenuBtn = document.getElementById('theme-menu-btn');
    const themeMenuPanel = document.getElementById('theme-menu-panel');

    if (themeMenuBtn && themeMenuPanel) {
        themeMenuBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            const open = themeMenuPanel.hidden;
            themeMenuPanel.hidden = !open;
            themeMenuBtn.setAttribute('aria-expanded', String(open));
        });

        document.addEventListener('click', function (event) {
            if (!themeMenuPanel.hidden && !themeMenuPanel.contains(event.target)) {
                themeMenuPanel.hidden = true;
                themeMenuBtn.setAttribute('aria-expanded', 'false');
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !themeMenuPanel.hidden) {
                themeMenuPanel.hidden = true;
                themeMenuBtn.setAttribute('aria-expanded', 'false');
                themeMenuBtn.focus();
            }
        });
    }

    profileTabLinks.forEach(function (link) {
        link.addEventListener('click', function (event) {
            const targetId = link.hash ? link.hash.slice(1) : '';
            const target = targetId ? document.getElementById(targetId) : null;

            if (!target) {
                return;
            }

            event.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    function updateProfileTabFromHash() {
        if (!window.location.hash) {
            return;
        }

        const matchingTab = Array.prototype.find.call(
            allProfileTabs,
            function (tab) { return tab.hash === window.location.hash; }
        );

        if (!matchingTab) {
            return;
        }

        allProfileTabs.forEach(function (tab) {
            tab.removeAttribute('aria-current');
        });
        matchingTab.setAttribute('aria-current', 'page');
    }

    updateProfileTabFromHash();
    window.addEventListener('hashchange', updateProfileTabFromHash);
})();
