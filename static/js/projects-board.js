/* =====================================================================
   PROJECTS BOARD — /petec/work (2026-07-13)
   Progressive enhancement over server-rendered markup: filtering, search,
   pagination, and the Project Detail modal (open/close, tabs, focus trap).
   Cards render server-side and stay readable with JS off; the detail modal
   (opened from a card) requires JavaScript.
   ===================================================================== */
(function () {
    'use strict';

    var root = document.querySelector('[data-pb]');
    if (!root) return;

    var grid = root.querySelector('[data-pb-grid]');
    var cards = Array.prototype.slice.call(root.querySelectorAll('[data-pb-card]'));
    var filters = Array.prototype.slice.call(root.querySelectorAll('[data-pb-filter]'));
    var searchInput = root.querySelector('[data-pb-search]');
    var emptyMsg = root.querySelector('[data-pb-empty]');
    var resetBtn = root.querySelector('[data-pb-reset]');
    var newBtn = root.querySelector('[data-pb-new]');
    var pager = root.querySelector('[data-pb-pager]');

    var PAGE_SIZE = parseInt((grid && grid.getAttribute('data-page-size')) || '6', 10) || 6;

    var state = { filter: 'all', query: '', page: 1 };

    /* ---------------------------------------------------- list rendering */
    function matches(card) {
        var okStatus = state.filter === 'all' || card.getAttribute('data-status') === state.filter;
        var okQuery = !state.query || (card.getAttribute('data-search') || '').indexOf(state.query) !== -1;
        return okStatus && okQuery;
    }

    function render() {
        var visible = cards.filter(matches);
        var pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
        if (state.page > pageCount) state.page = pageCount;

        var start = (state.page - 1) * PAGE_SIZE;
        var end = start + PAGE_SIZE;

        cards.forEach(function (card) { card.hidden = true; });
        visible.forEach(function (card, i) {
            card.hidden = !(i >= start && i < end);
        });

        if (emptyMsg) emptyMsg.hidden = visible.length !== 0;
        renderPager(pageCount);
    }

    function renderPager(pageCount) {
        if (!pager) return;
        if (pageCount <= 1) { pager.hidden = true; pager.innerHTML = ''; return; }
        pager.hidden = false;

        var html = '';
        html += '<button type="button" data-pb-page="prev" aria-label="Previous page"' + (state.page === 1 ? ' disabled' : '') + '>&lsaquo;</button>';
        for (var n = 1; n <= pageCount; n++) {
            html += '<button type="button" data-pb-page="' + n + '"' +
                (n === state.page ? ' class="is-active" aria-current="page"' : '') +
                '>' + n + '</button>';
        }
        html += '<button type="button" data-pb-page="next" aria-label="Next page"' + (state.page === pageCount ? ' disabled' : '') + '>&rsaquo;</button>';
        pager.innerHTML = html;
    }

    /* ------------------------------------------------------------ filters */
    filters.forEach(function (btn) {
        btn.addEventListener('click', function () {
            filters.forEach(function (b) {
                b.classList.toggle('is-active', b === btn);
                b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
            });
            state.filter = btn.getAttribute('data-pb-filter');
            state.page = 1;
            render();
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            state.query = searchInput.value.trim().toLowerCase();
            state.page = 1;
            render();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            state.filter = 'all';
            state.query = '';
            state.page = 1;
            if (searchInput) searchInput.value = '';
            filters.forEach(function (b) {
                var on = b.getAttribute('data-pb-filter') === 'all';
                b.classList.toggle('is-active', on);
                b.setAttribute('aria-pressed', on ? 'true' : 'false');
            });
            render();
        });
    }

    if (pager) {
        pager.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-pb-page]');
            if (!btn || btn.disabled) return;
            var val = btn.getAttribute('data-pb-page');
            var pageCount = Math.max(1, Math.ceil(cards.filter(matches).length / PAGE_SIZE));
            if (val === 'prev') state.page = Math.max(1, state.page - 1);
            else if (val === 'next') state.page = Math.min(pageCount, state.page + 1);
            else state.page = parseInt(val, 10) || 1;
            render();
            if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    /* -------------------------------------------------------- New Project */
    if (newBtn) {
        newBtn.addEventListener('click', function () {
            toast('New Project — creating and editing projects is coming soon.');
        });
    }

    var toastEl = null, toastTimer = null;
    function toast(message) {
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.className = 'pb-toast';
            toastEl.setAttribute('role', 'status');
            toastEl.style.cssText = 'position:fixed;left:50%;bottom:2rem;transform:translateX(-50%);z-index:1400;' +
                'background:#0a1b36;color:#fff;padding:0.75rem 1.25rem;border-radius:12px;font:600 0.9rem/1.3 Inter,sans-serif;' +
                'box-shadow:0 16px 40px rgba(6,16,38,0.4);max-width:90vw;text-align:center;opacity:0;transition:opacity 200ms ease;';
            document.body.appendChild(toastEl);
        }
        toastEl.textContent = message;
        requestAnimationFrame(function () { toastEl.style.opacity = '1'; });
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () { toastEl.style.opacity = '0'; }, 3200);
    }

    /* ============================================================ MODAL */
    var modal = document.querySelector('[data-pb-modal]');

    /* Portal the modal to <body>. <main> sets `isolation: isolate`, which
       creates a stacking context that would otherwise trap the modal beneath
       the sticky global header no matter how high its z-index. As a direct
       child of <body> it competes with the header at the root level and wins.
       Its palette tokens live on the element itself, so they survive the move. */
    if (modal && modal.parentElement !== document.body) {
        document.body.appendChild(modal);
    }

    var dialog = modal ? modal.querySelector('[data-pb-dialog]') : null;
    var details = modal ? Array.prototype.slice.call(modal.querySelectorAll('[data-detail]')) : [];
    var lastTrigger = null;

    function detailFor(slug) {
        for (var i = 0; i < details.length; i++) {
            if (details[i].getAttribute('data-detail') === slug) return details[i];
        }
        return null;
    }

    function openModal(slug, trigger) {
        var detail = detailFor(slug);
        if (!modal || !detail) return;

        details.forEach(function (d) { d.hidden = (d !== detail); });
        resetTabs(detail);

        lastTrigger = trigger || document.activeElement;
        modal.hidden = false;
        document.body.classList.add('pb-modal-open');

        var title = detail.querySelector('.pb-detail__title');
        if (title && title.id && dialog) dialog.setAttribute('aria-labelledby', title.id);

        if (dialog) dialog.scrollTop = 0;
        var closeBtn = detail.querySelector('[data-pb-close]');
        if (closeBtn) closeBtn.focus();

        document.addEventListener('keydown', onKeydown, true);
    }

    function closeModal() {
        if (!modal || modal.hidden) return;
        modal.hidden = true;
        document.body.classList.remove('pb-modal-open');
        document.removeEventListener('keydown', onKeydown, true);
        if (lastTrigger && typeof lastTrigger.focus === 'function') {
            lastTrigger.focus();
        }
        lastTrigger = null;
    }

    function onKeydown(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            closeModal();
            return;
        }
        if (e.key === 'Tab') trapFocus(e);
    }

    function focusables() {
        if (!dialog) return [];
        var visibleDetail = details.filter(function (d) { return !d.hidden; })[0];
        if (!visibleDetail) return [];
        var nodes = visibleDetail.querySelectorAll(
            'a[href], button:not([disabled]), input, [tabindex]:not([tabindex="-1"])'
        );
        // Require tabIndex >= 0 so the inactive roving-tabindex="-1" tabs are
        // excluded — otherwise a tab whose panel has no focusable content would
        // leave the last "focusable" as an unreachable tab and the wrap (and
        // thus focus containment) would silently break.
        return Array.prototype.slice.call(nodes).filter(function (el) {
            return el.tabIndex >= 0 && (el.offsetParent !== null || el === document.activeElement);
        });
    }

    function trapFocus(e) {
        var items = focusables();
        if (!items.length) return;
        var first = items[0];
        var last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }

    /* Card open triggers */
    root.querySelectorAll('[data-pb-open]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            openModal(btn.getAttribute('data-pb-open'), btn);
        });
    });

    /* Close controls (✕ button + backdrop) */
    if (modal) {
        modal.querySelectorAll('[data-pb-close]').forEach(function (el) {
            el.addEventListener('click', closeModal);
        });
    }

    /* Click-outside-to-close: the dialog scroll layer sits above the backdrop
       and fills the viewport, so a click on its padding area (not on the
       .pb-detail card) is the real "outside" click. */
    if (dialog) {
        dialog.addEventListener('click', function (e) {
            if (e.target === dialog) closeModal();
        });
    }

    /* ------------------------------------------------------------- tabs */
    function resetTabs(detail) {
        // Every project opens on its Overview tab for consistency.
        activateTab(detail, 'overview', false);
    }

    function activateTab(detail, key, focus) {
        var tabs = Array.prototype.slice.call(detail.querySelectorAll('[data-pb-tab]'));
        var panels = Array.prototype.slice.call(detail.querySelectorAll('[data-pb-panel]'));
        tabs.forEach(function (t) {
            var on = t.getAttribute('data-pb-tab') === key;
            t.classList.toggle('is-active', on);
            t.setAttribute('aria-selected', on ? 'true' : 'false');
            t.tabIndex = on ? 0 : -1;
            if (on && focus) t.focus();
        });
        panels.forEach(function (p) {
            var on = p.getAttribute('data-pb-panel') === key;
            p.classList.toggle('is-active', on);
            p.hidden = !on;
            // Make the active panel focusable (APG) so panels without focusable
            // content are still reachable/scrollable and give the focus trap a
            // reliable last boundary.
            if (on) { p.setAttribute('tabindex', '0'); } else { p.removeAttribute('tabindex'); }
        });
    }

    if (modal) {
        modal.addEventListener('click', function (e) {
            var tab = e.target.closest('[data-pb-tab]');
            if (tab) {
                var detail = tab.closest('[data-detail]');
                activateTab(detail, tab.getAttribute('data-pb-tab'), false);
                return;
            }
            var goto = e.target.closest('[data-pb-goto-tab]');
            if (goto) {
                var d = goto.closest('[data-detail]');
                activateTab(d, goto.getAttribute('data-pb-goto-tab'), true);
            }
        });

        /* Arrow-key navigation within a tablist (ARIA tabs pattern) */
        modal.addEventListener('keydown', function (e) {
            var tab = e.target.closest('[data-pb-tab]');
            if (!tab) return;
            if (['ArrowRight', 'ArrowLeft', 'Home', 'End'].indexOf(e.key) === -1) return;
            e.preventDefault();
            var detail = tab.closest('[data-detail]');
            var tabs = Array.prototype.slice.call(detail.querySelectorAll('[data-pb-tab]'));
            var idx = tabs.indexOf(tab);
            var next = idx;
            if (e.key === 'ArrowRight') next = (idx + 1) % tabs.length;
            else if (e.key === 'ArrowLeft') next = (idx - 1 + tabs.length) % tabs.length;
            else if (e.key === 'Home') next = 0;
            else if (e.key === 'End') next = tabs.length - 1;
            activateTab(detail, tabs[next].getAttribute('data-pb-tab'), true);
        });
    }

    /* Deep link: /petec/work#project-slug opens that project on load. */
    function openFromHash() {
        var slug = (window.location.hash || '').replace('#', '');
        if (slug && detailFor(slug)) openModal(slug, null);
    }

    render();
    openFromHash();
})();
