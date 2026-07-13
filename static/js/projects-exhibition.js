/* PROJECTS — THE PROJECT EXHIBITION (2026-07-13)
   Interaction layer for the exhibition stage. Progressive enhancement:
   without JS the first project is forward and every project's content is
   in the document. Adds: scroll-driven focus (IntersectionObserver on
   normal document scroll — never hijacked), prev/next/selector controls,
   keyboard navigation, URL hash sync, and polite screen-reader
   announcements. */
(function () {
    'use strict';

    var root = document.querySelector('[data-pjx]');
    if (!root) return;

    var stage = root.querySelector('[data-pjx-stage]');
    var panels = Array.prototype.slice.call(root.querySelectorAll('[data-pjx-panel]'));
    if (!stage || panels.length === 0) return;

    var prevBtn = root.querySelector('[data-pjx-prev]');
    var nextBtn = root.querySelector('[data-pjx-next]');
    var dots = Array.prototype.slice.call(root.querySelectorAll('[data-pjx-goto]'));
    var current = root.querySelector('[data-pjx-current]');
    var live = root.querySelector('[data-pjx-live]');
    var markers = Array.prototype.slice.call(root.querySelectorAll('[data-pjx-marker]'));

    var active = 0;
    var scrollDriven = false; // guards observer feedback while buttons scroll

    function pad(n) { return (n + 1 < 10 ? '0' : '') + (n + 1); }

    /* Assign is-left / is-right around the active panel: earlier panels
       stack left, later panels stack right — matching the governing
       mockups (e.g. active 03 → 02 left, 01 right by proximity). */
    function apply() {
        var lefts = [];
        var rights = [];
        panels.forEach(function (p, i) {
            p.classList.remove('is-left', 'is-right');
            if (i === active) return;
            (i < active ? lefts : rights).push(p);
        });
        // Balance wings so the stage always reads as a triptych when
        // possible: if one side is empty, borrow from the other.
        if (lefts.length === 0 && rights.length > 1) lefts.push(rights.shift());
        if (rights.length === 0 && lefts.length > 1) rights.push(lefts.pop());
        lefts.forEach(function (p) { p.classList.add('is-left'); });
        rights.forEach(function (p) { p.classList.add('is-right'); });

        dots.forEach(function (d, i) {
            d.setAttribute('aria-pressed', String(i === active));
        });
        if (current) current.textContent = pad(active);
        if (prevBtn) prevBtn.disabled = active === 0;
        if (nextBtn) nextBtn.disabled = active === panels.length - 1;
    }

    function announce() {
        if (!live) return;
        var p = panels[active];
        var name = p.getAttribute('data-pjx-name') || 'Project';
        var note = p.querySelector('.pjx-panel__demo-note, .pjx-panel__pending');
        live.textContent = 'Project ' + pad(active) + ' of ' + pad(panels.length - 1).replace(/^0/, '') +
            ': ' + name + (note ? '. ' + note.textContent.trim() : '');
    }

    function setActive(index, opts) {
        opts = opts || {};
        index = Math.max(0, Math.min(panels.length - 1, index));
        if (index === active && !opts.force) return;
        active = index;
        apply();
        announce();
        var slug = panels[active].getAttribute('data-pjx-slug');
        if (slug && window.history && window.history.replaceState) {
            window.history.replaceState(null, '', '#' + slug);
        }
        // Keep the scroll position in step so the observer doesn't fight
        // the buttons on desktop. Never scroll on initial load.
        if (!opts.fromScroll && !opts.initial && markers[index] && window.matchMedia('(min-width: 768px)').matches) {
            scrollDriven = true;
            var behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
            markers[index].scrollIntoView({ behavior: behavior, block: 'center' });
            window.setTimeout(function () { scrollDriven = false; }, 900);
        }
    }

    /* Controls */
    if (prevBtn) prevBtn.addEventListener('click', function () { setActive(active - 1); });
    if (nextBtn) nextBtn.addEventListener('click', function () { setActive(active + 1); });
    dots.forEach(function (d) {
        d.addEventListener('click', function () {
            setActive(parseInt(d.getAttribute('data-pjx-goto'), 10));
        });
    });

    /* Clicking a wing panel brings it forward (pointer enhancement; the
       controls remain the accessible path). */
    panels.forEach(function (p, i) {
        var sel = p.querySelector('[data-pjx-select]');
        if (sel) sel.addEventListener('click', function () { setActive(i); });
    });

    /* Keyboard: arrows / Home / End move focus target; Enter/Space opens
       the active project when it has a published case study. */
    root.addEventListener('keydown', function (event) {
        var tag = (event.target.tagName || '').toLowerCase();
        var isField = tag === 'input' || tag === 'textarea' || tag === 'select';
        if (isField) return;
        switch (event.key) {
            case 'ArrowLeft': event.preventDefault(); setActive(active - 1); break;
            case 'ArrowRight': event.preventDefault(); setActive(active + 1); break;
            case 'Home': event.preventDefault(); setActive(0); break;
            case 'End': event.preventDefault(); setActive(panels.length - 1); break;
            case 'Enter':
            case ' ':
                // Only when the press isn't already on an interactive element.
                if (tag !== 'button' && tag !== 'a') {
                    var cta = panels[active].querySelector('[data-pjx-cta]');
                    if (cta) { event.preventDefault(); cta.click(); }
                }
                break;
        }
    });

    /* Scroll-driven focus on desktop: each marker section activates its
       project as it crosses the viewport middle. Normal scrolling only. */
    if ('IntersectionObserver' in window && markers.length === panels.length) {
        var observer = new IntersectionObserver(function (entries) {
            if (scrollDriven) return;
            if (!window.matchMedia('(min-width: 768px)').matches) return;
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                var idx = parseInt(entry.target.getAttribute('data-pjx-marker'), 10);
                if (idx !== active) setActive(idx, { fromScroll: true });
            });
        }, { rootMargin: '-45% 0px -45% 0px' });
        markers.forEach(function (m) { observer.observe(m); });
    }

    /* Deep link: #slug selects that project on load. */
    var hash = (window.location.hash || '').replace('#', '');
    var start = 0;
    panels.forEach(function (p, i) {
        if (p.getAttribute('data-pjx-slug') === hash) start = i;
    });
    setActive(start, { force: true, initial: start === 0 });
})();
