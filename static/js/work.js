// Projects page behavior (templates/work.html).
// Handles the four project tabs (only one panel shows at a time) and the
// "Ask Pete AI" buttons that hand a question off to the shared chatbot.

document.addEventListener('DOMContentLoaded', function () {
    const tabs = Array.from(document.querySelectorAll('[data-work-project]'));
    const panels = Array.from(document.querySelectorAll('[data-work-panel]'));

    // Shows the panel whose data-work-panel matches projectId and marks its
    // tab active; every other tab/panel is switched off. shouldFocus moves
    // the screen (and screen-reader focus) to the panel when it's opened
    // by a click, but not on the very first page load.
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

    // "Ask Pete AI" buttons on this page carry a data-ask attribute with a
    // ready-made question. window.askPeteAI (defined in chatbot.js) opens
    // the floating chat panel and sends that question immediately.
    document.addEventListener('click', function (event) {
        const askButton = event.target.closest('[data-ask-resume]');
        if (!askButton) return;

        const prompt = askButton.dataset.ask || askButton.textContent.trim();
        if (window.askPeteAI) {
            window.askPeteAI(prompt);
        }
    });
});
