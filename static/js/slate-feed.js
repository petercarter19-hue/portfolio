// Slate Feed interactions — browser-only, no secrets.
// Three small behaviors:
//   1. The "All Activity" dropdown filters feed cards by their type.
//   2. Celebrate / React buttons toggle one appreciation per visitor
//      and bump the visible peer count (click again to take it back).
//   3. "Not now" quietly dismisses the Suggested Next Step panel.

(function () {
    // ---- 1. Activity type filter ----
    var filter = document.getElementById('sf-filter');
    var items = document.querySelectorAll('[data-feed-type]');

    if (filter) {
        filter.addEventListener('change', function () {
            var selected = filter.value;

            items.forEach(function (item) {
                item.hidden = selected !== 'all' && item.dataset.feedType !== selected;
            });
        });
    }

    // ---- 2. Celebrate / React ----
    document.querySelectorAll('[data-cheer]').forEach(function (button) {
        button.addEventListener('click', function () {
            var isPressed = button.getAttribute('aria-pressed') !== 'true';
            button.setAttribute('aria-pressed', String(isPressed));

            var card = button.closest('article');
            var count = card ? card.querySelector('[data-count]') : null;

            if (count) {
                // data-count keeps the original server-rendered number, so
                // toggling never drifts: shown = original + (you, or not).
                var base = parseInt(count.dataset.count, 10) || 0;
                count.textContent = (base + (isPressed ? 1 : 0)) + ' ' + count.dataset.label;
            }
        });
    });

    // ---- 3. Dismiss the suggested next step ----
    var dismiss = document.querySelector('[data-dismiss-suggest]');
    var suggestPanel = document.getElementById('sf-suggest-panel');
    var suggestDone = document.getElementById('sf-suggest-done');

    if (dismiss && suggestPanel && suggestDone) {
        dismiss.addEventListener('click', function () {
            suggestPanel.hidden = true;
            suggestDone.hidden = false;
        });
    }
})();
