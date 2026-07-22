/* PS-COMMUNITY-TABS-001 — Community's two-view, no-reload tab shell.
   Feed and The Break are real links without JavaScript. Normal activation
   swaps the already-rendered panels, maintains the bookmarked URL and browser
   history, and keeps roving tab focus inside the two-item tablist. */
(function () {
  'use strict';

  var root = document.querySelector('[data-community-tabs]');
  if (!root) { return; }

  var TAB_KEYS = ['feed', 'break'];
  var URLS = {
    feed: root.getAttribute('data-feed-url'),
    break: root.getAttribute('data-break-url')
  };
  var COPY = {
    feed: { title: 'Feed', subtitle: 'What people are building, learning, and living.' },
    break: { title: 'The Break', subtitle: 'Step away. Recharge. Come back with more you.' }
  };
  var allTriggers = Array.prototype.slice.call(root.querySelectorAll('[data-comm-tab]'));
  var tabs = allTriggers.filter(function (trigger) { return trigger.getAttribute('role') === 'tab'; });
  var panels = Array.prototype.slice.call(root.querySelectorAll('[data-tab-panel]'));
  var pageTitleEl = document.getElementById('pageTitle');
  var pageSubtitleEl = document.getElementById('pageSubtitle');
  var announcer = document.getElementById('announcer');

  function announce(message) {
    if (!announcer) { return; }
    announcer.textContent = '';
    window.setTimeout(function () { announcer.textContent = message; }, 40);
  }

  function validTab(key) {
    return TAB_KEYS.indexOf(key) !== -1 ? key : 'feed';
  }

  function currentTab() {
    return validTab(root.getAttribute('data-active-tab') || root.getAttribute('data-initial-tab'));
  }

  function tabFor(key) {
    return tabs.filter(function (tab) { return tab.getAttribute('data-comm-tab') === key; })[0];
  }

  function pathTab() {
    return /\/the-slate\/break\/?$/.test(window.location.pathname) ? 'break' : 'feed';
  }

  function hydrateDeferredMedia(tabKey) {
    if (tabKey !== 'break') { return; }
    root.querySelectorAll('[data-deferred-src]').forEach(function (image) {
      image.setAttribute('src', image.getAttribute('data-deferred-src'));
      image.setAttribute('srcset', image.getAttribute('data-deferred-srcset'));
      image.setAttribute('sizes', image.getAttribute('data-deferred-sizes'));
      var isHero = image.classList.contains('bk-hero__image');
      image.setAttribute('loading', isHero ? 'eager' : 'lazy');
      image.setAttribute('fetchpriority', isHero ? 'high' : 'low');
      image.removeAttribute('data-deferred-src');
      image.removeAttribute('data-deferred-srcset');
      image.removeAttribute('data-deferred-sizes');
    });
  }

  function setTab(key, options) {
    var opts = options || {};
    var next = validTab(key);
    if (!URLS[next]) { return false; }

    hydrateDeferredMedia(next);
    panels.forEach(function (panel) {
      panel.hidden = panel.getAttribute('data-tab-panel') !== next;
    });
    tabs.forEach(function (tab) {
      var active = tab.getAttribute('data-comm-tab') === next;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    if (pageTitleEl) { pageTitleEl.textContent = COPY[next].title; }
    if (pageSubtitleEl) { pageSubtitleEl.textContent = COPY[next].subtitle; }
    document.title = COPY[next].title + ' · Community | PeerSlate';
    root.setAttribute('data-active-tab', next);

    if (opts.updateUrl && window.location.pathname !== URLS[next]) {
      window.history.pushState({ communityTab: next }, '', URLS[next]);
    }
    if (opts.focus) {
      var nextTab = tabFor(next);
      if (nextTab) { nextTab.focus(); }
    }
    if (opts.announce !== false) { announce(COPY[next].title + ' selected.'); }
    return true;
  }

  allTriggers.forEach(function (trigger) {
    trigger.addEventListener('click', function (event) {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey ||
          event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      event.preventDefault();
      var next = validTab(trigger.getAttribute('data-comm-tab'));
      setTab(next, { updateUrl: next !== currentTab(), focus: false });
    });
  });

  tabs.forEach(function (tab) {
    tab.addEventListener('keydown', function (event) {
      var index = TAB_KEYS.indexOf(tab.getAttribute('data-comm-tab'));
      var next = null;
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        next = TAB_KEYS[(index + 1) % TAB_KEYS.length];
      } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        next = TAB_KEYS[(index - 1 + TAB_KEYS.length) % TAB_KEYS.length];
      } else if (event.key === 'Home') {
        next = TAB_KEYS[0];
      } else if (event.key === 'End') {
        next = TAB_KEYS[TAB_KEYS.length - 1];
      }
      if (!next) { return; }
      event.preventDefault();
      setTab(next, { updateUrl: next !== currentTab(), focus: true });
    });
  });

  var createPost = root.querySelector('[data-comm-create-post]');
  if (createPost) {
    createPost.addEventListener('click', function () {
      setTab('feed', { updateUrl: currentTab() !== 'feed', focus: false, announce: false });
      window.requestAnimationFrame(function () {
        var composer = root.querySelector('[data-tab-panel="feed"] [data-open-composer]');
        if (composer) {
          composer.focus();
          announce('Feed selected. The post composer is ready.');
        } else {
          announce('Feed selected.');
        }
      });
    });
  }

  root.querySelectorAll('[data-mood]').forEach(function (option) {
    option.addEventListener('click', function () {
      root.querySelectorAll('[data-mood]').forEach(function (mood) {
        var active = mood === option;
        mood.classList.toggle('is-active', active);
        mood.setAttribute('aria-pressed', String(active));
      });
      announce(option.querySelector('strong').textContent + ' mood selected for this page only.');
    });
  });

  window.addEventListener('popstate', function () {
    setTab(pathTab(), { updateUrl: false, focus: false, announce: true });
  });

  setTab(validTab(root.getAttribute('data-initial-tab')), { updateUrl: false, focus: false, announce: false });
})();
