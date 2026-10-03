/* MVP1 increment C: private Resume composer.
 *
 * One guide connects explicit input, recording/transcription, review and
 * optional questions. Provider work starts only on a member action. Page
 * reads never start it; canonical facts require acknowledged confirmation.
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
 *  - one adaptive foreground guide; the actual private document stays behind
 *    it and only acknowledged facts cause the background to become clearer.
 *
 * No draft is written to browser storage: sensitive drafts are not persisted
 * client-side. Owner-scoped durable drafts use the selected retention policy.
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
        originals: root.getAttribute('data-intake-originals-url'),
        guide: root.getAttribute('data-guide-url'),
        guideStatus: root.getAttribute('data-guide-status-url'),
        interview: root.getAttribute('data-interview-url')
    };

    var guidePanel = document.getElementById('resume-intake-guide');
    var manual = document.getElementById('resume-intake-manual');
    var manualStatus = document.getElementById('resume-intake-manual-status');
    var manualSave = document.getElementById('resume-intake-manual-save');
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
    // The fixed reopen control must escape the page panel's stacking context.
    // Native dialog already uses the top layer; its launcher does not.
    document.body.appendChild(reopenButton.parentNode);

    var FIELDS = {
        role: ['role_title', 'employer_name', 'location_text', 'summary', 'start_date',
               'end_date', 'date_precision', 'employment_type', 'current_role'],
        education: ['title', 'institution_name', 'degree_name', 'field_of_study',
                    'education_status', 'grade_text', 'location_text', 'summary',
                    'start_date', 'end_date', 'date_precision'],
        credential: ['name', 'issuer', 'identifier', 'issue_date', 'expiration_date',
                     'issue_date_precision', 'expiration_date_precision', 'verification_url', 'completion_status'],
        skill: ['name', 'summary'],
        accomplishment: ['wording', 'metric_value', 'metric_label'],
        knowledge: ['title', 'wording', 'classification']
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
                     issue_date: 'resume-intake-credential-issue-date', expiration_date: 'resume-intake-credential-expiration-date',
                     issue_date_precision: 'resume-intake-credential-issue-precision', expiration_date_precision: 'resume-intake-credential-expiration-precision'},
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
        accomplishment: ['wording'], knowledge: ['title', 'wording', 'classification']
    };

    var queuedFacts = [];
    var attachments = [];
    var recorder = null;
    var pendingAdd = null;         // immutable request, FormData and submitted text
    var pendingGuide = null;       // immutable member choice until acknowledged
    var pendingDecision = null;
    var pendingInterview = null;
    var decisionBusy = false;
    var guideBusy = false;
    var interviewBusy = false;
    var microphonePending = false;
    var heldRecording = null;
    var proposals = [];
    var selectedProposalKey = null;
    var newestProposalKeys = [];
    var ownerCatalog = [];
    var correctionTarget = null;
    var correctionInputs = {};
    var correctionDraft = null;
    var pendingCorrection = null;
    var conversationIntent = null;
    var lastAcknowledgement = '';
    var lastConfirmedKey = null;
    var proposalDrafts = {};
    var screen = 'welcome';
    var initialized = false;
    var acknowledgedFacts = 0;
    var catalogLoaded = false;
    var seenQuestions = [];
    var welcomeTitle = document.getElementById('resume-intake-title').textContent;
    var parentCandidates = [];     // owner-scoped parents for an Impact entry
    var guideHidden = false;
    var guideDismissed = false;
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
            .then(function (response) {
                if (!response.ok) throw new Error('Workspace unavailable');
                return response.json();
            })
            .then(function (payload) {
                if (!Array.isArray(payload.items)) throw new Error('Workspace unavailable');
                ownerCatalog = payload.items.slice();
                if (!catalogLoaded) {
                    acknowledgedFacts = payload.items.length;
                    catalogLoaded = true;
                    updateReveal();
                }
                parentCandidates = (payload.items || []).filter(function (item) {
                    return item.record_type === 'role' && item.editable === true &&
                        item.save_mode === 'canonical' && !item.orphaned;
                }).map(function (item) {
                    return {record_key: item.record_key, label: parentLabel(item),
                            record_type: item.record_type};
                });
                return parentCandidates;
            })
            .catch(function () { ownerCatalog = []; parentCandidates = []; return []; });
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
            attachments.some(function (row) { return row.status !== 'cancelled'; }) ||
            microphonePending || (recorder && recorder.state === 'recording') ||
            heldRecording || pendingAdd || pendingDecision || pendingCorrection ||
            Object.values(correctionInputs).some(function (value) { return Boolean(value.trim()); }) || Object.keys(proposalDrafts).length
        );
    }

    function refreshDraftLabel() {
        if (!draftLabel) {
            return;
        }
        draftLabel.textContent = hasUnsavedInput()
            ? 'Draft answer \u00b7 Not added yet'
            : (proposals.length + ' suggestions to review · ' + acknowledgedFacts + ' saved privately');
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
        manualStatus.textContent = message || '';
        manualStatus.setAttribute('data-kind', kind || 'ok');
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
        cancelRecordingButton.hidden = !recording && !transcribing && !microphonePending;
        cancelRecordingButton.textContent = recording || microphonePending ? 'Cancel recording' : 'Cancel transcription';
        root.setAttribute('data-recording', recording ? 'true' : 'false');
        document.getElementById('resume-intake-recording').hidden = !recording;
        micButton.querySelector('span').textContent = recording ? 'Stop recording' : 'Start recording';
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
            credential: 'Credential', accomplishment: 'Impact', knowledge: 'Personal story', unspecified: 'Unsorted words'
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
        if (type === 'credential') encodeCredentialDates(values);
        return values;
    }

    function encodeCredentialDates(values) {
        ['issue_date', 'expiration_date'].forEach(function (name) {
            if (!values[name]) { if (Object.prototype.hasOwnProperty.call(values, name + '_precision')) values[name + '_precision'] = null; return; }
            var raw = String(values[name]), precision = values[name + '_precision'] || ({4: 'year', 7: 'month', 10: 'day'})[raw.length];
            var length = {year: 4, month: 7, day: 10}[precision];
            if (!length || raw.length !== length || !({4: /^\d{4}$/, 7: /^\d{4}-\d{2}$/, 10: /^\d{4}-\d{2}-\d{2}$/}[length]).test(raw))
                throw new Error('Use the credential date detail you know: YYYY, YYYY-MM or YYYY-MM-DD.');
            values[name] = raw + (length === 4 ? '-01-01' : length === 7 ? '-01' : '');
            // Legacy exact-day commands keep their existing contract.
            if (precision === 'day') delete values[name + '_precision'];
            else values[name + '_precision'] = precision;
        });
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
        Array.prototype.forEach.call(manual.querySelectorAll('[data-role-field]'), function (node) {
            node.hidden = type !== 'role';
        });
        Array.prototype.forEach.call(manual.querySelectorAll('[data-skill-field]'), function (node) {
            node.hidden = type !== 'skill';
        });
        Array.prototype.forEach.call(manual.querySelectorAll('[data-education-field]'), function (node) {
            node.hidden = type !== 'education';
        });
        Array.prototype.forEach.call(manual.querySelectorAll('[data-credential-field]'), function (node) {
            node.hidden = type !== 'credential';
        });
        var completedCredential = document.querySelector('[data-credential-completed-field]');
        var credentialStatus = document.getElementById('resume-intake-credential-status');
        if (completedCredential) {
            completedCredential.hidden = type !== 'credential' ||
                !credentialStatus || credentialStatus.value !== 'completed';
        }
        Array.prototype.forEach.call(manual.querySelectorAll('[data-accomplishment-field]'), function (node) {
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
            remove.disabled = Boolean(pendingAdd && pendingAdd.mode === 'manual');
            remove.addEventListener('click', function () {
                if (pendingAdd && pendingAdd.mode === 'manual') return;
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
                cancelled: 'transcription cancelled; any uploaded audio stays private',
                held: 'kept on this page'
            }[row.status] || row.status;
            item.appendChild(document.createTextNode(' ' + row.label + ' \u00b7 ' + state));
            if (row.message) {
                item.appendChild(document.createTextNode(' \u00b7 ' + row.message));
            }
            if ((row.kind === 'document' && (row.status === 'selected' || row.status === 'failed')) ||
                (row.kind === 'recording' && !row.transcribing && ['selected', 'failed', 'held', 'pending'].indexOf(row.status) !== -1)) {
                var remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'resume-intake__quiet';
                remove.textContent = 'Remove';
                remove.setAttribute('aria-label', 'Remove ' + row.label);
                remove.disabled = Boolean(pendingAdd) || addButton.disabled;
                remove.addEventListener('click', function () {
                    if (pendingAdd || addButton.disabled) return;
                    if (heldRecording === row) heldRecording = null;
                    attachments = attachments.filter(function (entry) { return entry.client_key !== row.client_key; });
                    renderAttachments();
                    refreshDraftLabel();
                    setStatus('Removed this unsent attachment. Your other input is kept.', 'ok');
                });
                item.appendChild(document.createTextNode(' '));
                item.appendChild(remove);
            }
            if ((row.status === 'failed' || row.status === 'pending' || row.status === 'held') && row.retryable && row.blob) {
                var retry = document.createElement('button');
                retry.type = 'button';
                retry.className = 'resume-intake__quiet';
                retry.textContent = row.status === 'held' ? 'Transcribe recording' : 'Try again';
                retry.addEventListener('click', function () {
                    // Each attachment owns its immutable request metadata.
                    // A later recording cannot replace the request or duration
                    // used when this exact blob was first submitted.
                    if (heldRecording === row) heldRecording = null;
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
            empty.textContent = 'Nothing added yet. Type, speak or attach a file, then continue.';
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

    var FIELD_LABELS = {
        role_title: 'Role', employer_name: 'Employer', location_text: 'Location',
        summary: 'Description', start_date: 'Start date', end_date: 'End date',
        date_precision: 'Date detail', employment_type: 'Employment type', current_role: 'Role status',
        title: 'Program', institution_name: 'Institution', degree_name: 'Degree',
        field_of_study: 'Field of study', education_status: 'Education status', grade_text: 'Grade',
        name: 'Name', issuer: 'Issuer', identifier: 'Identifier', issue_date: 'Issue date',
        expiration_date: 'Expiration date', verification_url: 'Verification link',
        issue_date_precision: 'Issue date detail', expiration_date_precision: 'Expiration date detail',
        completion_status: 'Credential status', wording: 'Contribution', metric_value: 'Result', metric_label: 'Result measure'
    };
    var CHOICES = {
        current_role: [['true', 'Current role'], ['false', 'Past role']],
        date_precision: [['unknown', 'Unknown'], ['year', 'Year'], ['month', 'Month'], ['day', 'Exact day']],
        employment_type: ['full_time', 'part_time', 'contract', 'freelance', 'internship', 'volunteer', 'military', 'other'],
        education_status: ['in_progress', 'completed', 'planned', 'admitted', 'paused', 'withdrawn'],
        completion_status: ['in_progress', 'planned', 'completed']
    };
    CHOICES.issue_date_precision = CHOICES.expiration_date_precision = [['year', 'Year'], ['month', 'Month'], ['day', 'Exact day']];
    function node(tag, text, className) {
        var el = document.createElement(tag);
        if (text !== undefined) el.textContent = text;
        if (className) el.className = className;
        return el;
    }
    function updateReveal() {
        // No timer or completion percentage claims that unsaved words are facts.
        var blur = screen === 'finish' ? 0 : Math.max(0, 8 - acknowledgedFacts * 2);
        if (editorSection) editorSection.style.setProperty('--resume-reveal-blur', blur + 'px');
    }
    function factSaved(count) {
        acknowledgedFacts += count || 1;
        updateReveal();
        document.dispatchEvent(new Event('resume-intake-fact-saved'));
        loadParentCandidates().then(function () { fillParentSelect(parentSelect); });
    }
    function showScreen(next, focus) {
        if (next !== screen) setStatus('', 'ok');
        if (screen === 'input' && next !== 'input' && microphonePending) {
            recordingGeneration += 1; microphonePending = false; syncRecordingCancel();
        }
        if (screen === 'input' && next !== 'input' && recorder && recorder.state === 'recording') {
            recorder.keepLocal = true; stopRecording();
        }
        screen = next;
        root.setAttribute('data-screen', next);
        ['welcome', 'input', 'review', 'next', 'optional', 'sharing', 'finish'].forEach(function (name) {
            document.getElementById('resume-intake-' + name).hidden = name !== (next === 'correction' ? 'review' : next);
        });
        var copy = {
            welcome: [welcomeTitle, ''],
            input: ['Let’s start with you.', 'Talk naturally or type. We’ll help you turn the details into something useful.'],
            review: ['Does this look right?', 'These details are suggestions. Confirm them before they become part of your résumé.'],
            correction: ['Make it yours.', 'Keep what’s right and correct anything we missed.'],
            next: ['Your résumé is taking shape.', 'Your confirmed details are saved. A little more context can help your personal AI understand your work.'],
            optional: ['Bring more of you into view.', ''],
            sharing: ['You’re in control.', ''],
            finish: ['A foundation you can build on.', '']
        }[next];
        document.getElementById('resume-intake-title').textContent = copy[0];
        var description = document.getElementById('resume-intake-description');
        description.textContent = copy[1]; description.hidden = !copy[1];
        document.getElementById('resume-intake-eyebrow').textContent = next === 'welcome' ? 'WELCOME TO PEERSLATE' : 'YOUR PEERSLATE';
        document.getElementById('resume-intake-back').hidden = next === 'welcome' || next === 'finish';
        document.getElementById('resume-intake-finish-unsent').hidden = !hasUnsavedInput();
        receiptBox.hidden = true;
        updateReveal();
        if (focus !== false && root.open) {
            root.querySelector('.resume-intake__surface').scrollTop = 0;
            document.getElementById('resume-intake-title').focus({preventScroll: true});
        }
    }
    function displayValue(name, value, values) {
        if (value === null || value === undefined || value === '') return 'Not supplied';
        if (name === 'current_role') return value === true ? 'Current role' : 'Past role';
        if (name === 'start_date' || name === 'end_date') {
            if (values.date_precision === 'year') return String(value).slice(0, 4);
            if (values.date_precision === 'month') return String(value).slice(0, 7);
        }
        if (name === 'issue_date' || name === 'expiration_date') {
            var precision = values[name + '_precision'];
            if (precision === 'year') return String(value).slice(0, 4);
            if (precision === 'month') return String(value).slice(0, 7);
        }
        return typeof value === 'string' && CHOICES[name] ? value.replace(/_/g, ' ') : String(value);
    }
    function renderProposals(rows, preserveScreen) {
        proposals = rows.slice().sort(function (a, b) {
            return (a.record_type === 'accomplishment' ? 1 : 0) - (b.record_type === 'accomplishment' ? 1 : 0);
        });
        if (pendingDecision && !proposals.some(function (p) { return p.proposal_key === pendingDecision.proposal.proposal_key; })) {
            proposals.unshift(pendingDecision.proposal);
        }
        document.getElementById('resume-intake-review-pending').hidden = !proposals.length;
        if (preserveScreen) return;
        proposalList.replaceChildren();
        var oldSuggestionOverview = document.getElementById('resume-intake-suggestion-overview');
        if (oldSuggestionOverview) oldSuggestionOverview.remove();
        if (!proposals.length) return;
        var proposal = pendingDecision ? pendingDecision.proposal :
            proposals.find(function (row) { return row.proposal_key === selectedProposalKey; }) ||
            proposals.find(function (row) { return newestProposalKeys.indexOf(row.proposal_key) !== -1; }) || proposals[0];
        selectedProposalKey = proposal.proposal_key;
        var proposed = Object.assign({}, proposal.proposed_values || {});
        var known = ownerCatalog.find(function (row) { return row.record_key === proposal.target_key; });
        if (known) proposed = Object.assign({}, known.has_draft ? known.proposed_values : known.values, proposed);
        var fixedType = FIELDS[proposal.record_type] ? proposal.record_type : null;
        var draft = proposalDrafts[proposal.proposal_key];
        var type = fixedType || (draft && draft.type) ||
            (proposed.suggested_category === 'story' ? 'knowledge' : '');
        var item = node('li');
        var group = node('div', undefined, 'resume-intake__inset');
        var facts = node('dl', undefined, 'resume-intake__review-facts');
        var correction = node('fieldset', undefined, 'resume-intake__correction');
        var inputs = {};
        var initial = {};
        var typeField = null;
        var parentField = null;
        var correcting = !fixedType || Boolean(draft);
        var dirty = {};
        function field(name, choices) {
            var wrap = node('p');
            var label = node('label', FIELD_LABELS[name] || name);
            var input = node(choices ? 'select' : (name === 'summary' || name === 'wording' ? 'textarea' : 'input'));
            input.id = 'resume-proposal-' + name;
            input.setAttribute('data-proposal-field', name);
            label.htmlFor = input.id;
            var value = proposed[name];
            if (!fixedType && name === 'wording') {
                value = proposed[name] || proposed.text || proposal.quote || '';
            }
            if (!fixedType && type === 'knowledge') {
                if (name === 'title') value = proposed.title || 'My story';
                if (name === 'classification') value = 'personal';
            }
            if (choices) {
                input.appendChild(new Option('Not supplied', ''));
                choices.forEach(function (choice) {
                    var pair = Array.isArray(choice) ? choice : [choice, choice.replace(/_/g, ' ')];
                    input.appendChild(new Option(pair[1], pair[0]));
                });
                if (value !== undefined && value !== null && value !== '') {
                    var raw = String(value), normalized = raw.toLowerCase();
                    if (Array.from(input.options).some(function (o) { return o.value === normalized; })) input.value = normalized;
                    else { var unsupported = new Option('Source: ' + raw + ' — choose a value', raw); unsupported.disabled = true; input.appendChild(unsupported); input.value = raw; }
                }
            } else {
                input.value = value == null ? '' : displayValue(name, value, proposed);
                if (input.tagName === 'INPUT') input.type = 'text';
                if (name === 'start_date' || name === 'end_date') input.placeholder = 'YYYY, YYYY-MM or YYYY-MM-DD';
                if (name === 'issue_date' || name === 'expiration_date') input.placeholder = 'YYYY, YYYY-MM or YYYY-MM-DD';
            }
            initial[name] = input.value;
            if (draft && draft[type] && Object.prototype.hasOwnProperty.call(draft[type], name)) input.value = draft[type][name];
            function remember() {
                dirty[name] = true;
                draft = proposalDrafts[proposal.proposal_key] || {type: type};
                draft[type] = draft[type] || {}; draft[type][name] = input.value;
                proposalDrafts[proposal.proposal_key] = draft;
            }
            input.addEventListener('input', remember);
            input.addEventListener('change', remember);
            if ((proposal.explicit_clears || []).indexOf(name) !== -1) {
                input.disabled = true;
                wrap.appendChild(node('span', 'This suggestion removes this field. Leave the suggestion out to keep the existing value.', 'resume-intake__hint'));
            }
            wrap.append(label, input); correction.appendChild(wrap); inputs[name] = input;
        }
        function buildFields() {
            correction.replaceChildren(); inputs = {}; initial = {}; dirty = {}; parentField = null;
            if (!fixedType) {
                var typeLabel = node('label', 'Save this as'); typeField = node('select');
                typeField.id = 'resume-proposal-type'; typeField.setAttribute('data-proposal-type', ''); typeLabel.htmlFor = typeField.id;
                typeField.appendChild(new Option('Choose where these words belong', ''));
                Object.keys(FIELDS).forEach(function (key) { typeField.appendChild(new Option(labelFor(key), key)); });
                typeField.value = type;
                typeField.addEventListener('change', function () {
                    type = typeField.value; draft = proposalDrafts[proposal.proposal_key] || {};
                    draft.type = type; proposalDrafts[proposal.proposal_key] = draft; buildFields();
                });
                correction.append(typeLabel, typeField);
            }
            (FIELDS[type] || []).forEach(function (name) {
                var choices = CHOICES[name];
                if (name === 'date_precision' && type === 'education') choices = choices.concat([['approximate', 'Approximate']]);
                field(name, choices);
            });
            if (type === 'credential') {
                var dateNote = node('p', 'Issue and expiry dates apply only to completed credentials.', 'resume-intake__hint');
                correction.appendChild(dateNote);
                function syncCredentialDates() {
                    var completed = inputs.completion_status.value === 'completed';
                    inputs.issue_date.parentNode.hidden = !completed;
                    inputs.expiration_date.parentNode.hidden = !completed;
                    inputs.issue_date_precision.parentNode.hidden = !completed;
                    inputs.expiration_date_precision.parentNode.hidden = !completed;
                    dateNote.hidden = completed;
                }
                inputs.completion_status.addEventListener('change', syncCredentialDates);
                syncCredentialDates();
            }
            if (type === 'accomplishment' && !proposal.target_key) {
                var label = node('label', 'Which role does this belong to?'); parentField = node('select');
                parentField.id = 'resume-proposal-parent'; label.htmlFor = parentField.id;
                var relationship = parentField;
                function rememberedParent() {
                    if (draft && Object.prototype.hasOwnProperty.call(draft, 'parent_key')) return draft.parent_key;
                    if (proposed.suggested_parent_key || proposal.parent_key) return proposed.suggested_parent_key || proposal.parent_key;
                    // Suggest only a uniquely named eligible role from this
                    // source passage. The member still confirms attribution.
                    var named = ownerCatalog.filter(function (row) {
                        var values = row.has_draft ? row.proposed_values : row.values;
                        var employer = values && values.employer_name;
                        return parentCandidates.some(function (parent) { return parent.record_key === row.record_key; }) &&
                            employer && (proposal.quote || '').toLowerCase().indexOf(employer.toLowerCase()) !== -1;
                    });
                    return named.length === 1 ? named[0].record_key : '';
                }
                fillParentSelect(relationship); relationship.value = rememberedParent();
                relationship.addEventListener('change', function () {
                    draft = proposalDrafts[proposal.proposal_key] || {type: type};
                    draft.parent_key = relationship.value;
                    proposalDrafts[proposal.proposal_key] = draft;
                });
                correction.append(label, parentField);
                loadParentCandidates().then(function () {
                    if (!relationship.isConnected) return;
                    fillParentSelect(relationship); relationship.value = rememberedParent();
                });
            }
        }
        buildFields();
        var groupedDates = type === 'role' || type === 'education';
        (FIELDS[type] || []).forEach(function (name) {
            if (groupedDates && ['start_date', 'end_date', 'date_precision', 'current_role'].indexOf(name) !== -1) return;
            if (proposed[name] === undefined || proposed[name] === null || proposed[name] === '') return;
            var row = node('div'); row.append(node('dt', FIELD_LABELS[name]), node('dd', displayValue(name, proposed[name], proposed))); facts.appendChild(row);
        });
        if (groupedDates && (proposed.start_date || proposed.end_date || typeof proposed.current_role === 'boolean')) {
            function reviewDate(name) {
                if (!proposed[name]) return '';
                if (!proposed.date_precision || proposed.date_precision === 'unknown') return 'Date unknown';
                return (proposed.date_precision === 'approximate' ? 'Around ' : '') + displayValue(name, proposed[name], proposed);
            }
            var start = reviewDate('start_date'), end = proposed.current_role === true ? 'Present' : reviewDate('end_date');
            var dates = start && end ? start + ' – ' + end : start ? 'From ' + start : end ? (end === 'Present' ? 'Current role' : 'Until ' + end) : 'Past role';
            var dateRow = node('div'); dateRow.append(node('dt', 'Dates'), node('dd', dates)); facts.appendChild(dateRow);
        }
        (proposal.explicit_clears || []).forEach(function (name) {
            var row = node('div'); row.append(node('dt', FIELD_LABELS[name]), node('dd', 'Remove the existing value')); facts.appendChild(row);
        });
        group.append(facts, correction); item.appendChild(group);
        item.appendChild(node('p', proposal.target_key ? 'Suggested change to an existing entry' : fixedType ? 'Suggested ' + labelFor(type).toLowerCase() + ' · not saved yet' : 'Your words · choose where they belong', 'resume-intake__proposal-source'));
        if (proposal.quote) item.appendChild(node('p', '“' + proposal.quote + '”', 'resume-intake__proposal-quote'));
        if (proposed.suggested_category === 'project' || (draft && draft.destination === 'project')) {
            var projectHint = node('p', 'For a contribution to a role, choose Impact and confirm its role. For a standalone project, add it privately in My Data. Your original words stay here for review.', 'resume-intake__hint');
            var projectLink = node('a', 'Add a private project in My Data'); projectLink.href = '/app/my-data';
            projectHint.appendChild(projectLink); item.appendChild(projectHint);
        }
        var actions = node('div', undefined, 'resume-intake__proposal-actions');
        var accept = node('button', 'Confirm details', 'resume-intake__add'); accept.type = 'button';
        var edit = node('button', 'Change something', 'resume-intake__secondary'); edit.type = 'button';
        var manualEdit = node('button', 'Edit fields manually', 'resume-intake__quiet'); manualEdit.type = 'button';
        var reject = node('button', 'Leave this out', 'resume-intake__quiet'); reject.type = 'button';
        actions.append(accept, edit); item.append(actions, manualEdit, reject); proposalList.appendChild(item);
        var overview = node('div', undefined, 'resume-intake__quiet-actions');
        if (lastAcknowledgement) overview.appendChild(node('p', lastAcknowledgement, 'resume-intake__hint'));
        overview.setAttribute('aria-label', 'Choose a suggestion');
        proposals.forEach(function (row) {
            var values = row.proposed_values || {};
            var choice = node('button', (newestProposalKeys.indexOf(row.proposal_key) !== -1 ? 'New: ' : '') +
                (values.role_title || values.title || values.name || values.wording || values.suggested_category || 'Your words').slice(0, 80), 'resume-intake__quiet');
            choice.type = 'button'; choice.disabled = Boolean(pendingDecision);
            choice.setAttribute('aria-pressed', String(row.proposal_key === proposal.proposal_key));
            choice.addEventListener('click', function () { selectedProposalKey = row.proposal_key; renderProposals(proposals); });
            overview.appendChild(choice);
        });
        proposalList.before(overview);
        var oldOverview = document.getElementById('resume-intake-suggestion-overview');
        if (oldOverview) oldOverview.remove();
        overview.id = 'resume-intake-suggestion-overview';
        document.getElementById('resume-intake-review-position').textContent = proposals.length === 1 ? 'One group of details to review' : proposals.length + ' groups to review · one at a time';
        function syncCorrection() {
            correction.hidden = !correcting; facts.hidden = correcting;
            edit.hidden = correcting;
            correction.disabled = Boolean(pendingDecision);
            accept.textContent = pendingDecision ? 'Retry confirmation' : 'Confirm details';
            reject.disabled = Boolean(pendingDecision);
            showScreen(correcting ? 'correction' : 'review', false);
        }
        manualEdit.addEventListener('click', function () { correcting = true; syncCorrection(); correction.querySelector('input,textarea,select').focus(); });
        edit.addEventListener('click', function () {
            if (pendingDecision || (pendingCorrection && pendingCorrection.proposal_key !== proposal.proposal_key)) {
                setStatus('Recover the earlier correction before starting another. Your words are kept; manual fields remain available.', 'error'); return;
            }
            if ((textarea.value || '').trim()) {
                setStatus('Your unfinished answer is kept. Finish it first, or edit these fields manually.', 'ok'); return;
            }
            correctionTarget = proposal; correctionDraft = textarea.value; textarea.value = correctionInputs[proposal.proposal_key] || '';
            showScreen('input');
            questionPrompt.textContent = 'What should I change about this suggestion?';
            questionContext.textContent = 'Say or type a correction. We will show the changes before you confirm. You can also edit the fields manually.';
            questionContext.hidden = false; textarea.focus(); refreshDraftLabel();
        });
        function confirmedValues() {
            if (!FIELDS[type]) throw new Error('Choose where these words belong before confirming.');
            var values = {};
            FIELDS[type].forEach(function (name) {
                var input = inputs[name], raw = input.value.trim();
                var changed = dirty[name] || raw !== initial[name];
                if (input.tagName === 'SELECT' && input.selectedOptions[0] && input.selectedOptions[0].disabled) throw new Error('Choose a supported ' + FIELD_LABELS[name].toLowerCase() + '.');
                if (raw === '') {
                    if (changed) values[name] = null;
                    else if (Object.prototype.hasOwnProperty.call(proposed, name)) values[name] = proposed[name];
                } else if (name === 'current_role') values[name] = raw === 'true';
                else values[name] = raw;
            });
            if (!proposal.target_key) (REQUIRED_FIELDS[type] || []).forEach(function (name) {
                if (!values[name]) throw new Error('Add the ' + FIELD_LABELS[name].toLowerCase() + ' before confirming.');
            });
            ['start_date', 'end_date'].forEach(function (name) {
                if (!values[name]) return;
                var precision = values.date_precision;
                var length = {year: 4, month: 7, day: 10, unknown: 10}[precision];
                if (type === 'education' && precision === 'approximate') length = 10;
                // Changing precision cannot silently invent information.
                var raw = String(values[name]);
                if (!length || raw.length !== length || !({4: /^\d{4}$/, 7: /^\d{4}-\d{2}$/, 10: /^\d{4}-\d{2}-\d{2}$/}[length]).test(raw)) throw new Error('Use the date detail you know: YYYY, YYYY-MM or YYYY-MM-DD.');
                values[name] = raw + (length === 4 ? '-01-01' : length === 7 ? '-01' : '');
            });
            if (type === 'role' && values.current_role === true && values.end_date) throw new Error('A current role has no end date. Clear it or choose Past role.');
            if (type === 'credential') {
                encodeCredentialDates(values);
                if (values.completion_status === 'completed' && !values.issue_date) throw new Error('Add the issue date for a completed credential.');
                if (values.completion_status && values.completion_status !== 'completed') {
                    values.issue_date = null; values.expiration_date = null;
                    delete values.issue_date_precision; delete values.expiration_date_precision;
                }
            }
            if (!fixedType) values.record_type = type;
            if (parentField && type === 'accomplishment') {
                if (!parentField.value) throw new Error('Choose which private role this contribution belongs to.');
                values.parent_key = parentField.value;
            }
            return values;
        }
        function decide(decision) {
            if (decisionBusy) return;
            if (!pendingDecision) {
                try {
                    var body = {request_id: requestId(), proposal_key: proposal.proposal_key, decision: decision};
                    if (decision === 'accept') body.confirmed_values = confirmedValues();
                    pendingDecision = {body: body, proposal: proposal};
                } catch (error) { correcting = true; syncCorrection(); setStatus(error.message, 'error'); return; }
            }
            var attempt = pendingDecision;
            decisionBusy = true; accept.disabled = true; edit.disabled = true; correction.disabled = true; reject.disabled = true;
            postJson(urls.decision, attempt.body).then(function (result) {
                var payload = result.payload;
                if (!result.response.ok) {
                    if ([400, 404, 409].indexOf(result.response.status) !== -1) pendingDecision = null;
                    throw new Error(payload.message || 'Confirmation is not acknowledged. Retry the same decision.');
                }
                if (payload.success !== true || payload.request_id !== attempt.body.request_id || payload.proposal_key !== attempt.body.proposal_key ||
                    payload.outcome !== (attempt.body.decision === 'accept' ? 'saved' : 'unresolved') || payload.publishes !== false) {
                    throw new Error('Confirmation is not acknowledged. Retry the same decision.');
                }
                pendingDecision = null;
                if (pendingCorrection && pendingCorrection.proposal_key === proposal.proposal_key) {
                    var retainedCorrection = correctionInputs[proposal.proposal_key] || '';
                    if (retainedCorrection && retainedCorrection !== pendingCorrection.statement &&
                        textarea.value.indexOf(retainedCorrection) === -1)
                        textarea.value += (textarea.value ? '\n\n' : '') + retainedCorrection;
                    pendingCorrection = null;
                }
                delete proposalDrafts[proposal.proposal_key];
                delete correctionInputs[proposal.proposal_key];
                if (payload.outcome === 'saved') lastConfirmedKey = (payload.item || {}).record_key || proposal.target_key || null;
                if (payload.outcome === 'saved') factSaved();
                proposals = proposals.filter(function (p) { return p.proposal_key !== proposal.proposal_key; });
                if (proposals.length) { renderProposals(proposals); showScreen(screen); }
                else { proposalList.replaceChildren(); showScreen(payload.outcome === 'saved' ? 'next' : 'input'); }
                refreshDraftLabel();
                if (!proposals.length) { var overview = document.getElementById('resume-intake-suggestion-overview'); if (overview) overview.remove(); }
                setStatus(payload.outcome === 'saved' ? 'Saved privately. Sharing settings are unchanged.' : 'Left out. Nothing was saved.', 'ok');
            }).catch(function (error) {
                setStatus(error.message || 'The response was lost. Retry the same confirmation; it will not create a duplicate.', 'error');
            }).finally(function () {
                decisionBusy = false;
                if (item.isConnected) { accept.disabled = false; edit.disabled = Boolean(pendingDecision); correction.disabled = Boolean(pendingDecision); reject.disabled = Boolean(pendingDecision); accept.textContent = pendingDecision ? 'Retry confirmation' : 'Confirm details'; }
            });
        }
        accept.addEventListener('click', function () { decide('accept'); });
        reject.addEventListener('click', function () { decide('reject'); });
        syncCorrection();
    }

    function applyQuestion(payload) {
        if (payload && payload.question && payload.question.prompt) {
            questionPrompt.textContent = payload.question.prompt;
            questionContext.textContent = payload.question.context || '';
            questionContext.hidden = !questionContext.textContent;
        }
    }
    function applyGuideState(workspace, guide) {
        if (initialized) return;
        initialized = true;
        var status = (workspace.guide && workspace.guide.status) || 'not_started';
        applyQuestion(guide);
        if (!guide || guide.load_state !== 'loaded') {
            if (!proposals.length) showScreen('input', false);
            return;
        }
        if (['paused', 'completed', 'skipped'].indexOf(status) !== -1 || guideDismissed) return;
        if (!proposals.length) showScreen(status === 'not_started' && !workspace.receipts_count ? 'welcome' : 'input', false);
        reopenGuide();
    }

    function refreshOriginals() {
        var list = document.getElementById('resume-intake-originals');
        if (!list || !urls.originals) return Promise.resolve();
        return send(urls.originals).then(function (result) {
            list.replaceChildren();
            if (!result.response.ok || !result.payload.success) {
                var error = document.createElement('li');
                error.textContent = 'Original files are unavailable right now.';
                list.appendChild(error); return;
            }
            var rows = (result.payload.originals || []).filter(function (row) { return row.state !== 'deleted'; });
            if (!rows.length) {
                var empty = document.createElement('li'); empty.textContent = 'No original files retained.';
                list.appendChild(empty); return;
            }
            rows.forEach(function (row, index) {
                var item = document.createElement('li');
                var title = document.createElement('span');
                var type = row.content_type === 'application/pdf' ? 'PDF' : (row.content_type === 'text/plain' ? 'text' : 'Word');
                title.textContent = type + ' original ' + (index + 1) + ' '; item.appendChild(title);
                if (row.downloadable) {
                    var link = document.createElement('a');
                    link.href = urls.originals + '/' + encodeURIComponent(row.original_key);
                    link.textContent = 'Download'; item.appendChild(link);
                }
                var button = document.createElement('button');
                button.type = 'button'; button.className = 'resume-intake__quiet';
                button.textContent = row.state === 'delete_pending' ? 'Retry deletion' : 'Delete original';
                button.setAttribute('aria-label', button.textContent + ' ' + type + ' ' + (index + 1));
                var deletionRequest = requestId();
                button.addEventListener('click', function () {
                    button.disabled = true;
                    send(urls.originals + '/' + encodeURIComponent(row.original_key), {
                        method: 'DELETE', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({request_id: deletionRequest, expected_version: row.version})
                    }).then(function (reply) {
                        if (!reply.response.ok || !reply.payload.success) {
                            setStatus(reply.payload.message || 'The original could not be deleted. Try again.', 'error');
                            button.disabled = false; return;
                        }
                        setStatus(reply.payload.outcome === 'delete_pending'
                            ? 'The original is unavailable while deletion finishes. You can retry.'
                            : 'Original deleted. Its extracted text is kept.', 'ok');
                        refreshOriginals();
                    }).catch(function () {
                        button.disabled = false;
                        setStatus('Deletion did not finish. Try again to check it.', 'error');
                    });
                });
                item.appendChild(button); list.appendChild(item);
            });
        }).catch(function () {
            list.replaceChildren(); var error = document.createElement('li');
            error.textContent = 'Original files are unavailable right now.'; list.appendChild(error);
        });
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
                    if (!initialized) showScreen('input', false);
                    setStatus(result.payload.message ||
                        'Saving is not enabled yet. Your typing stays here, unsent.', 'error');
                    return null;
                }
                if (!result.response.ok) {
                    if (!initialized) showScreen('input', false);
                    setStatus(result.payload.message || 'The composer could not be loaded.', 'error');
                    return null;
                }
                var policyText = document.getElementById('resume-intake-policy');
                var policy = result.payload.policy || {};
                if (policyText) policyText.textContent = policy.selected
                    ? 'Selectable-text PDF, Word or text files up to ' + (policy.max_document_bytes / 1000000) + ' MB each. English recordings up to ' + (policy.max_recording_seconds / 60) + ' minutes; you can add more than one. ' + policy.retention_statement
                    : 'Synthetic fixture policy only. Real onboarding retention is unavailable.';
                refreshOriginals();
                renderProposals(result.payload.pending_proposals || [], initialized);
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

    function buildRequestParts(mode) {
        return {
            type: 'add_submission',
            text: mode === 'manual' ? null : (textarea.value || '').trim() || null,
            items: (mode === 'manual' ? queuedFacts : []).map(function (row) {
                return {client_key: row.client_key, record_type: row.record_type,
                    values: row.values, explicit_clears: row.explicit_clears, parent_key: row.parent_key || null};
            }),
            attachments: (mode === 'manual' ? [] : attachments).filter(function (row) {
                return row.status !== 'cancelled';
            }).map(function (row) {
                return row.kind === 'recording'
                    ? {client_key: row.client_key, kind: 'recording', source_key: row.source_key}
                    : {client_key: row.client_key, kind: 'document', declared_content_type: row.declared_content_type, filename: row.filename};
            })
        };
    }
    function submitCorrection() {
        if (interviewBusy || pendingAdd || decisionBusy) return;
        if (microphonePending || (recorder && recorder.state === 'recording') || heldRecording ||
            attachments.some(function (row) { return row.kind === 'recording' && row.status !== 'cancelled' && !row.source_key; })) {
            setStatus('Stop recording and review the transcript before continuing. Your words and audio are kept.', 'error'); return;
        }
        if (!(textarea.value || '').trim()) { setStatus('Say or type what should change.', 'ok'); return; }
        if (root.getAttribute('data-interview-enabled') !== 'true') {
            setStatus('Conversational correction is unavailable. Your words are kept; use Edit fields manually.', 'error'); return;
        }
        var target = correctionTarget;
        var statement = textarea.value;
        interviewBusy = true; addButton.disabled = true;
        var prepare = pendingCorrection ? Promise.resolve(pendingCorrection) : send(editorLists.getAttribute('data-workspace-url')).then(function (result) {
            if (!result.response.ok || !Number.isInteger(result.payload.draft_version)) throw new Error('Your private context is unavailable. Your correction is kept.');
            pendingCorrection = {request_id: requestId(), expected_draft_version: result.payload.draft_version,
                proposal_key: target.proposal_key, statement: statement};
            return pendingCorrection;
        });
        prepare.then(function (attempt) { return postJson(urls.interview, attempt); }).then(function (result) {
            if (!result.response.ok) {
                if ([400, 404, 409].indexOf(result.response.status) !== -1) pendingCorrection = null;
                throw new Error(result.payload.message || 'Your correction could not be organized. Your words are kept.');
            }
            var data = result.payload, attempt = pendingCorrection;
            if (data.success !== true || data.saved !== false || data.publishes !== false ||
                data.base_revision !== attempt.expected_draft_version || !Array.isArray(data.candidates)) throw new Error('No valid correction arrived. Your words are kept.');
            var candidates = data.candidates.filter(function (candidate) { return FIELDS[candidate.record_type] &&
                (target.record_type === 'unspecified' || candidate.record_type === target.record_type); });
            pendingCorrection = null;
            if (candidates.length !== 1) {
                questionPrompt.textContent = data.next_question || 'Which detail should I change?';
                setStatus(data.response || 'I need one clearer detail before proposing a change.', 'ok'); return;
            }
            var candidate = candidates[0], draft = proposalDrafts[target.proposal_key] || {type: candidate.record_type};
            draft.type = candidate.record_type;
            draft[candidate.record_type] = Object.assign({}, draft[candidate.record_type] || {});
            Object.keys(candidate.values).forEach(function (name) {
                if (FIELDS[candidate.record_type].indexOf(name) !== -1 && candidate.values[name] !== null)
                    draft[candidate.record_type][name] = CHOICES[name] ? String(candidate.values[name]) : displayValue(name, candidate.values[name], Object.assign({}, target.proposed_values, candidate.values));
            });
            proposalDrafts[target.proposal_key] = draft;
            selectedProposalKey = target.proposal_key;
            correctionTarget = null;
            if (textarea.value === attempt.statement) textarea.value = correctionDraft || '';
            else correctionInputs[target.proposal_key] = textarea.value;
            if (textarea.value === (correctionDraft || '')) delete correctionInputs[target.proposal_key];
            correctionDraft = null;
            renderProposals(proposals);
            setStatus((data.response || 'I updated the suggestion.') + ' Review the fields and confirm when they are right. Nothing is saved yet.', 'ok');
        }).catch(function (error) { setStatus(error.message, 'error'); })
        .finally(function () { interviewBusy = false; addButton.disabled = false; refreshDraftLabel(); });
    }
    function submit(event, mode) {
        if (event) event.preventDefault();
        if (mode === 'guide' && correctionTarget) { submitCorrection(); return; }
        mode = mode || 'guide';
        if (addOperation) return;
        if (pendingAdd && pendingAdd.mode !== mode) {
            setStatus('An earlier submission needs its response recovered first. Return to that submission and retry it; your newer input is kept.', 'error'); return;
        }
        if (!pendingAdd) {
            if (mode === 'guide' && (microphonePending || (recorder && recorder.state === 'recording'))) {
                setStatus('Stop recording and review the transcript before continuing.', 'error'); return;
            }
            if (mode === 'guide' && (heldRecording || attachments.some(function (row) { return row.kind === 'recording' && row.status !== 'cancelled' && !row.source_key; }))) {
                setStatus('Finish transcribing or cancel the recording before continuing. Your words and audio are kept.', 'error'); return;
            }
            var request = buildRequestParts(mode);
            if (!request.text && !request.items.length && !request.attachments.length) {
                setStatus('Add something before saving.', 'error'); return;
            }
            request.request_id = requestId();
            var form = new FormData(); form.append('request', JSON.stringify(request));
            if (mode === 'guide') attachments.forEach(function (row) {
                if (row.kind === 'document' && row.file) form.append('file:' + row.client_key, row.file, row.filename || 'attachment');
            });
            pendingAdd = {request: request, form: form, submittedText: mode === 'manual' ? null : textarea.value, mode: mode};
        }
        var attempt = pendingAdd;
        addButton.disabled = true; manualSave.disabled = true;
        renderAttachments();
        var operation = beginActivity('add'); addOperation = operation;
        setStatus('Preparing your information…', 'ok');
        send(urls.submit, {method: 'POST', body: attempt.form}).then(function (result) {
            if ([400, 409].indexOf(result.response.status) !== -1) pendingAdd = null;
            if (!result.response.ok) throw new Error(result.payload.message || 'That submission did not finish. Retry to recover the same request.');
            var receipt = result.payload;
            if (receipt.success !== true || receipt.request_id !== attempt.request.request_id || !Array.isArray(receipt.results)) {
                throw new Error('No valid receipt arrived. Retry to recover the same request.');
            }
            pendingAdd = null;
            newestProposalKeys = (receipt.proposals || []).map(function (row) { return row.proposal_key; });
            if (!newestProposalKeys.length) receipt.results.forEach(function (row) {
                newestProposalKeys = newestProposalKeys.concat(row.proposal_keys || []);
            });
            selectedProposalKey = newestProposalKeys[0] || selectedProposalKey;
            var groups = {};
            (receipt.proposals || []).forEach(function (row) {
                if (row.record_type === 'unspecified' && conversationIntent === 'story' &&
                    !(row.proposed_values || {}).suggested_category)
                    proposalDrafts[row.proposal_key] = proposalDrafts[row.proposal_key] || {type: 'knowledge'};
                if (row.record_type === 'unspecified' && conversationIntent === 'project')
                    proposalDrafts[row.proposal_key] = proposalDrafts[row.proposal_key] || {destination: 'project'};
                var label = (row.proposed_values || {}).suggested_category || labelFor(row.record_type);
                groups[label] = (groups[label] || 0) + 1;
            });
            lastAcknowledgement = 'I received your answer. ' + (Object.keys(groups).length
                ? 'I organized ' + Object.keys(groups).map(function (label) { return groups[label] + ' ' + label.toLowerCase(); }).join(', ') + '.'
                : newestProposalKeys.length + ' suggestions are ready.') + ' Review before saving.';
            renderReceipt(receipt);
            var failure = receipt.results.filter(function (row) { return row.outcome === 'failed' || row.outcome === 'pending'; });
            var acknowledged = receipt.results.filter(function (row) {
                return row.outcome === 'saved' || row.outcome === 'unresolved' || row.outcome === 'duplicate';
            }).map(function (row) { return row.client_key; });
            queuedFacts = queuedFacts.filter(function (row) { return acknowledged.indexOf(row.client_key) === -1; });
            attachments = attachments.filter(function (row) { return acknowledged.indexOf(row.client_key) === -1; });
            attachments.forEach(function (row) {
                var match = receipt.results.find(function (entry) { return entry.client_key === row.client_key; });
                if (match) { row.status = match.outcome; row.message = match.message; }
            });
            var textAcknowledged = receipt.results.some(function (row) { return row.kind === 'text' && acknowledged.indexOf(row.client_key) !== -1; });
            if (textAcknowledged && textarea.value === attempt.submittedText) textarea.value = '';
            var savedCount = receipt.results.filter(function (row) { return row.outcome === 'saved'; }).length;
            if (savedCount) factSaved(savedCount);
            renderQueued(); renderAttachments(); refreshDraftLabel();
            setStatus(failure.length ? (receipt.message || 'Some input still needs attention.') : (attempt.mode === 'guide' ? 'I received your answer. ' + newestProposalKeys.length + ' new suggestions are ready for your review; nothing is saved yet.' : (receipt.message || 'Saved privately.')), failure.length ? 'error' : 'ok');
            return loadParentCandidates().then(load).then(function () {
                if (attempt.mode === 'guide' && !guideHidden) {
                    if (failure.length || (textarea.value || '').trim()) showScreen('input');
                    else if (proposals.length) { renderProposals(proposals); showScreen(screen); }
                    else showScreen(savedCount ? 'next' : 'input');
                    receiptBox.hidden = !failure.length;
                }
            });
        }).catch(function (error) {
            setStatus(error.name !== 'TypeError' && error.message ? error.message : 'The connection dropped before a receipt arrived. Your input is kept. Retry the same submission to find out whether it was received.', 'error');
        }).finally(function () {
            endActivity(operation); addOperation = null; addButton.disabled = false; manualSave.disabled = false;
            document.getElementById('resume-intake-add-label').textContent = pendingAdd ? 'Retry submission' : 'Continue';
            manualSave.textContent = pendingAdd && pendingAdd.mode === 'manual' ? 'Retry saving queued details' : 'Save queued details privately';
            renderAttachments(); renderQueued();
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
            if (result.payload.request_id !== recordingRequest.request_id ||
                typeof result.payload.source_key !== 'string' || typeof result.payload.transcript !== 'string') {
                throw new Error('The recording receipt was incomplete. Retry the same recording.');
            }
            appendTranscript(result.payload.transcript);
            existingRow.status = 'selected';
            existingRow.retryable = false;
            existingRow.source_key = result.payload.source_key;
            renderAttachments();
            refreshDraftLabel();
            setStatus('Transcript added. Review your words, then continue. No résumé details have been confirmed yet.', 'ok');
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
            recorder.stream.getTracks().forEach(function (track) { track.stop(); });
        }
    }

    function startRecording() {
        if (microphonePending || (recorder && recorder.state === 'recording')) return;
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            setStatus('Recording is not supported in this browser. You can keep typing.', 'error');
            return;
        }
        var generation = recordingGeneration;
        microphonePending = true;
        cancelRecordingButton.hidden = false;
        cancelRecordingButton.textContent = 'Cancel recording';
        navigator.mediaDevices.getUserMedia({audio: true}).then(function (stream) {
            if (generation !== recordingGeneration) { stream.getTracks().forEach(function (track) { track.stop(); }); return; }
            microphonePending = false;
            var recordedChunks = [];
            try { recorder = new MediaRecorder(stream); }
            catch (error) { stream.getTracks().forEach(function (track) { track.stop(); }); throw error; }
            var activeRecorder = recorder;
            var recordingStartedAt = Date.now();
            activeRecorder.addEventListener('dataavailable', function (event) {
                if (event.data && event.data.size) {
                    recordedChunks.push(event.data);
                }
            });
            activeRecorder.addEventListener('stop', function () {
                stream.getTracks().forEach(function (track) { track.stop(); });
                if (recorder === activeRecorder) micButton.setAttribute('aria-pressed', 'false');
                syncRecordingCancel();
                if (generation !== recordingGeneration) return;
                var blob = new Blob(recordedChunks, {type: activeRecorder.mimeType || 'audio/webm'});
                if (!blob.size) {
                    cancelRecordingButton.hidden = true;
                    setStatus('No audio was captured. You can keep typing.', 'error');
                    return;
                }
                var clientKey = requestId();
                var duration = Math.max(1, Math.round((Date.now() - recordingStartedAt) / 1000));
                if (guideHidden || activeRecorder.keepLocal) {
                    heldRecording = {client_key: clientKey, kind: 'recording', label: 'Recording',
                        status: 'held', blob: blob, retryable: true,
                        message: 'Kept on this page. Choose Transcribe recording to continue.',
                        recording_request: {request_id: requestId(), client_key: clientKey, signature: null, duration_seconds: duration}};
                    attachments.push(heldRecording); renderAttachments(); refreshDraftLabel();
                } else uploadRecording(blob, clientKey, null, duration);
            });
            activeRecorder.start();
            micButton.setAttribute('aria-pressed', 'true');
            syncRecordingCancel();
            setStatus('Recording. Press the microphone again to stop.', 'ok');
        }).catch(function () {
            if (generation !== recordingGeneration) return;
            microphonePending = false;
            cancelRecordingButton.hidden = true;
            setStatus('Microphone permission was not granted. You can keep typing.', 'error');
        });
    }

    /* -- guide --------------------------------------------------------- */

    function hideGuide() {
        guideHidden = true; guideDismissed = true;
        // Leaving stops capture immediately. onstop keeps the local blob; it
        // never starts cloud transcription after the member has left.
        if (microphonePending) { recordingGeneration += 1; microphonePending = false; }
        if (recorder) recorder.keepLocal = true;
        stopRecording();
        root.close(); root.hidden = true; reopenButton.hidden = false;
        document.body.classList.remove('resume-onboarding-open');
        if (editorSection) editorSection.classList.remove('resume-editor--onboarding');
        renderActivity(); syncRecordingCancel();
        reopenButton.focus({preventScroll: true});
    }
    function reopenGuide() {
        guideHidden = false; root.hidden = false; reopenButton.hidden = true;
        if (editorSection) editorSection.classList.add('resume-editor--onboarding');
        document.body.classList.add('resume-onboarding-open');
        if (!root.open) root.showModal();
        renderActivity();
        if (heldRecording) setStatus('Your recording is kept here. Choose Transcribe recording when you’re ready.', 'ok');
        showScreen(screen);
    }
    function setGuideStatus(status) {
        if (guideBusy) return;
        // A new choice cannot replace an unacknowledged member choice.
        if (pendingGuide && pendingGuide.status !== status) {
            setStatus('The previous guide update still needs a response. Retry it before making a different choice.', 'error'); return;
        }
        if (!pendingGuide) pendingGuide = {request_id: requestId(), status: status};
        var attempt = pendingGuide; guideBusy = true; completeButton.disabled = true;
        return postJson(urls.guideStatus, attempt).then(function (result) {
            if (!result.response.ok || result.payload.success !== true || result.payload.request_id !== attempt.request_id || result.payload.status !== attempt.status) {
                if ([400, 409].indexOf(result.response.status) !== -1) pendingGuide = null;
                throw new Error(result.payload.message || 'The guide update did not finish. Try again.');
            }
            pendingGuide = null;
            if (attempt.status === 'completed') { showScreen('finish'); setStatus('', 'ok'); }
            else setStatus('You can continue the guide whenever you’re ready.', 'ok');
        }).catch(function (error) { setStatus(error.message || 'The guide update did not finish. Try again.', 'error'); })
          .finally(function () {
              guideBusy = false; completeButton.disabled = false;
              document.getElementById('resume-intake-retry-guide').hidden = !pendingGuide;
          });
    }
    function nextQuestion() {
        if (interviewBusy) return;
        if (correctionTarget) { setStatus('Review this correction or return to the suggestion before asking another question. Your words are kept.', 'ok'); return; }
        showScreen('input');
        if (root.getAttribute('data-interview-enabled') !== 'true') {
            questionPrompt.textContent = 'What contribution are you proud of, and what changed because of it?';
            questionContext.textContent = 'AI guidance is unavailable here. You can still add your own words or finish for now.';
            questionContext.hidden = false; textarea.focus(); return;
        }
        interviewBusy = true;
        document.getElementById('resume-intake-next-question').disabled = true;
        document.getElementById('resume-intake-new-question').disabled = true;
        setStatus('Preparing a question from your confirmed experience…', 'ok');
        var prepare = pendingInterview ? Promise.resolve(pendingInterview) : send(editorLists.getAttribute('data-workspace-url')).then(function (result) {
            if (!result.response.ok || !Number.isInteger(result.payload.draft_version)) throw new Error('Your saved context is unavailable. You can keep typing.');
            // This is a guidance request, not an invented member statement.
            // Full source words are submitted separately through explicit Continue.
            pendingInterview = {request_id: requestId(), expected_draft_version: result.payload.draft_version,
                statement: 'Help me continue my résumé interview using my saved experience. ' +
                    (lastConfirmedKey ? 'Focus on the most recently confirmed entry ' + lastConfirmedKey + '. ' : '') +
                    'Ask one short question about a genuine gap or a useful new example. Do not ask again for known employers, dates or relationships. I can ask another question or finish this section.'};
            return pendingInterview;
        });
        prepare.then(function (attempt) { return postJson(urls.interview, attempt); }).then(function (result) {
            if (!result.response.ok) {
                if ([400, 409].indexOf(result.response.status) !== -1) pendingInterview = null;
                throw new Error(result.payload.message || 'AI guidance is unavailable. Your input is kept.');
            }
            var data = result.payload;
            if (data.success !== true || data.saved !== false || data.publishes !== false || data.base_revision !== pendingInterview.expected_draft_version || typeof data.next_question !== 'string') throw new Error('The guidance response was incomplete. Your input is kept.');
            pendingInterview = null;
            if (data.next_question && seenQuestions.indexOf(data.next_question) === -1) {
                questionPrompt.textContent = data.next_question;
                questionContext.textContent = typeof data.response === 'string' ? data.response : '';
                questionContext.hidden = !questionContext.textContent;
                seenQuestions.push(data.next_question);
                setStatus('Use what helps. You can skip this question or finish for now.', 'ok');
            } else {
                showScreen('optional');
                setStatus('We’ve already covered that question. You can add an example or finish for now.', 'ok');
            }
        }).catch(function (error) {
            questionPrompt.textContent = 'What would you like to add about your work?';
            questionContext.hidden = true;
            setStatus(error.message || 'AI guidance is unavailable. You can keep typing or finish for now.', 'error');
        }).finally(function () {
            interviewBusy = false; document.getElementById('resume-intake-next-question').disabled = false;
            document.getElementById('resume-intake-new-question').disabled = false;
            document.getElementById('resume-intake-new-question').textContent = pendingInterview ? 'Try guidance again' : 'Ask another question';
        });
    }
    function on(id, action) {
        var button = document.getElementById('resume-intake-' + id);
        if (button) button.addEventListener('click', action);
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
            ['issue_date', 'expiration_date', 'issue_date_precision', 'expiration_date_precision'].forEach(function (name) { delete values[name]; });
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
        setStatus('Queued. Choose Save queued details privately when you’re ready.', 'ok');
    });
    typeSelect.addEventListener('change', syncDirectFields);
    var credentialStatusInput = document.getElementById('resume-intake-credential-status');
    if (credentialStatusInput) {
        credentialStatusInput.addEventListener('change', syncDirectFields);
    }
    composer.addEventListener('submit', function (event) { submit(event, 'guide'); });
    manualSave.addEventListener('click', function () { submit(null, 'manual'); });
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
        microphonePending = false;
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
        root.setAttribute('data-recording', 'false');
        document.getElementById('resume-intake-recording').hidden = true;
        setStatus('Recording cancelled. Your typed words are kept. Any audio already uploaded stays private; its transcript will not be inserted.', 'ok');
    });
    micButton.addEventListener('click', function () {
        if (recorder && recorder.state === 'recording') {
            stopRecording();
        } else {
            startRecording();
        }
    });
    hideButton.addEventListener('click', function () { hideGuide(); setGuideStatus('paused'); });
    reopenButton.addEventListener('click', reopenGuide);
    root.addEventListener('cancel', function (event) { event.preventDefault(); hideGuide(); setGuideStatus('paused'); });
    skipButton.addEventListener('click', function () { hideGuide(); setGuideStatus('skipped'); });
    completeButton.addEventListener('click', function () { setGuideStatus('completed'); });
    on('start-type', function () { showScreen('input'); textarea.focus(); });
    on('start-upload', function () { showScreen('input'); fileInput.click(); });
    on('start-voice', function () { showScreen('input'); startRecording(); });
    function leaveCorrection() {
        if (!correctionTarget || interviewBusy) return false;
        correctionInputs[correctionTarget.proposal_key] = textarea.value;
        textarea.value = correctionDraft || ''; correctionDraft = null; correctionTarget = null;
        refreshDraftLabel(); return true;
    }
    on('back', function () { if (leaveCorrection()) renderProposals(proposals); else showScreen(screen === 'input' ? 'welcome' : screen === 'sharing' ? 'optional' : 'input'); });
    on('next-question', nextQuestion);
    on('new-question', nextQuestion);
    on('retry-guide', function () { if (pendingGuide) setGuideStatus(pendingGuide.status); });
    on('review-pending', function () { if (interviewBusy) return; leaveCorrection(); renderProposals(proposals); });
    on('skip-question', function () { seenQuestions.push(questionPrompt.textContent); nextQuestion(); });
    on('input-finish', function () { if (interviewBusy) return; leaveCorrection(); showScreen('optional'); });
    on('next-finish', function () { showScreen('optional'); });
    on('optional-next', function () { showScreen('sharing'); });
    on('view', function () { hideGuide(); var preview = document.getElementById('resume-editor-review'); if (preview) preview.click(); });
    on('keep-adding', function () { showScreen('input'); textarea.focus(); });
    on('add-example', function () { conversationIntent = 'project'; correctionTarget = null; showScreen('input'); questionPrompt.textContent = 'Tell us about a project: what did you do, and what changed?'; questionContext.hidden = true; textarea.focus(); });
    on('add-story', function () { conversationIntent = 'story'; correctionTarget = null; showScreen('input'); questionPrompt.textContent = 'What outside work helps people understand you?'; questionContext.textContent = 'A hobby, a turning point, or something you care about. This is optional and stays private.'; questionContext.hidden = false; textarea.focus(); });
    on('add-photo', function () {
        hideGuide();
        var target = document.getElementById('resume-media');
        var launcher = document.getElementById('resume-media-reopen');
        if (target) {
            if (target.hidden && launcher) launcher.click();
            target.scrollIntoView({block: 'center'});
            var tab = document.getElementById('resume-media-tab-photos');
            if (tab) tab.focus();
        }
    });
    root.hidden = true;
    window.addEventListener('pagehide', function () { recordingGeneration += 1; stopRecording(); });
    protectNavigation();
    syncDirectFields();
    renderQueued();
    renderAttachments();
    loadParentCandidates().then(function () { fillParentSelect(parentSelect); });
    load().catch(function () { if (!initialized) showScreen('input', false); setStatus('The guide could not be loaded. You can edit manually or reopen it to try again.', 'error'); });
})();
