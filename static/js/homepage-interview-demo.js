/* PS-HOME-INTERVIEW-DEMO-001 — homepage Interview Studio illustrative
   walkthrough. A "Walk me through it" button pops out a modal (same guided
   pattern as the Voice hero's capture overlay) and steps through four fixed,
   server-rendered states. This file only opens/closes the modal and toggles
   which step is visible — no network request, no storage, no media API, and
   no form is ever created here. See
   docs/initiatives/PS-HOME-INTERVIEW-DEMO-001/01_BOUNDARY_AND_STATE_CONTRACT.md
   §3 for the binding prohibition list this file must keep satisfying. */
(function () {
    'use strict';

    var root = document.querySelector('[data-home-interview-demo]');
    if (!root || root.dataset.intReady) return;
    root.dataset.intReady = 'true';

    function one(selector) { return root.querySelector(selector); }
    function all(selector) { return Array.prototype.slice.call(root.querySelectorAll(selector)); }
    function text(element, value) { if (element) element.textContent = value == null ? '' : String(value); }

    var STATE_NAMES = { 1: 'Question', 2: 'Sample answer', 3: 'Coaching review', 4: 'Improved retry' };
    var NEXT_LABELS = { 1: 'Show illustrative answer', 2: 'Submit sample answer', 3: 'Show improved retry' };

    var openButton = one('[data-int-open]');
    var overlay = one('[data-int-overlay]');
    var modal = one('[data-int-modal]');
    var live = one('[data-int-live]');
    var count = one('[data-int-count]');
    var steps = all('[data-int-step]');
    var panels = all('[data-int-state]');
    var methodButtons = all('[data-int-method]');
    var methodPanels = all('[data-int-method-panel]');
    var backButton = one('[data-int-back]');
    var nextButton = one('[data-int-next]');
    var nextLabel = one('[data-int-next-label]');
    var finishLink = one('[data-int-finish]');

    var current = 1;
    var isOpen = false;
    var invoker = null;
    var previousBodyOverflow = '';

    // The homepage's main.main-content sets `isolation: isolate`, which traps
    // a fixed overlay below the sticky global header (z-index 1200). Portal the
    // overlay to <body> — inside a `home-v3` wrapper so the design-system
    // classes (.hv-chip, .hv-btn) and --hv-* tokens still resolve — so it
    // escapes that stacking context and covers the full viewport, matching the
    // Voice hero overlay. Element references were captured above before the
    // move, so they remain valid.
    if (overlay && overlay.parentNode) {
        var portal = document.createElement('div');
        portal.className = 'home-v3 hv-int-portal';
        document.body.appendChild(portal);
        portal.appendChild(overlay);
    }

    function panelFor(n) {
        return panels.filter(function (p) { return Number(p.getAttribute('data-int-state')) === n; })[0];
    }

    function focusables() {
        return Array.prototype.filter.call(
            modal.querySelectorAll('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])'),
            function (el) { return !el.disabled && el.offsetParent !== null; }
        );
    }

    function go(n, moveFocus) {
        n = Math.min(4, Math.max(1, Number(n) || 1));

        var nextPanel = panelFor(n);
        if (!nextPanel) return;

        panels.forEach(function (panel) {
            panel.hidden = Number(panel.getAttribute('data-int-state')) !== n;
        });

        steps.forEach(function (stepButton) {
            var stepNumber = Number(stepButton.getAttribute('data-int-step'));
            if (stepNumber === n) stepButton.setAttribute('aria-current', 'step');
            else stepButton.removeAttribute('aria-current');
            stepButton.setAttribute('data-done', stepNumber < n ? 'true' : 'false');
            if (stepNumber < n) stepButton.setAttribute('aria-label', STATE_NAMES[stepNumber] + ', completed');
            else stepButton.removeAttribute('aria-label');
        });

        text(count, 'Step ' + n + ' of 4');
        text(live, 'Step ' + n + ' of 4: ' + STATE_NAMES[n]);

        if (backButton) backButton.hidden = n === 1;
        if (nextButton) nextButton.hidden = n === 4;
        if (finishLink) finishLink.hidden = n !== 4;
        if (nextLabel && NEXT_LABELS[n]) text(nextLabel, NEXT_LABELS[n]);

        current = n;

        if (moveFocus) {
            var heading = nextPanel.querySelector('.hv-int-state__title');
            if (heading) heading.focus();
        }
    }

    function setMethod(method) {
        methodButtons.forEach(function (button) {
            button.setAttribute('aria-pressed', button.getAttribute('data-int-method') === method ? 'true' : 'false');
        });
        methodPanels.forEach(function (panel) {
            panel.hidden = panel.getAttribute('data-int-method-panel') !== method;
        });
    }

    function openModal() {
        if (isOpen) return;
        // The only opener is the trigger button, so restore focus there on
        // close regardless of how it was activated (mouse, keyboard, touch).
        invoker = openButton || document.activeElement;
        overlay.hidden = false;
        // Force reflow before adding the class so the fade-in transition runs.
        void overlay.offsetWidth;
        overlay.classList.add('is-open');
        previousBodyOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        isOpen = true;
        go(1, false);
        setMethod('voice');
        // Focus the first step's heading so the step is announced.
        var heading = panelFor(1).querySelector('.hv-int-state__title');
        if (heading) heading.focus();
    }

    function closeModal() {
        if (!isOpen) return;
        overlay.classList.remove('is-open');
        overlay.hidden = true;
        document.body.style.overflow = previousBodyOverflow;
        isOpen = false;
        if (invoker && document.contains(invoker)) invoker.focus();
    }

    // The opener lives in the poster (still under the scene root).
    if (openButton) openButton.addEventListener('click', openModal);

    // Everything else lives inside the (now portaled) overlay, so delegate
    // modal controls and the backdrop click there.
    overlay.addEventListener('click', function (event) {
        if (event.target.closest('[data-int-close]')) { closeModal(); return; }
        if (event.target.closest('[data-int-back]')) { go(current - 1, true); return; }
        if (event.target.closest('[data-int-next]')) { go(current + 1, true); return; }
        var stepButton = event.target.closest('[data-int-step]');
        if (stepButton) { go(Number(stepButton.getAttribute('data-int-step')), true); return; }
        var methodButton = event.target.closest('[data-int-method]');
        if (methodButton) { setMethod(methodButton.getAttribute('data-int-method')); return; }
        // The finish link (data-int-finish) is a normal anchor — never intercepted.
        if (event.target === overlay) { closeModal(); return; }  // backdrop
    });

    // Escape closes; Tab is trapped inside the modal.
    overlay.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') { event.preventDefault(); closeModal(); return; }
        if (event.key !== 'Tab') return;
        var items = focusables();
        if (!items.length) return;
        var first = items[0], last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });

    // Reveal the interactive controls (and hide the no-JS link) only once this
    // script has wired everything up.
    root.classList.add('hv-int--js');
}());
