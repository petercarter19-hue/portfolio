(function () {
    const defaultTheme = 'command-gold';
    const storageKey = 'peerslateTheme';
    const themeButtons = document.querySelectorAll('[data-theme-option]');

    function applyTheme(themeName) {
        document.body.dataset.theme = themeName;
        localStorage.setItem(storageKey, themeName);

        themeButtons.forEach(function (button) {
            const isActive = button.dataset.themeOption === themeName;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    }

    const savedTheme = localStorage.getItem(storageKey) || defaultTheme;
    applyTheme(savedTheme);

    themeButtons.forEach(function (button) {
        button.addEventListener('click', function (event) {
            event.stopPropagation();
            applyTheme(button.dataset.themeOption);
        });
    });
})();
