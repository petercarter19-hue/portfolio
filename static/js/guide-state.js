/* Detached B1 working-set consumer. The server owns order, counts and identity. */
(function (global) {
    'use strict';
    function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
    function text(value) { return typeof value === 'string' && value.length > 0; }
    function count(value) { return Number.isSafeInteger(value) && value >= 0; }
    function freeze(value) {
        if (value && typeof value === 'object') {
            Object.keys(value).forEach(function (key) { freeze(value[key]); });
            Object.freeze(value);
        }
        return value;
    }
    function counts(value, keys) {
        return object(value) && keys.every(function (key) { return count(value[key]); });
    }
    var countKeys = ['saved', 'waiting', 'hidden', 'skipped', 'updates_waiting'];
    function validate(payload) {
        if (!object(payload) || payload.success !== true || payload.schema_version !== 1 || payload.load_state !== 'loaded' ||
            !Array.isArray(payload.section_order) || !payload.section_order.length ||
            !payload.section_order.every(text) || new Set(payload.section_order).size !== payload.section_order.length ||
            !Array.isArray(payload.sections) || payload.sections.length !== payload.section_order.length ||
            !Array.isArray(payload.unplaced) || !Array.isArray(payload.non_tab_items) ||
            !Array.isArray(payload.legacy_outcomes) || !Array.isArray(payload.active_sources) ||
            !counts(payload.counts, countKeys) || !counts(payload.child_counts, countKeys) || !count(payload.child_count) ||
            !count(payload.draft_version) || !count(payload.lifecycle_epoch) || !text(payload.working_set_token) ||
            ['unpublished', 'published', 'changes_waiting', 'unknown'].indexOf(payload.publication_state) < 0) {
            throw new Error('Invalid Guide working set');
        }
        var index = new Map();
        function item(row) {
            if (!object(row) || !text(row.item_ref) || !Array.isArray(row.identity_aliases) ||
                ['saved', 'pending', 'source'].indexOf(row.origin) < 0 ||
                ['saved', 'waiting', 'hidden', 'skipped'].indexOf(row.state) < 0 || !object(row.values) ||
                !Array.isArray(row.proposals) || !Array.isArray(row.evidence) || !Array.isArray(row.children)) {
                throw new Error('Invalid Guide item');
            }
            [row.item_ref].concat(row.identity_aliases).forEach(function (ref) {
                if (!text(ref) || index.has(ref)) throw new Error('Ambiguous Guide reference');
                index.set(ref, row);
            });
            row.children.forEach(item);
        }
        payload.sections.forEach(function (section, i) {
            if (!object(section) || section.key !== payload.section_order[i] || !text(section.label) ||
                typeof section.tab_visible !== 'boolean' || !Array.isArray(section.items) ||
                !counts(section.counts, countKeys) || !counts(section.child_counts, countKeys)) throw new Error('Invalid Guide section');
            section.items.forEach(item);
        });
        payload.unplaced.forEach(item);
        payload.non_tab_items.forEach(item);
        payload.active_sources.forEach(function (source) {
            if (!object(source) || !text(source.source_key) || !count(source.source_version) ||
                !object(source.organization) || !text(source.organization.state) ||
                !(source.page_count === null || count(source.page_count)) ||
                !(source.text_page_count === null || count(source.text_page_count)) || !count(source.unit_count)) {
                throw new Error('Invalid Guide source');
            }
        });
        return index;
    }
    function create() {
        var current = null, index = new Map(), selectedRef = null, loadState = 'unavailable';
        function fail() { current = null; index = new Map(); loadState = 'unavailable'; }
        return Object.freeze({
            accept: function (payload) {
                try {
                    var copy = JSON.parse(JSON.stringify(payload));
                    var nextIndex = validate(copy);
                    var previous = selectedRef && nextIndex.get(selectedRef);
                    current = freeze(copy); index = nextIndex; loadState = 'loaded';
                    selectedRef = previous ? previous.item_ref : null;
                    return true;
                } catch (_) { fail(); return false; }
            },
            fail: fail,
            data: function () { return current; },
            loadState: function () { return loadState; },
            select: function (ref) {
                if (!index.has(ref)) return false;
                selectedRef = index.get(ref).item_ref; return true;
            },
            selected: function () { return index.get(selectedRef) || null; }
        });
    }
    global.PeerSlateGuideState = Object.freeze({create: create});
})(window);
