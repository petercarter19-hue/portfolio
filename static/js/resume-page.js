/* Owner resume page renderer and layout behaviour (PS-RESUME-PAGE-OWNER-001, D1/D1d).
 *
 * Reads the signed-in member's private draft workspace (the server derives the
 * identity; no owner id is ever sent), maps it once through
 * PeerSlateResumePageModel and renders read-only sections. Every member value
 * is written with textContent; markup is only ever built from constants.
 *
 * Layout contract shared with the Guide (Lane C): the wrapper is
 * min(100% - 32px, 1240px) centred with a 268px rail, the page folds below
 * 960px, and leftColumnEdge() returns the live rail edge L.
 */
(function (global) {
    'use strict';

    var doc = global.document;
    var root = doc.getElementById('resume-page');
    if (!root) return;
    var Model = global.PeerSlateResumePageModel;
    var FOLD = 960;
    var reduceMotion = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : {matches: false};
    var status = doc.getElementById('resume-page-status');
    var sectionsHost = doc.getElementById('resume-page-sections');
    var hero = doc.getElementById('resume-page-hero');
    var secnav = doc.getElementById('resume-page-secnav');
    var jumpBar = doc.getElementById('resume-page-jump-bar');
    var jump = doc.getElementById('resume-page-jump');
    var rail = doc.getElementById('resume-page-rail');
    var workspaceUrl = root.getAttribute('data-workspace-url');
    var displayName = root.getAttribute('data-member-name') || '';
    var model = null, loadSeq = 0, navEntries = [];

    /* ---------- tiny DOM helpers (text only) ---------- */
    function el(tag, className, textValue) {
        var node = doc.createElement(tag);
        if (className) node.className = className;
        if (textValue !== undefined && textValue !== null && textValue !== '') node.textContent = textValue;
        return node;
    }
    function icon(name, className) {
        var svg = doc.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
        if (className) svg.setAttribute('class', className);
        var use = doc.createElementNS('http://www.w3.org/2000/svg', 'use');
        use.setAttribute('href', '#rp-i-' + name);
        svg.appendChild(use);
        return svg;
    }
    function setStatus(message, kind) {
        status.textContent = message || '';
        status.hidden = !message;
        status.dataset.kind = kind || '';
    }
    function card(id, labelText, extraClass) {
        var section = el('section', 'rp-card rp-sec' + (extraClass ? ' ' + extraClass : ''));
        section.id = 'rp-' + id;
        section.tabIndex = -1;
        var heading = el('h2', 'rp-sec__title', labelText);
        heading.id = 'rp-' + id + '-title';
        section.setAttribute('aria-labelledby', heading.id);
        return {section: section, heading: heading};
    }

    /* ---------- hero ---------- */
    function renderHero(m) {
        var person = m.person;
        var photo = hero.querySelector('[data-rp-photo]');
        photo.replaceChildren();
        var photoSrc = person.photo ? staticImagePath(person.photo.src) : null;
        if (photoSrc) {
            var img = el('img');
            img.src = photoSrc;
            img.alt = person.photo.alt || person.name;
            photo.appendChild(img);
            photo.removeAttribute('aria-hidden');
            hero.dataset.hasPhoto = 'true';
        } else {
            photo.appendChild(el('span', 'rp-hero__initials', person.initials));
            photo.setAttribute('aria-hidden', 'true');
            hero.dataset.hasPhoto = 'false';
        }
        var headline = hero.querySelector('[data-rp-headline]');
        headline.textContent = person.headline;
        headline.hidden = !person.headline;
        var statement = hero.querySelector('[data-rp-statement]');
        statement.textContent = person.statement;
        statement.hidden = !person.statement;
        var side = hero.querySelector('[data-rp-side]');
        var contact = hero.querySelector('[data-rp-contact]');
        contact.replaceChildren();
        (person.contact || []).forEach(function (row) {
            var li = el('li');
            li.appendChild(icon(row.kind === 'email' ? 'mail' : row.kind === 'link' ? 'link' : 'place'));
            li.appendChild(el('span', '', row.text));
            contact.appendChild(li);
        });
        var acts = hero.querySelector('[data-rp-acts]');
        acts.replaceChildren();
        if (person.contact && person.contact.length) {
            if (m.talk) acts.appendChild(link('#rp-talk', 'Connect', 'rp-btn rp-btn--gold'));
            var first = navEntries.filter(function (e) { return e.id !== 'overview'; })[0];
            if (first) acts.appendChild(link('#rp-' + first.id, 'View resume', 'rp-btn rp-btn--outline'));
        }
        side.hidden = !(person.contact && person.contact.length);
        hero.dataset.hasSide = String(!side.hidden);
        // Highlight tiles (D2): two to four, each a saved bullet's own number and words. A tile the
        // Guide suggests is drawn dashed "waiting for your OK" and is never a saved or public tile.
        var hl = hero.querySelector('[data-rp-highlights]');
        hl.replaceChildren();
        var tiles = (m.highlights || []).filter(function (h) { return h && h.value; }).slice(0, 4);
        if (tiles.length < 2) tiles = [];
        tiles.forEach(function (h) {
            var waiting = h.state === 'suggested';
            var tile = el(h.role && !waiting ? 'button' : 'div', 'rp-hl' + (waiting ? ' rp-hl--waiting' : ''));
            if (tile.tagName === 'BUTTON') tile.type = 'button';
            if (waiting) tile.appendChild(el('span', 'rp-hl__tag', 'Suggested by the Guide · waiting for your OK'));
            tile.appendChild(el('strong', '', h.value));
            tile.appendChild(el('span', 'rp-hl__label', h.label));
            if (h.role && !waiting) {
                var em = el('em', '', 'See the role');
                em.appendChild(icon('next'));
                tile.appendChild(em);
                tile.addEventListener('click', function () { openChapter(h.role, true); });
            }
            hl.appendChild(tile);
        });
        hl.style.setProperty('--rp-hl-count', String(tiles.length || 4));
        hl.hidden = !hl.children.length;
        hero.dataset.hasHighlights = String(!hl.hidden);
    }
    function link(href, label, className) {
        var a = el('a', className, label);
        a.href = href;
        return a;
    }

    /* ---------- sections ---------- */
    function renderStory(m) {
        if (!m.story) return null;
        var c = card('story', m.story.title, 'rp-story');
        var t = el('div', 'rp-story__text');
        t.appendChild(el('p', 'rp-kicker', 'My story'));
        t.appendChild(c.heading);
        t.appendChild(el('p', 'rp-story__lead', m.story.text));
        c.section.appendChild(t);
        c.section.appendChild(el('div', 'rp-story__pic'));
        return c.section;
    }

    /* Skills in Practice (D1d): every resume line that shows the selected skill, at most
     * three, each with its role's employer and dates. Lines that fit are centred in the
     * panel; lines that overflow scroll in one named region with an always-visible bar
     * (the Guide's height rule: one scroll region, never nested). */
    /* The one guard for every image source this page sets (hero photo, Looking Ahead picture
     * and its phone variant). It returns the normalised same-origin /static/ path, or null.
     * Rejected: anything not starting with /static/, a scheme or //host, a query or fragment,
     * "..", backslashes, whitespace or control characters, and percent-encoded dots or slashes
     * (%2e %2f %5c, any case) in the raw string or after one decode, so "/static/%2e%2e/x" and
     * "/static/%252e%252e/x" never become /x. The browser's own resolution must leave the path
     * unchanged, and only that normalised path is ever assigned. */
    var UNSAFE_IMAGE = /\.\.|\\|%2e|%2f|%5c|[?#\s\u0000-\u001f\u007f]|^[a-z][a-z0-9+.-]*:|\/\//i;
    function staticImagePath(raw) {
        if (typeof raw !== 'string' || !raw || raw.length > 512 || raw.indexOf('/static/') !== 0) return null;
        var decoded;
        try { decoded = decodeURIComponent(raw); } catch (error) { return null; }
        if (UNSAFE_IMAGE.test(raw) || UNSAFE_IMAGE.test(decoded)) return null;
        var url;
        try { url = new global.URL(raw, global.location.origin); } catch (error) { return null; }
        if (url.origin !== global.location.origin || url.search || url.hash) return null;
        if (url.pathname.indexOf('/static/') !== 0 || url.pathname !== raw) return null;
        return url.pathname;
    }

    var skillPanels = [];
    function fitSkillPanel(entry) {
        var scroll = entry.scroll, bar = entry.bar, thumb = entry.thumb;
        if (!scroll.isConnected) return;
        var over = scroll.scrollHeight > scroll.clientHeight + 1;
        entry.panel.classList.toggle('is-overflowing', over);
        if (over) scroll.tabIndex = 0; else scroll.removeAttribute('tabindex');
        // Where the browser hides its own scrollbar at rest, draw the same track and thumb.
        var style = global.getComputedStyle(scroll);
        var native = scroll.offsetWidth - scroll.clientWidth - (parseFloat(style.borderLeftWidth) || 0) -
            (parseFloat(style.borderRightWidth) || 0);
        var draw = over && native < 1;
        bar.hidden = !draw;
        entry.panel.classList.toggle('has-drawn-bar', draw);
        if (!draw) return;
        var track = bar.clientHeight, ratio = scroll.clientHeight / scroll.scrollHeight;
        var size = Math.max(24, Math.round(track * ratio));
        var room = track - size, range = scroll.scrollHeight - scroll.clientHeight;
        thumb.style.height = size + 'px';
        thumb.style.transform = 'translateY(' + (range > 0 ? Math.round(scroll.scrollTop / range * room) : 0) + 'px)';
    }
    function drawnScrollbar(panel, scroll) {
        var bar = el('div', 'rp-scrollbar');
        bar.setAttribute('aria-hidden', 'true');
        bar.hidden = true;
        var thumb = el('div', 'rp-scrollbar__thumb');
        bar.appendChild(thumb);
        var entry = {panel: panel, scroll: scroll, bar: bar, thumb: thumb};
        scroll.addEventListener('scroll', function () { fitSkillPanel(entry); }, {passive: true});
        bar.addEventListener('pointerdown', function (event) {
            event.preventDefault();
            var range = scroll.scrollHeight - scroll.clientHeight;
            var room = bar.clientHeight - thumb.offsetHeight;
            if (event.target !== thumb) {
                // A click on the track pages toward the click.
                var below = event.clientY > thumb.getBoundingClientRect().top;
                scroll.scrollTop += (below ? 1 : -1) * scroll.clientHeight * 0.9;
                return;
            }
            var startY = event.clientY, startTop = scroll.scrollTop;
            if (thumb.setPointerCapture) thumb.setPointerCapture(event.pointerId);
            function move(e) { scroll.scrollTop = startTop + (e.clientY - startY) * (room > 0 ? range / room : 0); }
            function up() {
                thumb.removeEventListener('pointermove', move);
                thumb.removeEventListener('pointerup', up);
                thumb.removeEventListener('pointercancel', up);
            }
            thumb.addEventListener('pointermove', move);
            thumb.addEventListener('pointerup', up);
            thumb.addEventListener('pointercancel', up);
        });
        skillPanels.push(entry);
        return entry;
    }
    var skillObserver = global.ResizeObserver ? new global.ResizeObserver(function () { skillPanels.forEach(fitSkillPanel); }) : null;

    function renderSkills(m) {
        var skills = m.sections.skills.filter(function (s) { return s.name; });
        if (!skills.length) return null;
        var c = card('skills', 'Skills in Practice');
        var head = el('div', 'rp-sec__head');
        head.appendChild(c.heading);
        var withLines = skills.filter(function (s) { return s.lines && s.lines.length; });
        if (withLines.length) head.appendChild(el('p', 'rp-sec__sub', 'Pick a skill to see the lines on the resume that show it.'));
        c.section.appendChild(head);
        var wrap = el('div', withLines.length ? 'rp-skills' : 'rp-skills rp-skills--plain');
        var grid = el('ul', 'rp-skills__grid');
        var panel = el('div', 'rp-skills__line');
        panel.id = 'rp-skills-line';
        var scroll = el('div', 'rp-skills__scroll');
        scroll.setAttribute('role', 'region');
        scroll.setAttribute('aria-live', 'polite');
        var inner = el('div', 'rp-skills__in');
        scroll.appendChild(inner);
        panel.appendChild(scroll);
        skillPanels = [];
        var entry = drawnScrollbar(panel, scroll);
        panel.appendChild(entry.bar);
        var buttons = [];
        function show(skill, button) {
            buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(b === button)); });
            scroll.setAttribute('aria-label', 'Resume lines for ' + skill.name);
            var list = el('ul', 'rp-skills__lines');
            skill.lines.slice(0, Model.MAX_SKILL_LINES).forEach(function (line) {
                var li = el('li', 'rp-skills__item');
                li.appendChild(el('p', 'rp-skills__quote', line.text));
                var source = [line.employer, line.title, line.dates].filter(Boolean).join(' \u00b7 ');
                if (source) li.appendChild(el('p', 'rp-skills__src', source));
                // "See it in the role" opens that role's chapter and moves focus there, like the hero's
                // "See the role". (Experience renders after this section, so the chapter is looked up on click.)
                if (line.roleKey) {
                    var go = link('#rp-experience', 'See it in the role \u2192', 'rp-link rp-skills__role');
                    go.setAttribute('aria-label', 'See it in the role: ' + [line.employer, line.title].filter(Boolean).join(', '));
                    go.addEventListener('click', function (event) {
                        if (!chapters[line.roleKey]) return;  // no chapter: the ordinary in-page link to Experience
                        event.preventDefault();
                        event.stopPropagation();
                        openChapter(line.roleKey, true);
                    });
                    li.appendChild(go);
                }
                list.appendChild(li);
            });
            inner.replaceChildren(el('p', 'rp-kicker', skill.name), list);
            scroll.scrollTop = 0;
            fitSkillPanel(entry);
        }
        skills.forEach(function (skill) {
            var li = el('li');
            if (skill.lines && skill.lines.length) {
                var b = el('button', 'rp-skill');
                b.type = 'button';
                b.setAttribute('aria-pressed', 'false');
                b.setAttribute('aria-controls', panel.id);
                b.appendChild(el('span', '', skill.name));
                b.appendChild(icon('chev'));
                b.addEventListener('click', function () { show(skill, b); });
                buttons.push(b);
                li.appendChild(b);
            } else {
                li.appendChild(el('span', 'rp-skill rp-skill--plain', skill.name));
            }
            grid.appendChild(li);
        });
        wrap.appendChild(grid);
        if (withLines.length) {
            wrap.appendChild(panel);
            show(withLines[0], buttons[0]);
            if (skillObserver) { skillObserver.disconnect(); skillObserver.observe(panel); skillObserver.observe(inner); }
        }
        c.section.appendChild(wrap);
        return c.section;
    }

    var chapters = {};
    function openChapter(roleKey, scroll) {
        var entry = chapters[roleKey];
        if (!entry) return;
        Object.keys(chapters).forEach(function (key) {
            var other = chapters[key], open = key === roleKey && (other.panel.hidden || scroll);
            other.panel.hidden = !open;
            other.button.setAttribute('aria-expanded', String(open));
            other.card.classList.toggle('is-open', open);
        });
        if (scroll && !entry.panel.hidden) {
            entry.card.scrollIntoView({block: 'start', behavior: reduceMotion.matches ? 'auto' : 'smooth'});
            entry.panel.focus({preventScroll: true});
        }
    }

    function renderExperience(m) {
        var roles = m.sections.experience;
        if (!roles.length && !m.unlinked.length) return null;
        var c = card('experience', 'Experience');
        var head = el('div', 'rp-sec__head');
        head.appendChild(c.heading);
        c.section.appendChild(head);
        chapters = {};
        var row = el('div', 'rp-roles');
        var panels = el('div', 'rp-chapters');
        roles.forEach(function (role, index) {
            var art = el('article', 'rp-role');
            art.setAttribute('aria-labelledby', 'rp-role-' + index + '-org');
            var top = el('div', 'rp-role__top');
            top.appendChild(el('span', 'rp-badge', role.badge));
            var who = el('div');
            var org = el('h3', 'rp-role__org', role.org || role.title);
            org.id = 'rp-role-' + index + '-org';
            who.appendChild(org);
            if (role.dates) who.appendChild(el('p', 'rp-role__dates', role.dates));
            top.appendChild(who);
            art.appendChild(top);
            if (role.org && role.title) art.appendChild(el('p', 'rp-role__title', role.title));
            if (role.location) art.appendChild(el('p', 'rp-role__place', role.location));
            if (role.summary) art.appendChild(el('p', 'rp-role__summary', role.summary));
            if (role.summary || role.bullets.length) {
                var panel = el('div', 'rp-chapter');
                panel.id = 'rp-chapter-' + index;
                panel.tabIndex = -1;
                panel.hidden = true;
                var ph = el('p', 'rp-chapter__head');
                ph.appendChild(el('b', '', role.org || role.title));
                ph.appendChild(doc.createTextNode([role.org ? role.title : '', role.dates].filter(Boolean)
                    .map(function (part) { return ' · ' + part; }).join('')));
                panel.appendChild(ph);
                if (role.summary) panel.appendChild(el('p', 'rp-chapter__summary', role.summary));
                if (role.bullets.length) {
                    var ul = el('ul', 'rp-bullets');
                    role.bullets.forEach(function (b) { ul.appendChild(el('li', '', b.text)); });
                    panel.appendChild(ul);
                }
                var button = el('button', 'rp-link', 'View full chapter →');
                button.type = 'button';
                button.setAttribute('aria-expanded', 'false');
                button.setAttribute('aria-controls', panel.id);
                button.addEventListener('click', function () {
                    var opening = panel.hidden;
                    openChapter(role.key, false);
                    if (!opening) { panel.hidden = true; button.setAttribute('aria-expanded', 'false'); art.classList.remove('is-open'); }
                });
                art.appendChild(button);
                chapters[role.key] = {panel: panel, button: button, card: art};
                panels.appendChild(panel);
            }
            row.appendChild(art);
        });
        c.section.appendChild(row);
        c.section.appendChild(panels);
        if (m.unlinked.length) {
            var extra = el('div', 'rp-unlinked');
            extra.appendChild(el('h3', 'rp-kicker', 'More highlights from your experience'));
            var list = el('ul', 'rp-bullets');
            m.unlinked.forEach(function (b) { list.appendChild(el('li', '', b.text)); });
            extra.appendChild(list);
            c.section.appendChild(extra);
        }
        return c.section;
    }

    /* ---------- owner editing on the page (D2): the existing private draft path ----------
     * Saves go only to the server-rendered draft commands URL (create_private_item /
     * save_item), the same private draft path today's editor uses. Nothing here publishes, and a refused
     * save keeps the member's words in the form. */
    var commandsUrl = root.getAttribute('data-commands-url');
    var openForms = [], savedNotice = false;
    function requestId() {
        if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
        var bytes = new Uint8Array(16);
        global.crypto.getRandomValues(bytes);
        bytes[6] = (bytes[6] & 0x0f) | 0x40;
        bytes[8] = (bytes[8] & 0x3f) | 0x80;
        var hex = Array.prototype.map.call(bytes, function (b) { return (b + 256).toString(16).slice(1); }).join('');
        return hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' + hex.slice(16, 20) + '-' + hex.slice(20);
    }
    function sendCommand(body) {
        return global.fetch(commandsUrl, {
            method: 'POST', credentials: 'same-origin',
            headers: {'Content-Type': 'application/json', 'X-PeerSlate-Request': 'same-origin', Accept: 'application/json'},
            body: JSON.stringify(body)
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (payload) {
                return {ok: response.ok && payload && payload.success === true, status: response.status, payload: payload || {}};
            });
        }, function () { return {ok: false, status: 0, payload: {}}; });
    }
    function refusal(result) {
        var message = result.payload && typeof result.payload.message === 'string' ? result.payload.message : '';
        if (result.status === 409) return (message || 'This changed somewhere else.') + ' Your words are still here.';
        if (result.status === 503 || result.status === 0) return 'Your words weren’t saved just now. They’re still here. Try again in a moment.';
        return (message || 'That couldn’t be saved.') + (/kept|still here/i.test(message) ? '' : ' Your words are still here.');
    }
    /* The draft's version and each item's token are state, kept from every complete read
     * (load) and every command reply, even while a form stays open; they are never a side
     * effect of drawing the page. */
    var current = {draftVersion: null, items: {}};
    // An item's fingerprint: its tokens and every value the page could show or overwrite.
    function fingerprint(row) {
        return JSON.stringify([row.content_token, row.access_revision, row.values || null, row.proposed_values || null,
            row.conversion_destination || null]);
    }
    function noteWorkspace(payload) {
        current.draftVersion = Number.isInteger(payload.draft_version) ? payload.draft_version : null;
        var items = {};
        (payload.items || []).forEach(function (row) {
            if (row && typeof row.record_key === 'string') items[row.record_key] = fingerprint(row);
        });
        current.items = items;
    }
    function noteReply(payload) {
        if (payload && Number.isInteger(payload.draft_version)) current.draftVersion = payload.draft_version;
        var row = payload && payload.item;
        if (row && typeof row.record_key === 'string') {
            current.items = Object.assign({}, current.items);
            current.items[row.record_key] = fingerprint(row);
        }
    }
    /* One save of the member's words.
     * - An uncertain attempt (no reply, or 503) is resent exactly (same request id), so the
     *   server replays it rather than saving twice.
     * - A 409 means the draft moved on: the page re-reads it, and if this item itself is
     *   unchanged it retries once with a fresh request id and the new expected version. If it
     *   still conflicts, or the item itself changed elsewhere, the words stay and the page says so. */
    function saveEntry(entry, recordType, values, attempt) {
        var it = entry && entry.item, words = JSON.stringify(values);
        var seen = it ? attempt.opened[it.record_key] : null;  // the item as it was when the form opened
        function build() {
            return it
                ? {type: 'save_item', request_id: requestId(), record_key: it.record_key, record_type: recordType,
                    values: values, expected_draft_version: current.draftVersion !== null ? current.draftVersion : 0,
                    expected_content_token: it.content_token, expected_access_revision: it.access_revision}
                : {type: 'create_private_item', request_id: requestId(),
                    record_key: attempt.recordKey || (attempt.recordKey = requestId()), record_type: recordType, values: values};
        }
        function send(body) {
            attempt.words = words;
            attempt.body = body;
            return sendCommand(body).then(function (result) {
                attempt.uncertain = result.status === 0 || result.status === 503;
                if (result.ok) noteReply(result.payload);
                return result;
            });
        }
        var CHANGED = {ok: false, status: 409, payload: {message: 'This item was changed somewhere else, so this edit wasn’t saved.'}};
        var replay = attempt.body && attempt.uncertain && attempt.words === words;
        // A fresh save never overwrites an item that changed elsewhere after this form opened.
        if (!replay && it && seen !== current.items[it.record_key]) return global.Promise.resolve(CHANGED);
        return send(replay ? attempt.body : build()).then(function (result) {
            if (result.status !== 409 || !it) return result;
            return load().then(function () {
                if (!seen || seen !== current.items[it.record_key]) return CHANGED;  // changed elsewhere: honest conflict
                return send(build());
            });
        });
    }
    function field(form, labelText, input, optional) {
        var wrap = el('p', 'rp-form__field');
        var id = form.id + '-' + input.name;
        input.id = id;
        var label = el('label', 'rp-form__label', labelText);
        label.htmlFor = id;
        if (optional) label.appendChild(el('span', 'rp-form__opt', 'Optional'));
        wrap.appendChild(label);
        wrap.appendChild(input);
        return wrap;
    }
    function textInput(name, value, maxLength) {
        var input = el('input', 'rp-form__input');
        input.type = 'text';
        input.name = name;
        input.autocomplete = 'off';
        if (maxLength) input.maxLength = maxLength;
        input.value = value || '';
        return input;
    }
    /* One small owner form: Save privately / Cancel, a status line, and the words kept on refusal. */
    function ownerForm(id, title, build, collect, submit, onCancel) {
        var form = el('form', 'rp-form');
        form.id = id;
        form.noValidate = true;
        if (title) {
            var h = el('h3', 'rp-form__title', title);
            h.id = id + '-title';
            form.setAttribute('aria-labelledby', h.id);
            form.appendChild(h);
        }
        build(form);
        var acts = el('p', 'rp-form__acts');
        var save = el('button', 'rp-btn rp-btn--gold rp-btn--sm', 'Save privately');
        save.type = 'submit';
        var cancel = el('button', 'rp-link rp-form__cancel', 'Cancel');
        cancel.type = 'button';
        acts.appendChild(save);
        acts.appendChild(cancel);
        form.appendChild(acts);
        var note = el('p', 'rp-form__status');
        note.setAttribute('role', 'status');
        note.setAttribute('aria-live', 'polite');
        form.appendChild(note);
        var attempt = {opened: current.items};  // the items as they were when this form opened
        var entry = {form: form};  // while open, a reload keeps this form's section (and its words) as they are
        openForms.push(entry);
        cancel.addEventListener('click', function () { close(); if (onCancel) onCancel(); });
        function close() {
            openForms = openForms.filter(function (f) { return f !== entry; });
            form.remove();
        }
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            var values;
            try { values = collect(form); } catch (error) { note.textContent = error.message; note.dataset.kind = 'error'; return; }
            save.disabled = true;
            note.textContent = 'Saving privately…';
            note.dataset.kind = '';
            submit(values, attempt).then(function (result) {
                save.disabled = false;
                if (!result.ok) { note.textContent = refusal(result); note.dataset.kind = 'error'; return; }
                close();
                savedNotice = true;
                doc.dispatchEvent(new global.Event('resume-private-draft-changed'));
            });
        });
        return form;
    }

    /* Projects form: Guide D91's fields and labels (ARCH 6j), B2's essentials (name and a
     * one-line description), optional category, organization, dates and up to three https links. */
    var DATES_RE = /^(\d{4}(?:-\d{2})?)(?:\s*(?:–|—|-|to)\s*(\d{4}(?:-\d{2})?))?$/;
    function projectForm(id, project, onCancel) {
        var v = project ? Object.assign({}, project.item.values || {}, project.item.proposed_values || {}) : {};
        function datesText() {
            var s = (v.start_date || '').slice(0, v.date_precision === 'year' ? 4 : 7);
            var e = (v.end_date || '').slice(0, v.date_precision === 'year' ? 4 : 7);
            if (!v.date_precision || v.date_precision === 'unknown') return '';
            return s && e ? s + ' – ' + e : s || e;
        }
        var linkValues = [v.project_url].concat(Array.isArray(v.additional_project_urls) ? v.additional_project_urls : [])
            .filter(function (x) { return typeof x === 'string' && x; });
        return ownerForm(id, project ? null : 'Add a project', function (form) {
            var grid = el('div', 'rp-form__grid');
            grid.appendChild(field(form, 'Project name', textInput('project_name', v.project_name, 300)));
            var cat = el('select', 'rp-form__input');
            cat.name = 'project_category';
            cat.appendChild(new global.Option('Choose a category', ''));
            Object.keys(Model.PROJECT_CATEGORIES).forEach(function (k) { cat.appendChild(new global.Option(Model.PROJECT_CATEGORIES[k], k)); });
            cat.value = v.project_category || '';
            grid.appendChild(field(form, 'Category', cat, true));
            var desc = field(form, 'Description, in one line', textInput('summary', v.summary, 8000));
            desc.classList.add('rp-form__field--wide');
            grid.appendChild(desc);
            grid.appendChild(field(form, 'Organization', textInput('organization_name', v.organization_name, 300), true));
            var dates = textInput('dates', datesText(), 40);
            dates.placeholder = '2021 – 2023';
            grid.appendChild(field(form, 'Dates', dates, true));
            form.appendChild(grid);
            var links = el('fieldset', 'rp-form__links');
            var legend = el('legend', 'rp-form__label', 'Links: GitHub, a website');
            legend.appendChild(el('span', 'rp-form__opt', 'Optional'));
            links.appendChild(legend);
            var inputs = [];
            for (var i = 0; i < Model.MAX_PROJECT_LINKS; i += 1) {
                var input = textInput('link_' + i, linkValues[i] || '', 1000);
                input.type = 'url';
                input.id = id + '-link-' + i;
                input.placeholder = 'https://';
                input.setAttribute('aria-label', 'Link ' + (i + 1) + ' of ' + Model.MAX_PROJECT_LINKS);
                inputs.push(input);
                links.appendChild(input);
            }
            // Only the next empty link box shows, up to three.
            function reveal() {
                var shown = true;
                inputs.forEach(function (input) { input.hidden = !shown; if (!input.value.trim()) shown = false; });
            }
            inputs.forEach(function (input) { input.addEventListener('input', reveal); });
            reveal();
            form.appendChild(links);
        }, function (form) {
            var get = function (name) { return form.elements.namedItem(name).value.trim(); };
            var values = {project_name: get('project_name'), summary: get('summary'),
                project_category: get('project_category') || null, organization_name: get('organization_name') || null};
            if (!values.project_name || !values.summary) throw new Error('Add the project name and a one-line description.');
            var raw = get('dates').replace(/\s+/g, ' ');
            var start = null, end = null, precision = 'unknown';
            // Untouched dates are not sent, so a stored date and its detail are never rewritten.
            var keepDates = raw === datesText().replace(/\s+/g, ' ');
            if (raw && !keepDates) {
                var match = DATES_RE.exec(raw);
                if (!match) throw new Error('Write the dates as a year or year-month, like 2021 – 2023.');
                var a = match[1], b = match[2] || null;
                if (b && a.length !== b.length) throw new Error('Use the same detail for both dates, like 2021 – 2023.');
                precision = a.length === 4 ? 'year' : 'month';
                start = a + (precision === 'year' ? '-01-01' : '-01');
                end = b ? b + (precision === 'year' ? '-01-01' : '-01') : null;
            }
            if (!keepDates) {
                values.start_date = start;
                values.end_date = end;
                values.date_precision = precision;
            }
            var links = [];
            for (var i = 0; i < Model.MAX_PROJECT_LINKS; i += 1) {
                var link = form.elements.namedItem('link_' + i).value.trim();
                if (!link) continue;
                if (!Model.projectLink(link)) throw new Error('Links start with https:// and name a website.');
                links.push(link);
            }
            values.project_url = links[0] || null;
            values.additional_project_urls = links.slice(1);
            return values;
        }, function (values, attempt) { return saveEntry(project, 'project', values, attempt); }, onCancel);
    }

    function renderProjects(m) {
        var projects = m.sections.projects.filter(function (p) { return p.name; });
        if (!projects.length) return null;
        var c = card('projects', 'Projects');
        c.section.appendChild(c.heading);
        var ul = el('ul', 'rp-projects');
        projects.forEach(function (p, index) {
            var li = el('li', 'rp-project');
            var head = el('div', 'rp-project__head');
            head.appendChild(el('h3', 'rp-project__name', p.name));
            if (p.category) head.appendChild(el('span', 'rp-project__cat', p.category));
            li.appendChild(head);
            if (p.summary) li.appendChild(el('p', 'rp-project__line', p.summary));
            var meta = [p.organization, p.dates].filter(Boolean).join(' · ');
            if (meta) li.appendChild(el('p', 'rp-project__meta', meta));
            var foot = el('div', 'rp-project__foot');
            if (p.links.length) {
                var links = el('ul', 'rp-project__links');
                links.setAttribute('aria-label', p.name + ' links');
                p.links.forEach(function (l) {
                    var item = el('li');
                    var a = link(l.href, '', 'rp-link');
                    a.appendChild(icon('link'));
                    a.appendChild(doc.createTextNode(l.label));
                    a.target = '_blank';
                    a.rel = 'noopener noreferrer';
                    a.referrerPolicy = 'no-referrer';
                    a.setAttribute('aria-label', l.label + ' (opens in a new tab)');
                    item.appendChild(a);
                    links.appendChild(item);
                });
                foot.appendChild(links);
            }
            var edit = el('button', 'rp-link rp-project__edit', 'Edit');
            edit.type = 'button';
            edit.setAttribute('aria-label', 'Edit ' + p.name);
            edit.addEventListener('click', function () {
                if (li.querySelector('form')) return;
                li.classList.add('is-editing');
                var form = projectForm('resume-page-project-form-' + index, p, function () {
                    li.classList.remove('is-editing');
                    edit.focus();
                });
                li.appendChild(form);
                form.querySelector('input').focus();
            });
            foot.appendChild(edit);
            li.appendChild(foot);
            ul.appendChild(li);
        });
        c.section.appendChild(ul);
        return c.section;
    }

    /* "Add a project" lives in the Edit myself editor: the Projects section itself
     * appears only once a project exists (Pete, 10-13 decision 1c). */
    function renderAddProject() {
        var host = doc.getElementById('resume-page-add-project');
        if (!host || !commandsUrl) return;
        var slot = host.querySelector('[data-rp-add-project]');
        if (slot.querySelector('form')) return;
        var open = el('button', 'rp-btn rp-btn--outline rp-btn--sm', 'Add a project');
        open.type = 'button';
        open.addEventListener('click', function () {
            slot.replaceChildren(projectForm('resume-page-project-new', null, function () {
                slot.replaceChildren(open);
                open.focus();
            }));
            slot.querySelector('input').focus();
        });
        slot.replaceChildren(open);
        host.hidden = false;
    }

    function renderLookingAhead(m) {
        var c = card('looking-ahead', 'Looking Ahead', 'rp-ahead');
        c.heading.className = 'rp-kicker';
        // The member's own Looking Ahead picture fills the slot; without one there is no picture box.
        var pic = m.lookingAheadPicture;
        var picSrc = pic ? staticImagePath(pic.src) : null;
        if (picSrc) {
            var slot = el('div', 'rp-ahead__pic');
            var picture = el('picture');
            var phoneSrc = staticImagePath(pic.phoneSrc);
            if (phoneSrc) {
                var source = el('source');
                source.media = '(max-width: 959px)';
                source.srcset = phoneSrc;
                picture.appendChild(source);
            }
            var img = el('img');
            img.src = picSrc;
            img.alt = pic.alt ? String(pic.alt) : '';
            img.decoding = 'async';
            if (typeof pic.position === 'string' && /^\d{1,3}% \d{1,3}%$/.test(pic.position)) img.style.objectPosition = pic.position;
            picture.appendChild(img);
            slot.appendChild(picture);
            c.section.appendChild(slot);
        } else {
            c.section.classList.add('rp-ahead--text');
        }
        var t = el('div', 'rp-ahead__text');
        t.appendChild(c.heading);
        var shown;
        if (m.lookingAhead) {
            shown = el('p', 'rp-ahead__line', m.lookingAhead);
        } else {
            shown = el('div', 'rp-placeholder');
            shown.appendChild(el('span', 'rp-placeholder__tag', 'Placeholder'));
            shown.appendChild(el('p', 'rp-placeholder__line', 'Your Looking Ahead line goes here, in your own words.'));
            shown.appendChild(el('p', 'rp-placeholder__note',
                'One line in your own words, up to 120 characters. It stays hidden until you write it.'));
        }
        t.appendChild(shown);
        // The owner writes or edits the one line in place (D2). Member-written only: no AI line.
        if (commandsUrl) {
            var write = el('button', 'rp-link rp-ahead__edit', m.lookingAhead ? 'Edit' : 'Write your line');
            write.type = 'button';
            write.setAttribute('aria-label', m.lookingAhead ? 'Edit your Looking Ahead line' : 'Write your Looking Ahead line');
            write.addEventListener('click', function () {
                var entry = m.lookingAheadEntry;
                var form = ownerForm('resume-page-ahead-form', null, function (f) {
                    var input = textInput('wording', entry ? entry.text : '', Model.LOOKING_AHEAD_LIMIT);
                    f.appendChild(field(f, 'Your Looking Ahead line', input));
                }, function (f) {
                    var words = f.elements.namedItem('wording').value.trim();
                    if (!words) throw new Error('Write your line first. An empty line isn’t saved.');
                    var values = Object.assign({}, entry ? entry.item.values || {} : {}, entry ? entry.item.proposed_values || {} : {});
                    // A renamed entry (placed in Looking Ahead) keeps its own title.
                    return {title: (entry && typeof values.title === 'string' && values.title) || Model.LOOKING_AHEAD_TITLE, wording: words,
                        classification: values.classification === 'both' ? 'both' : 'work'};
                }, function (values, attempt) { return saveEntry(entry, 'knowledge', values, attempt); }, function () {
                    shown.hidden = false;
                    write.hidden = false;
                    write.focus();
                });
                shown.hidden = true;
                write.hidden = true;
                t.appendChild(form);
                form.querySelector('input').focus();
            });
            t.appendChild(write);
        }
        c.section.appendChild(t);
        return c.section;
    }

    function credentialColumn(title, rows, mapRow) {
        if (!rows.length) return null;
        var col = el('div', 'rp-creds__col');
        col.appendChild(el('h3', 'rp-creds__head', title));
        var ul = el('ul', 'rp-creds__list');
        rows.forEach(function (row) {
            var parts = mapRow(row);
            if (!parts[0]) return;
            var li = el('li');
            li.appendChild(el('b', '', parts[0]));
            var meta = el('span', 'rp-creds__meta');
            if (parts[1]) meta.appendChild(el('span', '', parts[1]));
            if (parts[1] && parts[2]) meta.appendChild(doc.createTextNode(' · '));
            if (parts[2]) meta.appendChild(el('em', '', parts[2]));
            if (meta.childNodes.length) li.appendChild(meta);
            ul.appendChild(li);
        });
        col.appendChild(ul);
        return col;
    }

    function renderCredentials(m) {
        var s = m.sections;
        var cols = [
            credentialColumn('Education', s.education, function (e) { return [e.title, e.institution, e.when]; }),
            credentialColumn('Certifications', s.certifications, function (c) { return [c.name, c.issuer, c.when]; }),
            credentialColumn('Awards & recognition', s.awards, function (a) { return [a.name, a.detail, a.when]; })
        ].filter(Boolean);
        if (!cols.length) return null;
        var c = card('credentials', 'Credentials');
        c.section.appendChild(c.heading);
        var grid = el('div', 'rp-creds rp-creds--' + cols.length);
        cols.forEach(function (col) { grid.appendChild(col); });
        c.section.appendChild(grid);
        return c.section;
    }

    function renderConstellation(m) {
        var stops = m.constellation;
        if (!stops.length) return null;
        var c = card('constellation-phone', 'See how the work became the story.', 'rp-const');
        var inner = el('div', 'rp-const__in');
        inner.appendChild(el('p', 'rp-kicker', 'Career constellation'));
        inner.appendChild(c.heading);
        var sky = el('div', 'rp-const__sky');
        var n = stops.length;
        var svg = doc.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'rp-const__line');
        svg.setAttribute('viewBox', '0 0 100 100');
        svg.setAttribute('preserveAspectRatio', 'none');
        svg.setAttribute('aria-hidden', 'true');
        var points = stops.map(function (_, i) {
            var t = n === 1 ? 0 : i / (n - 1);
            return {x: 6 + t * 88, y: 82 - t * 62};
        });
        var path = doc.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', points.map(function (p, i) { return (i ? 'L' : 'M') + p.x.toFixed(2) + ' ' + p.y.toFixed(2); }).join(' '));
        path.setAttribute('vector-effect', 'non-scaling-stroke');
        svg.appendChild(path);
        sky.appendChild(svg);
        var ol = el('ol', 'rp-const__stops');
        stops.forEach(function (stop, i) {
            var li = el('li', 'rp-stop rp-stop--' + stop.kind + (i % 2 ? ' rp-stop--above' : ' rp-stop--below'));
            li.style.setProperty('--x', points[i].x + '%');
            li.style.setProperty('--y', points[i].y + '%');
            var target = stop.kind === 'job' && chapters[stop.target] ? el('button', 'rp-stop__b') : el('a', 'rp-stop__b');
            if (target.tagName === 'BUTTON') {
                target.type = 'button';
                target.setAttribute('aria-label', stop.label + ', ' + stop.years + ': open the role');
                target.addEventListener('click', function () { openChapter(stop.target, true); });
            } else {
                target.href = stop.kind === 'job' ? '#rp-experience' : '#rp-credentials';
                target.setAttribute('aria-label', stop.label + ', ' + stop.years + ': see ' +
                    (stop.kind === 'job' ? 'Experience' : 'Credentials'));
            }
            target.appendChild(el('span', 'rp-stop__dot'));
            var lab = el('span', 'rp-stop__lab');
            lab.setAttribute('aria-hidden', 'true');
            lab.appendChild(el('b', '', stop.label));
            lab.appendChild(el('i', '', stop.years));
            target.appendChild(lab);
            li.appendChild(target);
            ol.appendChild(li);
        });
        sky.appendChild(ol);
        inner.appendChild(sky);
        c.section.appendChild(inner);
        return c.section;
    }

    function renderEnd(m) {
        if (!m.philosophy && !m.talk) return null;
        var c = card('talk', m.talk ? m.talk.title : 'My philosophy', 'rp-end');
        if (m.philosophy) {
            var ph = el('div', 'rp-end__philo');
            ph.appendChild(el('p', 'rp-kicker', 'My philosophy'));
            ph.appendChild(el('p', 'rp-end__quote', m.philosophy.quote));
            if (m.philosophy.text) ph.appendChild(el('p', 'rp-end__text', m.philosophy.text));
            c.section.appendChild(ph);
        }
        if (m.talk) {
            var talk = el('div', 'rp-end__talk');
            talk.appendChild(el('p', 'rp-kicker', 'Let’s talk'));
            talk.appendChild(c.heading);
            if (m.talk.text) talk.appendChild(el('p', 'rp-sec__sub', m.talk.text));
            if (m.talk.email && /^[^@\s]+@[^@\s]+$/.test(m.talk.email)) {
                var acts = el('div', 'rp-end__acts');
                acts.appendChild(link('mailto:' + m.talk.email, 'Contact me', 'rp-btn rp-btn--gold'));
                talk.appendChild(acts);
            }
            c.section.appendChild(talk);
        } else {
            c.heading.className = 'rp-sr';
            c.section.prepend(c.heading);
        }
        return c.section;
    }

    /* ---------- desktop career constellation: the live page's band ---------- */
    var bandHost = doc.getElementById('resume-page-band');
    var afterWrap = doc.getElementById('resume-page-after-wrap');
    var afterHost = doc.getElementById('resume-page-after');
    var SVG_NS = 'http://www.w3.org/2000/svg';
    var MAIN_D = 'M20 540 C110 470 160 440 216 442 C285 395 350 350 408 336 C510 320 560 320 600 330 C675 350 720 350 756 347 C835 360 920 350 984 336 C1070 318 1135 270 1200 220';
    var BRANCH_D = 'M600 330 C670 190 740 130 816 112 C885 100 950 90 1008 67 C1065 55 1110 40 1152 22';
    var OUTCOME_ICONS = ['file', 'users', 'repeat', 'direction', 'chart', 'box', 'bolt', 'shield'];

    function cIcon(name) {
        var svg = doc.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
        var use = doc.createElementNS(SVG_NS, 'use');
        use.setAttribute('href', '#rp-c-' + name);
        svg.appendChild(use);
        return svg;
    }
    function svgPath(d, className) {
        var path = doc.createElementNS(SVG_NS, 'path');
        path.setAttribute('d', d);
        if (className) path.setAttribute('class', className);
        return path;
    }

    function renderBand(m) {
        bandHost.replaceChildren();
        var stops = m.band || [];
        if (stops.length < 3) { bandHost.hidden = true; return false; }
        var story = m.careerStory || {};
        var section = el('section', 'rp-band__section');
        section.id = 'rp-constellation';
        section.tabIndex = -1;
        section.setAttribute('aria-labelledby', 'rp-band-title');
        var scene = el('div', 'rp-band__scene');

        var intro = el('header', 'rp-band__intro');
        intro.appendChild(el('p', 'rp-band__kicker', 'The Career Constellation'));
        var h2 = el('h2', '', 'See how the work became the story.');
        h2.id = 'rp-band-title';
        intro.appendChild(h2);
        intro.appendChild(el('em', '', 'And where the story is going next.'));
        intro.appendChild(el('span', 'rp-band__rule'));
        if (story.intro) intro.appendChild(el('p', 'rp-band__lead', story.intro));
        scene.appendChild(intro);

        var kinds = {};
        stops.forEach(function (stop) { kinds[stop.kind] = true; });
        var legend = el('div', 'rp-band__legend');
        legend.setAttribute('aria-label', 'Timeline categories');
        [['education', 'Education'], ['experience', 'Experience'], ['credential', 'Credentials'], ['future', 'Future']]
            .forEach(function (pair) {
                if (!kinds[pair[0]]) return;
                var span = el('span');
                var dot = el('i', 'is-' + pair[0]);
                dot.setAttribute('aria-hidden', 'true');
                span.appendChild(dot);
                span.appendChild(doc.createTextNode(pair[1]));
                legend.appendChild(span);
            });
        scene.appendChild(legend);

        if (story.evolution && story.evolution.text) {
            var evo = el('aside', 'rp-band__evolution');
            evo.setAttribute('aria-label', 'Career evolution');
            var small = el('small');
            small.appendChild(cIcon('repeat'));
            small.appendChild(doc.createTextNode('The evolution'));
            evo.appendChild(small);
            evo.appendChild(el('p', '', story.evolution.text));
            if (story.evolution.from && story.evolution.to) {
                evo.appendChild(el('span', '', 'Focus shift'));
                var strong = el('strong');
                strong.appendChild(doc.createTextNode(story.evolution.from + ' '));
                var arrow = el('i', '', '->');  // Inter draws its arrow ligature here, as on the live page
                arrow.setAttribute('aria-hidden', 'true');
                strong.appendChild(arrow);
                strong.appendChild(doc.createTextNode(' ' + story.evolution.to));
                evo.appendChild(strong);
            }
            scene.appendChild(evo);
        }

        var canvas = el('div', 'rp-band__canvas');
        var svg = doc.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('class', 'rp-band__line');
        svg.setAttribute('viewBox', '0 0 1200 560');
        svg.setAttribute('preserveAspectRatio', 'none');
        svg.setAttribute('aria-hidden', 'true');
        var hasBranch = stops.some(function (stop) { return stop.track === 'branch'; });
        svg.appendChild(svgPath(MAIN_D, 'rp-band__glow'));
        svg.appendChild(svgPath(MAIN_D));
        if (hasBranch) {
            svg.appendChild(svgPath(BRANCH_D, 'rp-band__glow rp-band__branch'));
            svg.appendChild(svgPath(BRANCH_D, 'rp-band__branch'));
        }
        if (stops.some(function (stop) { return stop.kind === 'future'; })) {
            var defs = doc.createElementNS(SVG_NS, 'defs');
            var marker = doc.createElementNS(SVG_NS, 'marker');
            [['id', 'rp-band-future-arrow'], ['viewBox', '0 0 10 10'], ['refX', '8'], ['refY', '5'], ['markerWidth', '8'],
                ['markerHeight', '8'], ['orient', 'auto-start-reverse']].forEach(function (a) { marker.setAttribute(a[0], a[1]); });
            marker.appendChild(svgPath('M 0 0 L 10 5 L 0 10 z'));
            defs.appendChild(marker);
            svg.insertBefore(defs, svg.firstChild);
            var tail = svgPath('M1152 22 C1170 17 1182 10 1194 2', 'rp-band__future-tail');
            tail.setAttribute('marker-end', 'url(#rp-band-future-arrow)');
            svg.appendChild(tail);
        }
        canvas.appendChild(svg);
        var junction = el('span', 'rp-band__junction');
        junction.setAttribute('aria-hidden', 'true');
        junction.appendChild(el('i'));
        canvas.appendChild(junction);

        var ol = el('ol', 'rp-band__nodes');
        stops.forEach(function (stop) {
            var li = el('li', 'rp-band-node is-' + stop.kind + ' label-' + stop.label + ' track-' + stop.track +
                (stop.onDark ? ' on-dark' : ''));
            li.style.setProperty('--node-x', stop.x + '%');
            li.style.setProperty('--node-y', stop.y + '%');
            var openRole = stop.kind === 'experience' && chapters[stop.target];
            var box = openRole ? el('button', 'rp-band-node__b') : el('div', 'rp-band-node__b');
            if (openRole) {
                box.type = 'button';
                box.addEventListener('click', function () { openChapter(stop.target, true); });
            }
            var marker = el('span', 'rp-band-node__marker');
            marker.setAttribute('aria-hidden', 'true');
            marker.appendChild(cIcon(stop.icon));
            box.appendChild(marker);
            var copy = el('span', 'rp-band-node__copy');
            if (stop.small) copy.appendChild(el('small', '', stop.small));
            copy.appendChild(el('strong', '', stop.title));
            if (stop.sub) copy.appendChild(el('span', 'rp-band-node__sub', stop.sub));
            if (stop.points && stop.points.length) {
                var ul = el('ul');
                stop.points.slice(0, 6).forEach(function (point) { ul.appendChild(el('li', '', point)); });
                copy.appendChild(ul);
            } else if (stop.text) {
                copy.appendChild(el('p', '', stop.text));
            }
            box.appendChild(copy);
            li.appendChild(box);
            ol.appendChild(li);
        });
        canvas.appendChild(ol);
        scene.appendChild(canvas);

        if (story.skills && story.skills.length) {
            var skills = el('div', 'rp-band__skills');
            skills.setAttribute('aria-label', 'Skills connecting the career chapters');
            story.skills.slice(0, 5).forEach(function (name) { skills.appendChild(el('span', '', name)); });
            scene.appendChild(skills);
        }
        if (story.evidence && story.evidence.metrics && story.evidence.metrics.length) {
            var ev = el('aside', 'rp-band__evidence');
            ev.setAttribute('aria-label', story.evidence.title || 'Evidence');
            ev.appendChild(el('h3', '', story.evidence.title || 'Evidence'));
            story.evidence.metrics.slice(0, 2).forEach(function (metric) {
                var span = el('span');
                span.appendChild(el('strong', '', metric.value));
                span.appendChild(doc.createTextNode(metric.label));
                ev.appendChild(span);
            });
            scene.appendChild(ev);
        }
        var outcomes = (story.outcomes && story.outcomes.length ? story.outcomes : m.highlights || []).slice(0, 8);
        if (outcomes.length) {
            var oc = el('section', 'rp-band__outcomes');
            oc.setAttribute('aria-labelledby', 'rp-band-outcomes-title');
            var oh = el('h3', '', 'Outcomes that matter');
            oh.id = 'rp-band-outcomes-title';
            oc.appendChild(oh);
            var row = el('div');
            row.style.setProperty('--outcome-count', String(outcomes.length));
            outcomes.forEach(function (metric, i) {
                var span = el('span');
                span.appendChild(cIcon(OUTCOME_ICONS[i % OUTCOME_ICONS.length]));
                span.appendChild(el('strong', '', metric.value));
                span.appendChild(doc.createTextNode(metric.label));
                row.appendChild(span);
            });
            oc.appendChild(row);
            scene.appendChild(oc);
        }
        if (story.quote || (story.traits && story.traits.length)) {
            var foot = el('footer', 'rp-band__footer');
            if (story.quote) foot.appendChild(el('blockquote', '', '“' + story.quote + '”'));
            var traits = el('div');
            (story.traits || []).slice(0, 5).forEach(function (trait) {
                var span = el('span');
                span.appendChild(cIcon(trait.icon || 'sparkles'));
                span.appendChild(el('strong', '', trait.label));
                if (trait.detail) span.appendChild(el('small', '', trait.detail));
                traits.appendChild(span);
            });
            foot.appendChild(traits);
            scene.appendChild(foot);
            var compass = el('span', 'rp-band__compass');
            compass.setAttribute('aria-hidden', 'true');
            compass.appendChild(cIcon('sparkles'));
            scene.appendChild(compass);
            scene.classList.add('has-footer');
        }
        section.appendChild(scene);
        bandHost.appendChild(section);
        bandHost.hidden = false;
        return true;
    }

    function renderAfter(m) {
        afterHost.replaceChildren();
        var end = renderEnd(m);
        if (end) afterHost.appendChild(end);
        afterWrap.hidden = !end;
        return end;
    }

    /* ---------- rail, jump bar, glance ---------- */
    function renderGlance(m) {
        ['resume-page-glance', 'resume-page-glance-phone'].forEach(function (id) {
            var box = doc.getElementById(id);
            if (!box) return;
            var list = box.querySelector('[data-rp-glance]');
            list.replaceChildren();
            m.glance.forEach(function (row) {
                var li = el('li');
                li.appendChild(icon(row.icon));
                var span = el('span');
                span.appendChild(el('b', '', row.title));
                if (row.sub) span.appendChild(el('span', 'rp-glance__sub', row.sub));
                li.appendChild(span);
                list.appendChild(li);
            });
            box.hidden = !m.glance.length;
        });
    }

    var NAV_ICONS = {overview: 'overview', story: 'story', skills: 'skills', experience: 'experience',
        projects: 'projects', 'looking-ahead': 'ahead', credentials: 'credentials', constellation: 'star', talk: 'mail'};
    function renderNav(entries) {
        secnav.replaceChildren();
        jump.replaceChildren();
        entries.forEach(function (entry) {
            var li = el('li');
            var a = link('#rp-' + entry.id, '', 'rp-secnav__a');
            a.dataset.target = entry.id;
            a.appendChild(icon(NAV_ICONS[entry.id] || 'overview'));
            a.appendChild(doc.createTextNode(entry.label));
            li.appendChild(a);
            secnav.appendChild(li);
            var option = new global.Option(entry.label, entry.id);
            jump.appendChild(option);
        });
        jumpBar.hidden = entries.length < 2;
        markCurrent('overview');
    }
    function markCurrent(id) {
        Array.prototype.forEach.call(secnav.querySelectorAll('a'), function (a) {
            if (a.dataset.target === id) a.setAttribute('aria-current', 'true');
            else a.removeAttribute('aria-current');
        });
        if (jump.value !== id && Array.prototype.some.call(jump.options, function (o) { return o.value === id; })) jump.value = id;
    }
    // After a jump, the chosen section stays marked until the member scrolls by themselves,
    // so a short section near the end of the page is not re-marked as its neighbour.
    var navLock = null;
    ['wheel', 'touchmove', 'keydown'].forEach(function (type) {
        global.addEventListener(type, function (event) {
            if (type === 'keydown' && ['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].indexOf(event.key) < 0) return;
            navLock = null;
        }, {passive: true});
    });
    // A section can have a desktop and a phone form (the constellation); use the one on screen.
    function sectionEl(id) {
        var wide = doc.getElementById('rp-' + id), phone = doc.getElementById('rp-' + id + '-phone');
        if (wide && wide.getClientRects().length) return wide;
        if (phone && phone.getClientRects().length) return phone;
        return wide || phone;
    }
    function goTo(id) {
        var target = sectionEl(id);
        if (!target) return;
        navLock = id;
        target.scrollIntoView({block: 'start', behavior: reduceMotion.matches ? 'auto' : 'smooth'});
        target.focus({preventScroll: true});
        markCurrent(id);
    }
    jump.addEventListener('change', function () { goTo(jump.value); });
    // Every in-page link (section list, glance, hero, constellation) moves focus with the scroll.
    root.addEventListener('click', function (event) {
        var a = event.target.closest('a[href^="#rp-"]');
        if (!a || !root.contains(a) || a.closest('#resume-page-editor')) return;
        var id = a.getAttribute('href').slice(4);
        if (!sectionEl(id)) return;
        event.preventDefault();
        goTo(id);
        if (global.history && global.history.replaceState) global.history.replaceState(null, '', '#rp-' + id);
    });

    var sectionObserver = null;
    function observeSections(entries) {
        if (sectionObserver) sectionObserver.disconnect();
        if (!global.IntersectionObserver) return;
        var visible = {};
        sectionObserver = new global.IntersectionObserver(function (records) {
            records.forEach(function (r) { visible[r.target.id.slice(3).replace(/-phone$/, '')] = r.isIntersecting ? r.intersectionRatio : 0; });
            var best = null;
            entries.forEach(function (entry) { if (!best && visible[entry.id] > 0) best = entry.id; });
            if (best && !navLock) markCurrent(best);
        }, {rootMargin: '-25% 0px -55% 0px', threshold: [0, 0.01]});
        entries.forEach(function (entry) {
            [doc.getElementById('rp-' + entry.id), doc.getElementById('rp-' + entry.id + '-phone')].forEach(function (node) {
                if (node) sectionObserver.observe(node);
            });
        });
    }

    /* ---------- the rail: always the full Ask panel (Pete, D1 review round 2) ----------
     * A rail taller than the window scrolls with the page so nothing in it is ever unreachable. */
    function fitRail() {
        if (!rail) return;
        var top = parseFloat(global.getComputedStyle(rail).top) || 0;
        rail.classList.remove('is-tall');
        if (global.innerWidth >= FOLD && rail.scrollHeight + top > global.innerHeight) rail.classList.add('is-tall');
    }

    /* ---------- shared layout token for the Guide (Lane C) ---------- */
    function leftColumnEdge() {
        if (global.innerWidth < FOLD || !rail) return 0;
        var box = rail.getBoundingClientRect();
        return Math.round(box.right);
    }
    function publishEdge() {
        doc.documentElement.style.setProperty('--resume-page-left-edge', leftColumnEdge() + 'px');
    }

    /* ---------- render ---------- */
    function render(m) {
        model = m;
        navEntries = [{id: 'overview', label: 'Overview'}];
        var builders = [
            ['story', renderStory, null],
            ['skills', renderSkills, 'Skills'],
            ['experience', renderExperience, 'Experience'],
            ['projects', renderProjects, 'Projects'],
            ['looking-ahead', renderLookingAhead, 'Looking Ahead'],
            ['credentials', renderCredentials, 'Credentials'],
            ['constellation-phone', renderConstellation, null]
        ];
        // A section holding an open owner form is kept as it is (its words untouched); every other
        // section is drawn afresh. Returns how many sections were kept.
        var keep = {};
        openForms = openForms.filter(function (f) { return f.form.isConnected; });
        openForms.forEach(function (f) {
            var section = f.form.closest('#resume-page-sections > section');
            if (section) keep[section.id] = section;
        });
        var keptCount = 0;
        sectionsHost.replaceChildren();
        bandHost.replaceChildren();
        bandHost.hidden = true;
        afterHost.replaceChildren();
        afterWrap.hidden = true;
        if (m.empty) {
            var empty = el('section', 'rp-card rp-sec rp-empty');
            empty.appendChild(el('h2', 'rp-sec__title', 'Your resume is empty so far'));
            empty.appendChild(el('p', 'rp-sec__sub', 'Use Edit myself to add your first section. Nothing is published until you choose to.'));
            sectionsHost.appendChild(empty);
        } else {
            builders.forEach(function (b) {
                var held = keep['rp-' + b[0]];
                var node = held || b[1](m);
                if (!node) return;
                if (held) keptCount += 1;
                sectionsHost.appendChild(node);
                if (b[2]) navEntries.push({id: b[0], label: b[2]});
            });
            // Desktop shows the live constellation band; phones show the simplified card instead.
            var hasBand = renderBand(m);
            if (hasBand || doc.getElementById('rp-constellation-phone')) navEntries.push({id: 'constellation', label: 'Career constellation'});
            if (renderAfter(m)) navEntries.push({id: 'talk', label: m.talk ? 'Let\u2019s talk' : 'My philosophy'});
        }
        renderHero(m);
        renderAddProject();
        renderGlance(m);
        renderNav(navEntries);
        observeSections(navEntries);
        if (global.PeerSlateResumePageAsk) global.PeerSlateResumePageAsk.setStarters(m);
        fitRail();
        publishEdge();
        root.dataset.state = 'ready';
        return keptCount;
    }

    /* ---------- reading the workspace: only a complete read is rendered ----------
     * A page that can't read everything never says the resume is empty. After a
     * good read, a later failed or incomplete read keeps what is shown and says so. */
    var lastGood = null;
    var STALE = 'Your resume couldn\u2019t be refreshed just now. You\u2019re seeing what was last loaded. Nothing was changed.';
    function showUnreadable(message) {
        savedNotice = false;  // a "Saved privately" notice never carries over to a later read
        if (lastGood) {
            root.dataset.state = 'stale';
            setStatus(STALE, 'error');
            return;
        }
        model = null;
        sectionsHost.replaceChildren();
        bandHost.replaceChildren();
        bandHost.hidden = true;
        afterHost.replaceChildren();
        afterWrap.hidden = true;
        ['resume-page-glance', 'resume-page-glance-phone'].forEach(function (id) {
            var box = doc.getElementById(id);
            if (box) box.hidden = true;
        });
        var card = el('section', 'rp-card rp-sec rp-unavailable');
        card.appendChild(el('h2', 'rp-sec__title', 'Your resume can\u2019t be shown right now'));
        card.appendChild(el('p', 'rp-sec__sub', message));
        sectionsHost.appendChild(card);
        navEntries = [{id: 'overview', label: 'Overview'}];
        renderNav(navEntries);
        root.dataset.state = 'unavailable';
        setStatus('', '');
    }
    function load() {
        var seq = ++loadSeq;
        root.dataset.state = 'loading';
        return global.fetch(workspaceUrl, {credentials: 'same-origin', headers: {Accept: 'application/json'}})
            .then(function (response) {
                return response.text().then(function (body) {
                    var payload = null;
                    try { payload = JSON.parse(body); } catch (error) { payload = null; }
                    return {ok: response.ok, status: response.status, payload: payload};
                });
            })
            .then(function (result) {
                if (seq !== loadSeq) return;
                var payload = result.payload;
                var readable = result.ok && payload && typeof payload === 'object' && Array.isArray(payload.items);
                if (!readable) {
                    showUnreadable(result.status === 503
                        ? 'Your saved resume is unavailable right now. Nothing was changed. Try again in a moment.'
                        : 'Your saved resume could not be read. Nothing was changed. Reload to try again.');
                    return;
                }
                var canonical = payload.capabilities && payload.capabilities.canonical_read;
                if (canonical !== 'ok') {
                    // Saved records could not all be read: never present this as the whole resume.
                    showUnreadable('Some of your saved records can\u2019t be read right now, so nothing is shown rather than an incomplete resume. Nothing was changed.');
                    return;
                }
                noteWorkspace(payload);
                var next = Model.fromWorkspace(payload, {displayName: displayName});
                // render() keeps any section that holds an open form, so the member's words stay put.
                var kept = render(next);
                lastGood = next;
                if (savedNotice) setStatus('Saved privately. Nothing was published.' + (kept ? ' Your unsaved words here are kept.' : ''), 'ok');
                else if (kept) setStatus('Something was saved elsewhere. Your unsaved words here are kept.', 'ok');
                else setStatus('', '');
                savedNotice = false;
            })
            .catch(function () {
                if (seq !== loadSeq) return;
                savedNotice = false;
                showUnreadable('Your saved resume could not be loaded. Check your connection and reload. Nothing was changed.');
            });
    }

    /* ---------- Edit myself (today's editor, unchanged) ---------- */
    var editButton = doc.getElementById('resume-page-edit');
    var editor = doc.getElementById('resume-page-editor');
    if (editButton && editor) {
        editButton.addEventListener('click', function () {
            var open = !editor.classList.contains('is-open');
            editor.classList.toggle('is-open', open);
            editButton.setAttribute('aria-expanded', String(open));
            editButton.textContent = open ? 'Close editor' : 'Edit myself';
            if (open) {
                var heading = editor.querySelector('#resume-editor-title');
                editor.scrollIntoView({block: 'start', behavior: reduceMotion.matches ? 'auto' : 'smooth'});
                if (heading) { heading.tabIndex = -1; heading.focus({preventScroll: true}); }
            }
        });
    }

    /* ---------- Continue with the Guide (D2) ----------
     * Opens the Guide panel only through its public open hook. Until the Guide publishes
     * that hook (PS-GUIDE-PANEL-001), the button stays absent: never a dead control. */
    var guideButton = doc.getElementById('resume-page-guide');
    function guideHook() {
        var panel = global.PeerSlateGuidePanel;
        return panel && typeof panel.open === 'function' ? panel : null;
    }
    function syncGuideButton() {
        if (guideButton) guideButton.hidden = !guideHook();
    }
    if (guideButton) {
        guideButton.addEventListener('click', function () {
            var panel = guideHook();
            if (!panel) { syncGuideButton(); return; }
            panel.open();
        });
        syncGuideButton();
        global.addEventListener('load', syncGuideButton);
    }

    doc.addEventListener('resume-private-draft-changed', function () { load(); });
    doc.addEventListener('resume-intake-fact-saved', function () { load(); });
    global.addEventListener('resize', function () { fitRail(); publishEdge(); });

    publishEdge();
    global.PeerSlateResumePage = Object.freeze({
        reload: load,
        leftColumnEdge: leftColumnEdge,
        foldWidth: FOLD,
        render: function (m) { render(m); setStatus('', ''); },
        state: function () { return model; },
        fitRail: fitRail
    });
    load();
})(window);
