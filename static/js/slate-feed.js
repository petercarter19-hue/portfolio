// Slate Feed interactions — browser-only, no secrets. Shared by the
// Progress feed (/slate-feed) and the People feed (/slate-feed/people).
// Behaviors:
//   1. The filter dropdown hides feed cards by their type.
//   2. Celebrate / React toggles one appreciation and bumps the count.
//   3. "Not now" dismisses the Suggested Next Step panel (Progress only).
//   4. The composer: post text (500-char live counter) + optional image.
//      Posts persist per-browser under a page-specific storage key.
//   5. Every card has a ••• menu: posted cards can be Edited or Deleted;
//      sample cards pulled from the slate board can be Deleted (dismissed),
//      and stay gone on reload.

(function () {
    // ---- 1. Type filter ----
    var filter = document.getElementById('sf-filter');

    function applyFilter() {
        if (!filter) { return; }
        var selected = filter.value;
        document.querySelectorAll('[data-feed-type]').forEach(function (item) {
            item.hidden = selected !== 'all' && item.dataset.feedType !== selected;
        });
    }

    if (filter) {
        filter.addEventListener('change', applyFilter);
    }

    // ---- 2. Celebrate / React ----
    document.querySelectorAll('[data-cheer]').forEach(function (button) {
        button.addEventListener('click', function () {
            var isPressed = button.getAttribute('aria-pressed') !== 'true';
            button.setAttribute('aria-pressed', String(isPressed));
            var card = button.closest('article');
            var count = card ? card.querySelector('[data-count]') : null;
            if (count) {
                var base = parseInt(count.dataset.count, 10) || 0;
                count.textContent = (base + (isPressed ? 1 : 0)) + ' ' + count.dataset.label;
            }
        });
    });

    // ---- 3. Dismiss the suggested next step ----
    var dismissSuggest = document.querySelector('[data-dismiss-suggest]');
    var suggestPanel = document.getElementById('sf-suggest-panel');
    var suggestDone = document.getElementById('sf-suggest-done');
    if (dismissSuggest && suggestPanel && suggestDone) {
        dismissSuggest.addEventListener('click', function () {
            suggestPanel.hidden = true;
            suggestDone.hidden = false;
        });
    }

    var feedEl = document.getElementById('sf-feed');
    if (!feedEl) { return; }

    // ---- shared ••• menu (Edit / Delete) ----
    // Closes any open menu when another opens or on an outside click.
    var openMenu = null;
    function closeMenu() {
        if (openMenu) {
            openMenu.menu.remove();
            openMenu.btn.setAttribute('aria-expanded', 'false');
            openMenu = null;
        }
    }
    document.addEventListener('click', function (e) {
        if (openMenu && !openMenu.wrap.contains(e.target)) { closeMenu(); }
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { closeMenu(); }
    });

    // Wire a card's ••• button to a popover menu. items = [{label, danger, run}].
    function attachMenu(card, items) {
        var btn = card.querySelector('.sf-item__more');
        if (!btn) { return; }
        // Sample cards ship as disabled previews — make them real.
        btn.removeAttribute('aria-disabled');
        btn.removeAttribute('title');
        btn.setAttribute('aria-haspopup', 'true');
        btn.setAttribute('aria-expanded', 'false');

        var wrap = btn.parentElement;   // .sf-item__meta (position: relative)
        wrap.classList.add('sf-menu-wrap');

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            if (openMenu && openMenu.btn === btn) { closeMenu(); return; }
            closeMenu();

            var menu = document.createElement('div');
            menu.className = 'sf-card-menu';
            items.forEach(function (item) {
                var b = document.createElement('button');
                b.type = 'button';
                b.className = 'sf-card-menu__item' + (item.danger ? ' sf-card-menu__item--danger' : '');
                b.textContent = item.label;
                b.addEventListener('click', function (ev) {
                    ev.stopPropagation();
                    closeMenu();
                    item.run();
                });
                menu.appendChild(b);
            });
            wrap.appendChild(menu);
            btn.setAttribute('aria-expanded', 'true');
            openMenu = { btn: btn, menu: menu, wrap: wrap };
        });
    }

    // ---- 4. The composer ----
    var compose = document.getElementById('sf-compose');
    if (!compose) { return; }   // both feed views ship a composer

    var MAX_CHARS = 500;
    var STORAGE_KEY = compose.dataset.storageKey || 'peerslateFeedPosts';
    var DISMISSED_KEY = STORAGE_KEY + ':dismissed';
    var ACTION_TEXT = compose.dataset.actionText || ' shared an update';
    var MAX_STORED_POSTS = 20;

    var textEl = document.getElementById('sf-compose-text');
    var countEl = document.getElementById('sf-compose-count');
    var postBtn = document.getElementById('sf-compose-post');
    var imageInput = document.getElementById('sf-compose-image');
    var preview = document.getElementById('sf-compose-preview');
    var previewImg = document.getElementById('sf-compose-preview-img');
    var removeImgBtn = document.getElementById('sf-compose-remove-img');

    var attachedImage = null;

    function readJSON(key) {
        try { return JSON.parse(localStorage.getItem(key)) || []; }
        catch (e) { return []; }
    }
    function writeJSON(key, value) {
        try { localStorage.setItem(key, JSON.stringify(value)); return true; }
        catch (e) { return false; }
    }

    function loadPosts() { return readJSON(STORAGE_KEY); }
    function savePosts(posts) { return writeJSON(STORAGE_KEY, posts.slice(0, MAX_STORED_POSTS)); }

    function loadDismissed() { return readJSON(DISMISSED_KEY); }
    function addDismissed(id) {
        var set = loadDismissed();
        if (set.indexOf(id) === -1) { set.push(id); writeJSON(DISMISSED_KEY, set); }
    }

    function relativeLabel(ts) {
        var mins = Math.max(0, Math.floor((Date.now() - ts) / 60000));
        if (mins < 1) { return 'now'; }
        if (mins < 60) { return mins + 'm ago'; }
        var hours = Math.floor(mins / 60);
        if (hours < 24) { return hours + 'h ago'; }
        return Math.floor(hours / 24) + 'd ago';
    }

    // Inline edit: swap the post text for a textarea + Save / Cancel.
    function editPost(card, post, bodyEl) {
        if (card.querySelector('.sf-item__edit')) { return; }   // already editing

        var editor = document.createElement('div');
        editor.className = 'sf-item__edit';
        var area = document.createElement('textarea');
        area.maxLength = MAX_CHARS;
        area.value = post.text;
        var bar = document.createElement('div');
        bar.className = 'sf-item__edit-bar';
        var counter = document.createElement('span');
        counter.className = 'sf-item__edit-count';
        var save = document.createElement('button');
        save.type = 'button';
        save.className = 'sf-compose__post';
        save.textContent = 'Save';
        var cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'sf-suggest__later';
        cancel.textContent = 'Cancel';

        function tick() { counter.textContent = area.value.length + ' / ' + MAX_CHARS; }
        area.addEventListener('input', tick);
        tick();

        bar.appendChild(counter);
        bar.appendChild(cancel);
        bar.appendChild(save);
        editor.appendChild(area);
        editor.appendChild(bar);

        bodyEl.hidden = true;
        bodyEl.insertAdjacentElement('afterend', editor);
        area.focus();

        cancel.addEventListener('click', function () {
            editor.remove();
            bodyEl.hidden = false;
        });
        save.addEventListener('click', function () {
            var next = area.value.trim().slice(0, MAX_CHARS);
            if (!next && !post.image) { return; }
            post.text = next;
            bodyEl.textContent = next;
            editor.remove();
            bodyEl.hidden = false;
            var posts = loadPosts().map(function (p) {
                return p.ts === post.ts ? post : p;
            });
            savePosts(posts);
        });
    }

    // Builds a feed card for a user post. DOM APIs / textContent only, so
    // typed input can never inject markup.
    function makePostCard(post) {
        var card = document.createElement('article');
        card.className = 'sf-item';
        card.dataset.feedType = 'post';
        card.dataset.postId = String(post.ts);

        var head = document.createElement('header');
        head.className = 'sf-item__head';

        var avatar = document.createElement('img');
        avatar.className = 'sf-avatar';
        avatar.src = compose.dataset.authorAvatar;
        avatar.alt = '';
        head.appendChild(avatar);

        var who = document.createElement('p');
        who.className = 'sf-item__who';
        var name = document.createElement('a');
        name.className = 'sf-item__name';
        name.href = compose.dataset.authorUrl;
        name.textContent = compose.dataset.authorName;
        var action = document.createElement('span');
        action.className = 'sf-item__action';
        action.textContent = ACTION_TEXT;
        who.appendChild(name);
        who.appendChild(action);
        head.appendChild(who);

        var meta = document.createElement('span');
        meta.className = 'sf-item__meta';
        var time = document.createElement('time');
        time.textContent = relativeLabel(post.ts);
        meta.appendChild(time);
        var more = document.createElement('button');
        more.className = 'sf-item__more';
        more.type = 'button';
        more.setAttribute('aria-label', 'Post options');
        more.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg>';
        meta.appendChild(more);
        head.appendChild(meta);
        card.appendChild(head);

        var body = document.createElement('p');
        body.className = 'sf-item__post-text';
        body.textContent = post.text;
        card.appendChild(body);

        if (post.image) {
            var img = document.createElement('img');
            img.className = 'sf-item__post-img';
            img.src = post.image;
            img.alt = '';
            card.appendChild(img);
        }

        var foot = document.createElement('footer');
        foot.className = 'sf-item__foot';
        var social = document.createElement('span');
        social.className = 'sf-social';
        var count = document.createElement('span');
        count.className = 'sf-social__count';
        count.textContent = 'Be the first to celebrate';
        social.appendChild(count);
        foot.appendChild(social);

        var acts = document.createElement('span');
        acts.className = 'sf-item__acts';
        var cheer = document.createElement('button');
        cheer.className = 'sf-act';
        cheer.type = 'button';
        cheer.setAttribute('aria-pressed', 'false');
        cheer.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" style="width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;"><path d="M5 12l-3 9 9-3z"/><path d="M6.5 13.5l4 4"/><path d="M13 6.5l1-3M17.5 10l3-1M15.5 4.5l-.5 2.5M20 15l-2.5.5M19.5 4.5l-3.5 3.5"/></svg>Celebrate';
        cheer.addEventListener('click', function () {
            var pressed = cheer.getAttribute('aria-pressed') !== 'true';
            cheer.setAttribute('aria-pressed', String(pressed));
            count.textContent = pressed ? '1 peer celebrated (you)' : 'Be the first to celebrate';
        });
        acts.appendChild(cheer);
        foot.appendChild(acts);
        card.appendChild(foot);

        // ••• menu: Edit + Delete for the author's own posts.
        attachMenu(card, [
            { label: 'Edit post', run: function () { editPost(card, post, body); } },
            { label: 'Delete post', danger: true, run: function () {
                card.remove();
                savePosts(loadPosts().filter(function (p) { return p.ts !== post.ts; }));
            } }
        ]);

        return card;
    }

    // Sample cards (server-rendered from the slate board): wire a Delete
    // that dismisses the card and remembers it so it stays gone on reload.
    function wireSampleCards() {
        var dismissed = loadDismissed ? loadDismissed() : [];
        Array.prototype.forEach.call(feedEl.querySelectorAll(':scope > .sf-item[id]'), function (card) {
            if (dismissed.indexOf(card.id) !== -1) { card.remove(); return; }
            attachMenu(card, [
                { label: 'Delete post', danger: true, run: function () {
                    card.remove();
                    addDismissed(card.id);
                } }
            ]);
        });
    }

    function refreshComposer() {
        var len = textEl.value.length;
        countEl.textContent = len + ' / ' + MAX_CHARS;
        countEl.classList.toggle('is-warn', len >= 450 && len < MAX_CHARS);
        countEl.classList.toggle('is-max', len >= MAX_CHARS);
        postBtn.disabled = len === 0 && !attachedImage;
    }

    textEl.addEventListener('input', function () {
        if (textEl.value.length > MAX_CHARS) { textEl.value = textEl.value.slice(0, MAX_CHARS); }
        refreshComposer();
    });

    imageInput.addEventListener('change', function () {
        var file = imageInput.files && imageInput.files[0];
        if (!file || !file.type.match(/^image\//)) { return; }
        var reader = new FileReader();
        reader.onload = function () {
            var img = new Image();
            img.onload = function () {
                var scale = Math.min(1, 900 / img.width);
                var canvas = document.createElement('canvas');
                canvas.width = Math.round(img.width * scale);
                canvas.height = Math.round(img.height * scale);
                canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
                attachedImage = canvas.toDataURL('image/jpeg', 0.82);
                previewImg.src = attachedImage;
                preview.hidden = false;
                refreshComposer();
            };
            img.src = reader.result;
        };
        reader.readAsDataURL(file);
    });

    removeImgBtn.addEventListener('click', function () {
        attachedImage = null;
        previewImg.src = '';
        preview.hidden = true;
        imageInput.value = '';
        refreshComposer();
    });

    postBtn.addEventListener('click', function () {
        var text = textEl.value.trim().slice(0, MAX_CHARS);
        if (!text && !attachedImage) { return; }

        var post = { ts: Date.now(), text: text, image: attachedImage };
        feedEl.insertBefore(makePostCard(post), feedEl.firstChild);

        var stored = loadPosts();
        stored.unshift(post);
        if (!savePosts(stored) && post.image) {
            savePosts([{ ts: post.ts, text: post.text, image: null }].concat(loadPosts()));
        }

        textEl.value = '';
        removeImgBtn.click();
        refreshComposer();
        applyFilter();
    });

    // ---- init ----
    wireSampleCards();
    loadPosts().reverse().forEach(function (post) {
        feedEl.insertBefore(makePostCard(post), feedEl.firstChild);
    });
    refreshComposer();
    applyFilter();
})();
