/* Owner resume page renderer and layout behaviour (PS-RESUME-PAGE-OWNER-001, D1).
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
    var railAsk = doc.getElementById('resume-page-ask-rail');
    var mainAsk = doc.getElementById('resume-page-ask-main');
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
        if (person.photo && person.photo.src && /^\/static\//.test(person.photo.src)) {
            var img = el('img');
            img.src = person.photo.src;
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
        var hl = hero.querySelector('[data-rp-highlights]');
        hl.replaceChildren();
        (m.highlights || []).slice(0, 4).forEach(function (h) {
            var button = el('button', 'rp-hl');
            button.type = 'button';
            button.appendChild(el('strong', '', h.value));
            button.appendChild(el('span', 'rp-hl__label', h.label));
            if (h.role) {
                var em = el('em', '', 'See the role');
                em.appendChild(icon('next'));
                button.appendChild(em);
                button.addEventListener('click', function () { openChapter(h.role, true); });
            }
            hl.appendChild(button);
        });
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

    function renderSkills(m) {
        var skills = m.sections.skills.filter(function (s) { return s.name; });
        if (!skills.length) return null;
        var c = card('skills', 'Skills in Practice');
        var head = el('div', 'rp-sec__head');
        head.appendChild(c.heading);
        var withLines = skills.filter(function (s) { return s.line; });
        if (withLines.length) head.appendChild(el('p', 'rp-sec__sub', 'Pick a skill to see the line on the resume that shows it.'));
        c.section.appendChild(head);
        var wrap = el('div', withLines.length ? 'rp-skills' : 'rp-skills rp-skills--plain');
        var grid = el('ul', 'rp-skills__grid');
        var panel = el('div', 'rp-skills__line');
        panel.id = 'rp-skills-line';
        panel.setAttribute('aria-live', 'polite');
        var buttons = [];
        function show(skill, button) {
            buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(b === button)); });
            panel.replaceChildren(el('p', 'rp-kicker', skill.name), el('p', 'rp-skills__quote', skill.line));
        }
        skills.forEach(function (skill) {
            var li = el('li');
            if (skill.line) {
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

    function renderProjects(m) {
        var projects = m.sections.projects.filter(function (p) { return p.name; });
        if (!projects.length) return null;
        var c = card('projects', 'Projects');
        c.section.appendChild(c.heading);
        var ul = el('ul', 'rp-projects');
        projects.forEach(function (p) {
            var li = el('li');
            li.appendChild(el('b', '', p.name));
            if (p.summary) li.appendChild(el('span', '', p.summary));
            ul.appendChild(li);
        });
        c.section.appendChild(ul);
        return c.section;
    }

    function renderLookingAhead(m) {
        var c = card('looking-ahead', 'Looking Ahead', 'rp-ahead');
        c.heading.className = 'rp-kicker';
        c.section.appendChild(el('div', 'rp-ahead__pic'));
        var t = el('div', 'rp-ahead__text');
        t.appendChild(c.heading);
        if (m.lookingAhead) {
            t.appendChild(el('p', 'rp-ahead__line', m.lookingAhead));
        } else {
            var ph = el('div', 'rp-placeholder');
            ph.appendChild(el('span', 'rp-placeholder__tag', 'Placeholder'));
            ph.appendChild(el('p', 'rp-placeholder__line', 'Your Looking Ahead line goes here, in your own words.'));
            ph.appendChild(el('p', 'rp-placeholder__note',
                'One line in your own words, up to 120 characters. It stays hidden until you write it.'));
            t.appendChild(ph);
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

    /* ---------- the rail Ask grows when the main card scrolls away ---------- */
    var askObserver = null, mainAskAway = false;
    function railHasRoom() {
        if (!rail || !railAsk) return false;
        var mores = railAsk.querySelectorAll('[data-rp-ask-more] > *');
        var extra = 0;
        Array.prototype.forEach.call(mores, function (node) { extra += node.scrollHeight; });
        var grown = railAsk.classList.contains('is-grown');
        var railHeight = rail.scrollHeight + (grown ? 0 : extra);
        var top = parseFloat(global.getComputedStyle(rail).top) || 0;
        // 16px hysteresis so the panel never flickers at the boundary.
        return railHeight + top + (grown ? 0 : 16) <= global.innerHeight;
    }
    function updateRailAsk() {
        if (!railAsk) return;
        var desktop = global.innerWidth >= FOLD;
        var conversation = railAsk.querySelector('[data-rp-ask-log]');
        var talking = conversation && !conversation.hidden;
        var grow = desktop && (talking || (mainAskAway && railHasRoom()));
        railAsk.classList.toggle('is-grown', grow);
        Array.prototype.forEach.call(railAsk.querySelectorAll('[data-rp-ask-more]'), function (region) {
            if (grow) region.removeAttribute('inert'); else region.setAttribute('inert', '');
        });
        railAsk.dataset.state = grow ? 'grown' : 'compact';
        // A rail taller than the window scrolls with the page so nothing in it is ever unreachable.
        var top = parseFloat(global.getComputedStyle(rail).top) || 0;
        rail.classList.remove('is-tall');
        if (desktop && rail.scrollHeight + top > global.innerHeight) rail.classList.add('is-tall');
    }
    function watchMainAsk() {
        if (!mainAsk || !global.IntersectionObserver) return;
        askObserver = new global.IntersectionObserver(function (records) {
            records.forEach(function (r) {
                // "Scrolled away" means the card left above the viewport.
                mainAskAway = !r.isIntersecting && r.boundingClientRect.bottom <= (r.rootBounds ? r.rootBounds.top : 0) + 1;
            });
            updateRailAsk();
        }, {threshold: 0});
        askObserver.observe(mainAsk);
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
                var node = b[1](m);
                if (!node) return;
                sectionsHost.appendChild(node);
                if (b[2]) navEntries.push({id: b[0], label: b[2]});
            });
            // Desktop shows the live constellation band; phones show the simplified card instead.
            var hasBand = renderBand(m);
            if (hasBand || doc.getElementById('rp-constellation-phone')) navEntries.push({id: 'constellation', label: 'Career constellation'});
            if (renderAfter(m)) navEntries.push({id: 'talk', label: m.talk ? 'Let\u2019s talk' : 'My philosophy'});
        }
        renderHero(m);
        renderGlance(m);
        renderNav(navEntries);
        observeSections(navEntries);
        if (global.PeerSlateResumePageAsk) global.PeerSlateResumePageAsk.setStarters(m);
        updateRailAsk();
        publishEdge();
        root.dataset.state = 'ready';
    }

    /* ---------- reading the workspace: only a complete read is rendered ----------
     * A page that can't read everything never says the resume is empty. After a
     * good read, a later failed or incomplete read keeps what is shown and says so. */
    var lastGood = null;
    var STALE = 'Your resume couldn\u2019t be refreshed just now. You\u2019re seeing what was last loaded. Nothing was changed.';
    function showUnreadable(message) {
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
                var next = Model.fromWorkspace(payload, {displayName: displayName});
                render(next);
                lastGood = next;
                setStatus('', '');
            })
            .catch(function () {
                if (seq !== loadSeq) return;
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

    doc.addEventListener('resume-private-draft-changed', function () { load(); });
    doc.addEventListener('resume-intake-fact-saved', function () { load(); });
    global.addEventListener('resize', function () { updateRailAsk(); publishEdge(); });
    if (reduceMotion.addEventListener) reduceMotion.addEventListener('change', updateRailAsk);

    watchMainAsk();
    publishEdge();
    global.PeerSlateResumePage = Object.freeze({
        reload: load,
        leftColumnEdge: leftColumnEdge,
        foldWidth: FOLD,
        render: function (m) { render(m); setStatus('', ''); },
        state: function () { return model; },
        updateRailAsk: updateRailAsk
    });
    load();
})(window);
