// story.js — My Slate (story page) interactivity, 2026-07-08.
// The "add a completed goal" feature on the journey timeline: the visitor
// opts in (clicks "Add a completed goal"), types a finished goal, picks
// Public or Private, and it lands on their timeline. Saved per-browser in
// localStorage (MVP convention, same as the-slate.js). Browser-only; no
// secrets, no network. User text is inserted via textContent only, so
// nothing typed can inject markup.

(function () {
    'use strict';

    var STORAGE_KEY = 'myStoryCompletedGoals';
    var MAX_GOALS = 12;

    var root = document.querySelector('.timeline-goals');
    if (!root) { return; }

    var list = root.querySelector('[data-goals-list]');
    var toggle = root.querySelector('[data-goals-toggle]');
    var form = root.querySelector('[data-goals-form]');
    var input = root.querySelector('[data-goals-input]');
    var cancel = root.querySelector('[data-goals-cancel]');
    var saveBtn = root.querySelector('.timeline-goals__save');
    var visButtons = Array.prototype.slice.call(root.querySelectorAll('.timeline-goals__visopt'));

    var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    function todayLabel() {
        // new Date() is fine in the browser (this is client-side, not the
        // workflow sandbox), so completed goals stamp with the real date.
        var d = new Date();
        return MONTHS[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
    }

    function load() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            var goals = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(goals)) { return []; }
            // Drop malformed entries (schema drift / hand-edited storage) so
            // one bad element can't throw inside the render loop below.
            return goals.filter(function (goal) {
                return goal && typeof goal === 'object' && typeof goal.title === 'string';
            });
        } catch (err) {
            return [];
        }
    }

    function save(goals) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(goals.slice(0, MAX_GOALS)));
        } catch (err) {
            /* storage blocked — the goal still shows this visit */
        }
    }

    function buildGoalCard(goal) {
        var isPrivate = goal.vis === 'Private';

        var card = document.createElement('article');
        card.className = 'timeline-goal';
        card.innerHTML =
            '<span class="timeline-goal__mark" aria-hidden="true">' +
                '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>' +
            '</span>' +
            '<div class="timeline-goal__body">' +
                '<p class="timeline-goal__date">Completed &middot; <span data-date></span></p>' +
                '<h4 data-title></h4>' +
                '<span class="timeline-goal__vis"></span>' +
            '</div>' +
            '<button type="button" class="timeline-goal__delete" aria-label="Remove this goal" title="Remove">&times;</button>';

        card.querySelector('[data-date]').textContent = goal.date;
        card.querySelector('[data-title]').textContent = goal.title;

        var visEl = card.querySelector('.timeline-goal__vis');
        visEl.classList.add(isPrivate ? 'timeline-goal__vis--private' : 'timeline-goal__vis--public');
        visEl.textContent = goal.vis;

        card.querySelector('.timeline-goal__delete').addEventListener('click', function () {
            save(load().filter(function (g) { return g.id !== goal.id; }));
            card.remove();
        });

        return card;
    }

    function render() {
        list.replaceChildren();
        load().forEach(function (goal) {
            list.appendChild(buildGoalCard(goal));
        });
    }

    function selectedVisibility() {
        var active = root.querySelector('.timeline-goals__visopt.is-active');
        return active ? active.dataset.vis : 'Public';
    }

    function openForm() {
        form.hidden = false;
        toggle.hidden = true;
        input.focus();
    }

    function closeForm() {
        form.hidden = true;
        toggle.hidden = false;
        input.value = '';
        saveBtn.disabled = true;
    }

    toggle.addEventListener('click', openForm);
    cancel.addEventListener('click', closeForm);

    input.addEventListener('input', function () {
        saveBtn.disabled = input.value.trim().length === 0;
    });

    visButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            visButtons.forEach(function (other) {
                var isActive = other === btn;
                other.classList.toggle('is-active', isActive);
                other.setAttribute('aria-pressed', String(isActive));
            });
        });
    });

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var title = input.value.trim();
        if (!title) { return; }

        // A simple client id — index in the prompt/label isn't available here,
        // so use a monotonic counter seeded from existing goals + length.
        var goals = load();
        var goal = {
            id: 'g' + (goals.length) + '-' + title.length + '-' + title.slice(0, 4),
            title: title,
            vis: selectedVisibility(),
            date: todayLabel()
        };

        // Guard against a duplicate id (same first chars + length): append a
        // suffix so delete stays reliable.
        while (goals.some(function (g) { return g.id === goal.id; })) {
            goal.id += 'x';
        }

        goals.unshift(goal);
        save(goals);
        list.insertBefore(buildGoalCard(goal), list.firstChild);
        closeForm();
    });

    render();
})();
