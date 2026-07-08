// mobile-nav.js — phone navigation helpers (2026-07-08).
// 1) Ask Pete AI is always available in the header: the [data-open-chat]
//    button opens the chat panel from anywhere.
// 2) A bottom tab bar mirrors the page's primary section tabs (the profile
//    tabs on portfolio pages, or The Slate tabs on the hub) so phone users
//    can move between sections without scrolling back to the top. It reveals
//    when scrolling up and tucks away when scrolling down.
// Browser-only; no secrets, no network.

(function () {
    'use strict';

    /* ---- Ask Pete AI opener (header, all sizes) ---- */
    document.querySelectorAll('[data-open-chat]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            // Click the floating launcher — it opens the chat panel WITHOUT
            // sending anything (askPeteAI() would submit an empty message).
            var toggle = document.getElementById('chat-toggle');
            if (toggle) {
                toggle.click();
            } else if (typeof window.askPeteAI === 'function') {
                window.askPeteAI('');
            }
        });
    });

    /* ---- Bottom tab bar ---- */
    var bar = document.getElementById('mobile-tabbar');
    var source = document.querySelector('[data-mobile-tabsource]');
    if (!bar || !source) { return; }

    // Clone each tab link into the bottom bar (text + href + active state).
    var links = source.querySelectorAll('a[href]');
    if (!links.length) { return; }

    links.forEach(function (link) {
        var a = document.createElement('a');
        a.href = link.getAttribute('href');
        a.className = 'mobile-tabbar__item';
        if (link.hasAttribute('aria-current')) {
            a.setAttribute('aria-current', 'page');
        }
        // Label = the link's visible text (icons in the source are decorative).
        a.textContent = link.textContent.trim();
        bar.appendChild(a);
    });

    bar.hidden = false;
    // Flag the page so CSS can let the top header scroll away here (the
    // bottom bar handles section nav). Pages WITHOUT a bottom bar keep the
    // header pinned at the top instead — see the mobile header rules.
    document.body.classList.add('has-mobile-tabbar');

    // Reveal on scroll-up, hide on scroll-down (and always show near the top
    // of the page). Uses a small threshold so tiny scrolls don't flicker.
    var lastY = window.pageYOffset;
    var shown = true;
    var ticking = false;

    function setShown(next) {
        if (next === shown) { return; }
        shown = next;
        bar.classList.toggle('is-hidden', !shown);
    }

    function onScroll() {
        var y = window.pageYOffset;
        var delta = y - lastY;

        if (y < 120) {
            setShown(true);
        } else if (delta > 6) {
            setShown(false);           // scrolling down
        } else if (delta < -6) {
            setShown(true);            // scrolling up
        }

        lastY = y;
        ticking = false;
    }

    window.addEventListener('scroll', function () {
        if (!ticking) {
            window.requestAnimationFrame(onScroll);
            ticking = true;
        }
    }, { passive: true });
})();
