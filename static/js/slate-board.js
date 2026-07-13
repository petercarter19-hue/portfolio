// Slate Board interactions. Browser storage remains the default; an explicit
// feature flag switches member-created items to the authenticated SQL API.

(function () {
    var board = document.querySelector('.whiteboard');
    if (!board) { return; }

    var boardPage = board.closest('[data-board-api]');
    var apiEnabled = boardPage && boardPage.dataset.boardApi === 'true';
    var statusEl = document.getElementById('board-compose-status');
    var SECTION_COLORS = { short: 'green', long: 'violet', projects: 'blue', work: 'red' };

    // Whiteboard / chalkboard preference is visual and safely remains local.
    var MODE_KEY = 'peerslateBoardMode';
    var modeButtons = document.querySelectorAll('[data-board-mode]');

    function applyMode(mode) {
        board.dataset.boardMode = mode;
        try { localStorage.setItem(MODE_KEY, mode); } catch (error) { /* optional */ }
        modeButtons.forEach(function (button) {
            var active = button.dataset.boardMode === mode;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });
    }

    modeButtons.forEach(function (button) {
        button.addEventListener('click', function () { applyMode(button.dataset.boardMode); });
    });

    var savedMode = null;
    try { savedMode = localStorage.getItem(MODE_KEY); } catch (error) { /* optional */ }
    applyMode(savedMode === 'chalk' ? 'chalk' : 'white');

    var MAX_CHARS = 90;
    var ENTRIES_KEY = 'peerslateBoardEntries';
    var input = document.getElementById('board-compose-input');
    var countEl = document.getElementById('board-compose-count');
    var addBtn = document.getElementById('board-compose-add');
    var sectionButtons = document.querySelectorAll('[data-wb-target]');
    if (!input || !addBtn || !countEl) { return; }

    var currentSection = 'short';

    function announce(message) {
        if (statusEl) { statusEl.textContent = message; }
    }

    function api(url, options) {
        var settings = options || {};
        settings.headers = Object.assign({}, settings.headers || {}, {
            'X-PeerSlate-Request': 'same-origin'
        });
        if (settings.body) { settings.headers['Content-Type'] = 'application/json'; }
        return fetch(url, settings).then(function (response) {
            return response.json().then(function (payload) {
                if (!response.ok || !payload.success) {
                    throw new Error(payload.message || 'PeerSlate could not complete the request.');
                }
                return payload;
            });
        });
    }

    sectionButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            currentSection = button.dataset.wbTarget;
            sectionButtons.forEach(function (candidate) {
                candidate.classList.toggle('is-active', candidate === button);
            });
        });
    });

    function loadLocalEntries() {
        try { return JSON.parse(localStorage.getItem(ENTRIES_KEY)) || []; }
        catch (error) { return []; }
    }

    function saveLocalEntries(entries) {
        try { localStorage.setItem(ENTRIES_KEY, JSON.stringify(entries)); }
        catch (error) { /* entry still remains for this page visit */ }
    }

    function removeEntry(entry, listItem, button) {
        if (!apiEnabled || !entry.id) {
            listItem.remove();
            saveLocalEntries(loadLocalEntries().filter(function (saved) {
                return saved.ts !== entry.ts;
            }));
            return;
        }

        button.disabled = true;
        api('/api/slate-items/' + entry.id + '/archive', {
            method: 'POST',
            body: JSON.stringify({ note: 'Archived from the Slate Board.' })
        }).then(function () {
            listItem.remove();
            announce('Board item archived.');
        }).catch(function (error) {
            button.disabled = false;
            announce(error.message);
        });
    }

    function inkEntry(entry) {
        if (!entry || typeof entry.text !== 'string' || !SECTION_COLORS[entry.section]) { return; }
        var list = document.querySelector('.wb-section[data-wb="' + entry.section + '"] .wb-list');
        if (!list) { return; }

        var listItem = document.createElement('li');
        listItem.className = 'wb-user';
        listItem.style.setProperty('--i', String(list.children.length));

        var ink = document.createElement('span');
        ink.className = 'wb-ink wb-ink--' + SECTION_COLORS[entry.section];
        ink.textContent = entry.text;
        listItem.appendChild(ink);

        var removeButton = document.createElement('button');
        removeButton.className = 'wb-del';
        removeButton.type = 'button';
        removeButton.setAttribute('aria-label', 'Archive this entry');
        removeButton.textContent = 'x';
        removeButton.addEventListener('click', function () {
            removeEntry(entry, listItem, removeButton);
        });
        listItem.appendChild(removeButton);
        list.appendChild(listItem);
    }

    function refreshCompose() {
        var length = input.value.length;
        countEl.textContent = length + ' / ' + MAX_CHARS;
        addBtn.disabled = input.value.trim().length === 0;
    }

    input.addEventListener('input', function () {
        if (input.value.length > MAX_CHARS) {
            input.value = input.value.slice(0, MAX_CHARS);
        }
        refreshCompose();
    });

    function saveDatabaseEntry(entry) {
        addBtn.disabled = true;
        announce('Saving privately to your Slate Board...');
        return api('/api/slate-items', {
            method: 'POST',
            body: JSON.stringify({
                space_name: 'Slate Board',
                space_type: 'board',
                item_type: currentSection,
                title: entry.text,
                category: currentSection,
                color_label: SECTION_COLORS[currentSection]
            })
        }).then(function (payload) {
            var saved = payload.items && payload.items[0];
            entry.id = saved && (saved.slate_item_id || saved.id);
            inkEntry(entry);
            input.value = '';
            announce('Saved privately to your Slate Board.');
        }).catch(function (error) {
            announce(error.message);
        }).finally(function () {
            refreshCompose();
            input.focus();
        });
    }

    addBtn.addEventListener('click', function () {
        var text = input.value.trim().slice(0, MAX_CHARS);
        if (!text) { return; }
        var entry = { ts: Date.now(), section: currentSection, text: text };

        if (apiEnabled) {
            saveDatabaseEntry(entry);
            return;
        }

        inkEntry(entry);
        var entries = loadLocalEntries();
        entries.push(entry);
        saveLocalEntries(entries);
        input.value = '';
        refreshCompose();
        input.focus();
    });

    input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            addBtn.click();
        }
    });

    if (apiEnabled) {
        api('/api/slate-spaces/Slate%20Board').then(function (payload) {
            var items = payload.slate_space && payload.slate_space.items || [];
            items.forEach(function (item) {
                var section = SECTION_COLORS[item.category] ? item.category : 'short';
                inkEntry({
                    id: item.slate_item_id,
                    ts: item.slate_item_id,
                    section: section,
                    text: item.title
                });
            });
            announce(items.length
                ? 'Your private Slate Board is loaded.'
                : 'Your Slate Board is empty. Add the first private item.');
        }).catch(function (error) {
            announce(error.message + ' You can still add the first private item.');
        });
    } else {
        loadLocalEntries().forEach(inkEntry);
    }

    refreshCompose();
})();
