// Slate theme selector and profile-tab helpers.
// This stays browser-only: it never reads environment variables or secrets.

(function () {
    // Four themes for now (more later):
    //   'slate-light' — the clean Light look (the default). It renders via the
    //                   body.slate-light class, which base.html already adds to
    //                   every page except the homepage (so there's no flash).
    //   'paper-slate' — "White Slate": the Light palette, but every surface
    //                   (page + cards + buttons) cut from the white-stone
    //                   photo through the slate pipeline. surfaceSlate=on.
    //   'stone-slate' — "Dark Slate Stone": the dark palette (a gray-slate
    //                   twin), with every surface ALSO cut from the dark stone.
    //                   surfaceSlate=on. This is the dark twin White Slate matches.
    //   'gray-slate'  — "Dark Slate": dark stone PAGE, but flat (non-stone)
    //                   cards/buttons. surfaceSlate=off.
    // The homepage keeps its own look (body.peerslate-home-page) and never
    // takes the slate-light class.
    const defaultTheme = 'slate-light';
    const storageKey = 'peerslateTheme';
    const themeButtons = document.querySelectorAll('[data-theme-option]');

    // Some browsers throw on ANY localStorage access (Chrome with site data
    // blocked, some private modes). Without these guards a single throw here
    // would kill this whole file — and the theme picker with it — site-wide.
    function readSavedTheme() {
        try {
            return localStorage.getItem(storageKey);
        } catch (error) {
            return null;
        }
    }

    function saveTheme(themeName) {
        try {
            localStorage.setItem(storageKey, themeName);
        } catch (error) {
            // Storage unavailable: the theme still applies for this visit,
            // it just won't persist to the next one.
        }
    }

    function applyTheme(themeName) {
        const isHomepage = document.body.classList.contains('peerslate-home-page');

        // The cinematic /experience page is one fixed, self-contained design
        // (everything is scoped under .cinematic-home-page). The theme picker
        // must NEVER repaint it — every theme should look exactly like Light,
        // including the frosted header — so we render it in the Light body
        // state no matter which theme is chosen. We still save the choice
        // below so the rest of the site honors the visitor's real theme.
        const isCinematic = document.body.classList.contains('cinematic-home-page');

        // All three stone themes run the photo pipeline: gray-slate (Dark
        // Slate), stone-slate (Dark Slate Stone) and paper-slate (White Slate).
        // Everything else is the flat Light look. The cinematic page opts out
        // entirely (always Light).
        const useStone = !isCinematic && (
            themeName === 'gray-slate'
            || themeName === 'stone-slate'
            || themeName === 'paper-slate');

        // "Surface slate": White Slate + Dark Slate Stone cut every card,
        // button and chip from the SAME fixed stone as the page, so nothing is
        // a flat panel. Plain Dark Slate keeps its flat cards. Never on the
        // homepage or the cinematic page (both have their own composition).
        const surfaceSlate = !isHomepage && !isCinematic
            && (themeName === 'stone-slate' || themeName === 'paper-slate');

        // The homepage has its own dark look gated on data-theme="gray-slate";
        // render Dark Slate Stone as gray-slate there so home styling applies
        // (the active-button highlight below still keys off the real themeName).
        // The cinematic page is pinned to the Light data-theme.
        const renderedTheme = isCinematic
            ? 'slate-light'
            : ((isHomepage && themeName === 'stone-slate') ? 'gray-slate' : themeName);
        document.body.dataset.theme = renderedTheme;

        // Light = the slate-light class (never on the homepage/cinematic page).
        // Stone themes = the stone photo pipeline (data-slate / data-slate-photo).
        if (!useStone && !isHomepage && !isCinematic) {
            document.body.classList.add('slate-light');
        } else {
            document.body.classList.remove('slate-light');
        }
        document.body.dataset.slate = useStone ? 'on' : 'off';
        document.body.dataset.slatePhoto = useStone ? 'on' : 'off';
        document.body.dataset.surfaceSlate = surfaceSlate ? 'on' : 'off';

        saveTheme(themeName);

        themeButtons.forEach(function (button) {
            const isActive = button.dataset.themeOption === themeName;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    }

    const savedTheme = readSavedTheme();
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
})();
