(function () {
    'use strict';

    const root = document.querySelector('[data-triptych]');
    if (!root) return;

    const panels = Array.from(root.querySelectorAll('[data-triptych-panel]'));
    const selectors = Array.from(root.querySelectorAll('[data-triptych-selector]'));
    const status = root.querySelector('[data-triptych-status]');
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    const state = {
        committed: null,
        hovered: null,
        focused: null
    };

    function activePanel() {
        return state.focused || state.hovered || state.committed;
    }

    function panelTitle(panelName) {
        const selector = selectors.find(function (candidate) {
            return candidate.dataset.triptychSelector === panelName;
        });
        return selector ? selector.textContent.trim() : panelName;
    }

    function render() {
        const active = activePanel();
        root.dataset.activePanel = active || '';
        root.dataset.phase = active ? 'focused' : 'arrival';

        panels.forEach(function (panel) {
            panel.classList.toggle(
                'is-active',
                panel.dataset.triptychPanel === active
            );
        });

        selectors.forEach(function (selector) {
            selector.setAttribute(
                'aria-pressed',
                String(selector.dataset.triptychSelector === state.committed)
            );
        });

        if (status) {
            status.textContent = active
                ? panelTitle(active) + ' is in focus. Its Enter link opens the full experience.'
                : 'Arrival. All three dimensions are visible.';
        }
    }

    function clearTransientState() {
        state.hovered = null;
        state.focused = null;
    }

    panels.forEach(function (panel) {
        const name = panel.dataset.triptychPanel;

        panel.addEventListener('pointerenter', function () {
            if (!finePointer.matches) return;
            state.hovered = name;
            render();
        });

        panel.addEventListener('pointerleave', function () {
            if (state.hovered !== name) return;
            state.hovered = null;
            render();
        });

        panel.addEventListener('focusin', function () {
            state.focused = name;
            render();
        });

        panel.addEventListener('focusout', function () {
            window.requestAnimationFrame(function () {
                if (!panel.contains(document.activeElement) && state.focused === name) {
                    state.focused = null;
                    render();
                }
            });
        });
    });

    selectors.forEach(function (selector, index) {
        const name = selector.dataset.triptychSelector;

        selector.addEventListener('click', function () {
            state.committed = state.committed === name ? null : name;
            render();
        });

        selector.addEventListener('keydown', function (event) {
            let targetIndex = null;

            if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
                targetIndex = (index + 1) % selectors.length;
            } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
                targetIndex = (index - 1 + selectors.length) % selectors.length;
            } else if (event.key === 'Home') {
                targetIndex = 0;
            } else if (event.key === 'End') {
                targetIndex = selectors.length - 1;
            }

            if (targetIndex === null) return;
            event.preventDefault();
            selectors[targetIndex].focus();
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape' || !activePanel()) return;
        clearTransientState();
        state.committed = null;
        render();
    });

    let pointerFrame = null;
    root.addEventListener('pointermove', function (event) {
        if (!finePointer.matches || reducedMotion.matches) return;
        if (pointerFrame !== null) return;

        pointerFrame = window.requestAnimationFrame(function () {
            const bounds = root.getBoundingClientRect();
            const x = ((event.clientX - bounds.left) / bounds.width) * 100;
            const y = ((event.clientY - bounds.top) / bounds.height) * 100;
            root.style.setProperty('--pointer-x', Math.max(0, Math.min(100, x)) + '%');
            root.style.setProperty('--pointer-y', Math.max(0, Math.min(100, y)) + '%');
            pointerFrame = null;
        });
    });

    function handleMotionPreference() {
        if (!reducedMotion.matches) return;
        root.style.removeProperty('--pointer-x');
        root.style.removeProperty('--pointer-y');
    }

    if (typeof reducedMotion.addEventListener === 'function') {
        reducedMotion.addEventListener('change', handleMotionPreference);
    } else if (typeof reducedMotion.addListener === 'function') {
        reducedMotion.addListener(handleMotionPreference);
    }

    root.classList.add('is-enhanced');
    render();
})();
