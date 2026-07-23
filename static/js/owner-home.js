// owner-home.js — PS-HOME-FRONTEND-001 progressive enhancement ONLY.
//
// The server-rendered page in owner_home.html is complete and fully
// functional without this file: every link is a real destination, and the
// one Retry control on a complete Home-data failure is a plain safe GET to
// /app. This script only smooths that same retry in place for browsers with
// JavaScript — it re-fetches the same bounded owner route (never a broader
// dataset, never the legacy /api/dashboard contract), swaps in the fresh
// server-rendered result, moves focus to the new heading, and announces
// completion once. It persists nothing (no localStorage/sessionStorage/
// IndexedDB) and never turns a "Coming later" preview into a request.
(function () {
    'use strict';

    document.addEventListener('click', function (event) {
        // Leave every browser-native alternative activation alone: modifier
        // keys, middle clicks, downloads, named targets, and a click another
        // handler already claimed must keep their ordinary link behavior.
        if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
        ) {
            return;
        }

        if (!event.target || typeof event.target.closest !== 'function') {
            return;
        }

        var link = event.target.closest('[data-oh-retry]');
        var target = link && link.getAttribute('target');
        if (
            !link ||
            link.getAttribute('aria-busy') === 'true' ||
            link.hasAttribute('download') ||
            (target && target.toLowerCase() !== '_self')
        ) {
            return;
        }
        event.preventDefault();
        retry(link);
    });

    function announce(message) {
        var region = document.getElementById('oh-live-region');
        if (!region) {
            return;
        }
        region.textContent = '';
        window.setTimeout(function () {
            region.textContent = message;
        }, 30);
    }

    function retry(link) {
        var destination = link.getAttribute('href');
        link.setAttribute('aria-busy', 'true');
        announce('Retrying Owner Home.');

        fetch(destination, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'fetch' }
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Owner Home retry failed.');
                }
                return response.text();
            })
            .then(function (html) {
                var parsed = new DOMParser().parseFromString(html, 'text/html');
                var freshRoot = parsed.querySelector('.oh');
                var freshNav = parsed.querySelector('.oh-bottomnav');
                var currentRoot = document.querySelector('.oh');
                var currentNav = document.querySelector('.oh-bottomnav');
                if (!freshRoot || !currentRoot) {
                    window.location.assign(destination);
                    return;
                }

                currentRoot.replaceWith(freshRoot);
                if (freshNav && currentNav) {
                    currentNav.replaceWith(freshNav);
                }
                if (parsed.title) {
                    document.title = parsed.title;
                }

                var heading = freshRoot.querySelector('h1');
                if (heading) {
                    heading.setAttribute('tabindex', '-1');
                    heading.focus();
                }
                announce('Owner Home updated.');
            })
            .catch(function () {
                // Bounded backoff of exactly one JS attempt, then the same
                // safe fallback a no-JS browser already uses.
                window.location.assign(destination);
            })
            .finally(function () {
                link.removeAttribute('aria-busy');
            });
    }
})();
