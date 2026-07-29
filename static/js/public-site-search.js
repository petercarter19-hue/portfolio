// Public destination search.
// Each [data-nav-search] instance shares the server-rendered destination
// index. Search is navigation only; member-specific AI belongs inside a
// published member Slate and is not a global search fallback.
(function () {
    'use strict';

    var roots = document.querySelectorAll('[data-nav-search]');
    var dataEl = document.getElementById('nav-search-data');

    if (!roots.length || !dataEl) return;

    var index = [];
    try {
        index = JSON.parse(dataEl.textContent);
    } catch (error) {
        return;
    }

    function score(entry, query) {
        var title = entry.title.toLowerCase();
        var keys = (entry.keys || '').toLowerCase();
        if (title.startsWith(query)) return 3;
        if (title.includes(query)) return 2;
        if (keys.includes(query)) return 1;
        return 0;
    }

    roots.forEach(function (root) {
        var input = root.querySelector('.nav-search__input');
        var results = root.querySelector('.nav-search__results');
        if (!input || !results) return;

        var items = [];
        var active = -1;

        function close() {
            results.hidden = true;
            input.setAttribute('aria-expanded', 'false');
            items = [];
            active = -1;
        }

        function render(rawQuery) {
            var query = rawQuery.trim().toLowerCase();
            if (!query) {
                close();
                return;
            }

            var hits = index
                .map(function (entry) {
                    return { entry: entry, score: score(entry, query) };
                })
                .filter(function (hit) { return hit.score > 0; })
                .sort(function (a, b) { return b.score - a.score; })
                .slice(0, 6);

            results.innerHTML = '';

            hits.forEach(function (hit) {
                var row = document.createElement('a');
                row.className = 'nav-search__item';
                row.href = hit.entry.href;
                row.setAttribute('role', 'option');
                row.innerHTML = '<strong></strong><small></small>';
                row.querySelector('strong').textContent = hit.entry.title;
                row.querySelector('small').textContent = hit.entry.sub;
                results.appendChild(row);
            });

            if (!hits.length) {
                var empty = document.createElement('p');
                empty.className = 'nav-search__empty';
                empty.setAttribute('role', 'status');
                empty.textContent = 'No matching public destination';
                results.appendChild(empty);
            }

            items = Array.prototype.slice.call(
                results.querySelectorAll('a[role="option"]')
            );
            active = -1;
            results.hidden = false;
            input.setAttribute('aria-expanded', 'true');
        }

        function highlight(next) {
            if (!items.length) return;
            active = (next + items.length) % items.length;
            items.forEach(function (item, indexPosition) {
                item.classList.toggle('is-active', indexPosition === active);
            });
        }

        input.addEventListener('input', function () { render(input.value); });
        input.addEventListener('focus', function () { render(input.value); });

        input.addEventListener('keydown', function (event) {
            if (results.hidden) return;

            if (event.key === 'ArrowDown') {
                event.preventDefault();
                highlight(active + 1);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                highlight(active - 1);
            } else if (event.key === 'Enter') {
                var pick = items[active] || items[0];
                if (pick) {
                    event.preventDefault();
                    window.location.href = pick.href;
                }
            } else if (event.key === 'Escape') {
                close();
                input.blur();
            }
        });

        root.addEventListener('focusout', function (event) {
            if (!root.contains(event.relatedTarget)) close();
        });

        document.addEventListener('pointerdown', function (event) {
            if (!root.contains(event.target)) close();
        });
    });
})();
