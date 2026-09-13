/* Private My Data entrance.
 *
 * One inventory (category and Activity views, search and filters) plus one
 * composer overlay (typing, voice, documents, Add, receipts, corrections,
 * optional guide). Reads ride the accepted entry-policy and resume-intake
 * APIs; every mutation carries one request id with expected versions so a
 * dropped response can be retried without duplicating work.
 *
 * Contracts this file owns:
 *  - only acknowledged inputs are cleared; failed work keeps member text/bytes;
 *  - a transcript that arrives after more typing is appended, never overwriting;
 *  - closing the overlay preserves the draft and the list position;
 *  - an outside click never dismisses an active recording;
 *  - unsubmitted draft text is kept in memory only, never browser storage;
 *  - new facts start private; sharing changes are explicit member choices.
 */
(function () {
    'use strict';

    var root = document.querySelector('[data-my-data-root]');
    if (!root || root.getAttribute('data-my-data-enabled') !== 'true') {
        return;
    }

    var urls = {
        entries: root.getAttribute('data-my-data-entries-url'),
        entryCommand: root.getAttribute('data-my-data-entry-command-url'),
        workspace: root.getAttribute('data-my-data-intake-workspace-url'),
        submit: root.getAttribute('data-my-data-intake-submit-url'),
        recording: root.getAttribute('data-my-data-intake-recording-url'),
        decision: root.getAttribute('data-my-data-intake-decision-url'),
        purge: root.getAttribute('data-my-data-intake-purge-url'),
        guide: root.getAttribute('data-my-data-guide-url'),
        guideStatus: root.getAttribute('data-my-data-guide-status-url')
    };

    var state = {
        view: 'category',
        search: '',
        category: '',
        permission: 'all',
        entries: [],
        activity: [],
        selected: {},
        lastFocusKey: null,
        scrollTop: 0
    };

    var composer = {
        requestId: null,
        files: [],
        mediaRecorder: null,
        mediaStream: null,
        recording: false,
        recordedChunks: [],
        guideLoaded: false,
        bodyOverflow: undefined,
        hostIsolation: undefined,
        lastOpener: null
    };

    function el(selector, scope) {
        return (scope || document).querySelector(selector);
    }

    function setFlag(card, name, show) {
        var marker = card.querySelector('[data-entry-flag="' + name + '"]');
        if (marker) {
            marker.hidden = !show;
        }
    }

    function newRequestId() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return window.crypto.randomUUID();
        }
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            var r = (Math.random() * 16) | 0;
            var v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    function sameOriginOptions(method, body, extraHeaders) {
        var headers = { 'X-PeerSlate-Request': 'same-origin' };
        if (extraHeaders) {
            for (var name in extraHeaders) {
                headers[name] = extraHeaders[name];
            }
        }
        return { method: method, headers: headers, body: body, credentials: 'same-origin' };
    }

    function setStatus(message) {
        var box = el('[data-my-data-status]', root);
        if (box) {
            box.textContent = message || '';
        }
    }

    /* -- inventory ---------------------------------------------------- */

    function entryTitle(entry) {
        var values = entry.values || {};
        switch (entry.canonical_type) {
            case 'role':
                return (values.role_title || 'Role') + ' at ' + (values.employer_name || 'unspecified employer');
            case 'education':
                return (values.title || 'Education') + ' at ' + (values.institution_name || 'unspecified school');
            case 'credential':
                return (values.credential_name || 'Credential') + ' from ' + (values.issuer_name || 'unspecified issuer');
            case 'skill':
                return values.skill_name || 'Skill';
            case 'achievement':
                return values.wording || 'Achievement';
            case 'project':
                return values.project_name || 'Project';
            default:
                return values.title || values.wording || 'About me';
        }
    }

    function entryDetail(entry) {
        var values = entry.values || {};
        var detail = values.summary || values.skill_summary || values.project_role || '';
        if (entry.canonical_type === 'achievement' && values.metric_value) {
            detail = (values.metric_label ? values.metric_label + ': ' : '') + values.metric_value;
        }
        return detail;
    }

    function entryDates(entry) {
        var values = entry.values || {};
        var start = values.start_date || values.issue_date || '';
        var end = values.end_date || values.expiration_date || '';
        if (!start && !end) {
            return '';
        }
        if (start && end) {
            return start + ' to ' + end;
        }
        return start ? 'From ' + start : 'Until ' + end;
    }

    function isDeleted(entry) {
        return entry.lifecycle === 'deleted';
    }

    function sharesResume(entry) {
        return !!entry.resume_display;
    }

    function sharesVisitorAi(entry) {
        return !!entry.visitor_ai;
    }

    function assistanceExcluded(entry) {
        return !!entry.private_assistance_excluded;
    }

    function permissionMatch(entry, permission) {
        var deleted = isDeleted(entry);
        if (permission === 'recently_deleted') {
            return deleted;
        }
        if (deleted) {
            return false;
        }
        if (permission === 'all') {
            return true;
        }
        if (permission === 'private') {
            return !sharesResume(entry) && !sharesVisitorAi(entry);
        }
        if (permission === 'resume') {
            return sharesResume(entry);
        }
        if (permission === 'visitor_ai') {
            return sharesVisitorAi(entry);
        }
        if (permission === 'excluded') {
            return assistanceExcluded(entry);
        }
        return false;
    }

    function entryMatches(entry) {
        if (state.category && entry.category !== state.category) {
            return false;
        }
        if (!permissionMatch(entry, state.permission)) {
            return false;
        }
        if (state.search) {
            var haystack = (entryTitle(entry) + ' ' + entryDetail(entry) + ' '
                + (entry.category || '') + ' ' + (entry.canonical_type || '')).toLowerCase();
            if (haystack.indexOf(state.search) === -1) {
                return false;
            }
        }
        return true;
    }

    function renderGroups() {
        var host = el('[data-my-data-groups]', root);
        if (!host) {
            return;
        }
        host.textContent = '';
        var order = ['experience', 'education', 'skill', 'achievement', 'credential', 'project', 'personal'];
        var titles = {
            experience: 'Work history', education: 'Education', skill: 'Skills',
            achievement: 'Achievements', credential: 'Credentials',
            project: 'Project experience', personal: 'About me'
        };
        order.forEach(function (category) {
            var items = state.entries.filter(function (entry) {
                return entry.category === category && entryMatches(entry);
            });
            if (!items.length) {
                return;
            }
            var section = document.createElement('section');
            section.setAttribute('aria-label', titles[category]);
            var heading = document.createElement('h3');
            heading.textContent = titles[category];
            section.appendChild(heading);
            items.forEach(function (entry) {
                section.appendChild(renderEntry(entry));
            });
            host.appendChild(section);
        });
        if (!host.hasChildNodes()) {
            host.textContent = state.entries.length
                ? 'Nothing matches these filters.'
                : 'Nothing saved yet. Add whatever you would like to share.';
        }
    }

    function renderEntry(entry) {
        var blueprint = document.getElementById('my-data-entry-template');
        var card = blueprint.content.firstElementChild.cloneNode(true);
        card.setAttribute('data-entry-key', entry.entry_key);
        card.querySelector('[data-entry-title]').textContent = entryTitle(entry);
        var detail = entryDetail(entry);
        card.querySelector('[data-entry-detail]').textContent = detail;
        var dates = entryDates(entry);
        var datesEl = card.querySelector('[data-entry-dates]');
        if (dates) {
            datesEl.textContent = dates;
            datesEl.hidden = false;
        }
        // Each sharing badge renders independently from its actual flag.
        // Private means neither résumé nor visitor AI sharing is
        // permitted; assistance exclusion is a separate setting that may
        // coexist with any of these states.
        var deleted = isDeleted(entry);
        setFlag(card, 'resume', !deleted && sharesResume(entry));
        setFlag(card, 'visitor_ai', !deleted && sharesVisitorAi(entry));
        setFlag(card, 'excluded', assistanceExcluded(entry));
        setFlag(card, 'private', !deleted && !sharesResume(entry) && !sharesVisitorAi(entry));
        setFlag(card, 'deleted', deleted);
        card.querySelector('[data-entry-edit]').hidden = deleted;
        card.querySelector('[data-entry-permissions]').hidden = deleted;
        card.querySelector('[data-entry-delete]').hidden = deleted;
        card.querySelector('[data-entry-restore]').hidden = !deleted;
        var checkbox = card.querySelector('[data-entry-select]');
        checkbox.checked = !!state.selected[entry.entry_key];
        checkbox.addEventListener('change', function () {
            if (checkbox.checked) {
                state.selected[entry.entry_key] = true;
            } else {
                delete state.selected[entry.entry_key];
            }
            renderBulk();
        });
        card.querySelector('[data-entry-edit]').addEventListener('click', function () {
            openInlineEditor(card, entry);
        });
        var permissionsButton = card.querySelector('[data-entry-permissions]');
        var permissionsForm = card.querySelector('[data-entry-permissions-form]');
        permissionsForm.querySelector('[data-permission="resume_display"]').checked = !!entry.resume_display;
        permissionsForm.querySelector('[data-permission="visitor_ai"]').checked = !!entry.visitor_ai;
        permissionsForm.querySelector('[data-permission="private_assistance_excluded"]').checked = !!entry.private_assistance_excluded;
        permissionsButton.addEventListener('click', function () {
            var open = permissionsForm.hidden;
            permissionsForm.hidden = !open;
            permissionsButton.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        permissionsForm.addEventListener('submit', function (event) {
            event.preventDefault();
            savePermissions([entry], permissionsForm);
        });
        card.querySelector('[data-entry-delete]').addEventListener('click', function () {
            requestDelete(entry, card);
        });
        card.querySelector('[data-entry-restore]').addEventListener('click', function () {
            sendEntryCommand({
                request_id: newRequestId(),
                type: 'restore',
                entry_key: entry.entry_key,
                expected_access_revision: entry.access_revision
            }, 'Information restored privately. Sharing stays off until you choose it.');
        });
        return card;
    }

    function activityEntryFor(event) {
        if (!event.entry_key) {
            return null;
        }
        for (var index = 0; index < state.entries.length; index++) {
            if (state.entries[index].entry_key === event.entry_key) {
                return state.entries[index];
            }
        }
        return null;
    }

    function renderActivity() {
        var list = el('[data-my-data-activity]', root);
        if (!list) {
            return;
        }
        list.textContent = '';
        var filtered = state.activity.filter(function (event) {
            var entry = activityEntryFor(event);
            if (entry) {
                return entryMatches(entry);
            }
            return !state.search && !state.category && state.permission === 'all';
        });
        filtered.forEach(function (event) {
            var item = document.createElement('li');
            var when = document.createElement('time');
            when.textContent = event.at || '';
            if (event.at) {
                when.setAttribute('datetime', event.at);
            }
            var what = document.createElement('span');
            what.textContent = ' ' + (event.text || '');
            item.appendChild(when);
            item.appendChild(what);
            list.appendChild(item);
        });
        if (!filtered.length) {
            list.textContent = 'No activity yet.';
        }
    }

    function renderBulk() {
        var bar = el('[data-my-data-bulk]', root);
        if (!bar) {
            return;
        }
        var keys = Object.keys(state.selected);
        bar.hidden = keys.length === 0;
        var count = el('[data-my-data-bulk-count]', root);
        if (count) {
            count.textContent = keys.length + ' selected. Bulk actions affect only these entries.';
        }
    }

    function renderAll() {
        var tabs = root.querySelectorAll('[data-my-data-view]');
        tabs.forEach(function (tab) {
            var active = tab.getAttribute('data-my-data-view') === state.view;
            tab.setAttribute('aria-selected', active ? 'true' : 'false');
            tab.tabIndex = active ? 0 : -1;
        });
        var panels = root.querySelectorAll('[data-my-data-panel]');
        panels.forEach(function (panel) {
            panel.hidden = panel.getAttribute('data-my-data-panel') !== state.view;
        });
        renderGroups();
        renderActivity();
        renderBulk();
    }

    function rememberPosition() {
        state.scrollTop = window.pageYOffset || document.documentElement.scrollTop || 0;
        state.lastFocusKey = null;
        var active = document.activeElement;
        if (active && active.closest) {
            var card = active.closest('[data-entry-key]');
            if (card) {
                state.lastFocusKey = card.getAttribute('data-entry-key');
            }
        }
    }

    function restorePosition() {
        window.scrollTo(0, state.scrollTop || 0);
        if (state.lastFocusKey) {
            var card = root.querySelector('[data-entry-key="' + state.lastFocusKey + '"]');
            if (card) {
                var focusable = card.querySelector('button, input, select, textarea, [tabindex]');
                if (focusable) {
                    focusable.focus();
                }
            }
        }
    }

    function refreshInventory(message) {
        rememberPosition();
        return window.fetch(urls.entries, { credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('entries_unavailable');
                }
                return response.json();
            })
            .then(function (payload) {
                if (!payload || payload.success !== true) {
                    throw new Error('entries_unavailable');
                }
                state.entries = payload.entries || [];
                return window.fetch(urls.workspace, { credentials: 'same-origin' });
            })
            .then(function (response) {
                if (!response.ok) {
                    state.activity = activityFromEntries();
                    return null;
                }
                return response.json();
            })
            .then(function (workspace) {
                if (workspace && workspace.success === true) {
                    state.activity = activityFromWorkspace(workspace);
                }
                renderAll();
                restorePosition();
                if (message) {
                    setStatus(message);
                }
            })
            .catch(function () {
                renderAll();
                restorePosition();
                setStatus('Your information is unavailable right now. Nothing was changed.');
            });
    }

    function activityFromEntries() {
        return state.entries
            .map(function (entry) {
                if (entry.lifecycle === 'deleted') {
                    // Deletions report the lifecycle timestamp, never the
                    // content timestamps. Without one, no dated deletion
                    // event is invented.
                    if (!entry.deleted_at) {
                        return null;
                    }
                    return {
                        at: entry.deleted_at,
                        kind: 'entry_deleted',
                        entry_key: entry.entry_key
                    };
                }
                var moment = entry.updated_at || entry.created_at;
                if (!moment) {
                    return null;
                }
                var kind = (entry.updated_at && entry.updated_at !== entry.created_at)
                    ? 'entry_updated' : 'entry_added';
                return { at: moment, kind: kind, entry_key: entry.entry_key };
            })
            .filter(function (event) { return event !== null; })
            .sort(function (a, b) { return (b.at || '') < (a.at || '') ? -1 : 1; });
    }

    function activityFromWorkspace(workspace) {
        var events = activityFromEntries();
        (workspace.pending_proposals || []).forEach(function (proposal) {
            if (proposal.created_at) {
                events.push({
                    at: proposal.created_at,
                    kind: 'proposal_needs_review',
                    text: 'An addition needs your review before it is saved.',
                    entry_key: proposal.target_key || null
                });
            }
        });
        if (workspace.last_receipt && workspace.last_receipt.created_at) {
            events.push({
                at: workspace.last_receipt.created_at,
                kind: 'composer_add',
                text: 'Information entered through the composer.',
                entry_key: null
            });
        }
        events.sort(function (a, b) { return (b.at || '') < (a.at || '') ? -1 : 1; });
        return events;
    }

    /* -- entry commands ----------------------------------------------- */

    function sendEntryCommand(payload, successMessage) {
        return window.fetch(urls.entryCommand, sameOriginOptions('POST', JSON.stringify(payload), {
            'Content-Type': 'application/json'
        }))
            .then(function (response) {
                return response.json().then(function (body) {
                    return { status: response.status, body: body };
                });
            })
            .then(function (result) {
                if (result.status === 409) {
                    setStatus('That item changed since you opened it. Refresh to see the latest state.');
                    return refreshInventory();
                }
                if (!result.body || result.body.success !== true) {
                    setStatus('That change could not be saved. Nothing was changed.');
                    return null;
                }
                var receipt = result.body.receipt || {};
                if (receipt.outcome === 'duplicate' || (result.body.match && result.body.match.decision === 'equivalent')) {
                    setStatus('Already saved. Nothing new was added.');
                } else if (successMessage) {
                    setStatus(successMessage);
                }
                if (result.body.match && result.body.match.needs_resolution) {
                    renderResolution(result.body.match);
                }
                return refreshInventory();
            })
            .catch(function () {
                setStatus('That change could not be saved. Nothing was changed.');
            });
    }

    // One editor per field, preserving each value's type. Boolean
    // fields (such as current_role) render as checkboxes so a later
    // save sends real booleans back; everything else edits as text.
    function fieldEditorValue(input) {
        if (input.type === 'checkbox') {
            return input.checked;
        }
        return input.value;
    }

    function appendFieldEditor(parent, name, value) {
        var label = document.createElement('label');
        label.textContent = name;
        var input = document.createElement('input');
        if (typeof value === 'boolean') {
            input.type = 'checkbox';
            input.checked = value;
        } else {
            input.type = 'text';
            input.value = value == null ? '' : String(value);
        }
        input.name = name;
        label.appendChild(input);
        parent.appendChild(label);
        return input;
    }

    function openInlineEditor(card, entry) {
        var values = entry.values || {};
        var form = document.createElement('form');
        form.className = 'my-data__editor';
        Object.keys(values).forEach(function (name) {
            appendFieldEditor(form, name, values[name]);
        });
        var save = document.createElement('button');
        save.type = 'submit';
        save.textContent = 'Save correction';
        var cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.textContent = 'Cancel';
        form.appendChild(save);
        form.appendChild(cancel);
        card.appendChild(form);
        cancel.addEventListener('click', function () {
            form.remove();
        });
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            var next = {};
            Object.keys(values).forEach(function (name) {
                next[name] = fieldEditorValue(form.elements[name]);
            });
            sendEntryCommand({
                request_id: newRequestId(),
                type: 'edit',
                entry_key: entry.entry_key,
                expected_content_version: entry.content_version,
                values: next
            }, 'Correction saved everywhere it is already permitted.');
        });
    }

    function savePermissions(entries, form) {
        var selected = entries.filter(function (entry) {
            return entry.lifecycle !== 'deleted';
        });
        if (!selected.length) {
            setStatus('Deleted entries cannot change sharing until restored.');
            return;
        }
        var read = function (name) {
            var box = form.querySelector('[data-permission="' + name + '"]');
            return box ? box.checked : false;
        };
        sendEntryCommand({
            request_id: newRequestId(),
            type: 'change_permissions',
            entry_key: selected[0].entry_key,
            entries: selected.map(function (entry) {
                return {
                    entry_key: entry.entry_key,
                    expected_access_revision: entry.access_revision,
                    permissions: {
                        resume_display: read('resume_display'),
                        visitor_ai: read('visitor_ai'),
                        private_assistance_excluded: read('private_assistance_excluded')
                    }
                };
            })
        }, 'Sharing saved. Restrictions take effect immediately.');
    }

    function requestDelete(entry, card) {
        var dependents = state.entries.filter(function (other) {
            return other.parent_key === entry.entry_key && other.lifecycle !== 'permanently_deleted';
        }).length;
        var label = dependents
            ? 'Delete this entry and ' + dependents + ' linked achievement' + (dependents === 1 ? '' : 's') + '? They move to Recently deleted for 30 days.'
            : 'Delete this entry? It moves to Recently deleted for 30 days.';
        var confirmBar = document.createElement('div');
        confirmBar.className = 'my-data__confirm';
        var prompt = document.createElement('p');
        prompt.textContent = label;
        var yes = document.createElement('button');
        yes.type = 'button';
        yes.textContent = 'Delete';
        var no = document.createElement('button');
        no.type = 'button';
        no.textContent = 'Keep';
        confirmBar.appendChild(prompt);
        confirmBar.appendChild(yes);
        confirmBar.appendChild(no);
        card.appendChild(confirmBar);
        yes.addEventListener('click', function () {
            sendEntryCommand({
                request_id: newRequestId(),
                type: 'delete',
                entry_key: entry.entry_key,
                expected_content_version: entry.content_version,
                expected_access_revision: entry.access_revision,
                dependent_keys: state.entries
                    .filter(function (other) { return other.parent_key === entry.entry_key; })
                    .map(function (other) { return other.entry_key; })
            }, 'Deleted. Removed from every use immediately.');
        });
        no.addEventListener('click', function () {
            confirmBar.remove();
        });
    }

    function renderResolution(match) {
        setStatus('A similar entry already exists. Choose what should happen.');
        var box = el('[data-my-data-status]', root);
        if (!box || !match.candidate_key) {
            return;
        }
        var row = document.createElement('div');
        var keep = document.createElement('button');
        keep.type = 'button';
        keep.textContent = 'Keep as separate';
        keep.addEventListener('click', function () {
            sendEntryCommand({
                request_id: newRequestId(),
                type: 'resolve_match',
                entry_key: match.entry_key,
                expected_content_version: match.content_version,
                candidate_key: match.candidate_key,
                match_decision: 'distinct'
            }, 'Kept as a separate entry.');
            row.remove();
        });
        row.appendChild(keep);
        box.appendChild(row);
    }

    /* -- composer ------------------------------------------------------- */

    function overlay() {
        return el('[data-my-data-overlay]', root);
    }

    function modalHost() {
        return document.querySelector('main.main-content');
    }

    function openComposer(opener) {
        composer.lastOpener = opener || document.activeElement;
        if (!composer.requestId) {
            composer.requestId = newRequestId();
        }
        // The settings shell isolates its stacking context, which would
        // flatten the modal under later siblings such as the footer.
        // Lift that isolation while the composer is open so the overlay
        // genuinely sits above all site chrome; restore it on close.
        var host = modalHost();
        if (host && composer.hostIsolation === undefined) {
            composer.hostIsolation = host.style.isolation || '';
            host.style.isolation = 'auto';
        }
        var panel = overlay();
        panel.hidden = false;
        if (composer.bodyOverflow === undefined) {
            composer.bodyOverflow = document.body.style.overflow || '';
        }
        document.body.style.overflow = 'hidden';
        var text = el('[data-my-data-text]', root);
        if (text) {
            text.focus();
        }
    }

    function closeComposer() {
        if (composer.recording) {
            setStatus('Recording in progress. Stop the recording before closing.');
            return;
        }
        overlay().hidden = true;
        var host = modalHost();
        if (host && composer.hostIsolation !== undefined) {
            host.style.isolation = composer.hostIsolation;
            composer.hostIsolation = undefined;
        }
        if (composer.bodyOverflow !== undefined) {
            document.body.style.overflow = composer.bodyOverflow;
            composer.bodyOverflow = undefined;
        }
        if (composer.lastOpener && composer.lastOpener.focus) {
            composer.lastOpener.focus();
        }
    }

    function dialogFocusables() {
        var panel = overlay();
        var dialog = panel ? panel.querySelector('[role="dialog"]') : null;
        if (!dialog) {
            return [];
        }
        var candidates = dialog.querySelectorAll(
            'button, [href], input, select, textarea, summary, [tabindex]'
        );
        return Array.prototype.filter.call(candidates, function (node) {
            if (node.disabled || node.type === 'hidden') {
                return false;
            }
            if (node.getAttribute('tabindex') === '-1') {
                return false;
            }
            var rect = node.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        });
    }

    function trapComposerTab(event) {
        if (event.key !== 'Tab' || overlay().hidden) {
            return;
        }
        var focusables = dialogFocusables();
        if (!focusables.length) {
            event.preventDefault();
            return;
        }
        var first = focusables[0];
        var last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function composerText() {
        var text = el('[data-my-data-text]', root);
        return text ? text.value : '';
    }

    function setDraftNote(message) {
        var note = el('[data-my-data-draft]', root);
        if (note) {
            note.textContent = message || '';
        }
    }

    function renderReceipt(body) {
        var box = el('[data-my-data-receipt]', root);
        if (!box) {
            return;
        }
        box.textContent = '';
        if (!body) {
            return;
        }
        var summary = ((body.results || []).length && body.summary) || body.receipt || {};
        var message = body.message || summary.message || '';
        if (typeof message !== 'string') {
            message = '';
        }
        var line = document.createElement('p');
        if (body.success === true && (summary.outcome === 'saved' || body.outcome === 'saved')) {
            line.textContent = message || 'Saved privately. Display and visitor AI stay off.';
        } else if (message) {
            line.textContent = message;
        } else if (body.success === false && body.code === 'policy_not_selected') {
            line.textContent = 'The composer policy is not selected yet. Your words are preserved below.';
        } else if (body.success === false && body.code === 'unavailable') {
            line.textContent = 'The composer is unavailable. Your words are preserved below.';
        } else {
            line.textContent = 'Nothing was saved yet.';
        }
        box.appendChild(line);
        renderProposals(body);
    }

    function renderProposals(body) {
        var host = el('[data-my-data-proposals]', root);
        if (!host) {
            return;
        }
        host.textContent = '';
        var proposals = body.pending_proposals || body.proposals || [];
        if (body.conflicts && !proposals.length) {
            proposals = body.conflicts.filter(function (conflict) {
                return conflict.proposal_key;
            });
        }
        proposals.forEach(function (proposal) {
            host.appendChild(renderProposal(proposal));
        });
    }

    function renderProposal(proposal) {
        var card = document.createElement('article');
        card.className = 'my-data__proposal';
        var heading = document.createElement('h4');
        heading.textContent = proposal.kind === 'contradiction'
            ? 'This conflicts with something saved. Only this item needs a choice.'
            : proposal.kind === 'additional_detail'
                ? 'This adds detail to something saved.'
                : 'Review this before it is saved.';
        card.appendChild(heading);
        if (proposal.quote) {
            var quote = document.createElement('blockquote');
            quote.textContent = proposal.quote;
            card.appendChild(quote);
        }
        // Each proposed field gets its own editor prefilled with that
        // field's proposed value. Field boundaries survive: editing one
        // field never rewrites the others, and untouched values submit
        // exactly as proposed.
        var editors = {};
        Object.keys(proposal.proposed_values || {}).forEach(function (name) {
            editors[name] = appendFieldEditor(
                card, name, proposal.proposed_values[name]
            );
        });
        var row = document.createElement('div');
        var accept = document.createElement('button');
        accept.type = 'button';
        accept.textContent = 'Save';
        var dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.textContent = 'Dismiss';
        var saveWording = document.createElement('button');
        saveWording.type = 'button';
        saveWording.textContent = 'Use my wording';
        row.appendChild(accept);
        row.appendChild(saveWording);
        row.appendChild(dismiss);
        card.appendChild(row);
        var decide = function (decision, confirmed) {
            var payload = {
                request_id: newRequestId(),
                proposal_key: proposal.proposal_key,
                decision: decision
            };
            if (confirmed !== undefined) {
                payload.confirmed_values = confirmed;
            }
            window.fetch(urls.decision, sameOriginOptions('POST', JSON.stringify(payload), {
                'Content-Type': 'application/json'
            }))
                .then(function (response) {
                    return response.json();
                })
                .then(function (result) {
                    renderReceipt(result);
                    return refreshInventory();
                })
                .catch(function () {
                    setStatus('That choice could not be saved. Your input is preserved.');
                });
        };
        accept.addEventListener('click', function () { decide('accept'); });
        dismiss.addEventListener('click', function () { decide('reject'); });
        saveWording.addEventListener('click', function () {
            var values = {};
            Object.keys(editors).forEach(function (name) {
                values[name] = fieldEditorValue(editors[name]);
            });
            decide('edit', values);
        });
        return card;
    }

    function submitAdd() {
        var text = composerText();
        if (!text && !composer.files.length) {
            setDraftNote('Add something before saving.');
            return;
        }
        var form = new FormData();
        var attachments = [];
        composer.files.forEach(function (staged, index) {
            var key = 'attachment-' + index;
            form.append('file:' + key, staged.file, staged.file.name || key);
            attachments.push({
                client_key: key,
                kind: 'document',
                declared_content_type: staged.file.type || '',
                filename: staged.file.name || key
            });
        });
        form.append('request', JSON.stringify({
            type: 'add_submission',
            request_id: composer.requestId,
            text: text,
            items: [],
            attachments: attachments
        }));
        setDraftNote('Saving privately…');
        window.fetch(urls.submit, sameOriginOptions('POST', form))
            .then(function (response) {
                return response.json().then(function (body) {
                    return { status: response.status, body: body };
                });
            })
            .then(function (result) {
                var body = result.body || {};
                if (result.status === 409 && body.code !== 'unavailable') {
                    renderReceipt(body);
                    composer.requestId = newRequestId();
                    return null;
                }
                if (body.success === true || body.success === false) {
                    renderReceipt(body);
                }
                var summary = body.summary || {};
                if (body.success === true && summary.failed === 0) {
                    el('[data-my-data-text]', root).value = '';
                    composer.files = [];
                    renderAttachments();
                    composer.requestId = newRequestId();
                    setDraftNote('');
                } else if (body.input_preserved !== false) {
                    setDraftNote('Your words are preserved above. Nothing was discarded.');
                    composer.requestId = newRequestId();
                }
                return refreshInventory();
            })
            .catch(function () {
                setDraftNote('Saving failed before reaching PeerSlate. Your words are preserved.');
            });
    }

    function renderAttachments() {
        var list = el('[data-my-data-attachments]', root);
        if (!list) {
            return;
        }
        list.textContent = '';
        composer.files.forEach(function (staged, index) {
            var item = document.createElement('li');
            item.textContent = (staged.file.name || 'file') + ' (' + staged.file.size + ' bytes) ';
            var remove = document.createElement('button');
            remove.type = 'button';
            remove.textContent = 'Remove';
            remove.addEventListener('click', function () {
                composer.files.splice(index, 1);
                renderAttachments();
            });
            item.appendChild(remove);
            list.appendChild(item);
        });
    }

    function startRecording() {
        if (composer.recording) {
            return;
        }
        if (!window.MediaRecorder) {
            setDraftNote('Voice recording is not supported in this browser. Typing still works.');
            return;
        }
        window.navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                composer.mediaStream = stream;
                composer.recordedChunks = [];
                var recorder = new window.MediaRecorder(stream);
                composer.mediaRecorder = recorder;
                recorder.ondataavailable = function (event) {
                    if (event.data && event.data.size) {
                        composer.recordedChunks.push(event.data);
                    }
                };
                recorder.onstop = finishRecording;
                recorder.start();
                composer.recording = true;
                var button = el('[data-my-data-mic]', root);
                if (button) {
                    button.setAttribute('aria-pressed', 'true');
                    button.textContent = 'Stop recording';
                }
                setDraftNote('Recording. Closing stays available after you stop.');
            })
            .catch(function () {
                setDraftNote('The microphone is unavailable. Typing still works.');
            });
    }

    function stopRecording() {
        if (composer.mediaRecorder && composer.recording) {
            composer.mediaRecorder.stop();
        }
    }

    function finishRecording() {
        composer.recording = false;
        var button = el('[data-my-data-mic]', root);
        if (button) {
            button.setAttribute('aria-pressed', 'false');
            button.textContent = 'Record voice';
        }
        if (composer.mediaStream) {
            composer.mediaStream.getTracks().forEach(function (track) { track.stop(); });
            composer.mediaStream = null;
        }
        var blob = new Blob(composer.recordedChunks, { type: 'audio/webm' });
        composer.recordedChunks = [];
        if (!blob.size) {
            setDraftNote('Nothing was recorded. Your text is preserved.');
            return;
        }
        var form = new FormData();
        form.append('request', JSON.stringify({
            type: 'transcribe_recording',
            request_id: newRequestId()
        }));
        form.append('recording', blob, 'recording.webm');
        setDraftNote('Transcribing privately…');
        window.fetch(urls.recording, sameOriginOptions('POST', form))
            .then(function (response) {
                return response.json();
            })
            .then(function (body) {
                var transcript = body && (body.transcript || body.provider_transcript || '');
                if (transcript) {
                    var text = el('[data-my-data-text]', root);
                    text.value = text.value ? text.value + ' ' + transcript : transcript;
                    renderReceipt(body);
                    setDraftNote('Transcript added below your words. Nothing was overwritten.');
                } else {
                    setDraftNote('Transcription is unavailable. Your recording is kept privately. Try again.');
                }
                return refreshInventory();
            })
            .catch(function () {
                setDraftNote('Transcription failed before reaching PeerSlate. Try again. Nothing was discarded.');
            });
    }

    function loadGuide() {
        if (composer.guideLoaded) {
            return;
        }
        composer.guideLoaded = true;
        window.fetch(urls.guide, { credentials: 'same-origin' })
            .then(function (response) { return response.json(); })
            .then(function (body) {
                var host = el('[data-my-data-guide-body]', root);
                if (host && body) {
                    host.textContent = body.message || body.status || '';
                }
            })
            .catch(function () { /* guide stays optional */ });
    }

    /* -- wiring --------------------------------------------------------- */

    function selectView(tab) {
        rememberPosition();
        state.view = tab.getAttribute('data-my-data-view');
        renderAll();
        restorePosition();
    }

    function wireToolbar() {
        root.querySelectorAll('[data-my-data-view]').forEach(function (tab) {
            tab.addEventListener('click', function () {
                selectView(tab);
            });
        });
        // Roving keyboard support for the view tabs: arrows move focus
        // and select in one step (automatic activation), Home/End jump.
        var tablist = root.querySelector('[role="tablist"]');
        if (tablist) {
            tablist.addEventListener('keydown', function (event) {
                var tabs = Array.prototype.slice.call(
                    root.querySelectorAll('[data-my-data-view]')
                );
                var current = tabs.indexOf(document.activeElement);
                if (current === -1) {
                    return;
                }
                var next = null;
                if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
                    next = (current + 1) % tabs.length;
                } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
                    next = (current - 1 + tabs.length) % tabs.length;
                } else if (event.key === 'Home') {
                    next = 0;
                } else if (event.key === 'End') {
                    next = tabs.length - 1;
                } else {
                    return;
                }
                event.preventDefault();
                selectView(tabs[next]);
                tabs[next].focus();
            });
        }
        var search = el('[data-my-data-search]', root);
        var timer = null;
        if (search) {
            search.addEventListener('input', function () {
                if (timer) {
                    window.clearTimeout(timer);
                }
                timer = window.setTimeout(function () {
                    rememberPosition();
                    state.search = search.value.trim().toLowerCase();
                    renderAll();
                    restorePosition();
                    search.focus();
                }, 200);
            });
        }
        var category = el('[data-my-data-category]', root);
        if (category) {
            category.addEventListener('change', function () {
                rememberPosition();
                state.category = category.value;
                renderAll();
                restorePosition();
            });
        }
        var permission = el('[data-my-data-permission]', root);
        if (permission) {
            permission.addEventListener('change', function () {
                rememberPosition();
                state.permission = permission.value;
                renderAll();
                restorePosition();
            });
        }
        var openButton = el('[data-my-data-open]', root);
        if (openButton) {
            openButton.addEventListener('click', function () {
                openComposer(openButton);
            });
        }
        var bulkResume = el('[data-my-data-bulk-resume]', root);
        if (bulkResume) {
            bulkResume.addEventListener('click', function () {
                bulkPermissions({ resume_display: true, visitor_ai: false, private_assistance_excluded: false });
            });
        }
        var bulkPrivate = el('[data-my-data-bulk-private]', root);
        if (bulkPrivate) {
            bulkPrivate.addEventListener('click', function () {
                bulkPermissions({ resume_display: false, visitor_ai: false, private_assistance_excluded: false });
            });
        }
    }

    function bulkPermissions(permissions) {
        var selected = state.entries.filter(function (entry) {
            return state.selected[entry.entry_key] && entry.lifecycle !== 'deleted';
        });
        if (!selected.length) {
            return;
        }
        sendEntryCommand({
            request_id: newRequestId(),
            type: 'change_permissions',
            entry_key: selected[0].entry_key,
            entries: selected.map(function (entry) {
                return {
                    entry_key: entry.entry_key,
                    expected_access_revision: entry.access_revision,
                    permissions: permissions
                };
            })
        }, 'Sharing saved for the selected entries. New additions stay private.');
    }

    function wireComposer() {
        var close = el('[data-my-data-close]', root);
        if (close) {
            close.addEventListener('click', closeComposer);
        }
        document.addEventListener('keydown', function (event) {
            trapComposerTab(event);
            if (event.key === 'Escape' && !overlay().hidden) {
                closeComposer();
            }
        });
        overlay().addEventListener('mousedown', function (event) {
            if (event.target === overlay() && !composer.recording) {
                closeComposer();
            }
        });
        var add = el('[data-my-data-add]', root);
        if (add) {
            add.addEventListener('click', submitAdd);
        }
        var discard = el('[data-my-data-discard]', root);
        if (discard) {
            discard.addEventListener('click', function () {
                el('[data-my-data-text]', root).value = '';
                composer.files = [];
                renderAttachments();
                renderReceipt(null);
                el('[data-my-data-proposals]', root).textContent = '';
                composer.requestId = newRequestId();
                setDraftNote('Draft discarded.');
            });
        }
        var file = el('[data-my-data-file]', root);
        if (file) {
            file.addEventListener('change', function () {
                Array.prototype.forEach.call(file.files || [], function (blob) {
                    if (blob.size > 10000000) {
                        setDraftNote('That file is over 10 MB and was not attached.');
                        return;
                    }
                    if (composer.files.length >= 5) {
                        setDraftNote('Attach up to 5 files per Add.');
                        return;
                    }
                    composer.files.push({ file: blob });
                });
                file.value = '';
                renderAttachments();
                if (composer.files.length) {
                    setDraftNote('Draft kept. Press Add when ready.');
                }
            });
        }
        var mic = el('[data-my-data-mic]', root);
        if (mic) {
            mic.addEventListener('click', function () {
                if (composer.recording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            });
        }
        var guide = el('[data-my-data-guide]', root);
        if (guide) {
            guide.addEventListener('toggle', function () {
                if (guide.open) {
                    loadGuide();
                }
            });
        }
        var text = el('[data-my-data-text]', root);
        if (text) {
            text.addEventListener('input', function () {
                if (text.value) {
                    setDraftNote('Draft kept. Press Add when ready.');
                }
            });
        }
    }

    function hydrateBootstrap() {
        var tag = document.getElementById('my-data-bootstrap');
        if (!tag) {
            return false;
        }
        try {
            var bootstrap = JSON.parse(tag.textContent || 'null');
            if (!bootstrap || typeof bootstrap !== 'object') {
                return false;
            }
            if (bootstrap.view === 'category' || bootstrap.view === 'activity') {
                state.view = bootstrap.view;
            }
            var groups = bootstrap.groups || [];
            var seeded = [];
            groups.forEach(function (group) {
                (group.entries || []).forEach(function (entry) {
                    seeded.push(entry);
                });
            });
            if (seeded.length) {
                state.entries = seeded;
            }
            if (Array.isArray(bootstrap.activity)) {
                state.activity = bootstrap.activity;
            }
            renderAll();
            return true;
        } catch (error) {
            return false;
        }
    }

    wireToolbar();
    wireComposer();
    hydrateBootstrap();
    refreshInventory();
})();
