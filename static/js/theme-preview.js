// Slate theme selector and profile-tab helpers.
// This stays browser-only: it never reads environment variables or secrets.

(function () {
    // Two themes for now (more later):
    //   'slate-light' — the clean Light look (the default). It renders via the
    //                   body.slate-light class, which base.html already adds to
    //                   every page except the homepage (so there's no flash).
    //   'gray-slate'  — one Dark Slate stone theme (data-slate-photo pipeline).
    // The homepage keeps its own look (body.peerslate-home-page) and never
    // takes the slate-light class.
    const defaultTheme = 'slate-light';
    const storageKey = 'peerslateTheme';
    const themeButtons = document.querySelectorAll('[data-theme-option]');
    const profileTabLinks = document.querySelectorAll('.profile-tab[href*="#"]');
    const allProfileTabs = document.querySelectorAll('.profile-tab');

    function applyTheme(themeName) {
        document.body.dataset.theme = themeName;

        const isHomepage = document.body.classList.contains('peerslate-home-page');
        const useStone = themeName === 'gray-slate';

        // Light = the slate-light class (never on the homepage). Dark Slate =
        // the stone photo pipeline (data-slate / data-slate-photo).
        if (!useStone && !isHomepage) {
            document.body.classList.add('slate-light');
        } else {
            document.body.classList.remove('slate-light');
        }
        document.body.dataset.slate = useStone ? 'on' : 'off';
        document.body.dataset.slatePhoto = useStone ? 'on' : 'off';

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
