/* Canonical PeerSlate Community frontend.
   The page keeps representative content and browser-only interactions honest
   until the protected Journal, Feed, and News services are connected. */
(function () {
  'use strict';

  var APP_ROOT = document.getElementById('feed-app');
  var ASSET_BASE = (APP_ROOT && APP_ROOT.getAttribute('data-asset-base')) || '/static/images/feed';
  var BOARD_URL = (APP_ROOT && APP_ROOT.getAttribute('data-board-url')) || '/petec/slate-board';
  var JOURNAL_NOTE_KEY = 'peerslateCommunityJournalNoteV1:petec-preview';
  var JOURNAL_DRAFTS_KEY = 'peerslateJournalDraftsV1:petec-preview';
  var BOARD_INBOX_KEY = 'peerslateSlateBoardInboxV1:petec-preview';
  var REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* The site's sticky global header owns the top of every page. Measure its
     real height so the private Journal Note rail sits beneath it on desktop. */
  function syncHeaderHeight() {
    var header = document.querySelector('.global-header');
    if (header && APP_ROOT) {
      APP_ROOT.style.setProperty('--site-header-h', header.offsetHeight + 'px');
    }
  }
  syncHeaderHeight();
  window.addEventListener('resize', syncHeaderHeight);

  /* style.css makes <body> the page's scroll container (overflow:hidden auto),
     so window.scrollTo is a no-op here — scroll whichever container moves. */
  function scrollFeedToTop() {
    var behavior = REDUCED ? 'auto' : 'smooth';
    window.scrollTo({ top: 0, behavior: behavior });
    document.body.scrollTo({ top: 0, behavior: behavior });
  }

  /* ---------- helpers ---------- */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function icon(name, cls, strokeWidth) {
    return '<svg class="icon' + (cls ? ' ' + cls : '') + '" fill="none" stroke="currentColor" stroke-width="' +
      (strokeWidth || '1.8') + '" aria-hidden="true"><use href="#i-' + name + '"/></svg>';
  }

  function avatar(initials, color, size) {
    return '<div class="avatar av-' + color + (size ? ' ' + size : '') + '" aria-hidden="true">' + esc(initials) + '</div>';
  }

  function announce(message) {
    var region = document.getElementById('announcer');
    region.textContent = '';
    window.setTimeout(function () { region.textContent = message; }, 40);
  }

  /* ---------- fixture data (contract-shaped demo content) ---------- */

  var POSTS_DEFAULT = [
    {
      id: 'p-pete-dinner', initials: 'PC', color: 'pc', name: 'Pete Carter',
      kind: 'Personal moment', dot: 'amber', time: 'Just now', audience: 'Connections',
      title: 'Dinner has been served!',
      image: 'dinner_served.jpg', badge: 'Outside work',
      alt: 'A candlelit dinner table set for two — lasagna on gray plates, woven placemats, a striped runner, roses in a vase, and a handwritten Carter’s Kitchen menu.'
    },
    {
      id: 'p-danielle-review', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Work update', dot: '', time: '2h', audience: 'Connections',
      title: 'The design review finally clicked today.',
      copy: 'We stopped debating screens and mapped the actual handoff. That one change made the entire workflow easier to explain—and much easier to build.',
      image: 'work_whiteboard.jpg', badge: 'Project Phoenix',
      alt: 'Danielle pointing at a whiteboard covered in workflow sketches during a design review.',
      linkline: '▣ &nbsp; From Danielle’s Journal &nbsp;·&nbsp; <strong>Linked to Project Phoenix</strong>'
    },
    {
      id: 'p-marcus-surf', initials: 'MR', color: 'mr', name: 'Marcus Rivera',
      kind: 'Personal moment', dot: 'amber', time: '4h', audience: 'Community',
      title: 'Got in the water before the workday.',
      copy: 'I’m not calling it balance yet, but this was a pretty good start.',
      image: 'surf_morning.jpg', badge: 'Video · Outside work', video: true, duration: '0:38',
      alt: 'A surfer riding a small wave at sunrise before work.'
    },
    {
      id: 'p-aisha-meeting', initials: 'AP', color: 'ap', name: 'Aisha Patel',
      kind: 'Reflection', dot: 'cyan', time: '5h', audience: 'Community',
      title: 'The meeting went better when I stopped trying to win it.',
      copy: 'The useful part was hearing what the other person was actually worried about. I’m writing that down before I forget it.',
      voice: true, voiceDuration: '1:12'
    }
  ];

  var POSTS_GALLERY = [
    {
      id: 'p-jordan-keyboard', initials: 'JL', color: 'jl', name: 'Jordan Lee',
      kind: 'Personal project', dot: 'green', time: '46m', audience: 'Community',
      title: 'The keyboard build is finally alive.',
      copy: 'It took three soldering attempts and one very patient Saturday, but every key works. I learned more about debugging from this than I expected.',
      gallery: ['keyboard_build.jpg', 'coffee_notes.jpg', 'office_prototype.jpg'],
      galleryAlts: ['A custom mechanical keyboard mid-assembly.', 'Coffee beside handwritten build notes.', 'A prototype laid out on an office desk.'],
      linkline: '▣ &nbsp; 3 photos &nbsp;·&nbsp; Personal project'
    },
    {
      id: 'p-danielle-screens', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Project update', dot: '', time: '3h', audience: 'Connections',
      title: 'A few screens from today’s prototype review.',
      copy: 'The final layout is simpler than the version we started with. That is the point.',
      gallery: ['office_prototype.jpg', 'whiteboard_close.jpg', 'work_whiteboard.jpg'],
      galleryAlts: ['A prototype laid out on an office desk.', 'A close-up of whiteboard workflow notes.', 'Danielle pointing at a whiteboard workflow sketch.'],
      linkline: '▣ &nbsp; Project Phoenix · 3 photos'
    }
  ];

  var POSTS_VIDEO = [
    {
      id: 'p-marcus-video', initials: 'MR', color: 'mr', name: 'Marcus Rivera',
      kind: 'Personal moment', dot: 'amber', time: '38 min', audience: 'Connections',
      title: 'Morning surf before the workday.',
      copy: 'Not everything worth remembering happens at a desk.',
      image: 'surf_morning.jpg', badge: 'Video', video: true, duration: '0:38',
      alt: 'A surfer riding a small wave at sunrise before work.'
    },
    {
      id: 'p-danielle-walkthrough', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Work update', dot: '', time: '2h', audience: 'Connections',
      title: 'The handoff no longer needs a walkthrough.',
      copy: 'We reduced the number of choices, exposed the owner at each step, and made the next action obvious.',
      image: 'work_whiteboard.jpg', badge: 'Project Phoenix',
      alt: 'Danielle pointing at a whiteboard covered in workflow sketches.'
    }
  ];

  var POSTS_RAIL = [
    POSTS_VIDEO[0],
    {
      id: 'p-danielle-prototype', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Project update', dot: '', time: '2h', audience: 'Connections',
      title: 'We finally have a prototype people can understand without a walkthrough.',
      copy: 'The breakthrough was removing choices, not adding features.',
      gallery: ['office_prototype.jpg', 'whiteboard_close.jpg', 'work_whiteboard.jpg'],
      galleryAlts: ['A prototype laid out on an office desk.', 'A close-up of whiteboard workflow notes.', 'Danielle pointing at a whiteboard workflow sketch.']
    }
  ];

  var DETAIL_POST = {
    id: 'p-danielle-detail', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
    kind: 'Work update', dot: '', time: '1h', audience: 'Connections',
    title: 'We changed the handoff after today’s review.',
    copy: 'The team was not asking for more documentation. They needed one clear decision point and a visible owner. That is what we are testing next.',
    image: 'work_whiteboard.jpg', badge: 'Project Phoenix',
    alt: 'Danielle pointing at a whiteboard covered in workflow sketches.'
  };

  var DETAIL_COMMENTS = [
    { initials: 'AK', color: 'ak', name: 'Alex Kim', time: '42 min',
      copy: 'This is exactly where our last handoff broke down. I can share the checklist we ended up using.', offerHelp: true },
    { initials: 'AP', color: 'ap', name: 'Aisha Patel', time: '27 min',
      copy: 'The visible owner is the important part. We had the same issue in a review last month.', offerHelp: false },
    { initials: 'MR', color: 'mr', name: 'Marcus Rivera', time: '11 min',
      copy: 'Would it help to test the flow with someone who has not seen the project before?', offerHelp: true }
  ];

  var TRANSCRIPT_LIVE = '“I finally got the prototype to a place where the team understood the handoff without me explaining every screen…”';
  var TRANSCRIPT_FULL = 'I finally got the prototype to a place where the team understood the handoff without me explaining every screen. We stopped debating individual pages and mapped the actual handoff.';

  var PROPOSAL = {
    reviewTitle: 'The handoff finally became clear.',
    publishTitle: 'We removed choices and the workflow finally clicked.',
    copy: 'We stopped debating screens and mapped the actual handoff. That one decision made the workflow easier to explain—and easier to build.'
  };

  var SUBTITLES = {
    'default': 'What people are building, learning, and living.',
    news: 'Trusted stories and useful context, kept separate from member updates.',
    gallery: 'Real work, real life, and the moments in between.',
    video: 'Photos and video should feel native—not bolted onto a text feed.',
    rail: 'A living view of the people and moments that matter to you.',
    empty: 'A calm feed is allowed to end.',
    loading: 'Fast, quiet loading with no fake content.',
    error: 'Clear recovery without losing the user’s place.',
    detail: 'Useful replies, context, and help—without turning the Feed into a debate stage.'
  };

  /* ---------- application state ---------- */

  var state = {
    composition: 'default',       // default | gallery | video | rail
    tab: 'feed',                  // feed | news
    view: 'feed',                 // feed | detail | loading | error
    detailPost: null,
    draft: { transcript: TRANSCRIPT_FULL, audience: 'community', connections: { phoenix: true, goal: false, source: false } },
    reactions: {},                // postId -> true
    saves: {},                    // postId -> true
    publishedPosts: [],           // fixture posts added through the publish flow
    detailExtraComments: []
  };

  var feedColumn = document.getElementById('feedColumn');
  var contextRail = document.getElementById('contextRail');
  var pageTitle = document.getElementById('pageTitle');
  var pageSubtitle = document.getElementById('pageSubtitle');
  var overlayRoot = document.getElementById('overlayRoot');
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.feed-tab'));

  /* ---------- render helpers (ported from the handoff build script) ---------- */

  function composerHTML(text) {
    return '<div class="composer">' + avatar('PC', 'pc', 'sm') +
      '<button class="composer-input" type="button" data-open-composer>' + esc(text || 'Talk about what happened…') + '</button>' +
      '<div class="composer-actions">' +
      '<button class="pill-btn" type="button" data-open-composer data-with-media>' + icon('image', 'sm') + ' Photo / video</button>' +
      '<button class="mic-btn" type="button" data-open-voice aria-label="Talk about what happened — start voice capture">' + icon('mic', '', '1.9') + '</button>' +
      '</div></div>';
  }

  var RESPOND_INTENTIONS = [
    { key: 'celebrate', label: 'Celebrate' },
    { key: 'support', label: 'Support' },
    { key: 'i_relate', label: 'I relate' },
    { key: 'ask', label: 'Ask' },
    { key: 'offer_help', label: 'Offer help' }
  ];

  function actionRowHTML(post) {
    var chosen = state.reactions[post.id] || null;
    var chosenLabel = null;
    RESPOND_INTENTIONS.forEach(function (item) {
      if (item.key === chosen) { chosenLabel = item.label; }
    });
    var saved = !!state.saves[post.id];
    var tray = RESPOND_INTENTIONS.map(function (item) {
      return '<button class="respond-option" type="button" data-respond="' + esc(post.id) +
        '" data-intent="' + item.key + '" aria-pressed="' + (chosen === item.key) + '">' +
        esc(item.label) + '</button>';
    }).join('');
    return '<div class="actions">' +
      '<button class="action primary-action" type="button" data-respond-toggle="' + esc(post.id) + '" aria-expanded="false" aria-pressed="' + (!!chosen) + '">' +
      icon('spark', 'sm') + ' ' + (chosenLabel || 'Respond') + '</button>' +
      '<button class="action" type="button" data-comment="' + esc(post.id) + '">' + icon('comment', 'sm') + ' Comment</button>' +
      '<button class="action save" type="button" data-save="' + esc(post.id) + '" aria-pressed="' + saved + '">' + icon('bookmark', 'sm') + ' ' + (saved ? 'Saved' : 'Save') + '</button>' +
      '</div>' +
      '<div class="respond-tray" data-respond-tray="' + esc(post.id) + '" hidden role="group" aria-label="Respond with an intention">' + tray + '</div>';
  }

  function mediaHTML(post) {
    if (post.gallery) {
      var imgs = post.gallery.slice(0, 3).map(function (file, i) {
        var alt = (post.galleryAlts && post.galleryAlts[i]) || '';
        return '<img class="g' + (i + 1) + '" src="' + ASSET_BASE + '/' + file + '" alt="' + esc(alt) + '">';
      }).join('');
      return '<div class="gallery">' + imgs + '</div>';
    }
    if (!post.image) { return ''; }
    var badge = post.badge ? '<div class="media-badge">' + esc(post.badge) + '</div>' : '';
    if (post.video) {
      return '<div class="media video"><img src="' + ASSET_BASE + '/' + post.image + '" alt="' + esc(post.alt || '') + '">' + badge +
        '<div class="media-overlay"></div>' +
        '<button class="play" type="button" data-play="' + esc(post.id) + '" aria-label="Play video: ' + esc(post.title) + ' (' + esc(post.duration) + ')"></button>' +
        '<div class="video-caption"><h3>' + esc(post.title) + '</h3><p>' + esc(post.copy || 'A real moment shared in the member’s own voice.') + '</p></div>' +
        '<div class="duration">' + esc(post.duration) + '</div></div>';
    }
    return '<div class="media landscape"><img src="' + ASSET_BASE + '/' + post.image + '" alt="' + esc(post.alt || '') + '">' + badge + '</div>';
  }

  function voicePlayerHTML(post) {
    var bars = new Array(38 + 1).join('<span></span>');
    return '<div class="voice-player"><button class="voice-play" type="button" data-play-voice="' + esc(post.id) + '" aria-label="Play voice note (' + esc(post.voiceDuration) + ')">▶</button>' +
      '<div class="wave" aria-hidden="true">' + bars + '</div><strong class="voice-time">' + esc(post.voiceDuration) + '</strong></div>';
  }

  function postHTML(post, options) {
    options = options || {};
    var meta = '<span class="dot' + (post.dot ? ' ' + post.dot : '') + '"></span> ' + esc(post.metaOverride || post.kind) +
      ' &nbsp; ' + esc(post.time) + (post.audience && !post.metaOverride ? ' &nbsp; ' + esc(post.audience) : '');
    var body = '';
    if (!post.video) {
      body += '<h2 class="post-title' + (post.editorial ? ' editorial' : '') + '">' + esc(post.title) + '</h2>';
      if (post.copy) { body += '<p class="post-copy">' + esc(post.copy) + '</p>'; }
    }
    body += mediaHTML(post);
    if (post.voice) { body += voicePlayerHTML(post); }
    if (post.linkline) { body += '<div class="post-linkline">' + post.linkline + '</div>'; }
    if (options.actions !== false) { body += actionRowHTML(post); }
    return '<article class="post' + (options.justPublished ? ' just-published' : '') + '" data-post="' + esc(post.id) + '">' +
      '<div class="post-head">' + avatar(post.initials, post.color) +
      '<div class="post-author"><div class="author-name">' + esc(post.name) + '</div><div class="author-meta">' + meta + '</div></div>' +
      '<span class="more" aria-hidden="true">···</span></div>' +
      '<div class="post-body">' + body + '</div></article>';
  }

  function readStoredValue(key, fallback) {
    try { return localStorage.getItem(key) || fallback; }
    catch (error) { return fallback; }
  }

  function journalNoteRailHTML() {
    return '<section class="rail-panel journal-note-card">' +
      '<div class="rail-title"><div><span class="rail-kicker">Only you</span><h2>Journal Note</h2></div><div class="spark">' + icon('shield') + '</div></div>' +
      '<p class="rail-prompt">Anything happen today you may want to remember?</p>' +
      '<label class="sr-only" for="communityJournalNote">Private Journal Note</label>' +
      '<textarea id="communityJournalNote" maxlength="1000" rows="8" placeholder="Write a private note…">' + esc(readStoredValue(JOURNAL_NOTE_KEY, '')) + '</textarea>' +
      '<p class="rail-save-state" id="journalNoteStatus">Saved in this browser</p>' +
      '<div class="rail-note-actions">' +
        '<button class="btn primary" type="button" data-note-journal>Add to Journal</button>' +
        '<button class="btn soft" type="button" data-note-board>Add to Slate Board</button>' +
        '<button class="rail-clear" type="button" data-note-clear>Clear</button>' +
      '</div>' +
      '<p class="rail-service-note">Browser-only until sign-in and protected storage are connected.</p>' +
      '</section>';
  }

  function newsHTML() {
    return '<section class="news-state" aria-labelledby="news-state-title">' +
      '<span class="news-state__eyebrow">News Feed</span>' +
      '<h2 id="news-state-title">Ready for a trusted news source</h2>' +
      '<p>This mode now has a permanent home in Community. No provider is connected yet, so PeerSlate is not showing invented headlines or stale sample stories.</p>' +
      '<div class="news-state__requirements"><strong>Before launch</strong><span>Approve sources, attribution, licensing, freshness, moderation, and failure behavior.</span></div>' +
      '</section>';
  }

  function skeletonHTML() {
    var post = '<article class="post"><div class="post-head"><div class="avatar"></div><div class="post-author"><div class="sk"></div>' +
      '<div class="author-meta"><span class="sk" style="display:block;width:120px;height:9px"></span></div></div></div>' +
      '<div class="post-body"><div class="post-title sk"></div><div class="line sk"></div><div class="line sk" style="width:85%"></div>' +
      '<div class="media landscape"></div></div></article>';
    return composerHTML('Loading your Feed…') + '<div class="date-label">Today</div>' +
      '<div class="skeleton" aria-hidden="true">' + post + post + post + '</div>';
  }

  function emptyHTML() {
    return composerHTML() +
      '<div class="empty-state"><div class="empty-illustration" aria-hidden="true"></div>' +
      '<h2>You’re caught up.</h2>' +
      '<p>There are no new member updates right now. Capture something from your week, or return to a saved conversation.</p>' +
      '<button class="btn primary" type="button" data-open-voice>' + icon('mic', 'sm', '1.9') + ' Talk about what happened</button></div>';
  }

  function errorHTML() {
    var cached = Object.assign({}, POSTS_DEFAULT[0], {
      metaOverride: 'Previously loaded', audience: '',
      copy: 'This previously loaded post remains visible while the refresh is retried.'
    });
    return composerHTML() +
      '<div class="error-panel"><div class="error-icon" aria-hidden="true">!</div><div>' +
      '<h2>We couldn’t refresh the Feed.</h2>' +
      '<p>Your drafts and captures are safe. Check the connection and try again. PeerSlate should never replace a real error with an empty success state.</p>' +
      '<button class="btn primary" type="button" data-retry>Try again</button> ' +
      '<a class="btn" href="' + BOARD_URL + '">Open Slate Board</a>' +
      '</div></div>' + postHTML(cached);
  }

  function detailHTML(post) {
    var comments = DETAIL_COMMENTS.concat(state.detailExtraComments).map(function (c, index) {
      var actions = '<button class="comment-action" type="button" data-comment-react="' + index + '" aria-pressed="' + (!!c.reacted) + '">Support</button>' +
        '<button class="comment-action" type="button" data-comment-reply>Reply</button>' +
        (c.offerHelp ? '<button class="offer-help" type="button" data-offer-help="' + index + '" aria-pressed="' + (!!c.offered) + '">Offer help</button>' : '');
      return '<div class="comment">' + avatar(c.initials, c.color, 'sm') +
        '<div class="comment-body"><div class="comment-head"><span class="comment-name">' + esc(c.name) + '</span><span class="comment-time">' + esc(c.time) + '</span></div>' +
        '<p class="comment-copy">' + esc(c.copy) + '</p>' +
        '<div class="comment-actions">' + actions + '</div></div></div>';
    }).join('');
    return '<button class="back-link" type="button" data-back>' + icon('arrow', 'sm') + ' Back to Feed</button>' +
      '<div class="detail-header">' + postHTML(post) + '</div>' +
      '<section class="thread" aria-label="Replies">' + comments + '</section>' +
      '<div class="comment-composer">' + avatar('PC', 'pc', 'xs') +
      '<label class="sr-only" for="replyInput">Add a useful reply</label>' +
      '<input id="replyInput" placeholder="Add a useful reply…">' +
      '<button class="mic-btn" type="button" data-open-voice aria-label="Reply by voice">' + icon('mic', '', '1.9') + '</button>' +
      '<button class="btn primary" type="button" data-send-reply>' + icon('send', 'sm') + ' Reply</button></div>';
  }

  /* ---------- top-level rendering ---------- */

  function compositionPosts() {
    switch (state.composition) {
      case 'gallery': return POSTS_GALLERY;
      case 'video': return POSTS_VIDEO;
      case 'rail': return POSTS_RAIL;
      default: return state.publishedPosts.concat(POSTS_DEFAULT);
    }
  }

  function setSubtitle(key) {
    pageSubtitle.textContent = SUBTITLES[key] || SUBTITLES['default'];
  }

  function setTabsVisual() {
    tabs.forEach(function (tab) {
      var active = (tab.getAttribute('data-tab') === state.tab);
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', active ? 'true' : 'false');
      tab.setAttribute('tabindex', active ? '0' : '-1');
    });
    feedColumn.setAttribute('aria-labelledby', state.tab === 'feed' ? 'tab-feed' : 'tab-news');
  }

  function setRail() {
    contextRail.innerHTML = journalNoteRailHTML();
    contextRail.hidden = false;
  }

  function render() {
    setTabsVisual();
    if (state.view === 'loading') {
      pageTitle.textContent = 'Feed';
      setSubtitle(state.subtitleKey || 'default');
      setRail();
      feedColumn.setAttribute('aria-busy', 'true');
      feedColumn.innerHTML = skeletonHTML();
      return;
    }
    feedColumn.removeAttribute('aria-busy');
    if (state.view === 'detail') {
      pageTitle.textContent = 'Conversation';
      setSubtitle('detail');
      setRail();
      feedColumn.innerHTML = detailHTML(state.detailPost || DETAIL_POST);
      return;
    }
    pageTitle.textContent = 'Feed';
    if (state.view === 'error') {
      setSubtitle('error');
      setRail();
      feedColumn.innerHTML = errorHTML();
      return;
    }
    if (state.tab === 'news') {
      pageTitle.textContent = 'News Feed';
      setSubtitle('news');
      setRail();
      feedColumn.innerHTML = newsHTML();
      return;
    }
    setSubtitle(state.composition);
    setRail();
    var posts = compositionPosts().map(function (post) {
      return postHTML(post, { justPublished: post === state.publishedPosts[0] && state.highlightPublished });
    }).join('');
    feedColumn.innerHTML = composerHTML() + '<div class="date-label">Today</div>' + posts;
    state.highlightPublished = false;
  }

  /* ---------- overlays ---------- */

  var activeOverlay = null;
  var overlayInvoker = null;
  var transcriptTimer = null;

  function openOverlay(html, labelledBy) {
    closeOverlay(false);
    overlayInvoker = document.activeElement;
    var overlay = document.createElement('div');
    overlay.className = 'overlay';
    overlay.innerHTML = '<section class="voice-modal" role="dialog" aria-modal="true" aria-labelledby="' + labelledBy + '">' + html + '</section>';
    overlayRoot.appendChild(overlay);
    activeOverlay = overlay;
    var preferred = overlay.querySelector('[data-autofocus]');
    if (preferred) {
      preferred.focus();
    } else {
      var focusables = overlay.querySelectorAll('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusables.length) { focusables[0].focus(); }
    }
    overlay.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { event.preventDefault(); dismissOverlay('Nothing was saved. Your draft is kept on this page until you leave it.'); return; }
      if (event.key !== 'Tab') { return; }
      var items = Array.prototype.filter.call(
        overlay.querySelectorAll('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])'),
        function (el) { return !el.disabled && el.offsetParent !== null; });
      if (!items.length) { return; }
      var first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    return overlay;
  }

  function closeOverlay(restoreFocus) {
    if (transcriptTimer) { window.clearInterval(transcriptTimer); transcriptTimer = null; }
    if (activeOverlay) {
      activeOverlay.remove();
      activeOverlay = null;
      if (restoreFocus !== false && overlayInvoker && document.contains(overlayInvoker)) { overlayInvoker.focus(); }
    }
  }

  function dismissOverlay(message) {
    closeOverlay(true);
    if (message) { announce(message); }
  }

  function openVoiceOverlay() {
    var bars = new Array(31 + 1).join('<i></i>');
    var overlay = openOverlay(
      '<header class="modal-head"><h2 id="voiceTitle">Talk about what happened</h2>' +
      '<button class="close" type="button" data-dismiss aria-label="Close">' + icon('close', '', '2') + '</button></header>' +
      '<div class="listening-body"><div class="listening-ring" aria-hidden="true">' + icon('mic', 'lg', '1.9') + '</div>' +
      '<p class="listening-title">Listening…</p>' +
      '<p class="listening-help">Speak naturally. You can edit everything before anything is saved.</p>' +
      '<div class="live-transcript"><span data-live-text></span><span class="cursor" aria-hidden="true"></span></div>' +
      '<div class="audio-level' + (REDUCED ? '' : ' live') + '" aria-hidden="true">' + bars + '</div>' +
      '<div class="modal-actions"><button class="cancel-btn" type="button" data-cancel-voice>Cancel</button>' +
      '<button class="stop-btn" type="button" data-stop-voice data-autofocus>Stop and review</button></div></div>',
      'voiceTitle');
    var target = overlay.querySelector('[data-live-text]');
    if (REDUCED) {
      target.textContent = TRANSCRIPT_LIVE;
    } else {
      var words = TRANSCRIPT_LIVE.split(' ');
      var shown = 0;
      transcriptTimer = window.setInterval(function () {
        shown += 1;
        target.textContent = words.slice(0, shown).join(' ');
        if (shown >= words.length) { window.clearInterval(transcriptTimer); transcriptTimer = null; }
      }, 260);
    }
    announce('Listening. Speak naturally — you can edit everything before anything is saved.');
  }

  function privacyOptionHTML(value, title, help) {
    var checked = state.draft.audience === value;
    return '<label class="privacy-option' + (checked ? ' selected' : '') + '">' +
      '<input type="radio" name="audience" value="' + value + '"' + (checked ? ' checked' : '') + '>' +
      '<span class="radio" aria-hidden="true"></span>' +
      '<span><strong>' + esc(title) + '</strong><span>' + esc(help) + '</span></span></label>';
  }

  function connectChipHTML(key, label) {
    var on = !!state.draft.connections[key];
    return '<button class="chip' + (on ? ' project' : '') + '" type="button" data-connect="' + key + '" aria-pressed="' + on + '">' +
      (on ? '✓ ' : '+ ') + esc(label) + '</button>';
  }

  function reviewOverlayHTML(aiStep) {
    var heading = aiStep ? 'AI-assisted publish review' : 'Review before saving';
    var proposalTitle = aiStep ? PROPOSAL.publishTitle : PROPOSAL.reviewTitle;
    var aiNote = aiStep
      ? '<div class="notice" style="margin-top:16px"><div class="symbol">' + icon('shield', 'sm') + '</div>' +
        '<div><strong style="color:#263955">Confidentiality check</strong><br>No employer, customer, or restricted details were detected. You still make the final decision.</div></div>'
      : '';
    var primaryLabel = state.draft.audience === 'private' ? 'Save privately' : 'Add update';
    return '<header class="modal-head"><h2 id="reviewTitle">' + heading + '</h2>' +
      '<button class="close" type="button" data-dismiss aria-label="Close">' + icon('close', '', '2') + '</button></header>' +
      '<div class="review-body"><div class="review-main">' +
      '<label class="field-label" for="transcriptEdit">Transcript</label>' +
      '<textarea class="transcript-box editable" id="transcriptEdit" rows="4" data-autofocus>' + esc(state.draft.transcript) + '</textarea>' +
      '<div class="proposal"><div class="proposal-head">' + icon('spark', 'sm') + ' PeerSlate proposal · editable</div>' +
      '<h3>' + esc(proposalTitle) + '</h3><p>' + esc(PROPOSAL.copy) + '</p>' +
      '<div class="chip-row"><span class="chip project">Project Phoenix</span><span class="chip">Work update</span><span class="chip ai">AI-assisted draft</span></div></div>' +
      aiNote + '</div>' +
      '<aside class="review-side"><div class="field-label" id="audienceLabel">Who can see this?</div>' +
      '<div role="radiogroup" aria-labelledby="audienceLabel">' +
      privacyOptionHTML('private', 'Keep private', 'Only you. Best for raw capture and reflection.') +
      privacyOptionHTML('connections', 'Connections', 'People you have accepted into your network.') +
      privacyOptionHTML('community', 'Community', 'Appears in Feed and your public Journal.') +
      privacyOptionHTML('selected', 'Selected people', 'Choose exactly who can see it.') +
      '</div>' +
      '<div class="field-label" style="margin-top:18px">Also connect to</div>' +
      '<div class="chip-row">' + connectChipHTML('phoenix', 'Project Phoenix') + connectChipHTML('goal', 'Goal') + connectChipHTML('source', 'Source') + '</div>' +
      '</aside>' +
      '<footer class="review-footer"><span class="meta">Original wording and source remain inspectable.</span>' +
      '<button class="cancel-btn" type="button" data-keep-editing>Keep editing</button>' +
      '<button class="btn primary" type="button" data-review-primary data-ai-step="' + (aiStep ? '1' : '0') + '">' + primaryLabel + '</button>' +
      '</footer></div>';
  }

  function openReviewOverlay(aiStep, announceText) {
    var overlay = openOverlay(reviewOverlayHTML(aiStep), 'reviewTitle');
    overlay.addEventListener('change', function (event) {
      if (event.target.name === 'audience') {
        state.draft.audience = event.target.value;
        overlay.querySelectorAll('.privacy-option').forEach(function (option) {
          option.classList.toggle('selected', option.querySelector('input').checked);
        });
        var primary = overlay.querySelector('[data-review-primary]');
        primary.textContent = state.draft.audience === 'private' ? 'Save privately' : 'Add update';
      }
    });
    overlay.addEventListener('input', function (event) {
      if (event.target.id === 'transcriptEdit') { state.draft.transcript = event.target.value; }
    });
    if (announceText) { announce(announceText); }
  }

  function publishDraft() {
    closeOverlay(true);
    if (state.draft.audience === 'private') {
      announce('Saved privately to your Journal. Nothing was published to the Feed.');
      return;
    }
    var audienceLabel = { connections: 'Connections', community: 'Community', selected: 'Selected people' }[state.draft.audience] || 'Community';
    var linked = state.draft.connections.phoenix ? ' &nbsp;·&nbsp; <strong>Linked to Project Phoenix</strong>' : '';
    state.publishedPosts.unshift({
      id: 'p-published-' + (state.publishedPosts.length + 1),
      initials: 'PC', color: 'pc', name: 'Pete Carter',
      kind: 'Work update', dot: '', time: 'Just now', audience: audienceLabel,
      title: PROPOSAL.publishTitle,
      copy: PROPOSAL.copy,
      linkline: '▣ &nbsp; From Pete’s Journal' + linked + ' &nbsp;·&nbsp; AI-assisted draft'
    });
    state.highlightPublished = true;
    state.composition = 'default';
    state.tab = 'feed';
    state.view = 'feed';
    render();
    scrollFeedToTop();
    announce('Added to this browser session for ' + audienceLabel + '. Protected publishing is connected in the backend phase.');
  }

  function updateJournalNoteStatus(message) {
    var status = document.getElementById('journalNoteStatus');
    if (status) { status.textContent = message; }
  }

  function writeBrowserValue(key, value) {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function readBrowserList(key) {
    try {
      var stored = JSON.parse(localStorage.getItem(key) || '[]');
      return Array.isArray(stored) ? stored : [];
    } catch (error) {
      return [];
    }
  }

  function currentJournalNote() {
    var input = document.getElementById('communityJournalNote');
    return input ? input.value.trim() : '';
  }

  function clearJournalNote() {
    var input = document.getElementById('communityJournalNote');
    if (input) { input.value = ''; }
    writeBrowserValue(JOURNAL_NOTE_KEY, '');
    updateJournalNoteStatus('Cleared');
  }

  function addJournalNoteTo(destination) {
    var text = currentJournalNote();
    if (!text) {
      var input = document.getElementById('communityJournalNote');
      if (input) { input.focus(); }
      announce('Write a note first. It stays private in this browser.');
      return;
    }
    var key = destination === 'board' ? BOARD_INBOX_KEY : JOURNAL_DRAFTS_KEY;
    var items = readBrowserList(key);
    items.unshift({
      id: 'community-note-' + Date.now(),
      title: text.slice(0, 80),
      description: text,
      createdAt: new Date().toISOString(),
      source: 'community-journal-note'
    });
    if (!writeBrowserValue(key, JSON.stringify(items.slice(0, 50)))) {
      updateJournalNoteStatus('Storage unavailable');
      announce('Browser storage is unavailable, so the note was not moved.');
      return;
    }
    clearJournalNote();
    if (destination === 'board') {
      updateJournalNoteStatus('Ready for Slate Board');
      announce('Private note queued for Slate Board in this browser. Open Slate Board to add it.');
    } else {
      updateJournalNoteStatus('Added to private Journal drafts');
      announce('Private Journal draft saved in this browser.');
    }
  }

  /* ---------- events ---------- */

  document.addEventListener('click', function (event) {
    var el = event.target.closest('button, a');
    if (!el) { return; }

    if (el.hasAttribute('data-note-clear')) { clearJournalNote(); announce('Private Journal Note cleared.'); return; }
    if (el.hasAttribute('data-note-journal')) { addJournalNoteTo('journal'); return; }
    if (el.hasAttribute('data-note-board')) { addJournalNoteTo('board'); return; }
    if (el.hasAttribute('data-open-voice')) { openVoiceOverlay(); return; }
    if (el.hasAttribute('data-open-composer')) {
      state.draft.transcript = '';
      openReviewOverlay(false, 'Review before saving. Type what happened — voice and text share the same review.');
      var edit = document.getElementById('transcriptEdit');
      if (edit) { edit.placeholder = 'Type what happened…'; edit.focus(); }
      return;
    }
    if (el.hasAttribute('data-cancel-voice')) { dismissOverlay('Recording discarded. Nothing was saved.'); return; }
    if (el.hasAttribute('data-stop-voice')) {
      state.draft.transcript = TRANSCRIPT_FULL;
      openReviewOverlay(false, 'Recording stopped. Review the transcript and proposal before anything is saved.');
      return;
    }
    if (el.hasAttribute('data-dismiss')) { dismissOverlay('Closed. Nothing was saved.'); return; }
    if (el.hasAttribute('data-keep-editing')) { dismissOverlay('Draft kept in this browser.'); return; }
    if (el.hasAttribute('data-review-primary')) {
      if (el.getAttribute('data-ai-step') === '1') { publishDraft(); }
      else { openReviewOverlay(true, 'AI-assisted review. Check the proposal, confidentiality note, and audience, then decide.'); }
      return;
    }
    if (el.hasAttribute('data-connect')) {
      var key = el.getAttribute('data-connect');
      state.draft.connections[key] = !state.draft.connections[key];
      var pressed = state.draft.connections[key];
      el.setAttribute('aria-pressed', pressed ? 'true' : 'false');
      el.classList.toggle('project', pressed);
      el.innerHTML = (pressed ? '✓ ' : '+ ') + esc({ phoenix: 'Project Phoenix', goal: 'Goal', source: 'Source' }[key]);
      return;
    }
    if (el.hasAttribute('data-respond-toggle')) {
      var trayId = el.getAttribute('data-respond-toggle');
      var tray = document.querySelector('[data-respond-tray="' + trayId + '"]');
      if (tray) {
        var open = tray.hidden;
        tray.hidden = !open;
        el.setAttribute('aria-expanded', open ? 'true' : 'false');
      }
      return;
    }
    if (el.hasAttribute('data-respond')) {
      var respondId = el.getAttribute('data-respond');
      var intent = el.getAttribute('data-intent');
      state.reactions[respondId] = state.reactions[respondId] === intent ? null : intent;
      render();
      announce(state.reactions[respondId]
        ? 'Response selected for this browser session: ' + intent.replace('_', ' ') + '.'
        : 'Response removed.');
      return;
    }
    if (el.hasAttribute('data-save')) {
      var saveId = el.getAttribute('data-save');
      state.saves[saveId] = !state.saves[saveId];
      el.setAttribute('aria-pressed', state.saves[saveId] ? 'true' : 'false');
      el.innerHTML = icon('bookmark', 'sm') + ' ' + (state.saves[saveId] ? 'Saved' : 'Save');
      announce(state.saves[saveId] ? 'Saved in this browser only.' : 'Removed from saved posts.');
      return;
    }
    if (el.hasAttribute('data-comment')) {
      var postId = el.getAttribute('data-comment');
      var post = compositionPosts().filter(function (p) { return p.id === postId; })[0];
      state.detailPost = (postId === 'p-danielle-review') ? DETAIL_POST : (post || DETAIL_POST);
      state.view = 'detail';
      render();
      scrollFeedToTop();
      announce('Conversation opened.');
      return;
    }
    if (el.hasAttribute('data-back')) {
      state.view = 'feed';
      state.detailExtraComments = [];
      render();
      announce('Back to the Feed.');
      return;
    }
    if (el.hasAttribute('data-send-reply')) {
      var input = document.getElementById('replyInput');
      var text = (input.value || '').trim();
      if (!text) { input.focus(); return; }
      state.detailExtraComments.push({ initials: 'PC', color: 'pc', name: 'Pete Carter', time: 'Just now', copy: text, offerHelp: false });
      render();
      var nextInput = document.getElementById('replyInput');
      if (nextInput) { nextInput.focus(); }
      announce('Reply added for this browser session.');
      return;
    }
    if (el.hasAttribute('data-comment-reply')) {
      var reply = document.getElementById('replyInput');
      if (reply) { reply.focus(); }
      return;
    }
    if (el.hasAttribute('data-comment-react')) {
      var commentIndex = Number(el.getAttribute('data-comment-react'));
      var all = DETAIL_COMMENTS.concat(state.detailExtraComments);
      if (all[commentIndex]) {
        all[commentIndex].reacted = !all[commentIndex].reacted;
        el.setAttribute('aria-pressed', all[commentIndex].reacted ? 'true' : 'false');
      }
      return;
    }
    if (el.hasAttribute('data-offer-help')) {
      var helpIndex = Number(el.getAttribute('data-offer-help'));
      var thread = DETAIL_COMMENTS.concat(state.detailExtraComments);
      if (thread[helpIndex]) {
        thread[helpIndex].offered = !thread[helpIndex].offered;
        el.setAttribute('aria-pressed', thread[helpIndex].offered ? 'true' : 'false');
        announce(thread[helpIndex].offered ? 'Offer to help selected for this browser session.' : 'Offer to help withdrawn.');
      }
      return;
    }
    if (el.hasAttribute('data-play')) {
      announce('Media playback needs the protected media service; no video is streamed in this frontend build.');
      return;
    }
    if (el.hasAttribute('data-play-voice')) {
      announce('Voice-note playback needs the protected media service.');
      return;
    }
    if (el.hasAttribute('data-retry')) {
      state.view = 'loading';
      render();
      announce('Refreshing the Feed…');
      window.setTimeout(function () {
        state.view = 'feed';
        state.composition = 'default';
        render();
        announce('Feed refreshed.');
      }, REDUCED ? 250 : 900);
      return;
    }
  });

  /* Enter key on the reply input sends the reply. */
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && event.target.id === 'replyInput') {
      event.preventDefault();
      var send = document.querySelector('[data-send-reply]');
      if (send) { send.click(); }
    }
  });

  document.addEventListener('input', function (event) {
    if (event.target.id !== 'communityJournalNote') { return; }
    if (writeBrowserValue(JOURNAL_NOTE_KEY, event.target.value)) {
      updateJournalNoteStatus('Saved in this browser');
    } else {
      updateJournalNoteStatus('Storage unavailable');
    }
  });

  function syncModeUrl(push) {
    var url = new URL(window.location.href);
    if (state.tab === 'news') { url.searchParams.set('view', 'news'); }
    else { url.searchParams.delete('view'); }
    window.history[push ? 'pushState' : 'replaceState']({}, '', url.pathname + url.search + url.hash);
  }

  /* Tabs: click + roving arrow keys. */
  tabs.forEach(function (tab, index) {
    tab.addEventListener('click', function () {
      state.tab = tab.getAttribute('data-tab');
      state.view = 'feed';
      syncModeUrl(true);
      render();
      announce(state.tab === 'news'
        ? 'News Feed selected. No provider is connected yet.'
        : 'Member Feed selected.');
    });
    tab.addEventListener('keydown', function (event) {
      var next = null;
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') { next = tabs[(index + 1) % tabs.length]; }
      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') { next = tabs[(index - 1 + tabs.length) % tabs.length]; }
      if (event.key === 'Home') { next = tabs[0]; }
      if (event.key === 'End') { next = tabs[tabs.length - 1]; }
      if (next) { event.preventDefault(); next.focus(); next.click(); }
    });
  });

  /* ---------- deep-linkable states (?state=…) ---------- */

  function applyInitialState() {
    var params = new URLSearchParams(window.location.search);
    var initial = params.get('state') || 'default';
    var showLoadingFirst = true;

    if (params.get('view') === 'news') { state.tab = 'news'; }

    switch (initial) {
      case 'gallery': state.composition = 'gallery'; break;
      case 'video': state.composition = 'video'; break;
      case 'rail': state.composition = 'rail'; break;
      case 'empty': state.tab = 'feed'; break;
      case 'detail': state.view = 'detail'; state.detailPost = DETAIL_POST; break;
      case 'error': state.view = 'error'; break;
      case 'loading':
        state.view = 'loading';
        state.subtitleKey = 'loading';
        render();
        return; // stays in the loading state for review
      case 'voice':
      case 'review':
      case 'publish':
        break;
      default: initial = 'default';
    }

    if (state.view === 'detail' || state.view === 'error') { showLoadingFirst = false; }

    if (showLoadingFirst && !REDUCED) {
      state.subtitleKey = 'default';
      var target = state.view;
      state.view = 'loading';
      render();
      window.setTimeout(function () {
        state.view = target === 'loading' ? 'feed' : target;
        render();
        afterFirstRender(initial);
      }, 650);
    } else {
      render();
      afterFirstRender(initial);
    }
  }

  function afterFirstRender(initial) {
    if (initial === 'voice') { openVoiceOverlay(); }
    if (initial === 'review') { state.draft.transcript = TRANSCRIPT_FULL; openReviewOverlay(false); }
    if (initial === 'publish') { state.draft.transcript = TRANSCRIPT_FULL; openReviewOverlay(true); }
  }

  state.view = 'feed';
  applyInitialState();

  window.addEventListener('popstate', function () {
    state.tab = new URLSearchParams(window.location.search).get('view') === 'news' ? 'news' : 'feed';
    state.view = 'feed';
    render();
  });
})();
