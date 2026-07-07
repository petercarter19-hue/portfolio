// Slate Feed interactions — browser-only, no secrets.
// Behaviors:
//   1. The "All Activity" dropdown filters feed cards by their type.
//   2. Celebrate / React buttons toggle one appreciation per visitor
//      and bump the visible peer count (click again to take it back).
//   3. "Not now" quietly dismisses the Suggested Next Step panel.
//   4. The composer: share a post (500-char live counter, optional
//      image) straight into the feed. Posts persist in this browser
//      (localStorage) until PeerSlate accounts bring real storage.

(function () {
    // ---- 1. Activity type filter ----
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
                // data-count keeps the original server-rendered number, so
                // toggling never drifts: shown = original + (you, or not).
                var base = parseInt(count.dataset.count, 10) || 0;
                count.textContent = (base + (isPressed ? 1 : 0)) + ' ' + count.dataset.label;
            }
        });
    });

    // ---- 3. Dismiss the suggested next step ----
    var dismiss = document.querySelector('[data-dismiss-suggest]');
    var suggestPanel = document.getElementById('sf-suggest-panel');
    var suggestDone = document.getElementById('sf-suggest-done');

    if (dismiss && suggestPanel && suggestDone) {
        dismiss.addEventListener('click', function () {
            suggestPanel.hidden = true;
            suggestDone.hidden = false;
        });
    }

    // ---- 4. The composer ----
    var compose = document.getElementById('sf-compose');
    var feedEl = document.getElementById('sf-feed');

    if (!compose || !feedEl) { return; }

    var MAX_CHARS = 500;
    var STORAGE_KEY = 'peerslateFeedPosts';
    var MAX_STORED_POSTS = 20;          // protects the ~5MB localStorage quota

    var textEl = document.getElementById('sf-compose-text');
    var countEl = document.getElementById('sf-compose-count');
    var postBtn = document.getElementById('sf-compose-post');
    var imageInput = document.getElementById('sf-compose-image');
    var preview = document.getElementById('sf-compose-preview');
    var previewImg = document.getElementById('sf-compose-preview-img');
    var removeImgBtn = document.getElementById('sf-compose-remove-img');

    var attachedImage = null;           // data-URL of the (downscaled) image

    function loadPosts() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function savePosts(posts) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(posts.slice(0, MAX_STORED_POSTS)));
            return true;
        } catch (e) {
            return false;               // quota exceeded — post still shows this visit
        }
    }

    function relativeLabel(ts) {
        var mins = Math.max(0, Math.floor((Date.now() - ts) / 60000));
        if (mins < 1) { return 'now'; }
        if (mins < 60) { return mins + 'm ago'; }
        var hours = Math.floor(mins / 60);
        if (hours < 24) { return hours + 'h ago'; }
        return Math.floor(hours / 24) + 'd ago';
    }

    // Builds a feed card for a post. DOM APIs only (textContent for the
    // user's words) so nothing typed can inject markup.
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
        action.textContent = ' shared an update';
        who.appendChild(name);
        who.appendChild(action);
        head.appendChild(who);

        var meta = document.createElement('span');
        meta.className = 'sf-item__meta';
        var time = document.createElement('time');
        time.textContent = relativeLabel(post.ts);
        meta.appendChild(time);
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
        count.dataset.count = '0';
        count.dataset.label = 'peers celebrated';
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

        var del = document.createElement('button');
        del.className = 'sf-item__delete';
        del.type = 'button';
        del.textContent = 'Delete';
        del.addEventListener('click', function () {
            card.remove();
            savePosts(loadPosts().filter(function (p) { return p.ts !== post.ts; }));
        });
        acts.appendChild(del);

        foot.appendChild(acts);
        card.appendChild(foot);

        return card;
    }

    // ---- live character counter (the part that must always work) ----
    function refreshComposer() {
        var len = textEl.value.length;
        countEl.textContent = len + ' / ' + MAX_CHARS;
        countEl.classList.toggle('is-warn', len >= 450 && len < MAX_CHARS);
        countEl.classList.toggle('is-max', len >= MAX_CHARS);
        postBtn.disabled = len === 0 && !attachedImage;
    }

    textEl.addEventListener('input', function () {
        // maxlength already blocks typing past 500; this also guards paste.
        if (textEl.value.length > MAX_CHARS) {
            textEl.value = textEl.value.slice(0, MAX_CHARS);
        }
        refreshComposer();
    });

    // ---- image attach: downscale to <=900px JPEG so storage stays small ----
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

    // ---- post it ----
    postBtn.addEventListener('click', function () {
        var text = textEl.value.trim().slice(0, MAX_CHARS);
        if (!text && !attachedImage) { return; }

        var post = { ts: Date.now(), text: text, image: attachedImage };
        feedEl.insertBefore(makePostCard(post), feedEl.firstChild);

        var stored = loadPosts();
        stored.unshift(post);
        if (!savePosts(stored) && post.image) {
            // Storage full with the image — keep at least the words.
            savePosts([{ ts: post.ts, text: post.text, image: null }].concat(loadPosts()));
        }

        textEl.value = '';
        removeImgBtn.click();
        refreshComposer();
        applyFilter();
    });

    // ---- restore this browser's saved posts (newest first) ----
    loadPosts().reverse().forEach(function (post) {
        feedEl.insertBefore(makePostCard(post), feedEl.firstChild);
    });

    refreshComposer();
    applyFilter();
})();
