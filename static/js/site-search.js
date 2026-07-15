// Header search (added 2026-07-07).
// Quick-nav across PeerSlate plus an "Ask Pete's AI" fallthrough: the last
// row of every result list turns the typed text into a real AI question, so
// a search is never a dead end. The destination index comes from the
// #nav-search-data JSON block that base.html renders (URLs from Flask).
// Browser-only: no environment variables, no secrets.
(function () {
    const root = document.getElementById('nav-search');
    const input = document.getElementById('nav-search-input');
    const results = document.getElementById('nav-search-results');
    const dataEl = document.getElementById('nav-search-data');

    if (!root || !input || !results || !dataEl) return;

    let index = [];
    try {
        index = JSON.parse(dataEl.textContent);
    } catch (error) {
        return; // Malformed index: leave the input inert rather than crash.
    }

    const askUrl = root.dataset.askUrl || '/petec/resume';
    let items = [];   // rendered result rows
    let active = -1;  // keyboard-highlighted row index

    // Rank: title prefix beats title substring beats keyword substring.
    function score(entry, query) {
        const title = entry.title.toLowerCase();
        if (title.startsWith(query)) return 3;
        if (title.includes(query)) return 2;
        if (entry.keys.includes(query)) return 1;
        return 0;
    }

    function close() {
        results.hidden = true;
        input.setAttribute('aria-expanded', 'false');
        items = [];
        active = -1;
    }

    function render(rawQuery) {
        const query = rawQuery.trim().toLowerCase();
        if (!query) {
            close();
            return;
        }

        const hits = index
            .map(function (entry) { return { entry: entry, s: score(entry, query) }; })
            .filter(function (hit) { return hit.s > 0; })
            .sort(function (a, b) { return b.s - a.s; })
            .slice(0, 6);

        results.innerHTML = '';

        hits.forEach(function (hit) {
            const row = document.createElement('a');
            row.className = 'nav-search__item';
            row.href = hit.entry.href;
            row.setAttribute('role', 'option');
            row.innerHTML = '<strong></strong><small></small>';
            row.querySelector('strong').textContent = hit.entry.title;
            row.querySelector('small').textContent = hit.entry.sub;
            results.appendChild(row);
        });

        // The AI fallthrough row — always present, always last.
        const ask = document.createElement('a');
        ask.className = 'nav-search__item nav-search__item--ask';
        ask.href = askUrl + '?ask=' + encodeURIComponent(rawQuery.trim());
        ask.setAttribute('role', 'option');
        ask.innerHTML = '<strong></strong><small>Get an instant AI answer</small>';
        ask.querySelector('strong').textContent = 'Ask Pete’s AI: “' + rawQuery.trim() + '”';
        results.appendChild(ask);

        items = Array.prototype.slice.call(results.children);
        active = -1;
        results.hidden = false;
        input.setAttribute('aria-expanded', 'true');
    }

    function highlight(next) {
        if (!items.length) return;
        active = (next + items.length) % items.length;
        items.forEach(function (el, i) {
            el.classList.toggle('is-active', i === active);
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
            event.preventDefault();
            const pick = items[active] || items[0];
            if (pick) window.location.href = pick.href;
        } else if (event.key === 'Escape') {
            close();
            input.blur();
        }
    });

    document.addEventListener('click', function (event) {
        if (!root.contains(event.target)) close();
    });
})();
