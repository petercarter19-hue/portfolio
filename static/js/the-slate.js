// the-slate.js — interactivity for The Slate hub (2026-07-08).
// Runs on the hub tabs: Slate Feed (People), My Slate, and Daily Slate.
// Browser-only; no secrets, no network calls. The composer and check-in
// store per-browser in localStorage until PeerSlate accounts bring real
// cross-visitor storage.

(function () {
    'use strict';

    var DAILY_KEY = 'theSlateDailyCards';
    var MAX_SAVED_CARDS = 20;
    var databasePage = document.querySelector('[data-database-ui="true"]');
    var apiEnabled = Boolean(databasePage);

    // Category chip → tag tint used when the visitor's card renders.
    var CAT_TINTS = {
        Work: 'green',
        Career: 'violet',
        Project: 'blue',
        Health: 'red',
        Education: 'orange',
        Personal: 'sky'
    };

    /* ============================================================
       Small helpers
       ============================================================ */

    function relativeLabel(timestamp) {
        var seconds = Math.max(0, (Date.now() - timestamp) / 1000);
        if (seconds < 90) { return 'Just now'; }
        var minutes = Math.round(seconds / 60);
        if (minutes < 60) { return minutes + 'm ago'; }
        var hours = Math.round(minutes / 60);
        if (hours < 24) { return hours + 'h ago'; }
        var days = Math.round(hours / 24);
        return days + 'd ago';
    }

    function loadSavedCards() {
        try {
            var raw = localStorage.getItem(DAILY_KEY);
            var cards = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(cards)) { return []; }
            // Drop malformed entries (schema drift / hand-edited storage):
            // one bad element would otherwise throw inside the render loop
            // and stop the rest of this file from wiring up.
            return cards.filter(function (card) {
                return card && typeof card === 'object' && typeof card.text === 'string';
            });
        } catch (err) {
            return [];
        }
    }

    function saveCards(cards) {
        try {
            localStorage.setItem(DAILY_KEY, JSON.stringify(cards.slice(0, MAX_SAVED_CARDS)));
        } catch (err) {
            /* storage full/blocked — the card still renders this visit */
        }
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

    // Single-select behavior for a group of chip buttons.
    function makeSingleSelect(buttons) {
        buttons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                buttons.forEach(function (other) {
                    var isActive = other === btn;
                    other.classList.toggle('is-active', isActive);
                    other.setAttribute('aria-pressed', String(isActive));
                });
            });
        });
    }

    /* ============================================================
       The Daily Slate card composer (Slate Feed + Daily Slate tabs)
       ============================================================ */

    // Builds a visitor card with the same skeleton as the sample cards.
    // User text goes in via textContent only (never innerHTML), so
    // nothing typed can inject markup.
    function buildDailyCard(card) {
        var article = document.createElement('article');
        article.className = 'ps-card ts-daily ts-daily--mine';
        article.innerHTML =
            '<span class="ts-daily__dot is-done" aria-hidden="true">' +
                '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>' +
            '</span>' +
            '<div class="ts-daily__who">' +
                '<span class="ts-ava ts-ava--you" aria-hidden="true">You</span>' +
                '<strong>You</strong>' +
                '<small></small>' +
            '</div>' +
            '<div class="ts-daily__copy">' +
                '<p class="ts-daily__text"></p>' +
                '<div class="ts-goal__tags">' +
                    '<span class="ts-tag"></span>' +
                    '<span class="ts-vis"></span>' +
                '</div>' +
            '</div>' +
            '<button class="ts-daily__delete" type="button" aria-label="Delete this card" title="Delete this card">&times;</button>';

        article.querySelector('.ts-daily__who small').textContent = relativeLabel(card.ts);
        article.querySelector('.ts-daily__text').textContent = card.text;

        var tag = article.querySelector('.ts-tag');
        tag.classList.add('ts-tag--' + (CAT_TINTS[card.cat] || 'blue'));
        tag.textContent = card.cat;

        var vis = article.querySelector('.ts-vis');
        vis.classList.add(card.privacy === 'Private' ? 'ts-vis--private' : 'ts-vis--public');
        vis.textContent = card.privacy;

        article.querySelector('.ts-daily__delete').addEventListener('click', function () {
            if (apiEnabled && card.id) {
                api('/api/slate-items/' + card.id + '/archive', {
                    method: 'POST',
                    body: JSON.stringify({ note: 'Archived from Daily Slate.' })
                }).then(function () { article.remove(); });
                return;
            }
            var cards = loadSavedCards().filter(function (saved) { return saved.ts !== card.ts; });
            saveCards(cards);
            article.remove();
        });

        return article;
    }

    function setUpComposer(composer) {
        var textarea = composer.querySelector('.ts-compose__text');
        var counter = composer.querySelector('.ts-compose__count');
        var postBtn = composer.querySelector('.ts-compose__post');
        var doneNote = composer.querySelector('.ts-compose__done');
        var catBtns = Array.prototype.slice.call(composer.querySelectorAll('.ts-cat'));
        var privacyBtns = Array.prototype.slice.call(composer.querySelectorAll('.ts-privacy__opt'));
        var dailyList = document.querySelector('[data-ts-daily-list]');

        makeSingleSelect(catBtns);
        makeSingleSelect(privacyBtns);

        if (apiEnabled) {
            privacyBtns.forEach(function (button) {
                var isPrivate = button.dataset.privacy === 'Private';
                button.classList.toggle('is-active', isPrivate);
                button.setAttribute('aria-pressed', String(isPrivate));
                if (!isPrivate) {
                    button.disabled = true;
                    button.title = 'Publishing is a separate action and is not enabled yet.';
                }
            });
        }

        textarea.addEventListener('input', function () {
            var length = textarea.value.length;
            counter.textContent = length + ' / 500';
            counter.classList.toggle('is-warn', length >= 440);
            postBtn.disabled = textarea.value.trim().length === 0;
        });

        postBtn.addEventListener('click', function () {
            var text = textarea.value.trim();
            if (!text) { return; }

            var activeCat = composer.querySelector('.ts-cat.is-active');
            var activePrivacy = composer.querySelector('.ts-privacy__opt.is-active');
            var card = {
                text: text,
                cat: activeCat ? activeCat.dataset.cat : 'Work',
                privacy: apiEnabled ? 'Private' : (activePrivacy ? activePrivacy.dataset.privacy : 'Public'),
                ts: Date.now()
            };

            if (apiEnabled) {
                postBtn.disabled = true;
                api('/api/slate-items', {
                    method: 'POST',
                    body: JSON.stringify({
                        space_name: 'Daily Slate',
                        space_type: 'daily',
                        item_type: 'progress',
                        title: text.slice(0, 200),
                        body: text,
                        category: card.cat
                    })
                }).then(function (payload) {
                    var saved = payload.items && payload.items[0];
                    card.id = saved && (saved.slate_item_id || saved.id);
                    if (dailyList) { dailyList.prepend(buildDailyCard(card)); }
                    textarea.value = '';
                    counter.textContent = '0 / 500';
                    counter.classList.remove('is-warn');
                    doneNote.textContent = 'Saved privately to your Daily Slate.';
                    doneNote.hidden = false;
                    window.setTimeout(function () { doneNote.hidden = true; }, 6000);
                }).catch(function (error) {
                    doneNote.textContent = error.message;
                    doneNote.hidden = false;
                }).finally(function () {
                    postBtn.disabled = textarea.value.trim().length === 0;
                });
                return;
            }

            var cards = loadSavedCards();
            cards.unshift(card);
            saveCards(cards);

            // On the Daily tab the card appears right below; on the Slate
            // Feed tab the note links across to the Daily Slate instead.
            if (dailyList) {
                dailyList.prepend(buildDailyCard(card));
            }

            textarea.value = '';
            counter.textContent = '0 / 500';
            counter.classList.remove('is-warn');
            postBtn.disabled = true;
            doneNote.hidden = false;
            window.setTimeout(function () { doneNote.hidden = true; }, 6000);
        });
    }

    document.querySelectorAll('[data-ts-compose]').forEach(setUpComposer);

    // Render previously saved cards at the top of the Daily list.
    var dailyList = document.querySelector('[data-ts-daily-list]');
    if (dailyList && apiEnabled) {
        api('/api/slate-spaces/Daily%20Slate').then(function (payload) {
            var items = payload.slate_space && payload.slate_space.items || [];
            items.slice().reverse().forEach(function (item) {
                dailyList.prepend(buildDailyCard({
                    id: item.slate_item_id,
                    text: item.body || item.title,
                    cat: item.category || 'Work',
                    privacy: 'Private',
                    ts: Date.parse(item.updated_at || item.created_at) || Date.now()
                }));
            });
        });
    } else if (dailyList) {
        loadSavedCards().reverse().forEach(function (card) {
            dailyList.prepend(buildDailyCard(card));
        });
    }

    /* ============================================================
       Hearts on the sample daily cards
       ============================================================ */

    document.querySelectorAll('[data-ts-heart]').forEach(function (heart) {
        heart.addEventListener('click', function () {
            var count = heart.querySelector('[data-ts-heart-count]');
            var isOn = heart.getAttribute('aria-pressed') === 'true';
            heart.setAttribute('aria-pressed', String(!isOn));
            heart.classList.toggle('is-on', !isOn);
            count.textContent = String(parseInt(count.textContent, 10) + (isOn ? -1 : 1));
        });
    });

    /* ============================================================
       AI cards — rotate through Slate-specific suggestions
       ============================================================ */

    document.querySelectorAll('[data-ts-ai]').forEach(function (panel) {
        var section = panel.closest('section');
        var ideasScript = section && section.querySelector('[data-ts-ai-ideas]');
        var nextBtn = panel.querySelector('[data-ts-ai-next]');
        if (!ideasScript || !nextBtn) { return; }

        var ideas;
        try {
            ideas = JSON.parse(ideasScript.textContent);
        } catch (err) {
            return;
        }

        var index = -1;
        nextBtn.addEventListener('click', function () {
            index = (index + 1) % ideas.length;
            var idea = ideas[index];
            panel.querySelector('[data-ts-ai-msg]').textContent = idea.msg;
            var go = panel.querySelector('[data-ts-ai-go]');
            go.textContent = idea.label;
            go.href = idea.href;
        });
    });

    // "Not now" — tuck the suggestion away politely.
    document.querySelectorAll('[data-ts-dismiss]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var section = btn.closest('section');
            var panel = btn.closest('.ts-ai__panel');
            var done = section && section.querySelector('.ts-ai__done');
            if (panel) { panel.hidden = true; }
            if (done) { done.hidden = false; }
        });
    });

    // Daily tab: "Create 2-Step Plan" reveals the plan inline.
    document.querySelectorAll('[data-ts-plan]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var panel = btn.closest('.ts-ai__panel');
            var steps = panel && panel.querySelector('[data-ts-plan-steps]');
            if (steps) { steps.hidden = false; }
            btn.textContent = 'Plan created ✓';
            btn.disabled = true;
        });
    });

    /* ============================================================
       My Slate — goal filters + "Focus this goal"
       ============================================================ */

    var goalCards = Array.prototype.slice.call(document.querySelectorAll('.ts-goal'));
    var boardCanvas = document.querySelector('.ts-board__canvas');
    var filterBtns = Array.prototype.slice.call(document.querySelectorAll('.ts-filter'));

    function clearFocus() {
        goalCards.forEach(function (card) {
            card.classList.remove('is-focus');
        });
    }

    function applyGoalFilter(zone) {
        clearFocus();
        goalCards.forEach(function (card) {
            var zones = (card.dataset.zones || '').split(/\s+/);
            var matches = zone === 'all' || zones.indexOf(zone) !== -1;
            card.classList.toggle('is-dim', !matches);
        });
        if (boardCanvas) {
            boardCanvas.classList.toggle('is-filtered', zone !== 'all');
        }
    }

    if (filterBtns.length) {
        makeSingleSelect(filterBtns);
        filterBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                applyGoalFilter(btn.dataset.filter);
            });
        });
    }

    // "Focus this goal" spotlights the behind-schedule card on the board.
    document.querySelectorAll('[data-ts-focus]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var target = document.getElementById(btn.dataset.tsFocus);
            if (!target) { return; }
            goalCards.forEach(function (card) {
                card.classList.toggle('is-dim', card !== target);
                card.classList.toggle('is-focus', card === target);
            });
            if (boardCanvas) { boardCanvas.classList.add('is-filtered'); }
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            window.setTimeout(function () {
                applyGoalFilter('all');
            }, 5000);
        });
    });

    /* ============================================================
       Slate Paths — the Daily Slate check-in
       ============================================================ */

    var checkin = document.querySelector('[data-ts-checkin]');
    if (checkin) {
        var checkinText = checkin.querySelector('.ts-checkin__text');
        var checkinCount = checkin.querySelector('.ts-checkin__count');
        var quickChips = Array.prototype.slice.call(checkin.querySelectorAll('.ts-quick'));
        var logBtn = checkin.querySelector('.ts-checkin__log');
        var checkinDone = checkin.querySelector('.ts-checkin__done');
        var updatesList = document.querySelector('[data-ts-updates]');

        function refreshLogButton() {
            var hasText = checkinText.value.trim().length > 0;
            var hasChip = quickChips.some(function (chip) {
                return chip.getAttribute('aria-pressed') === 'true';
            });
            logBtn.disabled = !(hasText || hasChip);
        }

        // Quick chips multi-select (a session can be several kinds at once).
        quickChips.forEach(function (chip) {
            chip.addEventListener('click', function () {
                var isOn = chip.getAttribute('aria-pressed') === 'true';
                chip.setAttribute('aria-pressed', String(!isOn));
                chip.classList.toggle('is-active', !isOn);
                refreshLogButton();
            });
        });

        checkinText.addEventListener('input', function () {
            checkinCount.textContent = checkinText.value.length + ' / 500';
            refreshLogButton();
        });

        logBtn.addEventListener('click', function () {
            var kinds = quickChips
                .filter(function (chip) { return chip.getAttribute('aria-pressed') === 'true'; })
                .map(function (chip) { return chip.dataset.quick.toLowerCase(); });
            var summary = kinds.length ? kinds.join(' + ') : 'progress';

            // Drop the check-in into "Top recent updates" so the loop closes.
            if (updatesList) {
                var item = document.createElement('li');
                item.innerHTML =
                    '<span class="ts-updatelist__icon ps-tint--green" aria-hidden="true">' +
                        '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8.5 12.4l2.3 2.3 4.7-5"/></svg>' +
                    '</span>' +
                    '<span class="ts-updatelist__body"><strong>You</strong> <b class="ts-updatelist__what"></b><small>Just now</small></span>';
                item.querySelector('.ts-updatelist__what').textContent = 'logged a check-in — ' + summary;
                updatesList.prepend(item);
            }

            checkinText.value = '';
            checkinCount.textContent = '0 / 500';
            quickChips.forEach(function (chip) {
                chip.setAttribute('aria-pressed', 'false');
                chip.classList.remove('is-active');
            });
            logBtn.disabled = true;
            checkinDone.hidden = false;
            window.setTimeout(function () { checkinDone.hidden = true; }, 6000);
        });
    }
})();
