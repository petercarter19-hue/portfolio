// Slate theme selector and profile-tab helpers.
// This stays browser-only: it never reads environment variables or secrets.

(function () {
    const defaultTheme = 'gray-slate';
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
    const slateThemes = ['light-slate', 'light-blue-slate', 'gray-slate', 'sage-slate'];

    // The two DARK slate themes go further: they use a real slate
    // photograph for the page and give every card/button/strip its own
    // raised stone-slab surface. style.css keys that treatment off
    // body[data-slate-photo="on"].
    const photoSlateThemes = ['gray-slate', 'sage-slate', 'light-slate', 'light-blue-slate'];

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
