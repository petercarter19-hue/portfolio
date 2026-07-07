// Slate Board interactions — browser-only, no secrets.
// Two features:
//   1. Whiteboard / Chalkboard toggle: flips data-board-mode on the
//      .whiteboard and remembers the choice in this browser.
//   2. "Chalk It Up" compose: pick a section (Short Term / Long Term /
//      Projects / Work), write up to 90 characters, and the entry inks
//      onto that quarter of the board. Entries persist in this browser
//      (localStorage) until PeerSlate accounts add real storage.

(function () {
    var board = document.querySelector('.whiteboard');
    if (!board) { return; }

    // Section key -> the ink color class family used by that quarter.
    var SECTION_COLORS = { short: 'green', long: 'violet', projects: 'blue', work: 'red' };

    // ---- 1. board style toggle ----
    var MODE_KEY = 'peerslateBoardMode';
    var modeButtons = document.querySelectorAll('[data-board-mode]');

    function applyMode(mode) {
        board.dataset.boardMode = mode;
        localStorage.setItem(MODE_KEY, mode);
        modeButtons.forEach(function (btn) {
            var active = btn.dataset.boardMode === mode;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-pressed', String(active));
        });
    }

    modeButtons.forEach(function (btn) {
        btn.addEventListener('click', function () { applyMode(btn.dataset.boardMode); });
    });

    var savedMode = localStorage.getItem(MODE_KEY);
    applyMode(savedMode === 'chalk' ? 'chalk' : 'white');

    // ---- 2. working "Chalk It Up" compose ----
    var MAX_CHARS = 90;
    var ENTRIES_KEY = 'peerslateBoardEntries';

    var input = document.getElementById('board-compose-input');
    var countEl = document.getElementById('board-compose-count');
    var addBtn = document.getElementById('board-compose-add');
    var sectionBtns = document.querySelectorAll('[data-wb-target]');

    if (!input || !addBtn) { return; }

    var currentSection = 'short';

    sectionBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            currentSection = btn.dataset.wbTarget;
            sectionBtns.forEach(function (b) {
                b.classList.toggle('is-active', b === btn);
            });
        });
    });

    function loadEntries() {
        try {
            return JSON.parse(localStorage.getItem(ENTRIES_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function saveEntries(entries) {
        try {
            localStorage.setItem(ENTRIES_KEY, JSON.stringify(entries));
        } catch (e) { /* quota — the line still shows this visit */ }
    }

    // Adds one ink line to a section's list. User lines are plain ink
    // (no card exists yet to link to) plus a tiny eraser button that
    // appears on hover. textContent keeps typed input inert.
    function inkEntry(entry) {
        var list = document.querySelector('.wb-section[data-wb="' + entry.section + '"] .wb-list');
        if (!list) { return; }

        var li = document.createElement('li');
        li.className = 'wb-user';
        li.style.setProperty('--i', String(list.children.length));

        var ink = document.createElement('span');
        ink.className = 'wb-ink wb-ink--' + (SECTION_COLORS[entry.section] || 'green');
        ink.textContent = entry.text;
        li.appendChild(ink);

        var del = document.createElement('button');
        del.className = 'wb-del';
        del.type = 'button';
        del.setAttribute('aria-label', 'Erase this entry');
        del.textContent = '×';
        del.addEventListener('click', function () {
            li.remove();
            saveEntries(loadEntries().filter(function (e) { return e.ts !== entry.ts; }));
        });
        li.appendChild(del);

        list.appendChild(li);
    }

    function refreshCompose() {
        var len = input.value.length;
        countEl.textContent = len + ' / ' + MAX_CHARS;
        addBtn.disabled = input.value.trim().length === 0;
    }

    input.addEventListener('input', function () {
        if (input.value.length > MAX_CHARS) {
            input.value = input.value.slice(0, MAX_CHARS);
        }
        refreshCompose();
    });

    addBtn.addEventListener('click', function () {
        var text = input.value.trim().slice(0, MAX_CHARS);
        if (!text) { return; }

        var entry = { ts: Date.now(), section: currentSection, text: text };
        inkEntry(entry);

        var entries = loadEntries();
        entries.push(entry);
        saveEntries(entries);

        input.value = '';
        refreshCompose();
        input.focus();
    });

    // Enter chalks it straight on (Shift+Enter still makes a new line).
    input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            addBtn.click();
        }
    });

    // Restore this browser's saved entries.
    loadEntries().forEach(inkEntry);
    refreshCompose();
})();
