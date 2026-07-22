/* PS-FEED-001 — Living Stream Feed prototype (Fable).
   Connected clickable states for the approved Feed Vision Handoff v1.
   Everything here is fixture/demo data shaped like specs/feed_content_contract.json.
   Nothing is persisted; publishing only updates the in-page fixture stream. */
(function () {
  'use strict';

  var APP_ROOT = document.getElementById('feed-app');
  var ASSET_BASE = (APP_ROOT && APP_ROOT.getAttribute('data-asset-base')) || '/static/images/feed';
  var REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var MEDIA_DIMENSIONS = {
    'dinner_served.jpg': [2000, 1500],
    'feed-workflow-whiteboard-2026-07-21.png': [1672, 941],
    'feed-surf-sunrise-2026-07-21.png': [1672, 941],
    'feed-team-demo-2026-07-21.png': [1672, 941],
    'feed-trail-run-2026-07-21.png': [1672, 941],
    'feed-coffee-notes-2026-07-21.png': [1672, 941],
    'feed-keyboard-build-2026-07-21.png': [1672, 941],
    'feed-keyboard-components-2026-07-21.png': [1672, 941],
    'feed-mountain-hike-2026-07-21.png': [1122, 1402],
    'feed-prototype-table-2026-07-21.png': [1672, 941],
    'feed-workflow-closeup-2026-07-21.png': [1672, 941],
    'feed-workflow-corkboard-2026-07-21.png': [1672, 941],
    'feed-surf-wave-2026-07-21.png': [1672, 941],
    'feed-journal-notebook-2026-07-21.png': [1672, 941],
    'feed-mountain-ridge-2026-07-21.png': [1672, 941]
  };

  /* The site's sticky global header (nav + slim sub-header) owns the top of
     every page; measure its real height so the community sidebar and Catch
     Up rail stick exactly beneath it at every breakpoint. */
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
      image: 'dinner_served.jpg', badge: 'Outside work', priority: 'high',
      alt: 'A candlelit dinner table set for two — lasagna on gray plates, woven placemats, a striped runner, roses in a vase, and a handwritten Carter’s Kitchen menu.'
    },
    {
      id: 'p-danielle-review', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Work update', dot: '', time: '2h', audience: 'Connections',
      title: 'The design review finally clicked today.',
      copy: 'We stopped debating screens and mapped the actual handoff. That one change made the entire workflow easier to explain—and much easier to build.',
      image: 'feed-workflow-whiteboard-2026-07-21.png', badge: 'Project Phoenix',
      alt: 'Two illustrative teammates mapping a product workflow on a glass board during a design review.',
      linkline: '▣ &nbsp; From Danielle’s Journal &nbsp;·&nbsp; <strong>Linked to Project Phoenix</strong>'
    },
    {
      id: 'p-marcus-surf', initials: 'MR', color: 'mr', name: 'Marcus Rivera',
      kind: 'Personal moment', dot: 'amber', time: '4h', audience: 'Community',
      title: 'Got in the water before the workday.',
      copy: 'I’m not calling it balance yet, but this was a pretty good start.',
      image: 'feed-surf-sunrise-2026-07-21.png', badge: 'Video · Outside work', video: true, duration: '0:38',
      alt: 'An illustrative surfer walking toward a sunrise beach with a board before work.'
    },
    {
      id: 'p-aisha-meeting', initials: 'AP', color: 'ap', name: 'Aisha Patel',
      kind: 'Reflection', dot: 'cyan', time: '5h', audience: 'Community',
      title: 'The meeting went better when I stopped trying to win it.',
      copy: 'The useful part was hearing what the other person was actually worried about. I’m writing that down before I forget it.',
      voice: true, voiceDuration: '1:12'
    },
    {
      id: 'p-jordan-summit', initials: 'JL', color: 'jl', name: 'Jordan Lee',
      kind: 'Personal moment', dot: 'amber', time: '6h', audience: 'Community',
      title: 'Sunday reset, above the clouds.',
      copy: 'No laptop, no notifications — just the trail. Monday me says thank you.',
      image: 'feed-mountain-hike-2026-07-21.png', frame: 'polaroid', polaroidCaption: 'above the clouds · Sunday',
      alt: 'An illustrative hiker walking a mountain trail toward a bright valley.'
    },
    {
      id: 'p-alex-demo', initials: 'AK', color: 'ak', name: 'Alex Kim',
      kind: 'Work update', dot: '', time: '7h', audience: 'Connections',
      title: 'Two-minute demo of the new onboarding flow.',
      copy: 'Recorded right after the standup — rough cut, real reactions.',
      image: 'feed-team-demo-2026-07-21.png', badge: 'Video', video: true, duration: '1:47', frame: 'film',
      alt: 'Three illustrative teammates reviewing a product model beside a laptop.'
    },
    {
      id: 'p-marcus-5k', initials: 'MR', color: 'mr', name: 'Marcus Rivera',
      kind: 'Milestone', dot: 'green', time: '9h', audience: 'Community',
      title: '5k before standup — a new personal record. 🎉',
      copy: 'Three months ago I couldn’t run a mile without stopping. Small steps, every day.',
      image: 'feed-trail-run-2026-07-21.png', badge: 'Milestone',
      alt: 'An illustrative runner pausing on a hillside trail at sunrise.'
    },
    {
      id: 'p-aisha-notes', initials: 'AP', color: 'ap', name: 'Aisha Patel',
      kind: 'Personal moment', dot: 'amber', time: 'Yesterday', audience: 'Community',
      title: 'Saturday morning: coffee, a pen, and zero meetings.',
      image: 'feed-coffee-notes-2026-07-21.png', frame: 'polaroid', polaroidCaption: 'the good kind of planning',
      alt: 'An illustrative coffee and open planning notebook on a wooden table.'
    }
  ];

  var POSTS_GALLERY = [
    {
      id: 'p-jordan-keyboard', initials: 'JL', color: 'jl', name: 'Jordan Lee',
      kind: 'Personal project', dot: 'green', time: '46m', audience: 'Community',
      title: 'The keyboard build is finally alive.',
      copy: 'It took three soldering attempts and one very patient Saturday, but every key works. I learned more about debugging from this than I expected.',
      gallery: ['feed-keyboard-build-2026-07-21.png', 'feed-journal-notebook-2026-07-21.png', 'feed-keyboard-components-2026-07-21.png'],
      galleryAlts: ['An illustrative custom mechanical keyboard mid-assembly.', 'An illustrative open planning notebook beside tea and a pen.', 'A distinct illustrative close-up of tactile mechanical keyboard components and hands at a workbench.'],
      linkline: '▣ &nbsp; 3 photos &nbsp;·&nbsp; Personal project'
    },
    {
      id: 'p-danielle-screens', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Project update', dot: '', time: '3h', audience: 'Connections',
      title: 'A few screens from today’s prototype review.',
      copy: 'The final layout is simpler than the version we started with. That is the point.',
      gallery: ['feed-prototype-table-2026-07-21.png', 'feed-workflow-closeup-2026-07-21.png', 'feed-workflow-corkboard-2026-07-21.png'],
      galleryAlts: ['An illustrative team reviewing a tangible prototype at a shared table.', 'An illustrative hand arranging a visual workflow on glass.', 'An illustrative team reviewing a corkboard workflow.'],
      linkline: '▣ &nbsp; Project Phoenix · 3 photos'
    }
  ];

  var POSTS_VIDEO = [
    {
      id: 'p-marcus-video', initials: 'MR', color: 'mr', name: 'Marcus Rivera',
      kind: 'Personal moment', dot: 'amber', time: '38 min', audience: 'Connections',
      title: 'Morning surf before the workday.',
      copy: 'Not everything worth remembering happens at a desk.',
      image: 'feed-surf-wave-2026-07-21.png', badge: 'Video', video: true, duration: '0:38',
      alt: 'An illustrative surfer riding a wave at sunrise before work.'
    },
    {
      id: 'p-danielle-walkthrough', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Work update', dot: '', time: '2h', audience: 'Connections',
      title: 'The handoff no longer needs a walkthrough.',
      copy: 'We reduced the number of choices, exposed the owner at each step, and made the next action obvious.',
      image: 'feed-workflow-corkboard-2026-07-21.png', badge: 'Project Phoenix',
      alt: 'An illustrative team reviewing a corkboard workflow.'
    }
  ];

  var POSTS_RAIL = [
    POSTS_VIDEO[0],
    {
      id: 'p-danielle-prototype', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
      kind: 'Project update', dot: '', time: '2h', audience: 'Connections',
      title: 'We finally have a prototype people can understand without a walkthrough.',
      copy: 'The breakthrough was removing choices, not adding features.',
      gallery: ['feed-prototype-table-2026-07-21.png', 'feed-workflow-closeup-2026-07-21.png', 'feed-workflow-corkboard-2026-07-21.png'],
      galleryAlts: ['An illustrative team reviewing a tangible prototype at a shared table.', 'An illustrative hand arranging a visual workflow on glass.', 'An illustrative team reviewing a corkboard workflow.']
    }
  ];

  var DETAIL_POST = {
    id: 'p-danielle-detail', initials: 'DM', color: 'dm', name: 'Danielle Morgan',
    kind: 'Work update', dot: '', time: '1h', audience: 'Connections',
    title: 'We changed the handoff after today’s review.',
    copy: 'The team was not asking for more documentation. They needed one clear decision point and a visible owner. That is what we are testing next.',
    image: 'feed-workflow-corkboard-2026-07-21.png', badge: 'Project Phoenix',
    alt: 'An illustrative team reviewing a corkboard workflow.'
  };

  var DETAIL_COMMENTS = [
    { initials: 'AK', color: 'ak', name: 'Alex Kim', time: '42 min',
      copy: 'This is exactly where our last handoff broke down. I can share the checklist we ended up using.', offerHelp: true },
    { initials: 'AP', color: 'ap', name: 'Aisha Patel', time: '27 min',
      copy: 'The visible owner is the important part. We had the same issue in a review last month.', offerHelp: false },
    { initials: 'MR', color: 'mr', name: 'Marcus Rivera', time: '11 min',
      copy: 'Would it help to test the flow with someone who has not seen the project before?', offerHelp: true }
  ];

  var CATCH_UP = {
    sub: 'Three meaningful updates since your last visit.',
    items: [
      { strong: 'Danielle simplified the Phoenix handoff.', span: 'She shared the decision that unlocked the prototype.' },
      { strong: 'Marcus posted a personal morning reset.', span: 'A short surf video before his workday.' },
      { strong: 'Aisha reflected on a difficult meeting.', span: 'Her takeaway: listen for the concern beneath the objection.' }
    ],
    listen: 'Listen · 1:18'
  };

  var TRANSCRIPT_LIVE = '“I finally got the prototype to a place where the team understood the handoff without me explaining every screen…”';
  var TRANSCRIPT_FULL = 'I finally got the prototype to a place where the team understood the handoff without me explaining every screen. We stopped debating individual pages and mapped the actual handoff.';

  var PROPOSAL = {
    reviewTitle: 'The handoff finally became clear.',
    publishTitle: 'We removed choices and the workflow finally clicked.',
    copy: 'We stopped debating screens and mapped the actual handoff. That one decision made the workflow easier to explain—and easier to build.'
  };

  var SUBTITLES = {
    'default': 'What people are building, learning, and living.',
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
    view: 'feed',                 // feed | detail | loading | error
    detailPost: null,
    draft: {
      transcript: TRANSCRIPT_FULL,
      audience: 'community',
      /* Connect-to targets are the member's own places (Pete, 2026-07-17). */
      connections: { story: false, board: false, resume: false },
      /* Attachments: photo/video/doc/audio, with member-chosen frames. */
      attach: { photo: false, photoFrame: 'standard', video: false, videoFrame: 'standard', doc: false, audio: false, audioDuration: '0:41' },
      aiStep: false
    },
    reactions: {},                // postId -> true
    // Per-post action state for this rendered Feed only. It never selects or
    // exposes a separate Community destination.
    saves: {},                    // postId -> true
    publishedPosts: [],           // fixture posts added through the publish flow
    detailExtraComments: []
  };

  var feedColumn = document.getElementById('feedColumn');
  var contextRail = document.getElementById('contextRail');
  var mainInner = document.getElementById('mainInner');
  var pageTitle = document.getElementById('pageTitle');
  var pageSubtitle = document.getElementById('pageSubtitle');
  var overlayRoot = document.getElementById('overlayRoot');
  /* Community view switching belongs to community-tabs.js. Feed only owns
     this panel's established stream and composer interactions. */

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

  function responsiveFile(file, width) {
    return file.replace(/\.[^.]+$/, '-' + width + '.webp');
  }

  function responsiveImageHTML(file, alt, options) {
    options = options || {};
    var dimensions = MEDIA_DIMENSIONS[file];
    var priority = options.priority === 'high';
    var loading = priority ? 'eager' : 'lazy';
    var attrs = ' alt="' + esc(alt || '') + '" loading="' + loading +
      '" decoding="async" fetchpriority="' + (priority ? 'high' : 'low') + '"';

    /* Every production fixture is registered above. The fallback protects an
       in-progress composer fixture without silently breaking its rendering. */
    if (!dimensions) {
      return '<img src="' + ASSET_BASE + '/' + file + '"' + attrs + '>';
    }

    var widths = file === 'feed-mountain-hike-2026-07-21.png' ? [560, 1120] : [640, 1280];
    var mobile = ASSET_BASE + '/' + responsiveFile(file, widths[0]);
    var desktop = ASSET_BASE + '/' + responsiveFile(file, widths[1]);
    return '<img src="' + mobile + '" srcset="' + mobile + ' ' + widths[0] +
      'w, ' + desktop + ' ' + widths[1] + 'w" sizes="' + esc(options.sizes ||
      '(min-width: 900px) 620px, calc(100vw - 32px)') + '" width="' + dimensions[0] +
      '" height="' + dimensions[1] + '"' + attrs + '>';
  }

  function mediaHTML(post) {
    if (post.gallery) {
      var imgs = post.gallery.slice(0, 3).map(function (file, i) {
        var alt = (post.galleryAlts && post.galleryAlts[i]) || '';
        return responsiveImageHTML(file, alt, {
          sizes: '(min-width: 900px) 200px, 31vw'
        }).replace('<img ', '<img class="g' + (i + 1) + '" ');
      }).join('');
      return '<div class="gallery">' + imgs + '</div>';
    }
    if (!post.image) { return ''; }
    var badge = post.badge ? '<div class="media-badge">' + esc(post.badge) + '</div>' : '';
    if (post.video) {
      var video = '<div class="media video">' + responsiveImageHTML(post.image, post.alt, {
        priority: post.priority,
        sizes: '(min-width: 900px) 620px, calc(100vw - 32px)'
      }) + badge +
        '<div class="media-overlay"></div>' +
        '<button class="play" type="button" data-play="' + esc(post.id) + '" aria-label="Play video: ' + esc(post.title) + ' (' + esc(post.duration) + ')"></button>' +
        '<div class="video-caption"><h3>' + esc(post.title) + '</h3><p>' + esc(post.copy || 'A real moment shared in the member’s own voice.') + '</p></div>' +
        '<div class="duration">' + esc(post.duration) + '</div></div>';
      /* Film-strip frame (member-chosen option, never a default): the video
         sits INSIDE a piece of film — sprocket holes above and below. */
      if (post.frame === 'film') {
        var holes = new Array(9 + 1).join('<i></i>');
        return '<div class="filmstrip"><div class="film-holes" aria-hidden="true">' + holes + '</div>' +
          video + '<div class="film-holes" aria-hidden="true">' + holes + '</div></div>';
      }
      return video;
    }
    /* Polaroid frame (member-chosen option, never a default): white instant-
       photo mat with a handwritten caption in the thick bottom border. */
    if (post.frame === 'polaroid') {
      return '<figure class="polaroid">' + responsiveImageHTML(post.image, post.alt, {
        priority: post.priority,
        sizes: '(min-width: 900px) 590px, calc(100vw - 56px)'
      }) +
        (post.polaroidCaption ? '<figcaption class="polaroid-caption">' + esc(post.polaroidCaption) + '</figcaption>' : '') +
        '</figure>';
    }
    return '<div class="media landscape">' + responsiveImageHTML(post.image, post.alt, {
      priority: post.priority,
      sizes: '(min-width: 900px) 620px, calc(100vw - 32px)'
    }) + badge + '</div>';
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
      '<button class="more" type="button" data-inert aria-label="More options for this post (not part of this prototype)">···</button></div>' +
      '<div class="post-body">' + body + '</div></article>';
  }

  /* Sticky-note reminder pad (Pete, 2026-07-17): a yellow pad pinned at the
     top of the right rail. Reminders live here for the session only, and
     each one can be sent to the Slate Board too. */
  var REMINDERS = [
    { text: 'Reply to Danielle about the handoff checklist', board: false },
    { text: 'Book the PMP exam window', board: true }
  ];

  function stickyPadHTML() {
    var notes = REMINDERS.map(function (item, index) {
      return '<li class="sticky-note-row">' +
        '<span class="sticky-note-text">' + esc(item.text) + '</span>' +
        '<button class="sticky-board-btn" type="button" data-reminder-board="' + index + '" aria-pressed="' + (!!item.board) + '">' +
        (item.board ? '✓ On board' : '+ Board') + '</button></li>';
    }).join('');
    return '<div class="sticky-pad" aria-label="Reminders">' +
      '<div class="sticky-pad-head"><h3>Reminders</h3><span class="sticky-pin" aria-hidden="true"></span></div>' +
      '<ul class="sticky-list">' + notes + '</ul>' +
      '<form class="sticky-add" data-reminder-form>' +
      '<label class="sr-only" for="reminderInput">Add a reminder</label>' +
      '<input id="reminderInput" placeholder="Add a reminder…" autocomplete="off">' +
      '<button class="sticky-add-btn" type="submit" aria-label="Add reminder">+</button></form>' +
      '<p class="sticky-hint">Reminders can also be added to your Slate Board.</p></div>';
  }

  function catchUpRailHTML() {
    var items = CATCH_UP.items.map(function (item) {
      return '<div class="catch-item"><strong>' + esc(item.strong) + '</strong><span>' + esc(item.span) + '</span></div>';
    }).join('');
    return stickyPadHTML() +
      '<div class="rail-panel"><div class="rail-title"><h3>Catch Up</h3><div class="spark">' + icon('spark') + '</div></div>' +
      '<p class="rail-sub">' + esc(CATCH_UP.sub) + '</p>' + items +
      '<button class="rail-cta" type="button" data-inert>' + icon('mic', 'sm') + ' ' + esc(CATCH_UP.listen) + '</button></div>' +
      '<div class="rail-note">' + icon('spark', 'sm') + ' <strong>AI summary</strong><br>Built only from posts you are allowed to see. Every summary links to its source.</div>';
  }

  function skeletonHTML() {
    var post = '<article class="post"><div class="post-head"><div class="avatar"></div><div class="post-author"><div class="sk"></div>' +
      '<div class="author-meta"><span class="sk" style="display:block;width:120px;height:9px"></span></div></div></div>' +
      '<div class="post-body"><div class="post-title sk"></div><div class="line sk"></div><div class="line sk" style="width:85%"></div>' +
      '<div class="media landscape"></div></div></article>';
    return composerHTML('Loading your Feed…') + '<div class="date-label">Today</div>' +
      '<div class="skeleton" aria-hidden="true">' + post + post + post + '</div>';
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
      '<a class="btn" href="/the-slate/my-slate">Open my Journal</a>' +
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

  /* PS-COMMUNITY-TABS-001 (2026-07-21): inside the shared Feed / The Break
     shell, #feed-app IS the whole comm-shell (not just the Feed panel) —
     #pageTitle/#pageSubtitle are the one page header both panels share.
     Feed's own render() still needs to populate #feedColumn / #contextRail
     while The Break is active (so switching to Feed later is instant, with
     no flash of empty content), but it must
     never overwrite that shared header while a different tab is the one the
     visitor is actually looking at — community-tabs.js owns the header text
     whenever Feed isn't active. On the standalone /feed-living-stream preview
     (#feed-app carries no data-community-tabs attribute) Feed is always "the"
     page, so this always resolves true and behavior there is unchanged. */
  function feedTabIsActive() {
    if (!APP_ROOT || !APP_ROOT.hasAttribute('data-community-tabs')) { return true; }
    var active = APP_ROOT.getAttribute('data-active-tab') || APP_ROOT.getAttribute('data-initial-tab') || 'feed';
    return active === 'feed';
  }

  function setRail(visible) {
    if (visible) {
      contextRail.innerHTML = catchUpRailHTML();
      contextRail.hidden = false;
      mainInner.classList.remove('no-rail');
    } else {
      contextRail.hidden = true;
      contextRail.innerHTML = '';
      mainInner.classList.add('no-rail');
    }
  }

  function render() {
    var headerIsFeeds = feedTabIsActive();
    if (state.view === 'loading') {
      if (headerIsFeeds) {
        pageTitle.textContent = 'Feed';
        setSubtitle(state.subtitleKey || 'default');
      }
      setRail(false);
      feedColumn.setAttribute('aria-busy', 'true');
      feedColumn.innerHTML = skeletonHTML();
      return;
    }
    feedColumn.removeAttribute('aria-busy');
    if (state.view === 'detail') {
      if (headerIsFeeds) {
        pageTitle.textContent = 'Conversation';
        setSubtitle('detail');
      }
      setRail(false);
      feedColumn.innerHTML = detailHTML(state.detailPost || DETAIL_POST);
      return;
    }
    if (headerIsFeeds) { pageTitle.textContent = 'Feed'; }
    if (state.view === 'error') {
      if (headerIsFeeds) { setSubtitle('error'); }
      setRail(false);
      feedColumn.innerHTML = errorHTML();
      return;
    }
    if (headerIsFeeds) { setSubtitle(state.composition); }
    /* The reminders + Catch Up rail is a standing part of the desktop feed
       (Pete, 2026-07-17), not a special composition. */
    setRail(true);
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

  function overlayFocusableItems(overlay) {
    return Array.prototype.filter.call(
      overlay.querySelectorAll('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])'),
      function (el) {
        if (el.disabled || el.hidden || el.getAttribute('aria-hidden') === 'true' || el.tabIndex < 0) {
          return false;
        }
        var style = window.getComputedStyle(el);
        /* Do not use offsetParent here: it can be null for otherwise
           tabbable controls within a constrained, scrolling dialog. */
        return style.display !== 'none' && style.visibility !== 'hidden' && el.getClientRects().length > 0;
      }
    );
  }

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
      preferred.focus({ preventScroll: true });
    } else {
      var focusables = overlayFocusableItems(overlay);
      if (focusables.length) { focusables[0].focus(); }
    }
    overlay.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { event.preventDefault(); dismissOverlay('Nothing was saved. Your draft is kept on this page until you leave it.'); return; }
      if (event.key !== 'Tab') { return; }
      var items = overlayFocusableItems(overlay);
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

  var CONNECT_LABELS = { story: 'My Story', board: 'Slate Board', resume: 'Resume' };

  function connectChipHTML(key, label) {
    var on = !!state.draft.connections[key];
    return '<button class="chip' + (on ? ' project' : '') + '" type="button" data-connect="' + key + '" aria-pressed="' + on + '">' +
      (on ? '✓ ' : '+ ') + esc(label) + '</button>';
  }

  /* Attachments row: photo / video / document / audio, all simulated. A
     photo can wear the Polaroid frame and a video the film-strip frame —
     member options, never defaults. */
  function attachRowHTML() {
    var a = state.draft.attach;
    var out = '<div class="field-label" style="margin-top:16px">Add to this post</div><div class="attach-row">';
    out += a.photo
      ? '<span class="attach-chip">' + icon('image', 'sm') + ' Photo <label class="frame-opt"><input type="checkbox" data-frame="photo"' + (a.photoFrame === 'polaroid' ? ' checked' : '') + '> Polaroid frame</label><button class="attach-x" type="button" data-detach="photo" aria-label="Remove photo">✕</button></span>'
      : '<button class="pill-btn" type="button" data-attach="photo">' + icon('image', 'sm') + ' Photo</button>';
    out += a.video
      ? '<span class="attach-chip">▶ Video <label class="frame-opt"><input type="checkbox" data-frame="video"' + (a.videoFrame === 'film' ? ' checked' : '') + '> Film-strip frame</label><button class="attach-x" type="button" data-detach="video" aria-label="Remove video">✕</button></span>'
      : '<button class="pill-btn" type="button" data-attach="video">▶ Video</button>';
    out += a.doc
      ? '<span class="attach-chip">▤ Systems_notes.pdf<button class="attach-x" type="button" data-detach="doc" aria-label="Remove document">✕</button></span>'
      : '<button class="pill-btn" type="button" data-attach="doc">▤ Document</button>';
    out += a.audio
      ? '<span class="attach-chip">' + icon('mic', 'sm') + ' Your recording · ' + esc(a.audioDuration) + '<button class="attach-x" type="button" data-detach="audio" aria-label="Remove audio">✕</button></span>'
      : '<button class="pill-btn" type="button" data-attach="audio">' + icon('mic', 'sm') + ' Audio</button>';
    return out + '</div>';
  }

  function reviewOverlayHTML(aiStep) {
    var heading = aiStep ? 'AI-assisted publish review' : 'Review before saving';
    var proposalTitle = aiStep ? PROPOSAL.publishTitle : PROPOSAL.reviewTitle;
    var aiNote = aiStep
      ? '<div class="notice" style="margin-top:16px"><div class="symbol">' + icon('shield', 'sm') + '</div>' +
        '<div><strong style="color:#263955">Confidentiality check</strong><br>No employer, customer, or restricted details were detected. You still make the final decision.</div></div>'
      : '';
    var primaryLabel = state.draft.audience === 'private' ? 'Save privately' : 'Publish update';
    var audioRow = state.draft.attach.audio
      ? '<div class="voice-player review-audio"><button class="voice-play" type="button" data-play-voice="draft" aria-label="Play your recording (' + esc(state.draft.attach.audioDuration) + ')">▶</button>' +
        '<div class="wave" aria-hidden="true">' + new Array(38 + 1).join('<span></span>') + '</div><strong class="voice-time">' + esc(state.draft.attach.audioDuration) + '</strong></div>'
      : '';
    return '<header class="modal-head"><h2 id="reviewTitle">' + heading + '</h2>' +
      '<button class="close" type="button" data-dismiss aria-label="Close">' + icon('close', '', '2') + '</button></header>' +
      '<div class="review-body"><div class="review-main">' +
      '<label class="field-label" for="transcriptEdit">What you said</label>' +
      audioRow +
      '<textarea class="transcript-box editable" id="transcriptEdit" rows="4" data-autofocus>' + esc(state.draft.transcript) + '</textarea>' +
      '<div class="proposal"><div class="proposal-head">' + icon('spark', 'sm') + ' Suggested post · editable</div>' +
      '<h3>' + esc(proposalTitle) + '</h3><p>' + esc(PROPOSAL.copy) + '</p>' +
      '<div class="chip-row"><span class="chip">Work update</span><span class="chip ai">AI-suggested draft</span></div></div>' +
      attachRowHTML() +
      aiNote + '</div>' +
      '<aside class="review-side"><div class="field-label" id="audienceLabel">Who can see this?</div>' +
      '<div role="radiogroup" aria-labelledby="audienceLabel">' +
      privacyOptionHTML('private', 'Keep private', 'Only you. Best for raw capture and reflection.') +
      privacyOptionHTML('connections', 'Connections', 'People you have accepted into your network.') +
      privacyOptionHTML('community', 'Community', 'Appears in Feed and your public Journal.') +
      privacyOptionHTML('selected', 'Selected people', 'Choose exactly who can see it.') +
      '</div>' +
      '<div class="field-label" style="margin-top:18px">Also connect to</div>' +
      '<div class="chip-row">' + connectChipHTML('story', 'My Story') + connectChipHTML('board', 'Slate Board') + connectChipHTML('resume', 'Resume') + '</div>' +
      '</aside>' +
      '<footer class="review-footer"><span class="meta">You can edit everything before it saves.</span>' +
      '<button class="cancel-btn" type="button" data-keep-editing>Keep editing</button>' +
      '<button class="btn primary" type="button" data-review-primary data-ai-step="' + (aiStep ? '1' : '0') + '">' + primaryLabel + '</button>' +
      '</footer></div>';
  }

  function openReviewOverlay(aiStep, announceText) {
    state.draft.aiStep = !!aiStep;
    var overlay = openOverlay(reviewOverlayHTML(aiStep), 'reviewTitle');
    overlay.addEventListener('change', function (event) {
      if (event.target.name === 'audience') {
        state.draft.audience = event.target.value;
        overlay.querySelectorAll('.privacy-option').forEach(function (option) {
          option.classList.toggle('selected', option.querySelector('input').checked);
        });
        var primary = overlay.querySelector('[data-review-primary]');
        primary.textContent = state.draft.audience === 'private' ? 'Save privately' : 'Publish update';
      }
      if (event.target.hasAttribute('data-frame')) {
        var kind = event.target.getAttribute('data-frame');
        if (kind === 'photo') { state.draft.attach.photoFrame = event.target.checked ? 'polaroid' : 'standard'; }
        if (kind === 'video') { state.draft.attach.videoFrame = event.target.checked ? 'film' : 'standard'; }
        announce(event.target.checked
          ? (kind === 'photo' ? 'Polaroid frame on.' : 'Film-strip frame on.')
          : 'Standard frame.');
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
    var linkedTo = Object.keys(state.draft.connections)
      .filter(function (key) { return state.draft.connections[key]; })
      .map(function (key) { return CONNECT_LABELS[key]; });
    var linked = linkedTo.length ? ' &nbsp;·&nbsp; <strong>Linked to ' + esc(linkedTo.join(', ')) + '</strong>' : '';
    var a = state.draft.attach;
    var post = {
      id: 'p-published-' + (state.publishedPosts.length + 1),
      initials: 'PC', color: 'pc', name: 'Pete Carter',
      kind: 'Work update', dot: '', time: 'Just now', audience: audienceLabel,
      title: PROPOSAL.publishTitle,
      copy: PROPOSAL.copy,
      linkline: '▣ &nbsp; From Pete’s Journal' + linked +
        (a.doc ? ' &nbsp;·&nbsp; 1 document attached' : '') + ' &nbsp;·&nbsp; AI-suggested draft'
    };
    if (a.video) {
      post.image = 'feed-team-demo-2026-07-21.png';
      post.video = true;
      post.duration = '1:47';
      post.badge = 'Video';
      post.priority = 'high';
      if (a.videoFrame === 'film') { post.frame = 'film'; }
      post.alt = 'Your attached video (simulated in this prototype).';
    } else if (a.photo) {
      post.image = 'feed-mountain-ridge-2026-07-21.png';
      post.alt = 'Your attached photo of two hikers on a mountain ridge (simulated in this prototype).';
      if (a.photoFrame === 'polaroid') { post.frame = 'polaroid'; post.polaroidCaption = 'from today'; }
    }
    if (a.audio) { post.voice = true; post.voiceDuration = a.audioDuration; }
    state.publishedPosts.unshift(post);
    state.highlightPublished = true;
    state.composition = 'default';
    state.view = 'feed';
    render();
    scrollFeedToTop();
    announce('Published to ' + audienceLabel + '. Your update is at the top of the Feed, and your original wording stays inspectable in your Journal.');
  }

  /* ---------- events ---------- */

  document.addEventListener('click', function (event) {
    var el = event.target.closest('button, a');
    if (!el) { return; }

    if (el.hasAttribute('data-inert')) {
      event.preventDefault();
      announce('That control is not part of this prototype.');
      return;
    }
    if (el.hasAttribute('data-open-voice')) { openVoiceOverlay(); return; }
    if (el.hasAttribute('data-open-composer')) {
      state.draft.transcript = '';
      state.draft.attach.audio = false;
      openReviewOverlay(false, 'Review before saving. Type what happened — voice and text share the same review.');
      var edit = document.getElementById('transcriptEdit');
      if (edit) { edit.placeholder = 'Type what happened…'; edit.focus(); }
      return;
    }
    if (el.hasAttribute('data-cancel-voice')) { dismissOverlay('Recording discarded. Nothing was saved.'); return; }
    if (el.hasAttribute('data-stop-voice')) {
      state.draft.transcript = TRANSCRIPT_FULL;
      /* The recording itself rides along with the draft as an audio
         attachment the member can keep or remove. */
      state.draft.attach.audio = true;
      openReviewOverlay(false, 'Recording stopped. Your audio is attached — review everything before it saves.');
      return;
    }
    if (el.hasAttribute('data-attach') || el.hasAttribute('data-detach')) {
      var attachKind = el.getAttribute('data-attach') || el.getAttribute('data-detach');
      var attaching = el.hasAttribute('data-attach');
      state.draft.attach[attachKind] = attaching;
      if (attachKind === 'photo' && !attaching) { state.draft.attach.photoFrame = 'standard'; }
      if (attachKind === 'video' && !attaching) { state.draft.attach.videoFrame = 'standard'; }
      openReviewOverlay(state.draft.aiStep);
      announce(attaching
        ? ({ photo: 'Photo attached (simulated). Choose the Polaroid frame if you like.',
             video: 'Video attached (simulated). Choose the film-strip frame if you like.',
             doc: 'Document attached (simulated).',
             audio: 'Audio attached (simulated).' }[attachKind])
        : 'Removed.');
      return;
    }
    if (el.hasAttribute('data-reminder-board')) {
      var remIndex = Number(el.getAttribute('data-reminder-board'));
      if (REMINDERS[remIndex]) {
        REMINDERS[remIndex].board = !REMINDERS[remIndex].board;
        render();
        announce(REMINDERS[remIndex].board
          ? 'Reminder added to your Slate Board (simulated in this prototype).'
          : 'Reminder removed from your Slate Board.');
      }
      return;
    }
    if (el.hasAttribute('data-dismiss')) { dismissOverlay('Closed. Nothing was saved.'); return; }
    if (el.hasAttribute('data-keep-editing')) { dismissOverlay('Draft kept. Nothing was published.'); return; }
    if (el.hasAttribute('data-review-primary')) {
      if (el.getAttribute('data-ai-step') === '1') { publishDraft(); }
      else { openReviewOverlay(true, 'AI-assisted publish review. Check the proposal, confidentiality note, and audience, then decide.'); }
      return;
    }
    if (el.hasAttribute('data-connect')) {
      var key = el.getAttribute('data-connect');
      state.draft.connections[key] = !state.draft.connections[key];
      var pressed = state.draft.connections[key];
      el.setAttribute('aria-pressed', pressed ? 'true' : 'false');
      el.classList.toggle('project', pressed);
      el.innerHTML = (pressed ? '✓ ' : '+ ') + esc(CONNECT_LABELS[key]);
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
        ? 'Response sent: ' + intent.replace('_', ' ') + '. Responses stay quiet — no public leaderboards.'
        : 'Response removed.');
      return;
    }
    if (el.hasAttribute('data-save')) {
      var saveId = el.getAttribute('data-save');
      state.saves[saveId] = !state.saves[saveId];
      el.setAttribute('aria-pressed', state.saves[saveId] ? 'true' : 'false');
      el.innerHTML = icon('bookmark', 'sm') + ' ' + (state.saves[saveId] ? 'Saved' : 'Save');
      announce(state.saves[saveId] ? 'Marked for this page only.' : 'Removed from this page.');
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
      announce('Reply added to the conversation.');
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
        announce(thread[helpIndex].offered ? 'Offer to help sent to ' + thread[helpIndex].name + '.' : 'Offer to help withdrawn.');
      }
      return;
    }
    if (el.hasAttribute('data-play')) {
      announce('Video playback is simulated in this prototype. Poster, duration, captions, and keyboard controls are shown; streaming arrives with the build phase.');
      return;
    }
    if (el.hasAttribute('data-play-voice')) {
      announce('Voice note playback is simulated in this prototype.');
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

  /* Enter in the reminder pad adds the reminder (session only, simulated). */
  document.addEventListener('submit', function (event) {
    if (!event.target.hasAttribute || !event.target.hasAttribute('data-reminder-form')) { return; }
    event.preventDefault();
    var input = document.getElementById('reminderInput');
    var text = (input && input.value || '').trim();
    if (!text) { if (input) { input.focus(); } return; }
    REMINDERS.unshift({ text: text, board: false });
    render();
    var next = document.getElementById('reminderInput');
    if (next) { next.focus(); }
    announce('Reminder added to your pad. Nothing is saved beyond this page.');
  });

  /* ---------- deep-linkable states (?state=…) ---------- */

  function applyInitialState() {
    var params = new URLSearchParams(window.location.search);
    var initial = params.get('state') || 'default';
    var showLoadingFirst = true;

    switch (initial) {
      case 'gallery': state.composition = 'gallery'; break;
      case 'video': state.composition = 'video'; break;
      case 'rail': state.composition = 'rail'; break;
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
})();
