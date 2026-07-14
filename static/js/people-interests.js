// people-interests.js — the People & Interests living board (PS-FEAT-002).
// Renders the corkboard feed from /api/feed/people-interests with cursor
// pagination, the pinned composer, and the post-detail overlay.
//
// Conventions (matching the-slate.js):
// - Vanilla IIFE, no dependencies, no secrets.
// - User-provided text ALWAYS enters the DOM via textContent — never
//   innerHTML — so nothing typed can inject markup.
// - Writes go to the API with the same-origin header. When no signed-in
//   identity exists (production is pre-launch), writes fall back to
//   per-browser storage and are labeled "this browser only" — the same
//   honest convention as the Daily Slate composer.
// - Paper size, color, rotation, and attachment are STORED with each
//   item; this file only reads them, so the collage never re-randomizes.

(function () {
    'use strict';

    var board = document.querySelector('[data-pi-board]');
    if (!board) { return; }

    var configEl = document.getElementById('pi-config');
    var initialEl = document.getElementById('pi-initial-feed');
    var CONFIG = configEl ? JSON.parse(configEl.textContent) : {};
    var INITIAL = initialEl ? JSON.parse(initialEl.textContent) : { items: [], next_cursor: null };

    var REACTIONS = CONFIG.reactions || [];
    var GOAL_REACTION = CONFIG.goal_reaction || null;
    var STATIC_BASE = CONFIG.static_base || '/static/';
    var BODY_MAX = CONFIG.post_body_max || 200;

    var LOCAL_POSTS_KEY = 'piBoardLocalPosts';
    var LOCAL_REACTIONS_KEY = 'piBoardViewerReactions';
    var LOCAL_SAVES_KEY = 'piBoardSaves';
    var LOCAL_COMMENTS_KEY = 'piBoardLocalComments';
    var MAX_LOCAL_POSTS = 20;

    var statusEl = document.querySelector('[data-pi-status]');
    var sentinel = document.querySelector('[data-pi-sentinel]');
    var postsById = {};
    var nextCursor = INITIAL.next_cursor;
    var loading = false;
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ============================================================
       Small helpers
       ============================================================ */

    function readStore(key, fallback) {
        try {
            var raw = localStorage.getItem(key);
            var value = raw ? JSON.parse(raw) : fallback;
            return value === null || value === undefined ? fallback : value;
        } catch (err) { return fallback; }
    }

    function writeStore(key, value) {
        try { localStorage.setItem(key, JSON.stringify(value)); } catch (err) { /* ignore */ }
    }

    function api(url, options) {
        var settings = options || {};
        settings.headers = Object.assign({}, settings.headers || {}, {
            'X-PeerSlate-Request': 'same-origin'
        });
        if (settings.body) { settings.headers['Content-Type'] = 'application/json'; }
        return fetch(url, settings).then(function (response) {
            return response.json().then(function (payload) {
                payload._status = response.status;
                if (!response.ok || !payload.success) {
                    var error = new Error(payload.message || 'PeerSlate could not complete the request.');
                    error.status = response.status;
                    throw error;
                }
                return payload;
            });
        });
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) { node.className = className; }
        if (text !== undefined && text !== null) { node.textContent = text; }
        return node;
    }

    function svgIcon(pathMarkup) {
        // Fixed, trusted markup only — never user content.
        var wrap = document.createElement('span');
        wrap.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + pathMarkup + '</svg>';
        return wrap.firstChild;
    }

    var ICONS = {
        comment: '<path d="M21 12a8 8 0 0 1-8 8H4l2.2-3.2A8 8 0 1 1 21 12z"/>',
        share: '<circle cx="6" cy="12" r="2.4"/><circle cx="17" cy="6" r="2.4"/><circle cx="17" cy="18" r="2.4"/><path d="M8.2 10.9l6.6-3.8M8.2 13.1l6.6 3.8"/>',
        save: '<path d="M6 3h12v18l-6-4-6 4z"/>',
        heart: '<path d="M12 20s-6.5-4.4-6.5-9A3.5 3.5 0 0 1 12 8a3.5 3.5 0 0 1 6.5 3c0 4.6-6.5 9-6.5 9z"/>'
    };

    function announce(message) {
        if (statusEl) { statusEl.textContent = message; }
    }

    function relativeLabel(timestamp) {
        var seconds = Math.max(0, (Date.now() - timestamp) / 1000);
        var minutes = Math.round(seconds / 60);
        if (minutes < 60) { return Math.max(1, minutes) + 'm'; }
        var hours = Math.round(minutes / 60);
        if (hours < 24) { return hours + 'h'; }
        return Math.round(hours / 24) + 'd';
    }

    var TAG_LABELS = {
        note: 'Note', win: 'Win', question: 'Question', goal: 'Goal',
        project: 'Project', idea: 'Idea', photo: 'Photo', quote: 'Quote',
        moment: 'Moment'
    };

    /* ============================================================
       Card renderer — one data-driven builder per presentation
       concern; content_type picks the paper details, never inline
       if/else scattered around.
       ============================================================ */

    function buildAvatar(author, size) {
        if (author && author.avatar) {
            var img = document.createElement('img');
            img.className = 'pi-ava pi-ava--img';
            img.src = STATIC_BASE + author.avatar;
            img.alt = '';
            img.setAttribute('aria-hidden', 'true');
            img.loading = 'lazy';
            return img;
        }
        var span = el('span', 'pi-ava pi-ava--' + ((author && author.tint) || 'blue'), (author && author.initials) || '•');
        span.setAttribute('aria-hidden', 'true');
        return span;
    }

    function buildAttachment(post) {
        if (post.attachment === 'tape') { return el('i', 'pi-tape'); }
        if (post.attachment === 'clip') { return el('i', 'pi-clip'); }
        var pin = el('i', 'pi-pin pi-pin--' + (post.pin_color || 'indigo'));
        return pin;
    }

    // Reactions to show for a post: fixture counts plus the viewer's own
    // per-browser reactions layered on top (mirroring the overlay's display
    // math). Ordered strongest-first. The goal-only reaction stays on goals.
    function reactionEntries(post) {
        var all = REACTIONS.concat(
            (GOAL_REACTION && post.content_type === 'goal') ? [GOAL_REACTION] : []
        );
        var localMine = viewerReactions()[post.id] || [];
        var serverMine = post.viewer_reactions || null;
        var server = post.reactions || {};
        var entries = [];
        all.forEach(function (reaction) {
            var localHas = localMine.indexOf(reaction.key) !== -1;
            var serverHas = serverMine ? serverMine.indexOf(reaction.key) !== -1 : false;
            // Show the viewer's *current* intent immediately: the fixture/server
            // base count already includes their reaction iff serverHas, so swap
            // that for their live local state. Add and remove both land on the
            // optimistic click, and it never double-counts once the server
            // confirms. (Pre-launch there is no serverMine, so this is just
            // base + the viewer's own local reaction.)
            var count = (server[reaction.key] || 0) - (serverHas ? 1 : 0) + (localHas ? 1 : 0);
            if (count > 0) {
                entries.push({ reaction: reaction, count: count, mine: localHas });
            }
        });
        entries.sort(function (a, b) { return b.count - a.count; });
        return entries;
    }

    function reactionTotal(post) {
        return reactionEntries(post).reduce(function (sum, entry) { return sum + entry.count; }, 0);
    }

    // Little emoji stickers "pressed" onto the board note so a post's
    // reactions read at a glance from the board. Decorative only.
    function buildStickers(post) {
        var entries = reactionEntries(post).slice(0, 3);
        if (!entries.length) { return null; }
        var wrap = el('span', 'pi-card__stickers');
        wrap.setAttribute('aria-hidden', 'true');
        entries.forEach(function (entry) {
            var chip = el('span', 'pi-sticker', entry.reaction.emoji);
            chip.dataset.key = entry.reaction.key;
            wrap.appendChild(chip);
        });
        return wrap;
    }

    // The board card's reaction + comment counts (footer, right-aligned).
    function buildSocial(post) {
        var social = el('span', 'pi-card__social');
        var reactions = reactionTotal(post);
        if (reactions > 0) {
            var reactMini = el('span', 'pi-mini');
            reactMini.appendChild(svgIcon(ICONS.heart));
            reactMini.appendChild(document.createTextNode(' ' + reactions));
            social.appendChild(reactMini);
        }
        if (post.comment_count > 0) {
            var commentMini = el('span', 'pi-mini');
            commentMini.appendChild(svgIcon(ICONS.comment));
            commentMini.appendChild(document.createTextNode(' ' + post.comment_count));
            social.appendChild(commentMini);
        }
        return social.childNodes.length ? social : null;
    }

    function buildPaper(post, isDetail) {
        var paper = el('div', 'pi-card__paper pi-card__paper--' + (post.paper || 'sticky') +
            ' pi-paper--' + (post.paper_color || 'yellow'));
        paper.style.setProperty('--pi-rot', (post.rotation || 0) + 'deg');
        if (!isDetail) {
            // Stored hand-placed nudges — the "not quite straight" pegboard look.
            paper.style.setProperty('--pi-offx', (post.offset_x || 0) + 'px');
            paper.style.setProperty('--pi-offy', (post.offset_y || 0) + 'px');
        }
        paper.setAttribute('aria-hidden', isDetail ? 'false' : 'true');

        // Attachment sits on the paper so it rotates with it.
        paper.appendChild(buildAttachment(post));

        var head = el('header', 'pi-card__head');
        head.appendChild(buildAvatar(post.author));
        var who = el('span', 'pi-card__who');
        who.appendChild(el('span', 'pi-card__name', post.author.name));
        head.appendChild(who);
        head.appendChild(el('span', 'pi-card__time', post.time_label));
        paper.appendChild(head);

        if (post.paper === 'quote') {
            var mark = el('span', 'pi-quote__mark', '“');
            mark.setAttribute('aria-hidden', 'true');
            paper.appendChild(mark);
        }

        if (post.title) {
            paper.appendChild(el('h3', 'pi-card__title', post.title));
        }

        if (post.photo && post.photo.src) {
            var photoWrap = el('div', 'pi-photo');
            var img = document.createElement('img');
            img.src = STATIC_BASE + (isDetail && post.photo.full ? post.photo.full : post.photo.src);
            img.alt = post.photo.alt || '';
            img.loading = 'lazy';
            photoWrap.appendChild(img);
            paper.appendChild(photoWrap);
        }

        if (post.body) {
            paper.appendChild(el('p', 'pi-card__body', post.body));
        }

        if (post.list_items && post.list_items.length) {
            var list = el('ul', 'pi-card__list');
            post.list_items.forEach(function (item) {
                list.appendChild(el('li', null, item));
            });
            paper.appendChild(list);
        }

        if (post.quote_attribution) {
            paper.appendChild(el('p', 'pi-card__attribution', '— ' + post.quote_attribution));
        }

        var foot = el('footer', 'pi-card__foot');
        foot.appendChild(el('span', 'pi-tag pi-tag--' + post.content_type, TAG_LABELS[post.content_type] || 'Note'));
        if (post.is_local) {
            foot.appendChild(el('span', 'pi-card__local', 'This browser only'));
        }
        if (!isDetail) {
            var social = buildSocial(post);
            if (social) { foot.appendChild(social); }
        }
        paper.appendChild(foot);

        if (post.content_type === 'goal' && post.joining_count > 0) {
            paper.appendChild(el('p', 'pi-card__joining', post.joining_count + ' people joining'));
        }

        if (post.flourish && !isDetail) {
            var flourish = el('span', 'pi-card__flourish', post.flourish);
            flourish.setAttribute('aria-hidden', 'true');
            paper.appendChild(flourish);
        }

        if (post.handwriting === 'print') {
            paper.classList.add('pi-card--print');
        }
        return paper;
    }

    function excerpt(text, length) {
        if (!text) { return ''; }
        return text.length > length ? text.slice(0, length - 1) + '…' : text;
    }

    function buildBoardItem(post, isNew) {
        var item = el('article', 'pi-item pi-item--' + (post.layout || 'standard'));
        if (isNew) { item.classList.add('pi-item--new'); }
        item.dataset.postId = post.id;

        var card = el('div', 'pi-card');
        var open = el('button', 'pi-card__open');
        open.type = 'button';
        open.setAttribute('aria-label',
            'Open ' + (TAG_LABELS[post.content_type] || 'note').toLowerCase() +
            ' by ' + post.author.name + ': ' + excerpt(post.title || post.body || 'photo', 80));
        open.addEventListener('click', function () { openDetail(post.id, open); });
        card.appendChild(open);
        card.appendChild(buildPaper(post, false));
        // Stickers live on .pi-card (not the paper) so the torn scraps'
        // clip-path never crops them at the corner.
        var stickers = buildStickers(post);
        if (stickers) { card.appendChild(stickers); }
        item.appendChild(card);
        return item;
    }

    function cardSelector(postId) {
        // Post ids are safe slugs / base36 locals; escape defensively anyway.
        var esc = (window.CSS && CSS.escape) ? CSS.escape(postId) : postId;
        return '.pi-item[data-post-id="' + esc + '"]';
    }

    // Reflect a post's current reactions back onto its board card: refresh
    // the corner stickers (landing a just-added one) and the footer counts.
    // Called after the viewer reacts inside the detail overlay.
    function syncBoardCard(postId, addedKey) {
        var item = board.querySelector(cardSelector(postId));
        if (!item) { return; }
        var post = postsById[postId];
        if (!post) { return; }
        var card = item.querySelector('.pi-card');
        var paper = item.querySelector('.pi-card__paper');

        var oldStickers = card.querySelector('.pi-card__stickers');
        if (oldStickers) { oldStickers.remove(); }
        var stickers = buildStickers(post);
        if (stickers) {
            card.appendChild(stickers);
            if (addedKey && !reducedMotion) {
                var esc = (window.CSS && CSS.escape) ? CSS.escape(addedKey) : addedKey;
                var landed = stickers.querySelector('.pi-sticker[data-key="' + esc + '"]');
                if (landed) { landed.classList.add('pi-sticker--land'); }
            }
        }

        if (paper) {
            var foot = paper.querySelector('.pi-card__foot');
            if (foot) {
                var oldSocial = foot.querySelector('.pi-card__social');
                if (oldSocial) { oldSocial.remove(); }
                var social = buildSocial(post);
                if (social) { foot.appendChild(social); }
            }
        }
    }

    function renderPage(items, isNew) {
        var fragment = document.createDocumentFragment();
        items.forEach(function (post) {
            postsById[post.id] = post;
            fragment.appendChild(buildBoardItem(post, isNew));
        });
        board.appendChild(fragment);
        scheduleLayout();
    }

    /* Content-fit masonry. Each note is exactly as tall as its own text or
       photo — no fixed row height, so short notes never leave an empty
       tail. We measure every note's natural (untransformed) height and
       span it across the board's fine 1px rows, baking a small gap in
       below. grid-auto-flow: dense then packs the two columns tight. */
    var ROW_GAP = 18;
    var layoutScheduled = false;

    function sizeItem(item) {
        var card = item.querySelector('.pi-card') || item.firstElementChild;
        if (!card) { return; }
        // offsetHeight ignores the paper's rotate/lift transform, so the
        // measurement is the true layout height.
        var h = card.offsetHeight;
        if (!h) { return; }
        item.style.gridRowEnd = 'span ' + (Math.ceil(h) + ROW_GAP);
    }

    function layoutBoard() {
        layoutScheduled = false;
        Array.prototype.slice.call(board.querySelectorAll('.pi-item')).forEach(sizeItem);
    }

    function scheduleLayout() {
        if (layoutScheduled) { return; }
        layoutScheduled = true;
        window.requestAnimationFrame(layoutBoard);
    }

    // Photos land after the text, so re-flow once each one decodes.
    board.addEventListener('load', function (event) {
        if (event.target && event.target.tagName === 'IMG') { scheduleLayout(); }
    }, true);

    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(scheduleLayout);
    }

    var resizeTimer = null;
    window.addEventListener('resize', function () {
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(scheduleLayout, 150);
    });

    /* ============================================================
       Infinite scroll — cursor pagination + paper skeletons
       ============================================================ */

    function addSkeletons(count) {
        var heights = [150, 214, 122, 184];
        var skeletons = [];
        for (var i = 0; i < count; i += 1) {
            var skeleton = el('div', 'pi-item');
            skeleton.setAttribute('aria-hidden', 'true');
            var h = heights[i % heights.length];
            skeleton.style.gridRowEnd = 'span ' + (h + ROW_GAP);
            var paper = el('div', 'pi-skeleton');
            paper.style.height = h + 'px';
            skeleton.appendChild(paper);
            board.appendChild(skeleton);
            skeletons.push(skeleton);
        }
        return skeletons;
    }

    function loadNextPage() {
        if (loading || !nextCursor) { return; }
        loading = true;
        board.setAttribute('aria-busy', 'true');
        var skeletons = addSkeletons(4);
        api(CONFIG.feed_url + '?cursor=' + encodeURIComponent(nextCursor) + '&limit=16')
            .then(function (payload) {
                skeletons.forEach(function (s) { s.remove(); });
                renderPage(payload.items || [], false);
                nextCursor = payload.next_cursor;
                if (!nextCursor) {
                    announce("You're all caught up.");
                }
            })
            .catch(function () {
                skeletons.forEach(function (s) { s.remove(); });
                announce('The board could not load more right now.');
            })
            .then(function () {
                loading = false;
                board.setAttribute('aria-busy', 'false');
            });
    }

    if (sentinel && 'IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) { loadNextPage(); }
            });
        }, { rootMargin: '600px 0px' });
        observer.observe(sentinel);
    }

    /* ============================================================
       Composer — expands, validates, posts optimistically
       ============================================================ */

    var composer = document.querySelector('[data-pi-composer]');
    var composerForm = document.querySelector('[data-pi-composer-form]');
    var composerOpen = document.querySelector('[data-pi-composer-open]');
    var composerPanel = document.querySelector('[data-pi-composer-panel]');
    var composerText = document.getElementById('pi-composer-text');
    var composerCount = document.querySelector('[data-pi-count]');
    var composerError = document.querySelector('[data-pi-error]');
    var composerDone = document.querySelector('[data-pi-done]');
    var composerPost = document.querySelector('.pi-composer__post');
    var composerBackdrop = document.querySelector('[data-pi-composer-backdrop]');
    var composerCloseEls = Array.prototype.slice.call(document.querySelectorAll('[data-pi-composer-close]'));
    var composerLastFocus = null;
    var photoHint = document.querySelector('[data-pi-photo-hint]');
    var composerOptions = document.querySelector('[data-pi-composer-options]');
    var typeButtons = Array.prototype.slice.call(document.querySelectorAll('[data-pi-type]'));
    var selectedType = 'note';
    var submitting = false;

    // Each kind reveals its own extras once chosen. Preview affordances for
    // now — visual toggles only until accounts wire them to real behaviour.
    var TYPE_OPTIONS = {
        goal: ['🎯 Target date', '🤝 Accountability partners', '📊 Track progress'],
        project: ['🔗 Add a link', '👥 Find collaborators', '🚦 Set a status'],
        idea: ['🏷️ Tag a topic', '💬 Ask for feedback'],
        photo: ['🖼️ Add a caption']
    };

    function renderTypeOptions(type) {
        if (!composerOptions) { return; }
        composerOptions.textContent = '';
        var opts = TYPE_OPTIONS[type];
        if (!opts) { composerOptions.hidden = true; return; }
        opts.forEach(function (label) {
            var chip = el('button', 'pi-opt', label);
            chip.type = 'button';
            chip.setAttribute('aria-pressed', 'false');
            chip.addEventListener('click', function () {
                var on = chip.classList.toggle('is-on');
                chip.setAttribute('aria-pressed', String(on));
            });
            composerOptions.appendChild(chip);
        });
        composerOptions.hidden = false;
    }

    // The composer POPS OUT as a modal dialog (backdrop + scroll lock +
    // focus trap), rather than expanding inline beneath the trigger bar.
    function expandComposer() {
        if (!composerPanel || !composerPanel.hidden) { return; }
        composerLastFocus = document.activeElement;
        if (composerBackdrop) { composerBackdrop.hidden = false; }
        composerPanel.hidden = false;
        composerOpen.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
        document.addEventListener('keydown', composerKeydown, true);
        window.requestAnimationFrame(function () { composerText.focus(); });
    }

    function collapseComposer() {
        if (composerPanel.hidden) { return; }
        composerPanel.hidden = true;
        if (composerBackdrop) { composerBackdrop.hidden = true; }
        composerOpen.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
        document.removeEventListener('keydown', composerKeydown, true);
        composerText.value = '';
        composerError.hidden = true;
        photoHint.hidden = true;
        selectedType = 'note';
        typeButtons.forEach(function (btn) {
            btn.classList.remove('is-active');
            btn.setAttribute('aria-pressed', 'false');
        });
        renderTypeOptions('note');
        updateCount();
        if (composerLastFocus && document.contains(composerLastFocus)) {
            composerLastFocus.focus();
        }
    }

    function composerKeydown(event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            collapseComposer();
            return;
        }
        if (event.key !== 'Tab') { return; }
        var focusable = focusableIn(composerPanel);
        if (!focusable.length) { return; }
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function updateCount() {
        var length = composerText.value.length;
        composerCount.textContent = length + ' / ' + BODY_MAX;
        composerCount.classList.toggle('is-limit', length >= BODY_MAX - 10);
        composerPost.disabled = length === 0 || submitting;
    }

    if (composerOpen) {
        composerOpen.addEventListener('click', expandComposer);
        composerCloseEls.forEach(function (closer) {
            closer.addEventListener('click', collapseComposer);
        });
        composerText.addEventListener('input', updateCount);

        typeButtons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var type = btn.dataset.piType;
                var wasActive = btn.classList.contains('is-active');
                typeButtons.forEach(function (other) {
                    other.classList.remove('is-active');
                    other.setAttribute('aria-pressed', 'false');
                });
                if (wasActive) {
                    selectedType = 'note';
                } else {
                    btn.classList.add('is-active');
                    btn.setAttribute('aria-pressed', 'true');
                    selectedType = type;
                }
                photoHint.hidden = selectedType !== 'photo';
                renderTypeOptions(selectedType);
                if (composerPanel.hidden) { expandComposer(); }
            });
        });

        composerForm.addEventListener('submit', function (event) {
            event.preventDefault();
            submitPost();
        });
    }

    // Right rail — Today's pick-me-up: rotate through the quotes.
    var pickmeNext = document.querySelector('[data-pi-pickme-next]');
    if (pickmeNext) {
        var pickmeData = JSON.parse(document.querySelector('[data-pi-pickme-data]').textContent);
        var pickmeQuote = document.querySelector('[data-pi-pickme-quote]');
        var pickmeBy = document.querySelector('[data-pi-pickme-by]');
        var pickmeIndex = 0;
        pickmeNext.addEventListener('click', function () {
            pickmeIndex = (pickmeIndex + 1) % pickmeData.length;
            pickmeQuote.textContent = pickmeData[pickmeIndex].quote;
            pickmeBy.textContent = '— ' + pickmeData[pickmeIndex].by;
        });
    }

    // Goal check-in: a fresh nudge each day, "Share an update" opens the
    // composer ready to post a goal update.
    var checkinPrompt = document.querySelector('[data-pi-checkin-prompt]');
    if (checkinPrompt) {
        var checkinData = JSON.parse(document.querySelector('[data-pi-checkin-data]').textContent);
        var dayIndex = Math.floor(Date.now() / 86400000) % checkinData.length;
        checkinPrompt.textContent = checkinData[dayIndex];
        document.querySelector('[data-pi-checkin-share]').addEventListener('click', function () {
            selectedType = 'goal';
            typeButtons.forEach(function (btn) {
                var isGoal = btn.dataset.piType === 'goal';
                btn.classList.toggle('is-active', isGoal);
                btn.setAttribute('aria-pressed', String(isGoal));
            });
            renderTypeOptions('goal');
            expandComposer();
            composerText.placeholder = "How's the goal coming? Two lines is plenty.";
            composer.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
        });
    }

    // Weekend challenge: a local "I'm in" toggle (accounts make it real).
    var challengeJoin = document.querySelector('[data-pi-challenge-join]');
    if (challengeJoin) {
        challengeJoin.addEventListener('click', function () {
            var joined = challengeJoin.classList.toggle('is-joined');
            challengeJoin.setAttribute('aria-pressed', String(joined));
            challengeJoin.querySelector('span').textContent = joined ? "You're in" : "I'm in";
        });
    }

    // Community poll: pick-one preview (real voting lands with accounts).
    var pollOpts = Array.prototype.slice.call(document.querySelectorAll('[data-pi-poll-opt]'));
    pollOpts.forEach(function (opt) {
        opt.addEventListener('click', function () {
            pollOpts.forEach(function (other) {
                other.setAttribute('aria-pressed', String(other === opt));
            });
        });
    });

    // "Share something good" opens the composer ready for a moment.
    var shareGood = document.querySelector('[data-pi-sharegood]');
    if (shareGood) {
        shareGood.addEventListener('click', function () {
            selectedType = 'moment';
            typeButtons.forEach(function (btn) {
                btn.classList.remove('is-active');
                btn.setAttribute('aria-pressed', 'false');
            });
            expandComposer();
            composerText.placeholder = 'Share something good — brighten the board.';
            composer.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
        });
    }

    // "Celebrate a win" in the right rail opens the composer as a Win.
    var celebrate = document.querySelector('[data-pi-celebrate]');
    if (celebrate) {
        celebrate.addEventListener('click', function () {
            selectedType = 'win';
            typeButtons.forEach(function (btn) {
                btn.classList.remove('is-active');
                btn.setAttribute('aria-pressed', 'false');
            });
            expandComposer();
            composerText.placeholder = 'What are you celebrating? 🎉';
            composer.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
        });
    }

    function localPosts() { return readStore(LOCAL_POSTS_KEY, []); }

    function buildLocalPost(body, contentType) {
        // Deterministic style from a stable seed (the created timestamp),
        // stored with the post so refreshes keep the same look.
        var created = Date.now();
        var seed = created % 997;
        var colors = ['yellow', 'green', 'blue', 'pink', 'cream'];
        var rotations = [-3.2, -2.1, -1.2, 0, 1.4, 2.3, 3.1];
        var attachments = ['pin', 'tape', 'pin', 'clip', 'pin', 'tape'];
        var pins = ['indigo', 'red', 'teal', 'amber', 'violet'];
        var papers = { note: 'sticky', win: 'sticky', goal: 'sticky', idea: 'torn', question: 'torn', project: 'lined', photo: 'sticky', quote: 'quote', moment: 'torn' };
        return {
            id: 'local-' + created.toString(36),
            author: { name: 'You', initials: 'You', tint: 'you' },
            content_type: contentType === 'photo' ? 'note' : contentType,
            created_ts: created,
            time_label: 'now',
            body: body,
            paper: papers[contentType] || 'sticky',
            paper_color: colors[seed % colors.length],
            layout: body.length <= 60 ? 'small' : (body.length > 140 ? 'tall' : 'standard'),
            rotation: rotations[seed % rotations.length],
            offset_x: [-6, 4, 0, 6, -4, 5][seed % 6],
            offset_y: [6, -8, 10, -5, 8, -6][seed % 6],
            attachment: attachments[seed % attachments.length],
            pin_color: pins[seed % pins.length],
            handwriting: body.length <= 120 ? 'cursive' : 'print',
            reactions: {},
            comment_count: 0,
            joining_count: 0,
            is_local: true
        };
    }

    function insertPostAtTop(post, focusIt) {
        postsById[post.id] = post;
        var item = buildBoardItem(post, !reducedMotion);
        var firstItem = board.querySelector('.pi-item');
        board.insertBefore(item, firstItem || null);
        scheduleLayout();
        if (focusIt) {
            var open = item.querySelector('.pi-card__open');
            if (open) { open.focus({ preventScroll: true }); }
        }
    }

    function submitPost() {
        if (submitting) { return; }
        var body = composerText.value.trim();
        if (!body) {
            composerError.textContent = 'Write something before posting.';
            composerError.hidden = false;
            return;
        }
        if (body.length > BODY_MAX) {
            composerError.textContent = 'Posts are limited to ' + BODY_MAX + ' characters.';
            composerError.hidden = false;
            return;
        }
        submitting = true;
        composerPost.disabled = true;
        composerError.hidden = true;
        var contentType = selectedType === 'photo' ? 'note' : selectedType;

        api(CONFIG.posts_url, {
            method: 'POST',
            body: JSON.stringify({ body: body, content_type: contentType })
        }).then(function (payload) {
            insertPostAtTop(payload.post, false);
            composerDone.textContent = 'Posted to the board.';
            composerDone.hidden = false;
            collapseComposer();
        }).catch(function (error) {
            if (error.status === 401) {
                // Pre-launch: no signed-in identity. Keep the moment honest —
                // the note goes on the board for THIS browser and says so.
                var post = buildLocalPost(body, contentType);
                var saved = localPosts();
                saved.unshift(post);
                writeStore(LOCAL_POSTS_KEY, saved.slice(0, MAX_LOCAL_POSTS));
                insertPostAtTop(post, false);
                composerDone.textContent = 'Added to the board in this browser. Posting to everyone arrives with PeerSlate accounts.';
                composerDone.hidden = false;
                collapseComposer();
            } else {
                composerError.textContent = error.message || 'The post could not be created.';
                composerError.hidden = false;
            }
        }).then(function () {
            submitting = false;
            updateCount();
            window.setTimeout(function () { composerDone.hidden = true; }, 6000);
        });
    }

    /* ============================================================
       Detail overlay — expanded paper + comments column
       ============================================================ */

    var modal = document.querySelector('[data-pi-modal]');
    // The template renders the overlay inside <main>, whose isolation:
    // isolate stacking context would trap it BELOW the sticky header.
    // Reparent it to <body> so its z-index competes at the root.
    if (modal && modal.parentElement !== document.body) {
        document.body.appendChild(modal);
    }
    var modalShell = document.querySelector('[data-pi-modal-shell]');
    var modalPost = document.querySelector('[data-pi-modal-post]');
    var modalCommentList = document.querySelector('[data-pi-comment-list]');
    var modalCommentCount = document.querySelector('[data-pi-comment-count]');
    var modalCommentForm = document.querySelector('[data-pi-comment-form]');
    var modalCommentInput = document.getElementById('pi-comment-input');
    var modalCommentSend = modalCommentForm ? modalCommentForm.querySelector('.pi-comments__send') : null;
    var lastFocused = null;
    var activePostId = null;
    var writeInProgress = false;

    function viewerReactions() { return readStore(LOCAL_REACTIONS_KEY, {}); }
    function viewerSaves() { return readStore(LOCAL_SAVES_KEY, []); }
    function localComments() { return readStore(LOCAL_COMMENTS_KEY, {}); }

    function buildComment(comment) {
        var li = el('li', 'pi-comment');
        li.appendChild(buildAvatar(comment.author));
        var body = el('span', 'pi-comment__body');
        var who = el('span', 'pi-comment__who');
        who.appendChild(el('strong', null, comment.author.name));
        who.appendChild(el('small', null, comment.time_label));
        body.appendChild(who);
        body.appendChild(el('p', 'pi-comment__text', comment.body));
        li.appendChild(body);

        var support = el('button', 'pi-comment__support');
        support.type = 'button';
        var count = comment.supports || 0;
        var supported = false;
        support.setAttribute('aria-label', 'Support this comment');
        support.setAttribute('aria-pressed', 'false');
        support.appendChild(svgIcon(ICONS.heart));
        var countNode = el('span', null, count > 0 ? String(count) : '');
        support.appendChild(countNode);
        support.addEventListener('click', function () {
            supported = !supported;
            support.classList.toggle('is-active', supported);
            support.setAttribute('aria-pressed', String(supported));
            var total = count + (supported ? 1 : 0);
            countNode.textContent = total > 0 ? String(total) : '';
        });
        li.appendChild(support);
        return li;
    }

    function buildReactionBar(post) {
        var bar = el('div', 'pi-reactions');
        bar.setAttribute('role', 'group');
        bar.setAttribute('aria-label', 'Reactions');
        var available = REACTIONS.slice();
        if (GOAL_REACTION && post.content_type === 'goal') {
            available.push(GOAL_REACTION);
        }
        var mine = viewerReactions()[post.id] || [];
        var serverMine = post.viewer_reactions || null;
        available.forEach(function (reaction) {
            var isActive = mine.indexOf(reaction.key) !== -1;
            var serverHas = serverMine ? serverMine.indexOf(reaction.key) !== -1 : false;
            var serverCount = (post.reactions || {})[reaction.key] || 0;
            // Swap the server's record of the viewer's reaction for their live
            // local state so the count matches the board sticker exactly.
            var display = serverCount - (serverHas ? 1 : 0) + (isActive ? 1 : 0);
            var btn = el('button', 'pi-reaction' + (isActive ? ' is-active' : ''));
            btn.type = 'button';
            btn.setAttribute('aria-pressed', String(isActive));
            btn.setAttribute('aria-label', reaction.label);
            var emoji = el('span', 'pi-reaction__emoji', reaction.emoji);
            emoji.setAttribute('aria-hidden', 'true');
            btn.appendChild(emoji);
            btn.appendChild(el('span', 'pi-reaction__label', reaction.label));
            var countNode = el('span', 'pi-reaction__count', display > 0 ? String(display) : '');
            btn.appendChild(countNode);
            btn.addEventListener('click', function () {
                toggleReaction(post, reaction, btn, countNode);
            });
            bar.appendChild(btn);
        });
        return bar;
    }

    // A single emoji lifts off the tapped reaction and fades — the tactile
    // "you reacted" beat, floating just above the reaction row.
    function floatReactionEmoji(anchor, emoji) {
        if (reducedMotion || !anchor) { return; }
        var float = el('span', 'pi-react-float', emoji);
        float.setAttribute('aria-hidden', 'true');
        anchor.appendChild(float);
        window.setTimeout(function () {
            if (float.parentNode) { float.parentNode.removeChild(float); }
        }, 900);
    }

    function toggleReaction(post, reaction, btn, countNode) {
        var key = reaction.key;
        var store = viewerReactions();
        var mine = store[post.id] || [];
        var has = mine.indexOf(key) !== -1;
        var currentCount = parseInt(countNode.textContent || '0', 10) || 0;

        // Optimistic flip, then reconcile with the API when available.
        var nowActive = !has;
        btn.classList.toggle('is-active', nowActive);
        btn.setAttribute('aria-pressed', String(nowActive));
        countNode.textContent = String(Math.max(0, currentCount + (nowActive ? 1 : -1)) || '');

        if (nowActive) { mine.push(key); } else { mine = mine.filter(function (k) { return k !== key; }); }
        store[post.id] = mine;
        writeStore(LOCAL_REACTIONS_KEY, store);

        // Float the emoji off the button, and land it as a sticker on the
        // board note so the reaction is visible from the board too.
        if (nowActive) { floatReactionEmoji(btn, reaction.emoji); }
        syncBoardCard(post.id, nowActive ? key : null);

        var request = nowActive
            ? api(CONFIG.posts_url + '/' + encodeURIComponent(post.id) + '/reactions', {
                method: 'POST',
                body: JSON.stringify({ reaction_type: key })
            })
            : api(CONFIG.posts_url + '/' + encodeURIComponent(post.id) + '/reactions/' + encodeURIComponent(key), {
                method: 'DELETE'
            });
        request.then(function (payload) {
            if (payload.reactions) {
                post.reactions = payload.reactions;
                // When the server tracks the viewer, trust its counts (so the
                // per-browser +1 isn't double-counted on the board / on reopen).
                if (payload.viewer_reactions) { post.viewer_reactions = payload.viewer_reactions; }
                var serverCount = payload.reactions[key] || 0;
                countNode.textContent = serverCount > 0 ? String(serverCount) : '';
                syncBoardCard(post.id, null);
            }
        }).catch(function () { /* per-browser fallback already applied */ });
    }

    function buildDetail(post) {
        modalPost.textContent = '';
        var card = el('div', 'pi-card pi-card--detail');
        card.appendChild(buildPaper(post, true));
        modalPost.appendChild(card);
        modalPost.appendChild(buildReactionBar(post));

        var actions = el('div', 'pi-modal__actions');
        var share = el('button', 'pi-action');
        share.type = 'button';
        share.appendChild(svgIcon(ICONS.share));
        share.appendChild(document.createTextNode('Share'));
        share.addEventListener('click', function () {
            var url = window.location.origin + window.location.pathname + '#' + post.id;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(function () {
                    share.replaceChild(document.createTextNode('Link copied'), share.lastChild);
                    window.setTimeout(function () {
                        share.replaceChild(document.createTextNode('Share'), share.lastChild);
                    }, 2500);
                });
            }
        });
        actions.appendChild(share);

        var save = el('button', 'pi-action');
        save.type = 'button';
        var saves = viewerSaves();
        var isSaved = saves.indexOf(post.id) !== -1;
        save.appendChild(svgIcon(ICONS.save));
        save.appendChild(document.createTextNode(isSaved ? 'Saved' : 'Save'));
        save.classList.toggle('is-active', isSaved);
        save.setAttribute('aria-pressed', String(isSaved));
        save.addEventListener('click', function () {
            var current = viewerSaves();
            var has = current.indexOf(post.id) !== -1;
            var next = has ? current.filter(function (id) { return id !== post.id; }) : current.concat([post.id]);
            writeStore(LOCAL_SAVES_KEY, next);
            save.classList.toggle('is-active', !has);
            save.setAttribute('aria-pressed', String(!has));
            save.replaceChild(document.createTextNode(!has ? 'Saved' : 'Save'), save.lastChild);
            api(CONFIG.posts_url + '/' + encodeURIComponent(post.id) + '/save', {
                method: 'POST'
            }).catch(function () { /* per-browser fallback already applied */ });
        });
        actions.appendChild(save);
        modalPost.appendChild(actions);
    }

    function renderComments(post, comments) {
        modalCommentList.textContent = '';
        var extras = (localComments()[post.id] || []).map(function (c) {
            return {
                id: c.id,
                author: { name: 'You', initials: 'You', tint: 'you' },
                body: c.body,
                time_label: relativeLabel(c.created_ts),
                supports: 0
            };
        });
        var all = (comments || []).concat(extras);
        modalCommentCount.textContent = all.length ? '(' + all.length + ')' : '';
        if (!all.length) {
            modalCommentList.appendChild(el('li', 'pi-comments__empty', 'No comments yet. Start the conversation.'));
            return;
        }
        all.forEach(function (comment) {
            modalCommentList.appendChild(buildComment(comment));
        });
        modalCommentList.scrollTop = 0;
    }

    function focusableIn(container) {
        return Array.prototype.slice.call(container.querySelectorAll(
            'button, [href], input, textarea, [tabindex]:not([tabindex="-1"])'
        )).filter(function (node) { return !node.disabled && node.offsetParent !== null; });
    }

    function trapFocus(event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            if (!writeInProgress) { closeDetail(); }
            return;
        }
        if (event.key !== 'Tab') { return; }
        var focusable = focusableIn(modalShell);
        if (!focusable.length) { return; }
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function openDetail(postId, triggerEl) {
        var post = postsById[postId];
        if (!post) { return; }
        activePostId = postId;
        lastFocused = triggerEl || document.activeElement;

        buildDetail(post);
        renderComments(post, post.comments || null);
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
        document.addEventListener('keydown', trapFocus, true);
        modalShell.focus();

        // Local posts and optimistic entries have everything client-side;
        // fixture posts fetch full detail (all comments, live counts).
        if (!post.is_local) {
            api(CONFIG.posts_url + '/' + encodeURIComponent(postId))
                .then(function (payload) {
                    if (activePostId !== postId) { return; }
                    postsById[postId] = Object.assign({}, post, payload.post);
                    renderComments(payload.post, payload.post.comments);
                })
                .catch(function () {
                    renderComments(post, post.comments || []);
                });
        }
    }

    function closeDetail() {
        modal.hidden = true;
        document.body.style.overflow = '';
        document.removeEventListener('keydown', trapFocus, true);
        activePostId = null;
        if (modalCommentInput) { modalCommentInput.value = ''; }
        if (document.activeElement && typeof document.activeElement.blur === 'function') {
            document.activeElement.blur();
        }
        if (lastFocused && document.contains(lastFocused)) {
            lastFocused.focus();
        }
    }

    Array.prototype.slice.call(document.querySelectorAll('[data-pi-modal-close]')).forEach(function (closer) {
        closer.addEventListener('click', function () {
            if (!writeInProgress) { closeDetail(); }
        });
    });

    if (modalCommentInput) {
        modalCommentInput.addEventListener('input', function () {
            modalCommentSend.disabled = modalCommentInput.value.trim().length === 0;
        });

        modalCommentForm.addEventListener('submit', function (event) {
            event.preventDefault();
            var body = modalCommentInput.value.trim();
            if (!body || !activePostId || writeInProgress) { return; }
            var postId = activePostId;
            var post = postsById[postId];
            writeInProgress = true;
            modalCommentSend.disabled = true;

            api(CONFIG.posts_url + '/' + encodeURIComponent(postId) + '/comments', {
                method: 'POST',
                body: JSON.stringify({ body: body })
            }).then(function (payload) {
                var emptyNote = modalCommentList.querySelector('.pi-comments__empty');
                if (emptyNote) { emptyNote.remove(); }
                modalCommentList.appendChild(buildComment(payload.comment));
                modalCommentCount.textContent = '(' + payload.comment.comment_count + ')';
                post.comment_count = payload.comment.comment_count;
            }).catch(function (error) {
                if (error.status === 401 || !error.status) {
                    // Pre-launch fallback: the comment stays in this browser.
                    var store = localComments();
                    var mine = store[postId] || [];
                    mine.push({ id: 'lc-' + Date.now().toString(36), body: body, created_ts: Date.now() });
                    store[postId] = mine;
                    writeStore(LOCAL_COMMENTS_KEY, store);
                    var emptyRow = modalCommentList.querySelector('.pi-comments__empty');
                    if (emptyRow) { emptyRow.remove(); }
                    modalCommentList.appendChild(buildComment({
                        author: { name: 'You', initials: 'You', tint: 'you' },
                        body: body,
                        time_label: 'now',
                        supports: 0
                    }));
                }
            }).then(function () {
                writeInProgress = false;
                modalCommentInput.value = '';
                modalCommentSend.disabled = true;
                modalCommentList.scrollTop = modalCommentList.scrollHeight;
                modalCommentInput.focus();
            });
        });
    }

    /* ============================================================
       Boot: local browser posts first, then the embedded first page
       ============================================================ */

    localPosts().forEach(function (post) {
        post.time_label = relativeLabel(post.created_ts || Date.now());
        post.is_local = true;
        postsById[post.id] = post;
    });

    renderPage(localPosts(), false);
    renderPage(INITIAL.items || [], false);
    if (!INITIAL.items || !INITIAL.items.length) {
        announce('The board is empty right now.');
    }
})();
