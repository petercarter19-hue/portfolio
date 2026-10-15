/* Owner resume page: the one narrow view-model adapter (PS-RESUME-PAGE-OWNER-001).
 *
 * Everything the page shows passes through fromWorkspace(). It reads the
 * signed-in member's private draft workspace (server-derived identity; the
 * page never names an owner) and returns plain data. No markup is built here.
 *
 * SECTION_ORDER mirrors the Guide's single shared order
 * (services/resume_guide_contract.py GUIDE_SECTION_ORDER, B1 API v1). When B2's
 * item types land, only TYPE_SECTION and the readers below change.
 */
(function (global) {
    'use strict';

    var SECTION_ORDER = Object.freeze([
        'impact_statement', 'skills', 'experience', 'projects', 'education', 'certifications', 'awards'
    ]);
    var SECTION_LABELS = Object.freeze({
        impact_statement: 'Impact Statement', skills: 'Skills', experience: 'Experience',
        projects: 'Projects', education: 'Education', certifications: 'Certifications', awards: 'Awards'
    });
    // record_type -> shared section. impact_statement / project / award are the
    // B2 types; they map here so the swap is one place.
    var TYPE_SECTION = Object.freeze({
        impact_statement: 'impact_statement', skill: 'skills', role: 'experience', project: 'projects',
        education: 'education', credential: 'certifications', award: 'awards'
    });
    var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var LONG_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
        'September', 'October', 'November', 'December'];

    function text(value) {
        if (value === null || value === undefined) return '';
        return String(value).replace(/\s+/g, ' ').trim();
    }

    function valuesOf(item) {
        return Object.assign({}, item.values || {}, item.proposed_values || {});
    }

    function parseDate(value, precision) {
        var match = /^(\d{4})(?:-(\d{2}))?/.exec(text(value));
        if (!match || precision === 'unknown') return null;
        var month = match[2] && precision !== 'year' ? parseInt(match[2], 10) : null;
        return {year: parseInt(match[1], 10), month: month && month >= 1 && month <= 12 ? month : null};
    }

    function shortDate(parsed) {
        if (!parsed) return '';
        return parsed.month ? MONTHS[parsed.month - 1] + ' ' + parsed.year : String(parsed.year);
    }

    function longDate(parsed) {
        if (!parsed) return '';
        return parsed.month ? LONG_MONTHS[parsed.month - 1] + ' ' + parsed.year : String(parsed.year);
    }

    function sortKey(parsed) {
        return parsed ? parsed.year * 100 + (parsed.month || 0) : -1;
    }

    function initials(value) {
        var words = text(value).replace(/[^A-Za-z0-9 ]+/g, ' ').split(' ').filter(Boolean);
        if (!words.length) return '';
        var picked = words.filter(function (word) { return word.length > 1 && /^[A-Z0-9]/.test(word); });
        if (picked.length < 2) picked = words.filter(function (word) { return /^[A-Z0-9]/.test(word); });
        if (picked.length < 2) picked = words;
        return (picked[0].charAt(0) + (picked.length > 1 ? picked[picked.length - 1].charAt(0) : picked[0].charAt(1) || ''))
            .toUpperCase();
    }

    function firstName(displayName) {
        return text(displayName).split(' ')[0] || '';
    }

    function readRole(item) {
        var v = valuesOf(item), precision = v.date_precision;
        var start = parseDate(v.start_date, precision), end = parseDate(v.end_date, precision);
        // Only the member's own current flag means Present; a missing end date says nothing either way.
        var current = v.current_role === true;
        var dates = !start ? '' : current ? shortDate(start) + ' – Present'
            : end ? shortDate(start) + ' – ' + shortDate(end) : shortDate(start);
        return {
            key: item.record_key, org: text(v.employer_name), title: text(v.role_title),
            location: text(v.location_text), summary: text(v.summary), dates: dates.replace(/ – $/, ''),
            current: current, start: start, end: end, badge: initials(v.employer_name), bullets: []
        };
    }

    function readBullet(item) {
        var v = valuesOf(item);
        return {key: item.record_key, text: text(v.wording), parent: item.parent_key || item.parent_ref || null};
    }

    function educationStatus(v, start, end) {
        switch (v.education_status) {
        case 'completed': return shortDate(end);
        case 'in_progress': return 'In progress';
        case 'admitted': return start ? 'Admitted · starts ' + shortDate(start) : 'Admitted';
        case 'planned': return start ? 'Planned · starts ' + shortDate(start) : 'Planned';
        case 'paused': return 'Paused';
        case 'withdrawn': return 'Withdrawn';
        default: return shortDate(end);
        }
    }

    function readEducation(item) {
        var v = valuesOf(item), precision = v.date_precision;
        var start = parseDate(v.start_date, precision), end = parseDate(v.end_date, precision);
        var title = text(v.title) || [text(v.degree_name), text(v.field_of_study)].filter(Boolean).join(', ');
        return {
            key: item.record_key, title: title, institution: text(v.institution_name), status: v.education_status || '',
            summary: text(v.summary),
            when: educationStatus(v, start, end), start: start, end: end,
            upcoming: ['admitted', 'planned', 'in_progress'].indexOf(v.education_status) >= 0
        };
    }

    function readCredential(item) {
        var v = valuesOf(item);
        var issued = parseDate(v.issue_date, v.issue_date_precision || 'day');
        var when = v.completion_status === 'in_progress' ? 'In progress'
            : v.completion_status === 'planned' ? 'Planned'
            : v.completion_status === 'completed' ? (shortDate(issued) || 'Certified') : shortDate(issued);
        return {key: item.record_key, name: text(v.name), issuer: text(v.issuer), when: when,
            status: v.completion_status || '', issued: issued};
    }

    function readAward(item) {
        var v = valuesOf(item);
        var date = parseDate(v.award_date || v.issue_date || v.date, v.date_precision || 'year');
        return {key: item.record_key, name: text(v.name || v.title), detail: text(v.issuer || v.detail),
            when: shortDate(date) || text(v.year), date: date};
    }

    /* Projects (D2): B2's fields. Links are the member's own words: only https:// with a
     * host is kept, at most three, shown by site name, and nothing here ever fetches one. */
    var PROJECT_CATEGORIES = Object.freeze({
        software: 'Software', research: 'Research', community_volunteer: 'Community & volunteer',
        business_product: 'Business & product', creative_design: 'Creative & design', other: 'Other'
    });
    var MAX_PROJECT_LINKS = 3;

    function projectLink(raw) {
        if (typeof raw !== 'string') return null;
        var value = raw.trim();
        if (!value || value.length > 1000 || /[\s\u0000-\u001f\u007f\\]/.test(value)) return null;
        var match = /^https:\/\/([a-z0-9.-]+)(:\d{1,5})?(?:[\/?#]|$)/i.exec(value);
        if (!match) return null;
        var host = match[1].toLowerCase();
        if (host.indexOf('.') < 1 || /\.\.|^-|-$|\.$/.test(host)) return null;
        var site = host.replace(/^www\./, '');
        return {href: value, label: site === 'github.com' ? 'GitHub' : site};
    }

    function readProject(item) {
        var v = valuesOf(item), precision = v.date_precision;
        var start = parseDate(v.start_date, precision), end = parseDate(v.end_date, precision);
        var dates = start && end ? shortDate(start) + ' – ' + shortDate(end) : shortDate(start || end);
        var links = [];
        [v.project_url].concat(Array.isArray(v.additional_project_urls) ? v.additional_project_urls : [])
            .forEach(function (raw) {
                var entry = projectLink(raw);
                if (entry && links.length < MAX_PROJECT_LINKS &&
                    !links.some(function (l) { return l.href === entry.href; })) links.push(entry);
            });
        return {
            key: item.record_key, name: text(v.project_name), summary: text(v.summary),
            category: PROJECT_CATEGORIES[v.project_category] || '', organization: text(v.organization_name),
            dates: dates, links: links, item: item
        };
    }

    /* Looking Ahead (D2): the member's own one line, never an AI line. Identified as the server
     * places it (resume_publication_projection resume_section_for): first by its placement
     * (presentation_section "looking_ahead", or the label alias "Looking Ahead"), so a renamed
     * entry still counts; otherwise by the approved title "Looking Ahead" on a work entry. A
     * placement entry wins over a title-only one, and only one line is ever shown. The bound
     * My Story entry never counts. At most 120 UTF-16 units, the server's limit and the
     * browser's own maxlength. */
    var LOOKING_AHEAD_TITLE = 'Looking Ahead';
    var LOOKING_AHEAD_LIMIT = 120;
    var PLACED_SECTIONS = {looking_ahead: 'looking_ahead', 'Looking Ahead': 'looking_ahead', awards: 'awards',
        impact_statement: 'impact_statement', 'Impact Statement': 'impact_statement', 'Professional summary': 'impact_statement',
        projects: 'projects', Projects: 'projects', 'Independent Project': 'projects', contact: 'contact',
        'Contact details': 'contact', languages: 'languages', Languages: 'languages', Awards: 'awards',
        story: 'story', 'My Story': 'story'};

    // 2 = placed in Looking Ahead, 1 = titled "Looking Ahead" with no other placement, 0 = not Looking Ahead.
    function lookingAheadRank(item, payload) {
        if (item.record_type !== 'knowledge') return 0;
        if (payload && payload.story_entry_key && payload.story_entry_key === item.record_key) return 0;
        var v = valuesOf(item);
        var stated = v.presentation_section !== undefined ? v.presentation_section : item.presentation_section;
        var placed = typeof stated === 'string' ? PLACED_SECTIONS[stated] : undefined;
        if (placed) return placed === 'looking_ahead' ? 2 : 0;
        return v.title === LOOKING_AHEAD_TITLE && (v.classification === 'work' || v.classification === 'both') ? 1 : 0;
    }

    /* Highlight tiles (D2): B2's highlight_refs, at most four saved accomplishment keys.
     * Each tile is resolved now from that saved bullet's own metric_value and metric_label
     * (its own wording when it has no label) and its role: a reference, never a copy. A
     * missing, orphaned, role-less or number-less bullet gives no tile. The row shows only
     * when two to four resolve (Q4: "2 to 4 tiles, never more"). */
    var MAX_HIGHLIGHTS = 4, MIN_HIGHLIGHTS = 2;

    function highlightTiles(payload, accomplishments, roleByKey) {
        var refs = payload && Array.isArray(payload.highlight_refs) ? payload.highlight_refs : [];
        var tiles = [], seen = {};
        refs.forEach(function (ref) {
            if (typeof ref !== 'string' || seen[ref] || tiles.length >= MAX_HIGHLIGHTS) return;
            seen[ref] = true;
            var item = accomplishments[ref];
            if (!item) return;
            var v = valuesOf(item), parent = item.parent_key || item.parent_ref || null;
            var value = text(v.metric_value);
            if (!value || !parent || !roleByKey[parent]) return;
            tiles.push({key: ref, value: value, label: text(v.metric_label) || text(v.wording), role: parent,
                state: 'saved'});
        });
        return tiles.length >= MIN_HIGHLIGHTS ? tiles : [];
    }

    function readSkill(item) {
        var v = valuesOf(item);
        return {key: item.record_key, name: text(v.name), summary: text(v.summary), lines: []};
    }

    /* ---------- Skills in Practice: the resume lines that show a skill ----------
     * The draft holds no skill-to-bullet link, so the lines are derived here,
     * read-only, from data already in the member's own draft: the skill's name
     * and summary, and the accomplishment bullets with the role they belong to.
     * A bullet shows a skill when (in this order of strength):
     *   0. it contains the skill's own summary line, or the summary contains it;
     *   1. its lead-in label ("Name. ..." / "Name: ...") is the skill's name;
     *   2. it mentions the skill's name as a whole phrase.
     * Ties keep page order (current role first, then newest; unlinked last).
     * At most three lines; a skill's own summary that matches no bullet is shown
     * as its own line, without a role. Nothing is reworded except that a lead-in
     * label equal to the skill's name is not repeated under the skill's name. */
    var MAX_SKILL_LINES = 3;

    function norm(value) {
        return text(value).toLowerCase().replace(/[‘’]/g, "'");
    }

    function leadIn(wording) {
        var match = /^([^.:]{2,60})[.:]\s+(\S[\s\S]*)$/.exec(text(wording));
        return match ? {label: match[1], rest: match[2]} : null;
    }

    function hasPhrase(haystack, phrase) {
        if (phrase.length < 2) return false;
        var at = haystack.indexOf(phrase);
        while (at >= 0) {
            var before = at === 0 || !/[a-z0-9]/.test(haystack.charAt(at - 1));
            var end = at + phrase.length;
            var after = end >= haystack.length || !/[a-z0-9]/.test(haystack.charAt(end));
            if (before && after) return true;
            at = haystack.indexOf(phrase, at + 1);
        }
        return false;
    }

    function skillLines(skill, bullets) {
        var name = norm(skill.name), summary = norm(skill.summary);
        var ranked = [];
        bullets.forEach(function (bullet, order) {
            var wording = norm(bullet.text), lead = leadIn(bullet.text);
            var body = lead ? norm(lead.rest) : wording;
            var rank = -1;
            if (summary.length >= 12 && (wording.indexOf(summary) >= 0 || (body.length >= 12 && summary.indexOf(body) >= 0))) rank = 0;
            else if (lead && norm(lead.label) === name) rank = 1;
            else if (hasPhrase(wording, name)) rank = 2;
            if (rank < 0) return;
            var shown = lead && norm(lead.label) === name ? lead.rest : bullet.text;
            ranked.push({rank: rank, order: order, line: {key: bullet.key, text: shown, roleKey: bullet.role ? bullet.role.key : null,
                employer: bullet.role ? (bullet.role.org || bullet.role.title) : '',
                title: bullet.role && bullet.role.org ? bullet.role.title : '', dates: bullet.role ? bullet.role.dates : ''}});
        });
        ranked.sort(function (a, b) { return (a.rank - b.rank) || (a.order - b.order); });
        var lines = ranked.map(function (r) { return r.line; });
        if (skill.summary && !ranked.some(function (r) { return r.rank === 0; })) {
            lines.unshift({key: skill.key + ':summary', text: skill.summary, roleKey: null, employer: '', title: '', dates: ''});
        }
        return lines.slice(0, MAX_SKILL_LINES);
    }

    function readStatement(item) {
        var v = valuesOf(item);
        return text(v.wording || v.text || v.summary);
    }

    function emptySections() {
        var sections = {};
        SECTION_ORDER.forEach(function (key) { sections[key] = []; });
        return sections;
    }

    function glance(sections) {
        var rows = [];
        var education = sections.education.slice();
        var done = education.filter(function (e) { return e.status === 'completed'; })
            .sort(function (a, b) { return sortKey(b.end) - sortKey(a.end); })[0];
        var next = education.filter(function (e) { return e.upcoming; })
            .sort(function (a, b) { return sortKey(b.start) - sortKey(a.start); })[0];
        if (done) rows.push({icon: 'degree', title: done.title, sub: done.institution});
        if (next) {
            var sub = next.status === 'in_progress' ? 'In progress'
                : (next.start ? 'Starting ' + longDate(next.start) : next.institution);
            rows.push({icon: 'next', title: next.title, sub: sub});
        }
        var cert = sections.certifications.filter(function (c) { return c.status === 'completed'; })[0];
        if (cert) rows.push({icon: 'cert', title: cert.name, sub: cert.issuer});
        var award = sections.awards[0];
        if (award) rows.push({icon: 'award', title: award.name,
            sub: [award.detail, award.when].filter(Boolean).join(' · ')});
        return rows.slice(0, 4);
    }

    function constellation(sections) {
        var stops = [];
        sections.experience.forEach(function (role) {
            if (!role.start) return;
            stops.push({kind: 'job', target: role.key, label: role.org || role.title, sort: sortKey(role.start),
                years: role.start.year + (role.current ? '–now' : (role.end && role.end.year !== role.start.year
                    ? '–' + role.end.year : ''))});
        });
        sections.education.forEach(function (edu) {
            var date = edu.status === 'completed' ? edu.end : edu.start;
            if (!date || edu.status === 'withdrawn') return;
            var prefix = {admitted: 'Starts ', planned: 'Starts ', in_progress: 'Since ', paused: 'Paused \u00b7 '}[edu.status] || '';
            if (!prefix && edu.status !== 'completed') return;
            stops.push({kind: edu.status === 'admitted' || edu.status === 'planned' ? 'future' : 'edu', target: null,
                label: edu.title, sort: sortKey(date), years: prefix + date.year});
        });
        sections.certifications.forEach(function (cert) {
            if (!cert.issued || cert.status !== 'completed') return;
            stops.push({kind: 'edu', target: null, label: cert.name, sort: sortKey(cert.issued),
                years: String(cert.issued.year)});
        });
        stops.sort(function (a, b) { return a.sort - b.sort; });
        return stops.length >= 3 ? stops.slice(-10) : [];
    }


    /* ---------- the desktop career constellation (the live page's design) ----------
     * The live scene draws one main path and an upward branch from a junction in
     * a 1200 x 560 box. Stops are placed on those curves from the member's own
     * dates: everything up to and including the first role sits before the
     * junction; later roles continue on the main path; later education and
     * certifications rise on the branch. Nothing here is specific to one member. */
    var MAIN_PATH = [[20, 540], [110, 470, 160, 440, 216, 442], [285, 395, 350, 350, 408, 336], [510, 320, 560, 320, 600, 330],
        [675, 350, 720, 350, 756, 347], [835, 360, 920, 350, 984, 336], [1070, 318, 1135, 270, 1200, 220]];
    var BRANCH_PATH = [[600, 330], [670, 190, 740, 130, 816, 112], [885, 100, 950, 90, 1008, 67], [1065, 55, 1110, 40, 1152, 22]];
    var TRACKS = {pre: [7.5, 34], main: [63, 82], branch: [68, 95.2]};
    var TRACK_LIMITS = {pre: 4, main: 3, branch: 3};
    var JOB_ICONS = ['plane', 'building', 'direction'];

    function curveY(path, xPercent) {
        var targetX = xPercent * 12, best = null, start = path[0];
        for (var i = 1; i < path.length; i += 1) {
            var c = path[i];
            for (var step = 0; step <= 60; step += 1) {
                var t = step / 60, u = 1 - t;
                var x = u * u * u * start[0] + 3 * u * u * t * c[0] + 3 * u * t * t * c[2] + t * t * t * c[4];
                var y = u * u * u * start[1] + 3 * u * u * t * c[1] + 3 * u * t * t * c[3] + t * t * t * c[5];
                if (!best || Math.abs(x - targetX) < best.d) best = {d: Math.abs(x - targetX), y: y};
            }
            start = [c[4], c[5]];
        }
        return Math.round(best.y / 560 * 1000) / 10;
    }

    function spread(range, count) {
        if (count <= 1) return [range === TRACKS.pre ? range[1] : range[0]];
        var out = [];
        for (var i = 0; i < count; i += 1) out.push(Math.round((range[0] + (range[1] - range[0]) * i / (count - 1)) * 10) / 10);
        return out;
    }

    function yearRange(role) {
        if (!role.start) return '';
        if (role.current === true) return role.start.year + '-Present';
        return role.end && role.end.year !== role.start.year ? role.start.year + '-' + role.end.year : String(role.start.year);
    }

    function bandStops(sections) {
        var events = [], jobIndex = 0, eduIndex = 0;
        sections.experience.slice().sort(function (a, b) { return sortKey(a.start) - sortKey(b.start); })
            .forEach(function (role) {
                if (!role.start) return;
                events.push({kind: 'experience', target: role.key, sort: sortKey(role.start), small: yearRange(role),
                    title: role.org || role.title, sub: role.org ? role.title : '',
                    points: (role.constellationPoints && role.constellationPoints.length ? role.constellationPoints
                        : role.bullets.slice(0, 3).map(function (b) { return b.text; })),
                    text: role.summary});
            });
        sections.education.forEach(function (edu) {
            var date = edu.status === 'completed' ? edu.end : edu.start;
            if (!date || edu.status === 'withdrawn') return;
            var future = edu.status === 'admitted' || edu.status === 'planned';
            var label = future ? 'Expected ' + date.year + ' start'
                : {completed: 'Completed', in_progress: 'In progress', paused: 'Paused'}[edu.status];
            if (!label) return;
            events.push({kind: future ? 'future' : 'education', target: null, sort: sortKey(date),
                small: label,
                title: edu.title, sub: edu.institution, points: [], text: edu.summary || ''});
        });
        sections.certifications.forEach(function (cert) {
            if (cert.status !== 'completed') return;
            events.push({kind: 'credential', target: null, sort: cert.issued ? sortKey(cert.issued) : 999999,
                small: 'Certified', title: cert.name, sub: cert.issuer, points: [], text: cert.summary || ''});
        });
        if (events.length < 3) return [];
        // Future plans always close the branch; undated certifications sit just before them.
        events.sort(function (a, b) { return ((a.kind === 'future') - (b.kind === 'future')) || (a.sort - b.sort); });
        var firstJob = -1;
        events.forEach(function (e, i) { if (firstJob < 0 && e.kind === 'experience') firstJob = i; });
        var split = firstJob < 0 ? Math.ceil(events.length / 3) - 1 : firstJob;
        var tracks = {pre: [], main: [], branch: []};
        events.forEach(function (e, i) {
            if (i <= split) tracks.pre.push(e);
            else if (e.kind === 'experience') tracks.main.push(e);
            else tracks.branch.push(e);
        });
        var stops = [];
        Object.keys(tracks).forEach(function (name) {
            var list = tracks[name].slice(-TRACK_LIMITS[name]);
            var xs = spread(TRACKS[name], list.length);
            list.forEach(function (e, i) {
                e.track = name;
                e.x = xs[i];
                e.y = curveY(name === 'branch' ? BRANCH_PATH : MAIN_PATH, e.x);
                e.label = e.y < 10 ? 'below' : 'above';
                e.onDark = e.x < 45;
                if (e.kind === 'experience') e.icon = JOB_ICONS[(jobIndex++) % JOB_ICONS.length];
                else if (e.kind === 'education') e.icon = (eduIndex++) % 2 ? 'book' : 'graduation';
                else e.icon = e.kind === 'credential' ? 'award' : 'sparkles';
                stops.push(e);
            });
        });
        return stops.sort(function (a, b) { return a.x - b.x; });
    }

    /* A privately moved item (B3b "Move to"): the owner's page shows it in its new place and
     * type. The draft row keeps the canonical (base) type and values for the publisher; a
     * confirmed move adds the exact `conversion` descriptor and `conversion_destination`
     * {record_type, parent_key, values}. Only a well-formed confirmed descriptor that agrees
     * with its destination is followed; any other `conversion` hides the row rather than
     * showing it in a place it no longer belongs. Without `conversion` the row is unchanged. */
    var CONVERSION_KEYS = ['base_access_revision', 'base_content_token', 'base_record_type', 'conversion_op_ref',
        'destination_parent_ref', 'destination_record_type', 'state'];

    function effectiveItem(item) {
        if (!item || !Object.prototype.hasOwnProperty.call(item, 'conversion')) return item;
        var c = item.conversion, d = item.conversion_destination;
        var ok = c && typeof c === 'object' && !Array.isArray(c) &&
            Object.keys(c).sort().join() === CONVERSION_KEYS.join() && c.state === 'confirmed_private' &&
            c.base_record_type === item.record_type &&
            d && typeof d === 'object' && typeof d.record_type === 'string' && d.record_type === c.destination_record_type &&
            (d.parent_key || null) === (c.destination_parent_ref || null) &&
            d.values && typeof d.values === 'object' && !Array.isArray(d.values);
        if (!ok) return null;
        var moved = Object.assign({}, item);
        moved.record_type = d.record_type;
        moved.parent_key = d.parent_key || null;
        delete moved.parent_ref;
        moved.values = d.values;
        moved.proposed_values = null;
        return moved;
    }

    function fromWorkspace(payload, options) {
        options = options || {};
        var name = text(options.displayName);
        var sections = emptySections();
        var bullets = [], story = null, statement = '', lookingAhead = null, accomplishments = {};
        var items = (payload && payload.items) || [];
        items.forEach(function (raw) {
            var item = effectiveItem(raw);
            if (!item || item.orphaned) return;
            var type = item.record_type;
            if (type === 'accomplishment') {
                bullets.push(readBullet(item));
                accomplishments[item.record_key] = item;
                return;
            }
            if (type === 'knowledge') {
                var rank = lookingAheadRank(item, payload);
                if (rank) {
                    if (!lookingAhead || rank > lookingAhead.rank) {
                        lookingAhead = {key: item.record_key, text: text(valuesOf(item).wording), item: item, rank: rank};
                    }
                    return;
                }
                if (payload.story_entry_key && item.record_key === payload.story_entry_key) {
                    var sv = valuesOf(item);
                    if (sv.classification === 'personal' && text(sv.wording)) {
                        story = {title: text(sv.title) || 'My Story', text: text(sv.wording)};
                    }
                }
                return;
            }
            var section = TYPE_SECTION[type];
            if (!section) return;
            if (section === 'impact_statement') { statement = statement || readStatement(item); return; }
            var reader = {skills: readSkill, experience: readRole, projects: readProject, education: readEducation,
                certifications: readCredential, awards: readAward}[section];
            var row = reader(item);
            if (row) sections[section].push(row);
        });
        if (statement) sections.impact_statement.push({key: 'impact_statement', text: statement});
        sections.experience.sort(function (a, b) {
            if (a.current !== b.current) return a.current ? -1 : 1;
            return sortKey(b.start) - sortKey(a.start);
        });
        sections.education.sort(function (a, b) {
            return sortKey(b.end || b.start) - sortKey(a.end || a.start);
        });
        var roleByKey = {};
        sections.experience.forEach(function (role) { roleByKey[role.key] = role; });
        var unlinked = [];
        bullets.forEach(function (bullet) {
            if (!bullet.text) return;
            if (bullet.parent && roleByKey[bullet.parent]) roleByKey[bullet.parent].bullets.push(bullet);
            else unlinked.push(bullet);
        });
        // Bullets in page order (roles as shown, then the ones not linked to a role) for Skills in Practice.
        var ordered = [];
        sections.experience.forEach(function (role) {
            role.bullets.forEach(function (bullet) { ordered.push({key: bullet.key, text: bullet.text, role: role}); });
        });
        unlinked.forEach(function (bullet) { ordered.push({key: bullet.key, text: bullet.text, role: null}); });
        sections.skills.forEach(function (skill) { skill.lines = skillLines(skill, ordered); });
        var currentRole = sections.experience.filter(function (role) { return role.current === true; })[0];
        var model = {
            person: {
                name: name, firstName: firstName(name), initials: initials(name),
                headline: currentRole ? currentRole.title : '', statement: statement,
                photo: null, contact: []
            },
            highlights: highlightTiles(payload, accomplishments, roleByKey), story: story, sections: sections,
            unlinked: unlinked, lookingAhead: lookingAhead && lookingAhead.text ? lookingAhead.text : null,
            lookingAheadEntry: lookingAhead, lookingAheadPicture: null, philosophy: null, talk: null,
            draftVersion: payload && Number.isInteger(payload.draft_version) ? payload.draft_version : null
        };
        model.glance = glance(sections);
        model.constellation = constellation(sections);
        model.band = bandStops(sections);
        model.careerStory = {intro: '', evolution: null, evidence: null, quote: '', traits: [],
            skills: sections.skills.map(function (k) { return k.name; }).filter(Boolean).slice(0, 5), outcomes: []};
        model.empty = SECTION_ORDER.every(function (key) { return !sections[key].length; }) && !story && !unlinked.length;
        return model;
    }

    global.PeerSlateResumePageModel = Object.freeze({
        SECTION_ORDER: SECTION_ORDER, SECTION_LABELS: SECTION_LABELS, TYPE_SECTION: TYPE_SECTION,
        MAX_SKILL_LINES: MAX_SKILL_LINES, PROJECT_CATEGORIES: PROJECT_CATEGORIES, MAX_PROJECT_LINKS: MAX_PROJECT_LINKS,
        LOOKING_AHEAD_TITLE: LOOKING_AHEAD_TITLE, LOOKING_AHEAD_LIMIT: LOOKING_AHEAD_LIMIT,
        MAX_HIGHLIGHTS: MAX_HIGHLIGHTS, MIN_HIGHLIGHTS: MIN_HIGHLIGHTS, projectLink: projectLink, fromWorkspace: fromWorkspace, skillLines: skillLines, glance: glance, constellation: constellation, bandStops: bandStops, curveY: curveY
    });
})(window);
