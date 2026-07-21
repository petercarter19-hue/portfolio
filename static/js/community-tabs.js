/* PS-COMMUNITY-TABS-001 — Community tab shell (Sonnet, 2026-07-21).
   Adopts the LIVE Interview Studio interaction pattern: every panel's full
   markup already exists in the page (server-rendered, see the_slate.html),
   so switching Feed / The Break / Saved only toggles which panel is
   [hidden] and pushes the real, bookmarkable URL — never a page reload.
   Mirrors static/js/interview-studio.js's setMode()/popstate handling. */
(function () {
  'use strict';

  var root = document.querySelector('[data-community-tabs]');
  if (!root) { return; }

  var TAB_KEYS = ['feed', 'break', 'saved'];
  var URLS = {
    feed: root.getAttribute('data-feed-url'),
    break: root.getAttribute('data-break-url'),
    saved: root.getAttribute('data-saved-url')
  };
  var COPY = {
    feed: { title: 'Feed', subtitle: 'What people are building, learning, and living.' },
    break: { title: 'The Break', subtitle: 'Step away. Recharge. Come back with more you.' },
    saved: { title: 'Saved', subtitle: 'Notes you’ve kept for later, all in one place.' }
  };

  // Real ARIA tabs (the persistent Feed / The Break / Saved pill) get the
  // full role=tab bookkeeping (aria-selected, roving tabindex). Plain
  // in-content shortcuts that also switch tabs — e.g. Break's "Back to the
  // Feed" — share data-comm-tab for the click behavior below but are not
  // part of the tablist itself.
  var allTriggers = Array.prototype.slice.call(root.querySelectorAll('[data-comm-tab]'));
  var tabs = allTriggers.filter(function (link) { return link.getAttribute('role') === 'tab'; });
  var panels = Array.prototype.slice.call(root.querySelectorAll('[data-tab-panel]'));
  var pageTitleEl = document.getElementById('pageTitle');
  var pageSubtitleEl = document.getElementById('pageSubtitle');
  var announcer = document.getElementById('announcer');

  function announce(message) {
    if (!announcer) { return; }
    announcer.textContent = '';
    window.setTimeout(function () { announcer.textContent = message; }, 40);
  }

  function tabFor(key) {
    return tabs.filter(function (link) { return link.getAttribute('data-comm-tab') === key; });
  }

  function currentTab() {
    return root.getAttribute('data-active-tab') || root.getAttribute('data-initial-tab') || 'feed';
  }

  function pathTab() {
    var path = window.location.pathname;
    if (/\/the-slate\/break\/?$/.test(path)) { return 'break'; }
    if (/\/the-slate\/saved\/?$/.test(path)) { return 'saved'; }
    return 'feed';
  }

  function setTab(key, options) {
    var opts = options || {};
    if (TAB_KEYS.indexOf(key) === -1) { key = 'feed'; }
    if (!URLS[key]) { return false; }

    panels.forEach(function (panel) {
      panel.hidden = panel.getAttribute('data-tab-panel') !== key;
    });

    tabs.forEach(function (link) {
      var linkKey = link.getAttribute('data-comm-tab');
      var active = linkKey === key;
      link.classList.toggle('active', active);
      link.setAttribute('aria-selected', active ? 'true' : 'false');
      link.tabIndex = active ? 0 : -1;
    });

    if (pageTitleEl) { pageTitleEl.textContent = COPY[key].title; }
    if (pageSubtitleEl) { pageSubtitleEl.textContent = COPY[key].subtitle; }
    document.title = COPY[key].title + ' · Community | PeerSlate';

    root.setAttribute('data-active-tab', key);

    if (opts.updateUrl) {
      window.history.pushState({ communityTab: key }, '', URLS[key]);
    }
    if (opts.focus) {
      var target = tabFor(key)[0];
      if (target) { target.focus(); }
    }
    announce(COPY[key].title + ' selected.');
    return true;
  }

  allTriggers.forEach(function (link) {
    link.addEventListener('click', function (event) {
      // Real, same-origin links stay real links (progressive enhancement,
      // right-click / open-in-new-tab / no-JS all keep working) — only a
      // plain left click is intercepted for the instant, no-reload swap.
      if (event.defaultPrevented || event.button !== 0 || event.metaKey ||
          event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      var key = link.getAttribute('data-comm-tab');
      event.preventDefault();
      if (key === currentTab()) { return; }
      setTab(key, { updateUrl: true, focus: false });
    });
  });

  tabs.forEach(function (link) {
    link.addEventListener('keydown', function (event) {
      var delta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
      if (!delta) { return; }
      event.preventDefault();
      var order = TAB_KEYS;
      var idx = order.indexOf(link.getAttribute('data-comm-tab'));
      var next = order[(idx + delta + order.length) % order.length];
      setTab(next, { updateUrl: true, focus: true });
    });
  });

  window.addEventListener('popstate', function () {
    setTab(pathTab(), { updateUrl: false, focus: false });
  });

  root.setAttribute('data-active-tab', root.getAttribute('data-initial-tab') || 'feed');
})();
