/* MVP1 increment C: private Resume composer.
 *
 * One composer keeps typing, the in-field microphone, document attachments and
 * explicit Add together. Nothing is processed until Add: this script never
 * saves, publishes, or starts provider work on its own.
 *
 * Contracts this file owns:
 *  - only the fields the member actually supplied are sent. Unspecified fields
 *    are absent, and a deliberate clear is sent as an explicit clear, so an
 *    overlay merge can never blank a value the member did not touch;
 *  - one Add (or one recording) keeps ONE request id and one immutable payload
 *    for as long as it is unacknowledged, so a dropped response can be safely
 *    retried without duplicating work; a new key is minted only after a
 *    definitive refusal or a completed Add;
 *  - a transcript that arrives after more typing is INSERTED, never
 *    overwriting what was typed (shared PeerSlateDictation.appendTranscript);
 *  - only acknowledged inputs are cleared. A failed upload or a request that
 *    never completed keeps the member's text and bytes, and newer edits are
 *    never discarded;
 *  - the approved states: centered first-use welcome, later docked desktop
 *    guide, and a mobile sheet with a floating "Guide me" reopen chip.
 *
 * No draft is written to browser storage: sensitive drafts are not persisted
 * client-side as a workaround for the withheld onboarding retention policy.
 */
(function () {
    'use strict';

    var root = document.getElementById('resume-intake');
    if (!root) {
        return;
    }

    var urls = {
        workspace: root.getAttribute('data-intake-workspace-url'),
        submit: root.getAttribute('data-intake-submit-url'),
        recording: root.getAttribute('data-intake-recording-url'),
        decision: root.getAttribute('data-intake-decision-url'),
        purge: root.getAttribute('data-intake-purge-url'),
        guide: root.getAttribute('data-guide-url'),
        guideStatus: root.getAttribute('data-guide-status-url')
    };

    var guidePanel = document.getElementById('resume-intake-guide');
    var scrim = document.getElementById('resume-intake-scrim');
    var hideButton = document.getElementById('resume-intake-hide');
    var reopenButton = document.getElementById('resume-intake-reopen');
    var textarea = document.getElementById('resume-intake-text');
    var fileInput = document.getElementById('resume-intake-file');
    var micButton = document.getElementById('resume-intake-mic');
    var cancelRecordingButton = document.getElementById('resume-intake-cancel-recording');
    var recordingGeneration = 0;
    var addButton = document.getElementById('resume-intake-add');
    var composer = document.getElementById('resume-intake-composer');
    var receiptBox = document.getElementById('resume-intake-receipt');
    var statusBox = document.getElementById('resume-intake-status');
    var activityBox = document.getElementById('resume-intake-activity');
    var activityText = document.getElementById('resume-intake-activity-text');
    var activitySlot = document.getElementById('resume-intake-activity-slot');
    var activityOperations = [];
    var addOperation = null;
    var draftLabel = document.getElementById('resume-intake-draft-label');
    var queuedList = document.getElementById('resume-intake-queued');
    var attachmentList = document.getElementById('resume-intake-attachments');
    var proposalList = document.getElementById('resume-intake-proposals');
    var questionPrompt = document.getElementById('resume-intake-question');
    var questionContext = document.getElementById('resume-intake-context');
    var typeSelect = document.getElementById('resume-intake-type');
    var addFactButton = document.getElementById('resume-intake-add-fact');
    var clearsBox = document.getElementById('resume-intake-clears');
    var skipButton = document.getElementById('resume-intake-skip');
    var completeButton = document.getElementById('resume-intake-complete');
    var editorSection = root.closest ? root.closest('.resume-editor') : null;
    var editorLists = document.getElementById('resume-editor-lists');
    var parentSelect = document.getElementById('resume-intake-parent');

    var FIELDS = {
        role: ['role_title', 'employer_name', 'location_text', 'summary', 'start_date',
               'end_date', 'date_precision', 'employment_type', 'current_role'],
        education: ['title', 'institution_name', 'degree_name', 'field_of_study',
                    'education_status', 'grade_text', 'location_text', 'summary',
                    'start_date', 'end_date', 'date_precision'],
        credential: ['name', 'issuer', 'identifier', 'issue_date', 'expiration_date',
                     'verification_url', 'completion_status'],
        skill: ['name', 'summary'],
        accomplishment: ['wording', 'metric_value', 'metric_label']
    };
    var FIELD_INPUTS = {
        role: {role_title: 'resume-intake-role-title', employer_name: 'resume-intake-employer',
               current_role: 'resume-intake-current-role', date_precision: 'resume-intake-role-date-precision',
               start_date: 'resume-intake-role-start', end_date: 'resume-intake-role-end'},
        skill: {name: 'resume-intake-skill'},
        education: {title: 'resume-intake-education-title', institution_name: 'resume-intake-institution',
                    education_status: 'resume-intake-education-status',
                    date_precision: 'resume-intake-education-date-precision',
                    start_date: 'resume-intake-education-start', end_date: 'resume-intake-education-end'},
        credential: {name: 'resume-intake-credential', issuer: 'resume-intake-issuer',
                     completion_status: 'resume-intake-credential-status',
                     issue_date: 'resume-intake-credential-issue-date'},
        accomplishment: {wording: 'resume-intake-wording'}
    };
    var REQUIRED_HINT = {
        role: 'role title and employer',
        skill: 'strength',
        education: 'program and institution',
        credential: 'credential and issuer',
        accomplishment: 'what you did'
    };
    var REQUIRED_FIELDS = {
        role: ['role_title', 'employer_name'],
        skill: ['name'],
        education: ['title', 'institution_name', 'education_status'],
        credential: ['name', 'issuer', 'completion_status'],
        accomplishment: ['wording']
    };

    var queuedFacts = [];
    var attachments = [];
    var recorder = null;
    var recordedChunks = [];
    var recordingStartedAt = 0;
    var pendingAdd = null;         // {request_id, signature}
    var pendingGuide = null;       // {request_id, signature}
    var parentCandidates = [];     // owner-scoped parents for an Impact entry
    var guideHidden = false;
    var guideDismissed = false;
    var firstUse = true;
    var unsavedBeforeUnload = null;

    function requestId() {
        if (window.crypto && window.crypto.randomUUID) {
            return window.crypto.randomUUID();
        }
        return '00000000-0000-4000-8000-000000000000'.replace(/0/g, function () {
            return Math.floor(Math.random() * 16).toString(16);
        });
    }

    /* EDIT-002 accepts only an owner-scoped private/draft/unpublished role with
       no sharing or approval history. The canonical reader exposes that exact
       predicate as editable=true / save_mode=canonical. */
    function parentLabel(item) {
        var values = item.values || {};
        return values.role_title || values.title || values.name || item.record_key;
    }

    function loadParentCandidates() {
        var url = editorLists && editorLists.getAttribute('data-workspace-url');
        if (!url) {
            return Promise.resolve([]);
        }
        return fetch(url, {credentials: 'same-origin'})
            .then(function (response) { return response.json().catch(function () { return {}; }); })
            .then(function (payload) {
                parentCandidates = (payload.items || []).filter(function (item) {
                    return item.record_type === 'role' && item.editable === true &&
                        item.save_mode === 'canonical' && !item.orphaned;
                }).map(function (item) {
                    return {record_key: item.record_key, label: parentLabel(item),
                            record_type: item.record_type};
                });
                return parentCandidates;
            })
            .catch(function () { return []; });
    }

    function fillParentSelect(select) {
        if (!select) {
            return;
        }
        select.replaceChildren();
        var prompt = document.createElement('option');
        prompt.value = '';
        prompt.textContent = parentCandidates.length
            ? 'Choose an entry...'
            : 'Add an eligible private role first';
        select.appendChild(prompt);
        parentCandidates.forEach(function (candidate) {
            var option = document.createElement('option');
            option.value = candidate.record_key;
            option.textContent = candidate.label + ' (role)';
            select.appendChild(option);
        });
    }

    function signatureOf(value) {
        return JSON.stringify(value);
    }

    function hasUnsavedInput() {
        return Boolean(
            (textarea.value || '').trim() ||
            queuedFacts.length ||
            attachments.length
        );
    }

    function refreshDraftLabel() {
        if (!draftLabel) {
            return;
        }
        draftLabel.textContent = hasUnsavedInput()
            ? 'Draft answer \u00b7 Not added yet'
            : 'Nothing waiting \u00b7 Nothing added yet';
    }

    function protectNavigation() {
        if (unsavedBeforeUnload) {
            return;
        }
        unsavedBeforeUnload = function (event) {
            if (!hasUnsavedInput()) {
                return undefined;
            }
            event.preventDefault();
            event.returnValue = 'Your answer is not added yet.';
            return event.returnValue;
        };
        window.addEventListener('beforeunload', unsavedBeforeUnload);
    }

    function setStatus(message, kind) {
        if (!statusBox) {
            return;
        }
        statusBox.textContent = message || '';
        statusBox.setAttribute('data-kind', kind || 'ok');
    }

    // Only locally outstanding work is busy. A pending/recovery HTTP receipt
    // is terminal for this request, not evidence of a background job.
    function renderActivity() {
        var adding = activityOperations.some(function (operation) { return operation.kind === 'add'; });
        var transcribing = activityOperations.some(function (operation) { return operation.kind === 'transcription'; });
        var waiting = activityOperations.some(function (operation) { return operation.longWait; });
        var message = adding ? 'Preparing your information…' : '';
        if (transcribing) {
            message += (message ? ' ' : '') + 'Turning your recording into text…';
        }
        if (message) {
            message += waiting
                ? ' This request is taking longer. You can keep typing; your new words will be kept.'
                : ' You can keep typing.';
        }
        activityText.textContent = message;
        activityBox.hidden = !activityOperations.length;
        // The live status is outside this form, so busy never defers its announcement.
        composer.setAttribute('aria-busy', activityOperations.length ? 'true' : 'false');
        addButton.setAttribute('aria-busy', adding ? 'true' : 'false');
        var destination = root.hidden ? reopenButton.parentNode : activitySlot;
        if (activityBox.parentNode !== destination) destination.insertBefore(activityBox, destination.firstChild);
        activityBox.classList.toggle('resume-intake__activity--outside', root.hidden);
    }

    function beginActivity(kind) {
        var operation = {kind: kind, longWait: false, timer: null};
        activityOperations.push(operation);
        operation.timer = window.setTimeout(function () {
            if (activityOperations.indexOf(operation) === -1) return;
            operation.longWait = true;
            renderActivity();
        }, 10000);
        renderActivity();
        activityBox.scrollIntoView({block: 'nearest'});
        return operation;
    }

    function endActivity(operation) {
        var index = activityOperations.indexOf(operation);
        if (index === -1) return;
        window.clearTimeout(operation.timer);
        activityOperations.splice(index, 1);
        renderActivity();
    }

    function syncRecordingCancel() {
        var recording = recorder && recorder.state === 'recording';
        var transcribing = attachments.some(function (row) { return row.transcribing; });
        cancelRecordingButton.hidden = !recording && !transcribing;
        cancelRecordingButton.textContent = recording ? 'Cancel recording' : 'Cancel transcription';
    }

    function send(url, options) {
        var settings = options || {};
        settings.credentials = 'same-origin';
        settings.headers = Object.assign(
            {'X-PeerSlate-Request': 'same-origin'}, settings.headers || {}
        );
        return fetch(url, settings).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (payload) {
                return {response: response, payload: payload};
            });
        });
    }

    function postJson(url, body) {
        return send(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
    }

    function labelFor(type) {
        return {
            role: 'Role', skill: 'Strength', education: 'Education',
            credential: 'Credential', accomplishment: 'Impact'
        }[type] || type;
    }

    /* Only the fields the member actually filled are returned. No null padding
       and no default booleans: an unspecified field must stay absent so an
       overlay merge cannot blank it. */
    function valuesFor(type, fields) {
        var values = {};
        Object.keys(fields || {}).forEach(function (name) {
            var raw = fields[name];
            if (typeof raw !== 'string') {
                return;
            }
            var trimmed = raw.trim();
            if (trimmed) {
                values[name] = name === 'current_role' ? trimmed === 'true' : trimmed;
            }
        });
        ['start_date', 'end_date'].forEach(function (name) {
            if (!values[name]) return;
            var precision = values.date_precision;
            var pattern = {year: /^\d{4}$/, month: /^\d{4}-\d{2}$/, day: /^\d{4}-\d{2}-\d{2}$/}[precision];
            if (!pattern || !pattern.test(values[name])) {
                throw new Error('Choose date detail and use YYYY, YYYY-MM or YYYY-MM-DD to match it. Leave unknown dates empty.');
            }
            // Existing canonical precision encoding; the supplied detail is
            // retained and presentation never claims these placeholder days.
            if (precision === 'year') values[name] += '-01-01';
            if (precision === 'month') values[name] += '-01';
        });
        return values;
    }

    function fieldsForType(type) {
        var values = {};
        var inputs = FIELD_INPUTS[type] || {};
        Object.keys(inputs).forEach(function (name) {
            var node = document.getElementById(inputs[name]);
            if (node) {
                values[name] = node.value;
            }
        });
        return values;
    }

    function clearsForType(type) {
        if (!clearsBox) {
            return [];
        }
        var cleared = [];
        Array.prototype.forEach.call(clearsBox.querySelectorAll('input[type="checkbox"]'), function (box) {
            if (box.checked && box.value) {
                cleared.push(box.value);
            }
        });
        return cleared;
    }

    function renderClears(type) {
        if (!clearsBox) {
            return;
        }
        clearsBox.replaceChildren();
        if (!type) {
            clearsBox.hidden = true;
            return;
        }
        clearsBox.hidden = false;
        var legend = document.createElement('legend');
        legend.textContent = 'Clear these fields on the existing entry (optional)';
        clearsBox.appendChild(legend);
        // Required fields are never offered as clears: clearing them could only
        // fail later at accept, so the affordance is not shown at all.
        var required = REQUIRED_FIELDS[type] || [];
        (FIELDS[type] || []).filter(function (name) {
            return required.indexOf(name) === -1;
        }).forEach(function (name) {
            var label = document.createElement('label');
            var box = document.createElement('input');
            box.type = 'checkbox';
            box.value = name;
            box.id = 'resume-intake-clear-' + name;
            label.setAttribute('for', box.id);
            label.appendChild(box);
            label.appendChild(document.createTextNode(' ' + name.replace(/_/g, ' ')));
            clearsBox.appendChild(label);
        });
    }

    function syncDirectFields() {
        var type = typeSelect.value;
        Array.prototype.forEach.call(root.querySelectorAll('[data-role-field]'), function (node) {
            node.hidden = type !== 'role';
        });
        Array.prototype.forEach.call(root.querySelectorAll('[data-skill-field]'), function (node) {
            node.hidden = type !== 'skill';
        });
        Array.prototype.forEach.call(root.querySelectorAll('[data-education-field]'), function (node) {
            node.hidden = type !== 'education';
        });
        Array.prototype.forEach.call(root.querySelectorAll('[data-credential-field]'), function (node) {
            node.hidden = type !== 'credential';
        });
        var completedCredential = document.querySelector('[data-credential-completed-field]');
        var credentialStatus = document.getElementById('resume-intake-credential-status');
        if (completedCredential) {
            completedCredential.hidden = type !== 'credential' ||
                !credentialStatus || credentialStatus.value !== 'completed';
        }
        Array.prototype.forEach.call(root.querySelectorAll('[data-accomplishment-field]'), function (node) {
            node.hidden = type !== 'accomplishment';
        });
        if (type === 'accomplishment') {
            if (!parentCandidates.length) {
                loadParentCandidates().then(function () { fillParentSelect(parentSelect); });
            } else {
                fillParentSelect(parentSelect);
            }
        }
        renderClears(type);
    }

    function renderQueued() {
        queuedList.replaceChildren();
        queuedFacts.forEach(function (row) {
            var item = document.createElement('li');
            var tag = document.createElement('span');
            tag.className = 'resume-intake__tag';
            tag.textContent = labelFor(row.record_type);
            item.appendChild(tag);
            item.appendChild(document.createTextNode(' ' + row.label));
            if (row.explicit_clears.length) {
                item.appendChild(document.createTextNode(' \u00b7 clears ' + row.explicit_clears.join(', ')));
            }
            var remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'resume-intake__quiet';
            remove.textContent = 'Remove';
            remove.addEventListener('click', function () {
                queuedFacts = queuedFacts.filter(function (entry) {
                    return entry.client_key !== row.client_key;
                });
                renderQueued();
                refreshDraftLabel();
            });
            item.appendChild(document.createTextNode(' '));
            item.appendChild(remove);
            queuedList.appendChild(item);
        });
    }

    function renderAttachments() {
        attachmentList.replaceChildren();
        attachments.forEach(function (row) {
            var item = document.createElement('li');
            var tag = document.createElement('span');
            tag.className = 'resume-intake__tag';
            tag.textContent = row.kind === 'recording' ? 'Recording' : 'File';
            item.appendChild(tag);
            var state = {
                selected: 'not added yet',
                saved: 'saved privately',
                unresolved: 'captured, needs your review',
                pending: 'processing claim pending \u00b7 still unsent',
                failed: 'could not be read \u00b7 still unsent',
                cancelled: 'transcription cancelled; any uploaded audio stays private'
            }[row.status] || row.status;
            item.appendChild(document.createTextNode(' ' + row.label + ' \u00b7 ' + state));
            if (row.message) {
                item.appendChild(document.createTextNode(' \u00b7 ' + row.message));
            }
            if (row.kind === 'document' && (row.status === 'selected' || row.status === 'failed')) {
                var remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'resume-intake__quiet';
                remove.textContent = 'Remove';
                remove.setAttribute('aria-label', 'Remove ' + row.label);
                remove.disabled = Boolean(pendingAdd) || addButton.disabled;
                remove.addEventListener('click', function () {
                    if (pendingAdd || addButton.disabled) return;
                    attachments = attachments.filter(function (entry) { return entry.client_key !== row.client_key; });
                    renderAttachments();
                    refreshDraftLabel();
                    setStatus('Removed this unsent attachment. Your other input is kept.', 'ok');
                });
                item.appendChild(document.createTextNode(' '));
                item.appendChild(remove);
            }
            if ((row.status === 'failed' || row.status === 'pending') && row.retryable && row.blob) {
                var retry = document.createElement('button');
                retry.type = 'button';
                retry.className = 'resume-intake__quiet';
                retry.textContent = 'Try again';
                retry.addEventListener('click', function () {
                    // Each attachment owns its immutable request metadata.
                    // A later recording cannot replace the request or duration
                    // used when this exact blob was first submitted.
                    uploadRecording(row.blob, row.client_key, row);
                });
                item.appendChild(document.createTextNode(' '));
                item.appendChild(retry);
            }
            attachmentList.appendChild(item);
        });
    }

    function renderReceipt(receipt) {
        receiptBox.replaceChildren();
        if (!receipt) {
            var empty = document.createElement('p');
            empty.className = 'resume-intake__receipt-empty';
            empty.textContent = 'Nothing added yet. Type, speak or attach a file, then press Add.';
            receiptBox.appendChild(empty);
            return;
        }
        var summary = receipt.summary || {};
        var headline = document.createElement('p');
        headline.className = summary.all_saved
            ? 'resume-intake__receipt-saved'
            : 'resume-intake__receipt-detail';
        headline.textContent = summary.all_saved
            ? '\u2713 ' + (receipt.message || 'Saved privately.')
            : (receipt.message || 'Add finished.');
        receiptBox.appendChild(headline);
        var detail = document.createElement('p');
        detail.className = 'resume-intake__receipt-detail';
        detail.textContent =
            (summary.saved || 0) + ' saved privately \u00b7 ' +
            (summary.unresolved || 0) + ' needs your review \u00b7 ' +
            (summary.failed || 0) + ' could not be saved.';
        receiptBox.appendChild(detail);
        if (receipt.results) {
            var list = document.createElement('ul');
            list.className = 'resume-intake__attachments';
            receipt.results.forEach(function (row) {
                var entry = document.createElement('li');
                var tag = document.createElement('span');
                tag.className = 'resume-intake__tag';
                tag.textContent = row.outcome;
                entry.appendChild(tag);
                entry.appendChild(document.createTextNode(' ' + (row.message || '')));
                list.appendChild(entry);
            });
            receiptBox.appendChild(list);
        }
    }

    function renderProposals(proposals) {
        proposalList.replaceChildren();
        if (!proposals.length) {
            var empty = document.createElement('li');
            empty.className = 'resume-intake__hint';
            empty.textContent = 'Nothing is waiting on you.';
            proposalList.appendChild(empty);
            return;
        }
        proposals.forEach(function (proposal, proposalIndex) {
            var item = document.createElement('li');
            var quote = document.createElement('p');
            quote.className = 'resume-intake__proposal-quote';
            quote.textContent = '\u201c' + (proposal.quote || (proposal.proposed_values || {}).text || '') + '\u201d';
            item.appendChild(quote);
            var kind = document.createElement('span');
            kind.className = 'resume-intake__tag';
            kind.textContent = proposal.kind.replace(/_/g, ' ');
            item.appendChild(kind);
            if (proposal.target_key) {
                item.appendChild(document.createTextNode(' \u00b7 changes something you already have'));
            }

            var needsCreateDetails = !proposal.target_key;
            var typeField = null;
            var wordingField = null;
            var parentField = null;
            var employerField = null;
            var institutionField = null;
            var issuerField = null;
            var educationStatusField = null;
            var credentialStatusField = null;
            var issueDateField = null;
            if (needsCreateDetails) {
                var typeLabel = document.createElement('label');
                typeLabel.textContent = 'Save this as';
                typeField = document.createElement('select');
                typeField.id = 'resume-proposal-' + proposalIndex + '-type';
                typeLabel.htmlFor = typeField.id;
                typeField.setAttribute('data-proposal-type', '');
                ['role', 'skill', 'education', 'credential', 'accomplishment'].forEach(function (value) {
                    var option = document.createElement('option');
                    option.value = value;
                    option.textContent = labelFor(value);
                    typeField.appendChild(option);
                });
                var typeWrap = document.createElement('p');
                typeWrap.appendChild(typeLabel);
                typeWrap.appendChild(typeField);
                item.appendChild(typeWrap);
                if (proposal.record_type && proposal.record_type !== 'unspecified') {
                    typeField.value = proposal.record_type;
                }

                var wordingLabel = document.createElement('label');
                wordingLabel.textContent = 'Your wording';
                wordingField = document.createElement('input');
                wordingField.id = 'resume-proposal-' + proposalIndex + '-wording';
                wordingLabel.htmlFor = wordingField.id;
                wordingField.type = 'text';
                wordingField.setAttribute('data-proposal-wording', '');
                var proposed = proposal.proposed_values || {};
                wordingField.value = proposed.text || proposed.role_title || proposed.title ||
                    proposed.name || proposed.wording || proposal.quote || '';
                wordingField.maxLength = 300;
                var wordingWrap = document.createElement('p');
                wordingWrap.appendChild(wordingLabel);
                wordingWrap.appendChild(wordingField);
                item.appendChild(wordingWrap);

                function detailField(labelText, attribute, type, value) {
                    var wrap = document.createElement('p');
                    wrap.hidden = true;
                    wrap.setAttribute(attribute + '-wrap', '');
                    var label = document.createElement('label');
                    label.textContent = labelText;
                    var field = document.createElement('input');
                    field.type = type || 'text';
                    field.value = value || '';
                    field.maxLength = 300;
                    field.setAttribute(attribute, '');
                    field.id = 'resume-proposal-' + proposalIndex + '-' + attribute;
                    label.htmlFor = field.id;
                    wrap.appendChild(label);
                    wrap.appendChild(field);
                    item.appendChild(wrap);
                    return field;
                }

                employerField = detailField('Employer', 'data-proposal-employer', 'text', proposed.employer_name);
                institutionField = detailField('Institution', 'data-proposal-institution', 'text', proposed.institution_name);
                issuerField = detailField('Issuer', 'data-proposal-issuer', 'text', proposed.issuer);
                issueDateField = detailField('Issue date', 'data-proposal-issue-date', 'date', proposed.issue_date);

                function statusField(labelText, attribute, choices, selected) {
                    var wrap = document.createElement('p');
                    wrap.hidden = true;
                    wrap.setAttribute(attribute + '-wrap', '');
                    var label = document.createElement('label');
                    label.textContent = labelText;
                    var field = document.createElement('select');
                    field.setAttribute(attribute, '');
                    field.id = 'resume-proposal-' + proposalIndex + '-' + attribute;
                    label.htmlFor = field.id;
                    choices.forEach(function (choice) {
                        var option = document.createElement('option');
                        option.value = choice[0];
                        option.textContent = choice[1];
                        field.appendChild(option);
                    });
                    if (selected) {
                        field.value = selected;
                    }
                    wrap.appendChild(label);
                    wrap.appendChild(field);
                    item.appendChild(wrap);
                    return field;
                }

                educationStatusField = statusField('Status', 'data-proposal-education-status', [
                    ['in_progress', 'In progress'], ['completed', 'Completed'], ['planned', 'Planned'],
                    ['admitted', 'Admitted'], ['paused', 'Paused'], ['withdrawn', 'Withdrawn']
                ], proposed.education_status);
                credentialStatusField = statusField('Status', 'data-proposal-credential-status', [
                    ['in_progress', 'In progress'], ['planned', 'Planned'], ['completed', 'Completed']
                ], proposed.completion_status);

                var parentLabelNode = document.createElement('label');
                parentLabelNode.textContent = 'Which entry does this belong to? (Impact only)';
                parentField = document.createElement('select');
                parentField.id = 'resume-proposal-' + proposalIndex + '-parent';
                parentLabelNode.htmlFor = parentField.id;
                parentField.hidden = true;
                fillParentSelect(parentField);
                var parentWrap = document.createElement('p');
                parentWrap.appendChild(parentLabelNode);
                parentWrap.appendChild(parentField);
                item.appendChild(parentWrap);

                function syncProposalDetails() {
                    var type = typeField.value;
                    employerField.parentNode.hidden = type !== 'role';
                    institutionField.parentNode.hidden = type !== 'education';
                    educationStatusField.parentNode.hidden = type !== 'education';
                    issuerField.parentNode.hidden = type !== 'credential';
                    credentialStatusField.parentNode.hidden = type !== 'credential';
                    issueDateField.parentNode.hidden = type !== 'credential' ||
                        credentialStatusField.value !== 'completed';
                    parentField.parentNode.hidden = type !== 'accomplishment';
                    parentField.hidden = type !== 'accomplishment';
                    if (typeField.value === 'accomplishment' && !parentCandidates.length) {
                        loadParentCandidates().then(function () { fillParentSelect(parentField); });
                    }
                }
                typeField.addEventListener('change', syncProposalDetails);
                credentialStatusField.addEventListener('change', syncProposalDetails);
                syncProposalDetails();
            }

            var actions = document.createElement('p');
            actions.className = 'resume-intake__proposal-actions';
            var accept = document.createElement('button');
            accept.type = 'button';
            accept.className = 'resume-intake__add';
            accept.textContent = proposal.target_key ? 'Save this change privately' : 'Save this privately';
            var reject = document.createElement('button');
            reject.type = 'button';
            reject.className = 'resume-intake__quiet';
            reject.textContent = 'Discard';

            accept.addEventListener('click', function () {
                var confirmed;
                if (needsCreateDetails) {
                    var type = typeField.value;
                    var value = wordingField.value.trim();
                    if (!value) {
                        setStatus('Add your wording before saving.', 'error');
                        return;
                    }
                    confirmed = {record_type: type};
                    var subject = {role: 'role_title', education: 'title',
                                   credential: 'name', skill: 'name',
                                   accomplishment: 'wording'}[type];
                    confirmed[subject] = value;
                    if (type === 'role') {
                        confirmed.employer_name = employerField.value.trim();
                        if (!confirmed.employer_name) {
                            setStatus('Add the employer for this role.', 'error');
                            return;
                        }
                    }
                    if (type === 'credential') {
                        confirmed.issuer = issuerField.value.trim();
                        if (!confirmed.issuer) {
                            setStatus('Add the issuer for this credential.', 'error');
                            return;
                        }
                        confirmed.completion_status = credentialStatusField.value;
                        if (confirmed.completion_status === 'completed') {
                            confirmed.issue_date = issueDateField.value;
                            if (!confirmed.issue_date) {
                                setStatus('Add the issue date for a completed credential.', 'error');
                                return;
                            }
                        }
                    }
                    if (type === 'education') {
                        confirmed.institution_name = institutionField.value.trim();
                        if (!confirmed.institution_name) {
                            setStatus('Add the institution for this education.', 'error');
                            return;
                        }
                        confirmed.education_status = educationStatusField.value;
                    }
                    if (type === 'accomplishment') {
                        var parentValue = parentField ? parentField.value : '';
                        if (!parentValue) {
                            setStatus('Choose which entry this Impact belongs to.', 'error');
                            return;
                        }
                        confirmed.parent_key = parentValue;
                    }
                } else {
                    // Only the fields the member supplied travel back: the
                    // service merges them over the target's current values.
                    confirmed = proposal.proposed_values || {};
                }
                postJson(urls.decision, {
                    request_id: requestId(),
                    proposal_key: proposal.proposal_key,
                    decision: 'accept',
                    confirmed_values: confirmed
                }).then(function (result) {
                    if (!result.response.ok) {
                        setStatus(result.payload.message || 'That could not be saved.', 'error');
                        return;
                    }
                    setStatus(result.payload.message || 'Saved privately.', 'ok');
                    load();
                });
            });
            reject.addEventListener('click', function () {
                postJson(urls.decision, {
                    request_id: requestId(),
                    proposal_key: proposal.proposal_key,
                    decision: 'reject'
                }).then(function (result) {
                    if (!result.response.ok) {
                        setStatus(result.payload.message || 'That could not be discarded.', 'error');
                        return;
                    }
                    setStatus('Proposal discarded. Nothing was saved.', 'ok');
                    load();
                });
            });
            actions.appendChild(accept);
            actions.appendChild(reject);
            item.appendChild(actions);
            proposalList.appendChild(item);
        });
    }

    function applyQuestion(payload) {
        if (payload && payload.question && payload.question.prompt) {
            questionPrompt.textContent = payload.question.prompt;
            if (payload.question.context) {
                questionContext.textContent = payload.question.context;
                questionContext.hidden = false;
            }
        }
    }

    function applyGuideState(workspace, guide) {
        var status = (workspace && workspace.guide && workspace.guide.status) || 'not_started';
        var receipts = (workspace && workspace.receipts_count) || 0;
        firstUse = receipts === 0 && status === 'not_started' && !guideDismissed;
        root.setAttribute('data-state', firstUse ? 'welcome' : 'docked');
        if (editorSection) {
            editorSection.classList.toggle('resume-editor--intake-welcome', firstUse);
        }
        if (scrim) {
            scrim.hidden = !firstUse;
        }
        if (guide && guide.status === 'completed') {
            setStatus('Guide marked complete. That was your choice.', 'ok');
        }
        applyQuestion(guide);
    }

    function load() {
        return fetch(urls.workspace, {credentials: 'same-origin'})
            .then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (payload) {
                    return {response: response, payload: payload};
                });
            })
            .then(function (result) {
                if (result.response.status === 503) {
                    setStatus(result.payload.message ||
                        'Saving is not enabled yet. Your typing stays here, unsent.', 'error');
                    return null;
                }
                if (!result.response.ok) {
                    setStatus(result.payload.message || 'The composer could not be loaded.', 'error');
                    return null;
                }
                renderProposals(result.payload.pending_proposals || []);
                renderReceipt(result.payload.last_receipt || null);
                return fetch(urls.guide, {credentials: 'same-origin'})
                    .then(function (response) {
                        return response.json().catch(function () { return {}; });
                    })
                    .then(function (guide) { applyGuideState(result.payload, guide); })
                    .catch(function () {
                        applyGuideState(result.payload, null);
                        setStatus('The guide question is unavailable. Your saved work is unchanged.', 'error');
                    });
            });
    }

    /* -- explicit Add ------------------------------------------------- */

    function buildRequestParts() {
        var request = {
            type: 'add_submission',
            text: (textarea.value || '').trim() || null,
            items: queuedFacts.map(function (row) {
                return {
                    client_key: row.client_key,
                    record_type: row.record_type,
                    values: row.values,
                    explicit_clears: row.explicit_clears,
                    parent_key: row.parent_key || null
                };
            }),
            attachments: attachments.filter(function (row) { return row.status !== 'cancelled'; }).map(function (row) {
                if (row.kind === 'recording') {
                    return {client_key: row.client_key, kind: 'recording', source_key: row.source_key};
                }
                return {
                    client_key: row.client_key, kind: 'document',
                    declared_content_type: row.declared_content_type,
                    filename: row.filename
                };
            })
        };
        return request;
    }

    function submit(event) {
        if (event) {
            event.preventDefault();
        }
        if (addOperation) return;
        var request = buildRequestParts();
        if (!request.text && !request.items.length && !request.attachments.length) {
            setStatus('Add something before saving.', 'error');
            return;
        }
        // One unacknowledged Add keeps its request id and its payload, so a
        // dropped response is retried as the SAME request rather than a new one.
        var signature = signatureOf(request);
        if (!pendingAdd || pendingAdd.signature !== signature) {
            pendingAdd = {request_id: requestId(), signature: signature};
        }
        request.request_id = pendingAdd.request_id;
        var submittedText = textarea.value;

        var form = new FormData();
        form.append('request', JSON.stringify(request));
        attachments.forEach(function (row) {
            if (row.kind === 'document' && row.file) {
                form.append('file:' + row.client_key, row.file, row.filename || 'attachment');
            }
        });
        addButton.disabled = true;
        renderAttachments();
        var operation = beginActivity('add');
        addOperation = operation;
        setStatus('Preparing your information\u2026', 'ok');
        send(urls.submit, {method: 'POST', body: form}).then(function (result) {
            endActivity(operation);
            addOperation = null;
            addButton.disabled = false;
            if (result.response.status === 400 || result.response.status === 409) {
                // A definitive refusal means this payload will never be
                // accepted as-is: the next attempt gets a fresh key.
                pendingAdd = null;
                renderAttachments();
                setStatus(result.payload.message ||
                    'That Add could not be completed. Your input is still here.', 'error');
                return;
            }
            if (!result.response.ok) {
                // Not acknowledged: keep the same request and every byte.
                var preserved = result.payload.input_preserved;
                setStatus(
                    (result.payload.message || 'That Add did not finish.') +
                    (preserved ? ' Your input is still here, unsent.' : ''),
                    'error'
                );
                return;
            }
            pendingAdd = null;
            var receipt = result.payload;
            renderReceipt(receipt);
            var failure = (receipt.results || []).filter(function (row) {
                return row.outcome === 'failed';
            });
            setStatus(failure.length
                ? (receipt.message || 'Some of that was not saved.')
                : (receipt.message || 'Add finished.'), failure.length ? 'error' : 'ok');

            var acknowledged = (receipt.results || []).filter(function (row) {
                return row.outcome === 'saved' || row.outcome === 'unresolved';
            }).map(function (row) { return row.client_key; });
            queuedFacts = queuedFacts.filter(function (row) {
                return acknowledged.indexOf(row.client_key) === -1;
            });
            attachments = attachments.filter(function (row) {
                return acknowledged.indexOf(row.client_key) === -1;
            });
            // Retained (refused) uploads keep their honest per-item state so
            // the member can see they are still unsent and retry them.
            attachments.forEach(function (row) {
                var match = (receipt.results || []).filter(function (entry) {
                    return entry.client_key === row.client_key;
                })[0];
                if (match) {
                    row.status = match.outcome;
                    row.message = match.message;
                }
            });
            // Clear the text only when it was acknowledged AND the member has
            // not typed something newer while the request was in flight.
            var textAcknowledged = (receipt.results || []).some(function (row) {
                return row.kind === 'text' && acknowledged.indexOf(row.client_key) !== -1;
            });
            if (textAcknowledged && textarea.value === submittedText) {
                textarea.value = '';
            }
            renderQueued();
            renderAttachments();
            refreshDraftLabel();
            load();
        }).catch(function () {
            endActivity(operation);
            addOperation = null;
            addButton.disabled = false;
            setStatus(
                'The connection dropped before Add finished. Your answer is still here, unsent.',
                'error'
            );
        });
    }

    /* -- microphone ---------------------------------------------------- */

    function appendTranscript(transcript) {
        var dictation = window.PeerSlateDictation;
        if (dictation && typeof dictation.appendTranscript === 'function') {
            dictation.appendTranscript(textarea, transcript);
            return;
        }
        var existing = textarea.value || '';
        var separator = existing && !/\s$/.test(existing) ? ' ' : '';
        textarea.value = existing + separator + transcript;
    }

    function recordingSignature(blob, clientKey) {
        if (!window.crypto || !window.crypto.subtle || !blob.arrayBuffer) {
            return Promise.reject(new Error('Audio digest is unavailable.'));
        }
        return blob.arrayBuffer().then(function (bytes) {
            return window.crypto.subtle.digest('SHA-256', bytes);
        }).then(function (digest) {
            var audioSha256 = Array.prototype.map.call(
                new Uint8Array(digest),
                function (value) { return value.toString(16).padStart(2, '0'); }
            ).join('');
            return signatureOf({
                client_key: clientKey,
                size: blob.size,
                type: blob.type,
                audio_sha256: audioSha256
            });
        });
    }

    function uploadRecording(blob, clientKey, retryRow, durationSeconds) {
        var existingRow = retryRow || attachments.filter(function (row) {
            return row.kind === 'recording' && row.client_key === clientKey;
        })[0];
        if (!existingRow) {
            existingRow = {
                client_key: clientKey, kind: 'recording', label: 'Recording',
                status: 'selected', blob: blob, retryable: false,
                recording_request: {
                    request_id: requestId(),
                    client_key: clientKey,
                    signature: null,
                    duration_seconds: durationSeconds
                }
            };
            attachments.push(existingRow);
        }
        if (existingRow.transcribing) return;
        var recordingRequest = existingRow.recording_request;
        var generation = recordingGeneration;
        existingRow.transcriptionGeneration = generation;
        existingRow.transcribing = true;
        var operation = beginActivity('transcription');
        existingRow.activityOperation = operation;
        cancelRecordingButton.hidden = false;
        cancelRecordingButton.textContent = 'Cancel transcription';
        setStatus('Transcribing\u2026 you can keep typing.', 'ok');
        recordingSignature(blob, clientKey).then(function (signature) {
            if (recordingRequest.signature && recordingRequest.signature !== signature) {
                throw new Error('The recording bytes changed before retry.');
            }
            recordingRequest.signature = signature;
            var form = new FormData();
            form.append('request', JSON.stringify({
                request_id: recordingRequest.request_id,
                client_key: recordingRequest.client_key,
                duration_seconds: recordingRequest.duration_seconds
            }));
            form.append('recording', blob, 'recording.webm');
            return send(urls.recording, {method: 'POST', body: form});
        }).then(function (result) {
            endActivity(operation);
            if (generation !== recordingGeneration) {
                existingRow.status = 'cancelled'; existingRow.retryable = false;
                renderAttachments(); refreshDraftLabel(); return;
            }
            existingRow.transcribing = false;
            syncRecordingCancel();
            if (result.response.status === 400 || result.response.status === 409) {
                existingRow.status = 'failed';
                existingRow.retryable = false;
                setStatus(result.payload.message ||
                    'That recording could not be transcribed. You can keep typing.', 'error');
                renderAttachments();
                refreshDraftLabel();
                return;
            }
            if (!result.response.ok || !result.payload.success) {
                // The audio never became a durable source: keep it retryable.
                existingRow.status = result.payload.outcome === 'pending' ? 'pending' : 'failed';
                existingRow.retryable = !result.payload.recovery_required;
                existingRow.message = result.payload.recovery_required
                    ? 'Recovery is required before this recording can be processed again.'
                    : null;
                setStatus(
                    (result.payload.message ||
                        'That recording did not finish uploading. Try again, or keep typing.') +
                    (result.payload.input_preserved ? ' Your recording is still here, unsent.' : ''),
                    'error'
                );
                renderAttachments();
                refreshDraftLabel();
                return;
            }
            // Insert, never overwrite: text typed while this was running stays.
            appendTranscript(result.payload.transcript);
            existingRow.status = 'selected';
            existingRow.retryable = false;
            existingRow.source_key = result.payload.source_key;
            renderAttachments();
            refreshDraftLabel();
            setStatus('Transcript added to your answer. Nothing is saved until you press Add.', 'ok');
        }).catch(function () {
            endActivity(operation);
            if (generation !== recordingGeneration) {
                existingRow.status = 'cancelled'; existingRow.retryable = false;
                renderAttachments(); refreshDraftLabel(); return;
            }
            existingRow.transcribing = false;
            syncRecordingCancel();
            existingRow.status = 'failed';
            existingRow.retryable = true;
            renderAttachments();
            refreshDraftLabel();
            setStatus('The recording did not finish uploading. Try again, or keep typing.', 'error');
        });
    }

    function stopRecording() {
        if (recorder && recorder.state !== 'inactive') {
            recorder.stop();
        }
    }

    function startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            setStatus('Recording is not supported in this browser. You can keep typing.', 'error');
            return;
        }
        var generation = recordingGeneration;
        cancelRecordingButton.hidden = false;
        cancelRecordingButton.textContent = 'Cancel recording';
        navigator.mediaDevices.getUserMedia({audio: true}).then(function (stream) {
            if (generation !== recordingGeneration) { stream.getTracks().forEach(function (track) { track.stop(); }); return; }
            recordedChunks = [];
            recorder = new MediaRecorder(stream);
            recorder.addEventListener('dataavailable', function (event) {
                if (event.data && event.data.size) {
                    recordedChunks.push(event.data);
                }
            });
            recorder.addEventListener('stop', function () {
                stream.getTracks().forEach(function (track) { track.stop(); });
                micButton.setAttribute('aria-pressed', 'false');
                if (generation !== recordingGeneration) return;
                var blob = new Blob(recordedChunks, {type: recorder.mimeType || 'audio/webm'});
                if (!blob.size) {
                    cancelRecordingButton.hidden = true;
                    setStatus('No audio was captured. You can keep typing.', 'error');
                    return;
                }
                uploadRecording(
                    blob,
                    requestId(),
                    null,
                    Math.max(1, Math.round((Date.now() - recordingStartedAt) / 1000))
                );
            });
            recorder.start();
            recordingStartedAt = Date.now();
            micButton.setAttribute('aria-pressed', 'true');
            setStatus('Recording. Press the microphone again to stop.', 'ok');
        }).catch(function () {
            if (generation !== recordingGeneration) return;
            cancelRecordingButton.hidden = true;
            setStatus('Microphone permission was not granted. You can keep typing.', 'error');
        });
    }

    /* -- guide --------------------------------------------------------- */

    function hideGuide() {
        guideHidden = true;
        guideDismissed = true;
        root.hidden = true;
        reopenButton.hidden = false;
        renderActivity();
        if (firstUse) {
            root.setAttribute('data-state', 'docked');
            if (editorSection) {
                editorSection.classList.remove('resume-editor--intake-welcome');
            }
            if (scrim) {
                scrim.hidden = true;
            }
        }
    }

    function reopenGuide() {
        guideHidden = false;
        root.hidden = false;
        reopenButton.hidden = true;
        renderActivity();
        if (firstUse) {
            root.setAttribute('data-state', 'welcome');
            if (scrim) {
                scrim.hidden = false;
            }
        }
        textarea.focus();
    }

    function setGuideStatus(status) {
        var signature = signatureOf({status: status});
        if (!pendingGuide || pendingGuide.signature !== signature) {
            pendingGuide = {request_id: requestId(), signature: signature};
        }
        postJson(urls.guideStatus, {
            request_id: pendingGuide.request_id,
            status: status
        }).then(function (result) {
            if (!result.response.ok) {
                if (result.response.status === 400 || result.response.status === 409) {
                    pendingGuide = null;
                }
                setStatus(result.payload.message || 'The guide could not be updated.', 'error');
                return;
            }
            pendingGuide = null;
            setStatus(status === 'completed'
                ? 'Guide marked complete. That was your choice.'
                : 'Question skipped. You can reopen the guide any time.', 'ok');
            if (status === 'completed' || status === 'skipped') {
                hideGuide();
            }
        }).catch(function () {
            setStatus('The guide update did not finish. Try again.', 'error');
        });
    }

    /* -- wiring -------------------------------------------------------- */

    addFactButton.addEventListener('click', function () {
        var type = typeSelect.value;
        if (!type) {
            setStatus('Choose a type for a direct fact, or just type your answer.', 'error');
            return;
        }
        var values;
        try {
            values = valuesFor(type, fieldsForType(type));
        } catch (error) {
            setStatus(error.message, 'error');
            return;
        }
        if (type === 'role' && values.current_role === true && values.end_date) {
            setStatus('A current role has no end date. Remove the end date or choose Past role.', 'error');
            return;
        }
        var clears = clearsForType(type);
        var subjectField = {role: 'role_title', education: 'title', credential: 'name',
                            skill: 'name', accomplishment: 'wording'}[type];
        if (!values[subjectField]) {
            setStatus('Add the ' + REQUIRED_HINT[type] + ' before queueing that fact.', 'error');
            return;
        }
        var missing = (REQUIRED_FIELDS[type] || []).filter(function (name) {
            return !values[name];
        });
        if (missing.length) {
            setStatus('Add the ' + REQUIRED_HINT[type] + ' before queueing that fact.', 'error');
            return;
        }
        if (type === 'credential' && values.completion_status === 'completed' && !values.issue_date) {
            setStatus('Add the issue date for a completed credential.', 'error');
            return;
        }
        if (type === 'credential' && values.completion_status !== 'completed') {
            delete values.issue_date;
        }
        var parentKey = null;
        if (type === 'accomplishment') {
            parentKey = parentSelect ? parentSelect.value : '';
            if (!parentKey) {
                setStatus(
                    parentCandidates.length
                        ? 'Choose which entry this Impact belongs to.'
                        : 'Add an eligible private role first, then add an Impact.',
                    'error'
                );
                return;
            }
        }
        if (clears.some(function (name) { return Object.prototype.hasOwnProperty.call(values, name); })) {
            setStatus('A field cannot be filled and cleared at the same time.', 'error');
            return;
        }
        queuedFacts.push({
            client_key: requestId(),
            record_type: type,
            values: values,
            explicit_clears: clears,
            parent_key: parentKey,
            label: values[subjectField]
        });
        // A subsequent fact must not inherit dates/currentness from this one.
        ['date_precision', 'start_date', 'end_date', 'current_role'].forEach(function (name) {
            var id = (FIELD_INPUTS[type] || {})[name];
            if (id) document.getElementById(id).value = '';
        });
        typeSelect.value = '';
        syncDirectFields();
        renderQueued();
        refreshDraftLabel();
        setStatus('Queued. It saves privately when you press Add.', 'ok');
    });
    typeSelect.addEventListener('change', syncDirectFields);
    var credentialStatusInput = document.getElementById('resume-intake-credential-status');
    if (credentialStatusInput) {
        credentialStatusInput.addEventListener('change', syncDirectFields);
    }
    composer.addEventListener('submit', submit);
    textarea.addEventListener('input', refreshDraftLabel);
    fileInput.addEventListener('change', function () {
        Array.prototype.forEach.call(fileInput.files, function (file) {
            attachments.push({
                client_key: requestId(),
                kind: 'document',
                file: file,
                filename: file.name,
                declared_content_type: file.type || 'application/octet-stream',
                label: file.name,
                status: 'selected'
            });
        });
        fileInput.value = '';
        renderAttachments();
        refreshDraftLabel();
        setStatus('Attached. Nothing is uploaded until you press Add.', 'ok');
    });
    cancelRecordingButton.addEventListener('click', function () {
        recordingGeneration += 1;
        attachments.forEach(function (row) {
            if (row.transcribing) {
                endActivity(row.activityOperation);
                row.status = 'cancelled'; row.retryable = false; row.transcribing = false;
            }
        });
        renderAttachments(); refreshDraftLabel();
        stopRecording();
        cancelRecordingButton.hidden = true;
        micButton.setAttribute('aria-pressed', 'false');
        setStatus('Recording cancelled. Your typed words are kept. Any audio already uploaded stays private; its transcript will not be inserted.', 'ok');
    });
    micButton.addEventListener('click', function () {
        if (recorder && recorder.state === 'recording') {
            stopRecording();
        } else {
            startRecording();
        }
    });
    hideButton.addEventListener('click', hideGuide);
    reopenButton.addEventListener('click', reopenGuide);
    if (scrim) {
        scrim.addEventListener('click', hideGuide);
    }
    skipButton.addEventListener('click', function () { setGuideStatus('skipped'); });
    completeButton.addEventListener('click', function () { setGuideStatus('completed'); });
    protectNavigation();
    syncDirectFields();
    renderQueued();
    renderAttachments();
    load();
})();
