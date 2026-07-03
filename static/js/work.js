document.addEventListener('DOMContentLoaded', function () {
    const tabs = Array.from(document.querySelectorAll('[data-work-project]'));
    const panels = Array.from(document.querySelectorAll('[data-work-panel]'));

    function selectProject(projectId, shouldFocus) {
        tabs.forEach(function (tab) {
            const isActive = tab.dataset.workProject === projectId;
            tab.classList.toggle('is-active', isActive);
            tab.setAttribute('aria-pressed', String(isActive));
        });

        panels.forEach(function (panel) {
            const isActive = panel.dataset.workPanel === projectId;
            panel.classList.toggle('is-active', isActive);

            if (isActive && shouldFocus) {
                panel.focus({ preventScroll: true });
                panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            selectProject(tab.dataset.workProject, true);
        });
    });

    document.addEventListener('click', function (event) {
        const askButton = event.target.closest('[data-ask-resume]');
        if (!askButton) return;

        const prompt = askButton.dataset.ask || askButton.textContent.trim();
        if (window.askPeteAI) {
            window.askPeteAI(prompt);
        }
    });
});
