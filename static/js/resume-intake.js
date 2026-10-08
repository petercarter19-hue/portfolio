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
        historyReview: root.getAttribute('data-history-review-url'),
        excludedReview: root.getAttribute('data-excluded-review-url'),
        purge: root.getAttribute('data-intake-purge-url'),
        organize: root.getAttribute('data-intake-organize-url'),
        originals: root.getAttribute('data-intake-originals-url'),
        guide: root.getAttribute('data-guide-url'),
        guideStatus: root.getAttribute('data-guide-status-url'),
        interview: root.getAttribute('data-interview-url'),
        draft: root.getAttribute('data-draft-url'),
        review: root.getAttribute('data-review-url'), preview: root.getAttribute('data-preview-url')
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
    var proposalInvitations = {};
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
                     'issue_date_precision', 'expiration_date_precision', 'verification_url', 'completion_status', 'resume_credential_wording'],
        skill: ['name', 'summary'],
        accomplishment: ['wording', 'metric_value', 'metric_label'],
        knowledge: ['title', 'wording', 'classification']
    };
    var FIELD_INPUTS = {
        role: {role_title: 'resume-intake-role-title', employer_name: 'resume-intake-employer',
               location_text: 'resume-intake-role-location', summary: 'resume-intake-role-summary',
               current_role: 'resume-intake-current-role', date_precision: 'resume-intake-role-date-precision',
               start_date: 'resume-intake-role-start', end_date: 'resume-intake-role-end'},
        skill: {name: 'resume-intake-skill', summary: 'resume-intake-skill-summary'},
        education: {title: 'resume-intake-education-title', institution_name: 'resume-intake-institution',
                    degree_name: 'resume-intake-degree', field_of_study: 'resume-intake-study',
                    grade_text: 'resume-intake-grade', location_text: 'resume-intake-education-location',
                    summary: 'resume-intake-education-summary',
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
        skill: 'skill',
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
    var correctionTarget = null, quickInputs = {};
    var correctionInputs = {};
    var correctionDraft = null;
    var pendingCorrection = null;
    var conversationIntent = null;
    var navigationHistory = [];
    var lastAcknowledgement = '';
    var lastConfirmedKey = null;
    var proposalDrafts = {};
    var reviewOverview = null, reviewScope = 'batch', allPendingRows = [], unplacedChoice = null;
    var pendingOrganize = null, organizeBusy = false, pausing = false, pauseNoticeTimer = null;
    var SAVE_TIMEOUT = 15000;
    var screen = 'welcome';
    var initialized = false;
    var acknowledgedFacts = 0;
    var catalogLoaded = false;
    var seenQuestions = [];
    var welcomeTitle = document.getElementById('resume-intake-title').textContent;
    var parentCandidates = [];     // owner-scoped parents for an Impact entry
    var parentCatalogGeneration = 0;
    var parentCatalogAvailable = false;
    var parentUnavailableMessage = 'Roles are unavailable right now. Your unfinished Impact and selected role are kept here. Choose Impact again to retry before queueing it.';
    var guideHidden = false;
    var guideDismissed = false;
    var unsavedBeforeUnload = null;
    var conversationSupported = false;
    var conversationNavigationEpoch = 0;
    var pendingConversation = null;
    // Only this page can know a prepared turn never reached dispatch. Restored
    // descriptors have an unknown outcome and retain their immutable replay.
    var undispatchedConversationKey = null;
    var conversationGeneration = 0;
    var draftVersion = null, draftReady = false, draftBusy = null, draftTimer = null;
    var savedDraftSignature = null, pendingDraftSave = null;
    var draftRecovery = null, draftRecoveryBusy = false, draftRecoveryGeneration = 0, heldDraftCopy = null;
    var draftRecoveryBox = document.getElementById('resume-intake-draft-recovery');
    var draftRecoveryKeep = document.getElementById('resume-intake-draft-recovery-keep');
    var draftRecoveryUse = document.getElementById('resume-intake-draft-recovery-use');
    var previewGeneration = 0;
    var restoringDraft = false;

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
        var generation = ++parentCatalogGeneration;
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
                // A later refresh owns this catalog even when its response is
                // still pending. Older responses cannot remove a newer choice.
                if (generation !== parentCatalogGeneration) return parentCandidates;
                parentCatalogAvailable = true;
                ownerCatalog = payload.items.slice();
                acknowledgedFacts = payload.items.length;
                if (!catalogLoaded) {
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
            .catch(function () {
                if (generation === parentCatalogGeneration) {
                    ownerCatalog = []; parentCandidates = []; parentCatalogAvailable = false;
                }
                return parentCandidates;
            });
    }

    function fillParentSelect(select) {
        if (!select) {
            return;
        }
        // Read the member's latest choice here, after the asynchronous read.
        // An outage preserves the unfinished selection, but cannot authorize it.
        var selected = select.value;
        select.disabled = !parentCatalogAvailable;
        if (!parentCatalogAvailable) {
            if (!select.options.length) {
                var unavailable = document.createElement('option');
                unavailable.value = ''; unavailable.textContent = 'Roles are unavailable right now';
                select.appendChild(unavailable);
            }
            if (select === parentSelect && typeSelect.value === 'accomplishment') setStatus(parentUnavailableMessage, 'error');
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
        var eligible = parentCandidates.some(function (candidate) { return candidate.record_key === selected; });
        select.value = eligible ? selected : '';
        if (select === parentSelect && typeSelect.value === 'accomplishment') {
            if (selected && !eligible) {
                setStatus('The role you selected is no longer available. Your Impact wording is still here. Choose an eligible role before queueing it.', 'error');
            } else if (manualStatus.textContent === parentUnavailableMessage) {
                setStatus('Roles refreshed. Your unfinished Impact is still here.', 'ok');
            }
        }
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
            heldRecording || pendingAdd || pendingDecision || pendingCorrection || pendingConversation ||
            Object.values(correctionInputs).some(function (value) { return Boolean(value.trim()); }) || Object.keys(proposalDrafts).length
        );
    }

    function refreshDraftLabel() {
        if (!draftLabel) {
            return;
        }
        document.getElementById('resume-intake-draft-state').hidden = true;
        document.getElementById('resume-intake-new-question').hidden = !seenQuestions.length;
        document.getElementById('resume-intake-skip-question').hidden = !seenQuestions.length;
        document.getElementById('resume-intake-input-finish').hidden = !lastConfirmedKey && !seenQuestions.length && !hasUnsavedInput();
        if (!addOperation && !interviewBusy) document.getElementById('resume-intake-add-label').textContent =
            pendingAdd ? 'Retry submission' : pendingConversation ? 'Recover turn' : 'Continue';
    }

    function protectNavigation() {
        if (unsavedBeforeUnload) {
            return;
        }
        unsavedBeforeUnload = function (event) {
            if (!hasUnsavedInput() || (savedDraftSignature === signatureOf(draftContents()) &&
                    !heldRecording && !microphonePending && !(recorder && recorder.state === 'recording') &&
                    !attachments.some(function (row) { return row.file || row.blob; }))) {
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
        var organizing = activityOperations.some(function (operation) { return operation.kind === 'organize'; });
        var message = adding ? 'Preparing your information…' : organizing ? 'Organizing your résumé…' : '';
        if (transcribing) {
            message += (message ? ' ' : '') + 'Turning your recording into text…';
        }
        if (message && !organizing) {
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

    // A request that names a timeout is abandoned when it runs out, so whatever waits on it
    // (a save before closing, a pause) always gets an answer instead of waiting for ever.
    function send(url, options) {
        var settings = options || {};
        var timeout = settings.timeout;
        delete settings.timeout;
        settings.credentials = 'same-origin';
        settings.headers = Object.assign(
            {'X-PeerSlate-Request': 'same-origin'}, settings.headers || {}
        );
        var timer = null;
        if (timeout && typeof AbortController === 'function' && !settings.signal) {
            var controller = new AbortController();
            settings.signal = controller.signal;
            timer = window.setTimeout(function () { controller.abort(); }, timeout);
        }
        return fetch(url, settings).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (payload) {
                return {response: response, payload: payload};
            });
        }).finally(function () { if (timer !== null) window.clearTimeout(timer); });
    }

    function postJson(url, body, timeout) {
        return send(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
            timeout: timeout
        });
    }

    function pluralLabel(count, label) {
        var text = String(label).toLowerCase(), many = {
            'role': 'roles', 'skill': 'skills', 'credential': 'credentials', 'impact': 'impacts',
            'private entry': 'private entries', 'education': 'education', 'unsorted words': 'unsorted words'};
        return count + ' ' + (count === 1 && text !== 'unsorted words' ? text : (many[text] || text));
    }
    function labelFor(type) {
        return {
            role: 'Role', skill: 'Skill', education: 'Education',
            credential: 'Credential', accomplishment: 'Impact', knowledge: 'Private entry', unspecified: 'Unsorted words'
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
                scheduleDraft();
            });
            item.appendChild(document.createTextNode(' '));
            item.appendChild(remove);
            queuedList.appendChild(item);
        });
    }

    function renderAttachments() {
        attachmentList.replaceChildren();
        attachments.forEach(function (row) {
            if (row.kind === 'recording' && row.source_key && row.status === 'ready') return;
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
            if ((row.kind === 'document' && ['selected', 'failed', 'needs_reattach'].indexOf(row.status) !== -1) ||
                (row.kind === 'recording' && !row.transcribing && ['selected', 'failed', 'held', 'pending', 'needs_reattach'].indexOf(row.status) !== -1)) {
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
                    scheduleDraft();
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
        completion_status: 'Credential status', resume_credential_wording: 'Complete credential details and limitations',
        wording: 'Contribution', metric_value: 'Result', metric_label: 'Result measure'
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
    function navigationFrame() {
        return {screen: screen, text: textarea.value, question: questionPrompt.textContent,
            context: questionContext.textContent, conversation_intent: conversationIntent,
            selected_proposal_key: selectedProposalKey};
    }
    function historyFits() {
        // Match the server's ASCII JSON accounting, including escaped Unicode;
        // keep margin for its whitespace without blocking the live draft save.
        var escaped = JSON.stringify(navigationHistory).replace(/[\u0080-\uffff]/g, function (character) {
            return '\\u' + ('0000' + character.charCodeAt(0).toString(16)).slice(-4);
        });
        return escaped.length <= 30000 && navigationHistory.every(function (frame) {
            return ['text', 'question', 'context'].every(function (name) {
                return new TextEncoder().encode(frame[name]).length <= 20000;
            });
        });
    }
    function showScreen(next, focus, recovering, previousFrame) {
        if (next !== screen && root.open && !restoringDraft && !recovering) {
            navigationHistory.push(previousFrame || navigationFrame());
            while (navigationHistory.length > 12 || (navigationHistory.length && !historyFits())) navigationHistory.shift();
        }
        if (next !== screen && window.PeerSlateResumeFieldVoice) window.PeerSlateResumeFieldVoice.stop();
        if (!restoringDraft && next !== screen) conversationNavigationEpoch += 1;
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
            input: ['Let’s start with you.', 'Supply résumé content directly, or talk with AI to organize and refine it.'],
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
        document.getElementById('resume-intake-back').hidden = !navigationHistory.length || next === 'finish';
        document.getElementById('resume-intake-finish-unsent').hidden = !hasUnsavedInput();
        receiptBox.hidden = true;
        updateReveal();
        refreshDraftLabel();
        scheduleDraft();
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
    /* -- the latest upload, reviewed as one batch ---------------------- */

    function batchOverview() {
        return reviewOverview && reviewOverview.batch ? reviewOverview : null;
    }
    function batchNeedsAttention() {
        var overview = batchOverview();
        return Boolean(overview && (overview.batch.retry_available ||
            (overview.unplaced.count && !overview.groups.length)));
    }
    function groupFor(proposalKey) {
        var overview = batchOverview();
        return overview ? overview.groups.find(function (group) { return group.proposal_key === proposalKey; }) || null : null;
    }
    // Review the new upload on its own. Older unfinished work stays reachable, and the loose
    // details nobody placed are opened one at a time on purpose, never as a long queue.
    function scopedRows(rows) {
        var overview = batchOverview();
        if (!overview) return rows;
        var grouped = {}, loose = {};
        overview.groups.forEach(function (group) { grouped[group.proposal_key] = true; });
        (overview.unplaced.proposal_keys || []).forEach(function (key) { loose[key] = true; });
        return rows.filter(function (row) {
            if (reviewScope === 'earlier') return !grouped[row.proposal_key] && !loose[row.proposal_key];
            return grouped[row.proposal_key] || row.proposal_key === unplacedChoice;
        });
    }
    function chooseLoose(proposalKey) {
        var row = allPendingRows.find(function (candidate) { return candidate.proposal_key === proposalKey; });
        if (!row) return;
        var base = proposals.filter(function (candidate) { return candidate.proposal_key !== unplacedChoice; });
        unplacedChoice = proposalKey; selectedProposalKey = proposalKey;
        renderProposals(base.concat([row]));
    }
    function countSentence(counts) {
        var parts = [];
        [['experience', 'role', 'roles'], ['education', 'education entry', 'education entries'],
         ['credentials', 'credential', 'credentials'], ['skills', 'skill', 'skills'],
         ['other', 'other detail', 'other details']].forEach(function (entry) {
            var count = counts[entry[0]] || 0;
            if (count) parts.push(count + ' ' + (count === 1 ? entry[1] : entry[2]));
        });
        return parts.join(' · ');
    }
    function organizeSource(mode) {
        var overview = batchOverview();
        if (!overview || organizeBusy) return;
        // One unacknowledged request keeps its id, so a dropped reply is safely retried.
        if (!pendingOrganize || pendingOrganize.mode !== mode) {
            pendingOrganize = {request_id: requestId(), source_key: overview.batch.source_key, mode: mode};
        }
        var attempt = pendingOrganize;
        organizeBusy = true;
        var operation = beginActivity('organize');
        setStatus(mode === 'retry' ? 'Organizing your résumé…' : 'Setting your details out one by one…', 'ok');
        postJson(urls.organize, attempt).then(function (result) {
            if (!result.response.ok) {
                if (result.response.status !== 503) pendingOrganize = null;
                throw new Error(result.payload.message || 'That did not finish. Nothing was changed.');
            }
            var payload = result.payload;
            if (payload.success !== true || payload.request_id !== attempt.request_id) {
                throw new Error('No valid reply arrived. You can try again.');
            }
            pendingOrganize = null;
            var message = payload.outcome === 'organized' ? 'Organized. Nothing is saved until you review it.'
                : payload.outcome === 'already_organized' ? 'This résumé is already organized.'
                : (payload.message || 'The organizer is unavailable right now. Nothing was changed.');
            return loadParentCandidates().then(load).then(function () {
                reviewScope = 'batch'; unplacedChoice = null;
                renderProposals(scopedRows(allPendingRows));
                renderBatchOverview(); showScreen('review');
                setStatus(message, payload.outcome === 'unavailable' ? 'error' : 'ok');
            });
        }).catch(function (error) {
            setStatus(error.name !== 'TypeError' && error.message ? error.message :
                'The connection dropped. Nothing was changed; you can try again.', 'error');
        }).finally(function () { endActivity(operation); organizeBusy = false; renderBatchOverview(); });
    }
    function renderBatchOverview() {
        var region = document.getElementById('resume-intake-batch');
        if (!region) return;
        region.replaceChildren();
        var overview = batchOverview();
        region.hidden = !overview;
        if (!overview) return;
        var batch = overview.batch;
        if (reviewScope === 'earlier') {
            region.appendChild(node('h3', 'Earlier unfinished items'));
            region.appendChild(node('p', 'These came from before your latest upload. Nothing here has been saved.', 'resume-intake__hint'));
            var back = node('button', 'Back to your uploaded résumé', 'resume-intake__quiet'); back.type = 'button';
            back.addEventListener('click', function () {
                reviewScope = 'batch'; unplacedChoice = null;
                renderProposals(scopedRows(allPendingRows)); renderBatchOverview();
            });
            region.appendChild(back);
            return;
        }
        region.appendChild(node('h3', 'Your uploaded résumé'));
        if (batch.retry_available) {
            region.appendChild(node('p', batch.retry_reason === 'legacy'
                ? 'I read this résumé, but its details were split into loose pieces. I can try organizing it again. Nothing you confirmed changes.'
                : 'I read your résumé but couldn’t organize it right now. Nothing is lost.'));
            var actions = node('div', undefined, 'resume-intake__proposal-actions');
            var again = node('button', 'Try organizing again', 'resume-intake__add'); again.type = 'button';
            again.disabled = organizeBusy;
            again.addEventListener('click', function () { organizeSource('retry'); });
            actions.appendChild(again);
            if (batch.organization.state === 'unavailable' && !overview.unplaced.count) {
                var manualSort = node('button', 'Sort it myself', 'resume-intake__secondary'); manualSort.type = 'button';
                manualSort.disabled = organizeBusy;
                manualSort.addEventListener('click', function () { organizeSource('sort_myself'); });
                actions.appendChild(manualSort);
            }
            region.appendChild(actions);
            region.appendChild(node('p', 'You can also add details yourself with the manual editor.', 'resume-intake__hint'));
        } else {
            var sentence = countSentence(overview.counts), savedCount = batch.saved || 0;
            region.appendChild(node('p', !sentence ? (savedCount ? 'Everything from your résumé is reviewed.' : 'Your résumé is organized.')
                : savedCount ? 'You have saved ' + savedCount + (savedCount === 1 ? ' item' : ' items') + ' from your résumé. Left to review: ' + sentence + '.'
                : 'I organized your résumé: ' + sentence + '.'));
            if ((batch.uncovered || []).length) {
                region.appendChild(node('p', batch.uncovered.length + (batch.uncovered.length === 1 ? ' line' : ' lines') +
                    ' of your original résumé ' + (batch.uncovered.length === 1 ? 'is' : 'are') +
                    ' not attached to any item. Open the original text below to see ' + (batch.uncovered.length === 1 ? 'it' : 'them') + '.', 'resume-intake__hint'));
            }
            if (batch.organization.rejected) {
                region.appendChild(node('p', batch.organization.rejected + (batch.organization.rejected === 1 ? ' detail' : ' details') +
                    ' couldn’t be placed and ' + (batch.organization.rejected === 1 ? 'is' : 'are') + ' listed below.', 'resume-intake__hint'));
            }
        }
        if (overview.unplaced.count) {
            var loose = node('details', undefined, 'resume-intake__loose');
            loose.appendChild(node('summary', overview.unplaced.count + (overview.unplaced.count === 1 ? ' detail' : ' details') + ' I couldn’t place'));
            var list = node('ul', undefined, 'resume-intake__loose-list');
            overview.unplaced.proposal_keys.forEach(function (key) {
                var row = allPendingRows.find(function (candidate) { return candidate.proposal_key === key; });
                if (!row) return;
                var text = String((row.proposed_values || {}).text || row.quote || '');
                var entry = node('li'), choose = node('button', text.length > 90 ? text.slice(0, 87) + '…' : text, 'resume-intake__quiet');
                choose.type = 'button'; choose.setAttribute('data-loose-key', key);
                choose.addEventListener('click', function () { chooseLoose(key); });
                entry.appendChild(choose); list.appendChild(entry);
            });
            loose.appendChild(list); region.appendChild(loose);
        }
        var batchLinks = node('div', undefined, 'resume-intake__batch-links');
        region.appendChild(batchLinks);
        if (overview.earlier.count) {
            var earlier = node('button', 'Earlier unfinished items (' + overview.earlier.count + ')', 'resume-intake__quiet'); earlier.type = 'button';
            earlier.setAttribute('data-earlier-items', '');
            earlier.addEventListener('click', function () {
                reviewScope = 'earlier'; unplacedChoice = null;
                renderProposals(scopedRows(allPendingRows)); renderBatchOverview();
                if (!proposals.length) setStatus('Nothing earlier is waiting.', 'ok');
            });
            batchLinks.appendChild(earlier);
        }
        var more = node('button', 'Add or upload something else', 'resume-intake__quiet'); more.type = 'button';
        more.setAttribute('data-add-more', '');
        more.addEventListener('click', function () { showScreen('input'); textarea.focus(); });
        batchLinks.appendChild(more);
    }

    /* -- pause: both steps must succeed before the member is told so -- */

    function pauseNotice(message, retry, settled) {
        var notice = document.getElementById('resume-intake-pause-notice');
        if (!notice) {
            notice = node('p', undefined, 'resume-intake__activity resume-intake__activity--outside');
            notice.id = 'resume-intake-pause-notice';
            notice.setAttribute('role', 'status'); notice.setAttribute('aria-live', 'polite');
            reopenButton.parentNode.insertBefore(notice, reopenButton.parentNode.firstChild);
        }
        window.clearTimeout(pauseNoticeTimer);
        notice.replaceChildren();
        notice.hidden = !message;
        if (!message) return;
        notice.appendChild(node('span', message));
        if (retry) {
            var button = node('button', 'Retry', 'resume-intake__quiet'); button.type = 'button';
            button.addEventListener('click', retry);
            notice.appendChild(button);
        } else if (settled) {
            // Only the fully successful notice clears itself. A Retry, or a notice about unsaved
            // changes, stays until it is acted on or replaced.
            pauseNoticeTimer = window.setTimeout(function () { notice.replaceChildren(); notice.hidden = true; }, 15000);
        }
    }
    function showPauseFailure(status) {
        var box = document.getElementById('resume-intake-pause-failure');
        if (!box) {
            box = node('div', undefined, 'resume-intake__inset resume-intake__pause-failure');
            box.id = 'resume-intake-pause-failure'; box.setAttribute('role', 'alert');
            guidePanel.appendChild(box);
        }
        box.replaceChildren();
        box.hidden = false;
        box.appendChild(node('p', 'We couldn’t save your draft just now. Try again, or close anyway. Changes made since your last save on this page may be lost.'));
        var row = node('div', undefined, 'resume-intake__quiet-actions');
        var retry = node('button', 'Try again', 'resume-intake__secondary'); retry.type = 'button';
        retry.addEventListener('click', function () { pauseGuide(status); });
        var close = node('button', 'Close anyway', 'resume-intake__quiet'); close.type = 'button';
        close.addEventListener('click', function () {
            box.hidden = true; hideGuide();
            setGuideStatus(status).then(function (recorded) {
                pauseNotice(recorded ? 'Closed. Your last saved draft is kept; newer changes on this page may be lost.'
                                     : 'Closed without saving your latest changes, and the pause wasn’t recorded.');
            });
        });
        row.append(retry, close); box.appendChild(row);
        retry.focus({preventScroll: true});
    }
    function pauseGuide(status) {
        if (pausing) return Promise.resolve(false);
        pausing = true;
        // Whatever happens to the requests, closing and trying again must stay possible.
        var watchdog = window.setTimeout(function () {
            if (!pausing) return;
            pausing = false; guideBusy = false; completeButton.disabled = false;
            showPauseFailure(status);
        }, SAVE_TIMEOUT * 2 + 5000);
        var stale = document.getElementById('resume-intake-pause-failure');
        if (stale) stale.hidden = true;
        var label = status === 'skipped' ? 'Manual editing' : 'Paused';
        // A pending choice between two draft copies already keeps both safe; there is nothing newer to save.
        var holding = Boolean(draftRecovery || draftRecoveryBusy);
        var kept = holding ? ' Both copies of your draft are kept; you’ll choose between them when you return.'
                           : ' Your draft is saved privately.';
        return Promise.resolve(conversationSupported && !holding ? checkpointDraft() : true).then(function (saved) {
            if (conversationSupported && !saved) { showPauseFailure(status); return false; }
            hideGuide();
            return setGuideStatus(status).then(function (recorded) {
                if (recorded) { pauseNotice(label + '.' + kept, null, true); return true; }
                pauseNotice('Draft saved, but ' + (status === 'skipped' ? 'switching to manual editing' : 'pausing') + ' wasn’t recorded.', function () {
                    setGuideStatus(status).then(function (ok) { if (ok) pauseNotice(label + '.' + kept, null, true); });
                });
                return false;
            });
        }).catch(function () { showPauseFailure(status); return false; })
          .finally(function () { window.clearTimeout(watchdog); pausing = false; });
    }

    function renderProposals(rows, preserveScreen, recoveredMode) {
        var previousFrame = navigationFrame();
        if (!preserveScreen && window.PeerSlateResumeFieldVoice) window.PeerSlateResumeFieldVoice.stop();
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
        var overviewGroup = groupFor(proposal.proposal_key);
        var proposed = Object.assign({}, proposal.proposed_values || {});
        var known = ownerCatalog.find(function (row) { return row.record_key === proposal.target_key; });
        if (known) proposed = Object.assign({}, known.values || {}, known.proposed_values || {}, proposed);
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
        var correcting = !fixedType || (recoveredMode ? recoveredMode === 'correction' : Boolean(draft));
        var dirty = {};
        function storyFields() {
            return type === 'knowledge' && (!fixedType || proposed.classification === 'personal');
        }
        function fieldLabel(name) {
            if (type === 'knowledge') {
                if (name === 'title') return storyFields() ? 'Story title' : 'Title';
                if (name === 'wording') return storyFields() ? 'Story text' : 'Text';
            }
            return FIELD_LABELS[name] || name;
        }
        function field(name, choices) {
            var wrap = node('p');
            var label = node('label', fieldLabel(name));
            var input = node(choices ? 'select' : (['summary', 'wording', 'resume_credential_wording'].indexOf(name) !== -1 ? 'textarea' : 'input'));
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
            var internalClassification = type === 'knowledge' && name === 'classification';
            if (!internalClassification && draft && draft[type] && Object.prototype.hasOwnProperty.call(draft[type], name)) input.value = draft[type][name];
            // Classification remains part of the canonical command, rather
            // than a content field the member needs to edit.
            if (internalClassification) { input.type = 'hidden'; wrap.hidden = true; }
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
            if (input.tagName === 'TEXTAREA' && window.PeerSlateResumeFieldVoice) window.PeerSlateResumeFieldVoice.bind(input, fieldLabel(name), setStatus);
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
                if (name === 'resume_credential_wording' && !Object.prototype.hasOwnProperty.call(proposed, name)) return;
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
                        var values = Object.assign({}, row.values || {}, row.proposed_values || {});
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
            if (type === 'knowledge' && name === 'classification') return;
            if (overviewGroup && ['summary', 'wording', 'resume_credential_wording'].indexOf(name) !== -1) return;
            if (groupedDates && ['start_date', 'end_date', 'date_precision', 'current_role'].indexOf(name) !== -1) return;
            if (proposed[name] === undefined || proposed[name] === null || proposed[name] === '') return;
            var row = node('div'); row.append(node('dt', fieldLabel(name)), node('dd', displayValue(name, proposed[name], proposed))); facts.appendChild(row);
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
            if (type === 'knowledge' && name === 'classification') return;
            var row = node('div'); row.append(node('dt', fieldLabel(name)), node('dd', 'Remove the existing value')); facts.appendChild(row);
        });
        group.appendChild(facts);
        if (overviewGroup && overviewGroup.lines.length) {
            var lineList = node('ul', undefined, 'resume-intake__lines');
            lineList.setAttribute('aria-label', 'Details from your résumé');
            overviewGroup.lines.forEach(function (line) {
                lineList.appendChild(node('li', line.text, 'resume-intake__line' + (line.role === 'header' ? ' resume-intake__line--header' : '')));
            });
            group.appendChild(lineList);
            if ((overviewGroup.uncertain_fields || []).length) {
                group.appendChild(node('p', 'Please check the ' + overviewGroup.uncertain_fields.map(function (name) {
                    return FIELD_LABELS[name] || name;
                }).join(' and ').toLowerCase() + '. I could not read it reliably from your résumé.', 'resume-intake__hint resume-intake__uncertain'));
            }
            var original = node('button', 'View original text', 'resume-intake__quiet'); original.type = 'button';
            original.addEventListener('click', function () {
                var details = document.getElementById('resume-intake-source-review');
                if (details) { details.hidden = false; details.open = true; details.scrollIntoView({block: 'nearest'}); }
            });
            group.appendChild(original);
        }
        group.appendChild(correction); item.appendChild(group);
        var invitation = proposalInvitations[proposal.proposal_key];
        var invitationRevision = proposal.resume_conversation_v1 || {};
        var substantiveRevision = invitationRevision.operation === 'revise_content' &&
            ['wording', 'summary'].some(function (name) { return !!proposal.proposed_values[name]; }) &&
            !(invitationRevision.bullet_edits || []).length;
        if (!invitation && (invitationRevision.operation === 'add_content' || substantiveRevision) &&
                !invitationRevision.recovery_review && !invitationRevision.history_review && !invitationRevision.resume_exclusion) {
            var subject = proposed.role_title || proposed.name || proposed.title;
            if (subject) invitation = proposal.record_type === 'role' ? 'For ' + subject + ', what contribution or result would you like people to understand?' :
                proposal.record_type === 'skill' ? 'How have you used ' + subject + ' in your work?' :
                invitationRevision.presentation_section === 'My Story' ? 'What do you enjoy or care about in ' + subject + '?' : null;
            if (invitation) proposalInvitations[proposal.proposal_key] = invitation;
        }
        if (invitation && seenQuestions.indexOf(invitation) === -1) {
            var optionalDetail = node('div', undefined, 'resume-intake__inset');
            optionalDetail.setAttribute('data-optional-invitation', '');
            optionalDetail.append(node('h3', 'An optional next detail'), node('p', invitation),
                node('p', 'You can keep these details without adding more.', 'resume-intake__hint'));
            var detailActions = node('div', undefined, 'resume-intake__quiet-actions');
            var addDetail = node('button', 'Add a detail', 'resume-intake__secondary'); addDetail.type = 'button';
            var keepDetails = node('button', 'Keep these details', 'resume-intake__quiet'); keepDetails.type = 'button';
            addDetail.addEventListener('click', function () {
                if (decisionBusy || interviewBusy || pendingConversation) return;
                if (textarea.value.trim()) {
                    setStatus('Your unfinished answer is kept. Finish it first, or confirm these details as they are.', 'ok'); return;
                }
                seenQuestions.push(invitation);
                correctionTarget = proposal; correctionDraft = textarea.value;
                textarea.value = correctionInputs[proposal.proposal_key] || '';
                showScreen('input'); questionPrompt.textContent = invitation;
                questionContext.textContent = 'Optional. Add only the detail you want to keep. Your earlier suggestion is still waiting for confirmation.';
                questionContext.hidden = false; textarea.focus(); refreshDraftLabel(); scheduleDraft();
            });
            keepDetails.addEventListener('click', function () {
                if (decisionBusy || interviewBusy) return;
                seenQuestions.push(invitation); renderProposals(proposals);
                setStatus('Your details are still waiting for your confirmation. Nothing was saved.', 'ok'); scheduleDraft();
            });
            detailActions.append(addDetail, keepDetails); optionalDetail.appendChild(detailActions);
            group.before(optionalDetail);
        }
        item.appendChild(node('p', proposal.target_key ? 'Suggested change to an existing entry' : fixedType ? 'Suggested ' + labelFor(type).toLowerCase() + ' · not saved yet' : 'Your words · choose where they belong', 'resume-intake__proposal-source'));
        if (proposal.quote) item.appendChild(node('p', '“' + proposal.quote + '”', 'resume-intake__proposal-quote'));
        var revision = proposal.resume_conversation_v1 || {};
        if (revision.history_review) {
            item.appendChild(node('p', 'Confirm the saved Resume choice below. Your approved entry stays unchanged.', 'resume-intake__hint'));
            if (revision.history_review.effect === 'section') item.appendChild(node('p', 'Place this entry in ' + revision.presentation_section + '.'));
            if (revision.history_review.effect === 'bullets') {
                item.appendChild(node('p', 'Keep this removed-bullet history for an explicit restore:'));
                (revision.excluded_bullets || []).forEach(function (bullet) { item.appendChild(node('p', bullet.text)); });
                if (!(revision.excluded_bullets || []).length) item.appendChild(node('p', 'No excluded bullets.'));
            }
        }
        if (revision.resume_exclusion) item.appendChild(node('p', 'This excludes the selected entry from your private Resume. Original evidence is kept. Confirm to apply this choice.', 'resume-intake__hint'));
        if (revision.resume_restoration) item.appendChild(node('p', 'This restores the selected entry to your private Resume. Confirm to apply this choice.', 'resume-intake__hint'));
        if (proposed.suggested_category === 'project' || (draft && draft.destination === 'project')) {
            var projectHint = node('p', 'For a contribution to a role, choose Impact and confirm its role. For a standalone project, add it privately in My Data. Your original words stay here for review.', 'resume-intake__hint');
            var projectLink = node('a', 'Add a private project in My Data'); projectLink.href = '/app/my-data';
            projectHint.appendChild(projectLink); item.appendChild(projectHint);
        }
        var actions = node('div', undefined, 'resume-intake__proposal-actions');
        if (textarea.value.trim()) {
            var continueAnswer = node('button', 'Continue your unfinished answer', 'resume-intake__quiet');
            continueAnswer.type = 'button';
            continueAnswer.addEventListener('click', function () { showScreen('input'); textarea.focus(); });
            item.appendChild(continueAnswer);
        }
        var accept = node('button', 'Confirm details', 'resume-intake__add'); accept.type = 'button';
        var edit = node('button', 'Change something', 'resume-intake__secondary'); edit.type = 'button';
        var manualEdit = node('button', 'Edit fields manually', 'resume-intake__quiet'); manualEdit.type = 'button';
        var reject = node('button', 'Leave this out', 'resume-intake__quiet'); reject.type = 'button';
        if (proposal.undo_exclusion_token) reject.textContent = 'Undo exclusion';
        var quietActions = node('div', undefined, 'resume-intake__quiet-actions');
        quietActions.append(manualEdit, reject);
        actions.append(accept, edit);
        // The role stays in view while the member says what to change: a short correction box on the card
        // itself. Recording and files are still one tap away behind "Change something".
        var quick = null;
        if (conversationSupported && root.getAttribute('data-interview-enabled') === 'true') {
            quick = node('form', undefined, 'resume-intake__quick-change');
            var quickId = 'resume-intake-quick-' + proposal.proposal_key;
            var quickLabel = node('label', 'Tell me what to change about this one', 'resume-intake__quick-label'); quickLabel.setAttribute('for', quickId);
            var quickText = document.createElement('textarea');
            quickText.id = quickId; quickText.rows = 2; quickText.maxLength = 2000;
            quickText.placeholder = 'For example: add the dates, or fix the title.';
            quickText.value = quickInputs[proposal.proposal_key] || '';
            quickText.addEventListener('input', function () { quickInputs[proposal.proposal_key] = quickText.value; });
            var quickSend = node('button', 'Send change', 'resume-intake__secondary'); quickSend.type = 'submit';
            quick.append(quickLabel, quickText, quickSend);
            quick.addEventListener('submit', function (event) {
                event.preventDefault();
                var statement = quickText.value.trim();
                if (!statement) { setStatus('Type what you would like changed, then send it.', 'ok'); quickText.focus(); return; }
                if (pendingDecision || decisionBusy || interviewBusy || pendingConversation || (textarea.value || '').trim()) {
                    setStatus((textarea.value || '').trim() ? 'Your unfinished answer is kept. Finish it first, then send this change.'
                        : 'Finish what is in progress, then send this change.', 'ok'); return;
                }
                quickSend.disabled = true;
                sendConversation({statement: statement, selectedTarget: 'proposal:' + proposal.proposal_key, target: proposal,
                    onSuccess: function () { delete quickInputs[proposal.proposal_key]; }})
                    .then(function () { quickSend.disabled = false; });
            });
        }
        item.append(actions); if (quick) item.append(quick); item.append(quietActions); proposalList.appendChild(item);
        var overview = node('div', undefined, 'resume-intake__suggestions');
        if (lastAcknowledgement) overview.appendChild(node('p', lastAcknowledgement, 'resume-intake__hint'));
        overview.setAttribute('aria-label', 'Choose a suggestion');
        var sections = {};
        function proposalLabel(row) {
            var canonical = ownerCatalog.find(function (record) { return record.record_key === row.target_key; });
            var values = Object.assign({}, (canonical || {}).values || {}, (canonical || {}).proposed_values || {}, row.proposed_values || {});
            return values.role_title ? values.role_title + (values.employer_name ? ' · ' + values.employer_name : '') :
                values.title || values.name || values.suggested_category || (values.wording || values.text || row.quote || 'Your supplied words');
        }
        proposals.forEach(function (row) {
            var section = (row.resume_conversation_v1 || {}).presentation_section || {role:'Experience',education:'Education',skill:'Skills',credential:'Credentials',accomplishment:'Impact',knowledge:'Summary'}[row.record_type] || 'Choose a section';
            if (!sections[section]) {
                var sectionGroup = node('div', undefined, 'resume-intake__suggestion-group');
                sectionGroup.appendChild(node('h3', section)); overview.appendChild(sectionGroup); sections[section] = sectionGroup;
            }
            var choice = node('button', proposalLabel(row), 'resume-intake__quiet');
            choice.type = 'button'; choice.disabled = Boolean(pendingDecision);
            choice.setAttribute('data-suggestion-key', row.proposal_key);
            choice.setAttribute('aria-pressed', String(row.proposal_key === proposal.proposal_key));
            choice.addEventListener('click', function () {
                selectedProposalKey = row.proposal_key; renderProposals(proposals);
                var selected = document.querySelector('[data-suggestion-key="' + row.proposal_key + '"]');
                if (selected) selected.focus();
            });
            sections[section].appendChild(choice);
        });
        proposalList.before(overview);
        var oldOverview = document.getElementById('resume-intake-suggestion-overview');
        if (oldOverview) oldOverview.remove();
        overview.id = 'resume-intake-suggestion-overview';
        (function () {
            var position = document.getElementById('resume-intake-review-position');
            if (overviewGroup) {
                var peers = proposals.filter(function (row) {
                    var peer = groupFor(row.proposal_key);
                    return peer && peer.section === overviewGroup.section;
                });
                var place = peers.findIndex(function (row) { return row.proposal_key === proposal.proposal_key; }) + 1;
                position.textContent = overviewGroup.section + ' · ' + place + ' of ' + peers.length;
                return;
            }
            position.textContent = reviewScope === 'earlier'
                ? proposals.length + (proposals.length === 1 ? ' earlier item' : ' earlier items') + ' from before your latest upload'
                : proposals.length === 1 ? 'One group of details to review' : proposals.length + ' groups to review · one at a time';
        })();
        function syncCorrection() {
            correction.hidden = !correcting; facts.hidden = correcting;
            edit.hidden = correcting;
            manualEdit.hidden = correcting;
            correction.disabled = Boolean(pendingDecision);
            accept.textContent = pendingDecision ? 'Retry confirmation' : 'Confirm details';
            reject.disabled = Boolean(pendingDecision);
            if (revision.history_review || (revision.recovery_review || {}).as_shown) { edit.hidden = true; manualEdit.hidden = true; correction.hidden = true; facts.hidden = false; if (quick) quick.hidden = true; }
            showScreen(correcting ? 'correction' : 'review', false, false, previousFrame);
            previousFrame = null;
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
                var input = inputs[name]; if (!input) return;
                var raw = input.value.trim();
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
            if (window.PeerSlateResumeFieldVoice) window.PeerSlateResumeFieldVoice.stop();
            if (!pendingDecision) {
                try {
                    var body = {request_id: requestId(), proposal_key: proposal.proposal_key, decision: decision};
                    if (decision === 'accept' && !revision.history_review && !(revision.recovery_review || {}).as_shown) body.confirmed_values = confirmedValues();
                    if (decision === 'reject' && proposal.undo_exclusion_token) body.undo_exclusion_token = proposal.undo_exclusion_token;
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
                    (attempt.body.decision === 'accept' ? ['saved', 'excluded', 'restored', 'reviewed'].indexOf(payload.outcome) === -1 : payload.outcome !== 'unresolved') || payload.publishes !== false) {
                    throw new Error('Confirmation is not acknowledged. Retry the same decision.');
                }
                pendingDecision = null;
                if (payload.restored_proposal) {
                    newestProposalKeys = [payload.restored_proposal.proposal_key];
                    selectedProposalKey = payload.restored_proposal.proposal_key;
                }
                if (pendingConversation && pendingConversation.selected_target === 'proposal:' + proposal.proposal_key) {
                    var retainedTurn = correctionInputs[proposal.proposal_key] || '';
                    if (retainedTurn && textarea.value.indexOf(retainedTurn) === -1)
                        textarea.value += (textarea.value ? '\n\n' : '') + retainedTurn;
                    pendingConversation = null;
                    undispatchedConversationKey = null;
                }
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
                else {
                    proposalList.replaceChildren();
                    if (payload.outcome === 'saved' && proposalInvitations[proposal.proposal_key] &&
                            seenQuestions.indexOf(proposalInvitations[proposal.proposal_key]) !== -1) {
                        showScreen('optional');
                    } else if (payload.outcome === 'saved') {
                        var confirmed = Object.assign({}, (payload.item || {}).values || {}, (payload.item || {}).proposed_values || {}, proposal.proposed_values || {});
                        var label = confirmed.role_title || confirmed.name || confirmed.title || 'this experience';
                        var invitation = proposal.record_type === 'role' ? 'For ' + label + ', what contribution or result would you like people to understand?' :
                            proposal.record_type === 'skill' ? 'How have you used ' + label + ' in your work?' :
                            proposal.record_type === 'education' ? 'What did you learn from ' + label + ' that you use now?' :
                            'Is there a useful example or detail you would like to add about ' + label + '?';
                        document.getElementById('resume-intake-followup').textContent = invitation;
                        seenQuestions.push(invitation);
                        questionPrompt.textContent = invitation; questionContext.textContent = 'Optional. Use the detail you know; leave it out if it does not fit.';
                        questionContext.hidden = false; conversationIntent = null; showScreen('next');
                    } else showScreen('input');
                }
                refreshDraftLabel();
                if (!proposals.length) { var overview = document.getElementById('resume-intake-suggestion-overview'); if (overview) overview.remove(); }
                setStatus(payload.outcome === 'saved' ? 'Saved privately. Sharing settings are unchanged.' : (payload.message || 'Left out. Nothing was saved.'), 'ok');
                loadParentCandidates().then(load).then(function () {
                    if (payload.restored_proposal) {
                        renderProposals(proposals);
                        setStatus('Exclusion undone. The original details are waiting for your confirmation. Nothing was saved.', 'ok');
                    }
                    return checkpointDraft();
                });
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
            if (!proposals.length) showScreen(batchNeedsAttention() ? 'review' : 'input', false);
            return;
        }
        if (['paused', 'completed', 'skipped'].indexOf(status) !== -1 || guideDismissed) return;
        if (!proposals.length) showScreen(batchNeedsAttention() ? 'review' : status === 'not_started' && !workspace.receipts_count ? 'welcome' : 'input', false);
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

    function renderCoverage(sources) {
        var region = document.getElementById('resume-intake-source-review');
        var content = document.getElementById('resume-intake-source-units');
        if (!region || !content) return;
        content.replaceChildren(); region.hidden = !sources.length;
        sources.forEach(function (source, index) {
            var details = node('details'), units = source.source_units || [];
            details.appendChild(node('summary', 'Source ' + (index + 1) + ' · ' + source.kind));
            var isScan = (source.pages || []).some(function (page) { return page.method === 'ocr' || page.ocr; });
            if (isScan) details.appendChild(node('p', 'Scanned text can misread words. Compare with your original file and correct the suggestion before confirming.', 'resume-intake__hint'));
            if (source.complete === false) details.appendChild(node('p', 'Some content could not be read. Keep the original and add the missing material manually.', 'resume-intake__hint'));
            units.forEach(function (unit) {
                var entry = node('p', unit.text, 'resume-intake__proposal-quote');
                entry.setAttribute('data-source-unit', unit.unit_id);
                details.append(node('span', unit.disposition || (unit.kind === 'content' ? 'Needs review' : unit.kind), 'resume-intake__hint'), entry);
            });
            content.appendChild(details);
        });
    }
    function refreshActualPreview() {
        var region = document.getElementById('resume-intake-document');
        var content = document.getElementById('resume-intake-document-content');
        var status = document.getElementById('resume-intake-document-status');
        if (!region || !urls.review || !urls.preview) return Promise.resolve();
        var generation = ++previewGeneration;
        region.hidden = false; region.setAttribute('aria-busy', 'true');
        status.textContent = 'Refreshing your actual private Resume preview.' +
            (content.childElementCount ? ' The earlier saved preview remains below until it is updated.' : '');
        return postJson(urls.review, {}).then(function (result) {
            if (generation !== previewGeneration) throw new Error();
            if (!result.response.ok || !Array.isArray(result.payload.entries)) throw new Error();
            var entries = result.payload.entries.map(function (row) {
                return {entry_key: row.entry_key, resume_display: true, visitor_ai: false};
            });
            return postJson(urls.review, {entries: entries});
        }).then(function (result) {
            if (generation !== previewGeneration) throw new Error();
            if (!result.response.ok || !result.payload.candidate || !result.payload.digest) throw new Error();
            return postJson(urls.preview, {candidate: result.payload.candidate,
                reviewed_digest: result.payload.digest, profile_identity: result.payload.profile_identity || null});
        }).then(function (result) {
            if (generation !== previewGeneration) return;
            if (!result.response.ok || !result.payload.html || result.payload.published !== false) {
                var refused = new Error(result.payload.message || 'The private Resume preview is unavailable.');
                refused.historyReview = result.payload.code === 'history_review_required'; throw refused;
            }
            var parsed = new DOMParser().parseFromString(result.payload.html, 'text/html');
            var composition = parsed.querySelector('.resume-publication--public');
            if (!composition) throw new Error();
            composition.querySelectorAll('script, #visitor-ai-panel, #visitor-ai-open').forEach(function (element) { element.remove(); });
            content.replaceChildren(document.importNode(composition, true)); region.hidden = false;
            status.textContent = 'Your actual private Resume preview. Suggestions remain in the guide until you confirm them. Nothing is published.';
        }).catch(function (error) {
            if (generation !== previewGeneration) return;
            if (error.historyReview) {
                region.hidden = false;
                status.textContent = error.message + (content.childElementCount ? ' The earlier preview remains below until you confirm the current choices.' : ' Choose and confirm the current choices in the guide.');
                return;
            }
            content.replaceChildren(); region.hidden = false;
            status.textContent = 'The private Resume preview is unavailable. Your information and pending suggestions are kept; manual editing remains available.';
        }).finally(function () {
            if (generation === previewGeneration) region.setAttribute('aria-busy', 'false');
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
                conversationSupported = (result.payload.capabilities || {}).supports_resume_conversation === true;
                if (policyText) policyText.textContent = policy.selected
                    ? 'Text or printed English scanned PDF, Word and text files up to ' + (policy.max_document_bytes / 1000000) + ' MB each. Review scanned text for recognition errors. English recordings up to ' + (policy.max_recording_seconds / 60) + ' minutes. ' + policy.retention_statement
                    : 'Synthetic fixture policy only. Real onboarding retention is unavailable.';
                refreshOriginals();
                renderHistoryConflicts(result.payload.resume_decision_conflicts || []);
                renderRecoverableDetails(result.payload.resume_recoverable_details || []);
                proposalInvitations = {};
                (result.payload.conversation_turns || []).forEach(function (turn) {
                    if (!turn.next_question) return;
                    (turn.proposals || []).forEach(function (row) { proposalInvitations[row.proposal_key] = turn.next_question; });
                });
                reviewOverview = result.payload.review_overview || null;
                allPendingRows = result.payload.pending_proposals || [];
                renderProposals(scopedRows(allPendingRows), initialized);
                renderBatchOverview();
                if (!initialized) renderReceipt(result.payload.last_receipt || null);
                renderCoverage(result.payload.source_accounting || []);
                return fetch(urls.guide, {credentials: 'same-origin'})
                    .then(function (response) {
                        return response.json().catch(function () { return {}; });
                    })
                    .then(function (guide) {
                        var initial = !initialized;
                        applyGuideState(result.payload, guide);
                        return initial ? restoreDraft().then(refreshActualPreview) : refreshActualPreview();
                    })
                    .catch(function () {
                        applyGuideState(result.payload, null);
                        setStatus('The guide question is unavailable. Your saved work is unchanged.', 'error');
                    });
            });
    }

    function renderHistoryConflicts(conflicts) {
        var region = document.getElementById('resume-intake-history-review');
        if (!region) return;
        region.replaceChildren(); region.hidden = !conflicts.length;
        if (!conflicts.length) return;
        region.appendChild(node('h3', 'Review a saved Resume choice'));
        region.appendChild(node('p', 'The order of these older choices is unavailable. Choose how the entry should appear now, then review and confirm it. Your approved content is kept.'));
        conflicts.forEach(function (conflict) {
            var item = ownerCatalog.find(function (row) { return row.record_key === conflict.record_key; });
            var values = item ? Object.assign({}, item.values || {}, item.proposed_values || {}) : {};
            var title = values.role_title || values.name || values.title || values.degree_name || 'Saved entry';
            region.appendChild(node('p', title));
            var seen = [];
            conflict.choices.forEach(function (choice) {
                var signature = JSON.stringify(choice.value);
                if (seen.indexOf(signature) !== -1) return;
                seen.push(signature);
                var label = conflict.effect === 'inclusion' ? (choice.value ? 'Exclude this entry' : 'Include this entry') :
                    conflict.effect === 'section' ? 'Use ' + choice.value :
                    conflict.effect === 'bullets' ? 'Review ' + choice.value.length + ' excluded bullets' : 'Review credential details';
                var button = node('button', label, 'resume-intake__secondary'); button.type = 'button';
                var attempt = {request_id: requestId(), record_key: conflict.record_key,
                    effect: conflict.effect, history_token: conflict.history_token, proposal_key: choice.proposal_key};
                button.addEventListener('click', function () {
                    if (decisionBusy || interviewBusy || pendingAdd) return;
                    button.disabled = true;
                    postJson(urls.historyReview, attempt).then(function (result) {
                        if (!result.response.ok) throw new Error(result.payload.message || 'That choice changed. Reload the guide and review it again.');
                        newestProposalKeys = (result.payload.proposals || []).map(function (row) { return row.proposal_key; });
                        selectedProposalKey = newestProposalKeys[0];
                        return loadParentCandidates().then(load).then(function () { renderProposals(proposals); });
                    }).catch(function (error) { setStatus(error.message, 'error'); })
                    .finally(function () { button.disabled = false; });
                });
                region.appendChild(button);
            });
        });
    }

    function renderRecoverableDetails(rows) {
        var region = document.getElementById('resume-intake-excluded-review');
        var content = document.getElementById('resume-intake-excluded-details');
        if (!region || !content) return;
        region.hidden = !rows.length; content.replaceChildren();
        rows.forEach(function (row) {
            var item = node('div', undefined, 'resume-intake__inset');
            item.append(node('p', row.label), node('p', row.text),
                node('p', 'Review first. Confirm only the details you want to keep.', 'resume-intake__hint'));
            var button = node('button', 'Review these details', 'resume-intake__secondary'); button.type = 'button';
            button.setAttribute('data-recovery-key', row.recovery_key);
            var attempt = {request_id: requestId(), recovery_key: row.recovery_key, recovery_token: row.recovery_token};
            button.addEventListener('click', function () {
                if (decisionBusy || interviewBusy || pendingAdd || pendingDecision || pendingConversation) return;
                button.disabled = true;
                postJson(urls.excludedReview, attempt).then(function (result) {
                    if (!result.response.ok) throw new Error(result.payload.message || 'Those details changed. Review the current list again.');
                    newestProposalKeys = (result.payload.proposals || []).map(function (p) { return p.proposal_key; });
                    selectedProposalKey = newestProposalKeys[0];
                    return loadParentCandidates().then(load).then(function () {
                        renderProposals(proposals); setStatus('The original details are waiting for your review. Nothing was saved.', 'ok'); scheduleDraft();
                    });
                }).catch(function (error) { setStatus(error.message, 'error'); })
                .finally(function () { button.disabled = false; });
            });
            item.appendChild(button); content.appendChild(item);
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
    function draftContents() {
        var fields = {};
        Array.prototype.forEach.call(manual.querySelectorAll('input[id],select[id],textarea[id]'), function (input) {
            fields[input.id] = input.type === 'checkbox' ? input.checked : input.value;
        });
        return {text: textarea.value || null,
            items: queuedFacts.map(function (row) { return {client_key: row.client_key, record_type: row.record_type,
                values: row.values, explicit_clears: row.explicit_clears, parent_key: row.parent_key || null}; }),
            attachments: attachments.filter(function (row) { return row.status !== 'cancelled'; }).map(function (row) {
                return {client_key: row.client_key, kind: row.kind, filename: row.filename || null,
                    declared_content_type: row.declared_content_type || null, source_key: row.source_key || null,
                    duration_seconds: row.duration_seconds || null}; }),
            guide_state: {screen: screen, selected_proposal_key: selectedProposalKey,
                correction_target_key: correctionTarget ? correctionTarget.proposal_key : null,
                correction_draft: correctionDraft, correction_inputs: correctionInputs, proposal_drafts: proposalDrafts,
                question: questionPrompt.textContent, context: questionContext.textContent,
                guide_hidden: guideHidden, conversation_intent: conversationIntent,
                manual_type: typeSelect.value, manual_fields: fields, pending_conversation: pendingConversation,
                seen_questions: seenQuestions.slice(-50), navigation_history: navigationHistory}};
    }
    function scheduleDraft() {
        if (!draftReady || !conversationSupported || restoringDraft) return;
        clearTimeout(draftTimer);
        draftTimer = setTimeout(function () { checkpointDraft().catch(function () {}); }, 1500);
    }
    function checkpointDraft() {
        if (!draftReady || !conversationSupported || !urls.draft) return Promise.resolve(false);
        if (draftBusy) return draftBusy.then(checkpointDraft);
        if (draftRecovery || draftRecoveryBusy) return Promise.resolve(false);
        var contents = draftContents(), signature = signatureOf(contents);
        if (!pendingDraftSave && signature === savedDraftSignature) return Promise.resolve(true);
        if (!pendingDraftSave) pendingDraftSave = JSON.parse(JSON.stringify(
            Object.assign({request_id: requestId(), expected_version: draftVersion}, contents)));
        var attempt = pendingDraftSave;
        draftBusy = send(urls.draft, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(attempt), timeout: SAVE_TIMEOUT})
            .then(function (result) {
                if (!result.response.ok || !result.payload.draft) {
                    if ([400, 409].indexOf(result.response.status) !== -1) pendingDraftSave = null;
                    setStatus(result.payload.message || 'Your draft is kept on this page. Saving it for reentry is unavailable.', 'error');
                    if (result.response.status === 409 && result.payload.code === 'draft_conflict') {
                        draftRecovery = {draft: null, available: false};
                        return readRecoveryCopy().then(function () { return false; });
                    }
                    return false;
                }
                draftVersion = result.payload.draft.version; pendingDraftSave = null;
                var acknowledged = Object.assign({}, attempt); delete acknowledged.request_id; delete acknowledged.expected_version;
                savedDraftSignature = signatureOf(acknowledged);
                return true;
            }).catch(function () { setStatus('Your draft is kept on this page. The save response did not arrive.', 'error'); return false; })
            .finally(function () { draftBusy = null; refreshDraftLabel(); });
        // Recovering an older lost acknowledgement must also persist the
        // current turn key before dispatch. Only exact current contents count.
        return draftBusy.then(function (saved) {
            return saved && savedDraftSignature !== signatureOf(draftContents()) ? checkpointDraft() : saved;
        });
    }
    function copyWords(copy) {
        if (!copy) return 'No saved draft remains.';
        var words = [copy.text || ''];
        (copy.items || []).forEach(function (row) { words.push(Object.values(row.values || {}).filter(Boolean).join('\n')); });
        Object.values((copy.guide_state || {}).manual_fields || {}).forEach(function (value) {
            if (typeof value === 'string' && value) words.push(value);
        });
        (copy.attachments || []).forEach(function (row) { words.push(row.filename || 'Recording'); });
        return words.filter(Boolean).join('\n\n') || 'This copy has no unfinished words.';
    }
    function renderRecoveryCopy(message) {
        var unknown = draftRecovery && !draftRecovery.available;
        draftRecoveryBox.hidden = false;
        document.getElementById('resume-intake-draft-recovery-current').hidden = !draftRecovery;
        document.getElementById('resume-intake-draft-recovery-actions').hidden = !draftRecovery;
        document.getElementById('resume-intake-draft-recovery-message').textContent = message ||
            (unknown ? 'The saved copy is unavailable right now. Your page copy is kept. Retry the read before choosing.' :
                draftRecovery && draftRecovery.draft ? 'The saved draft changed. Your page copy is kept. Review both before choosing.' :
                'The saved draft is gone. Your page copy is kept. You can save it as a new draft.');
        document.getElementById('resume-intake-draft-recovery-saved').textContent =
            draftRecovery && draftRecovery.available ? copyWords(draftRecovery.draft) : 'The saved copy could not be read. Retry reading it before choosing a copy.';
        draftRecoveryKeep.textContent = unknown ? 'Retry reading the saved draft' : "Save this page's draft";
        draftRecoveryKeep.disabled = draftRecoveryBusy;
        draftRecoveryUse.disabled = draftRecoveryBusy || !draftRecovery || !draftRecovery.available || !draftRecovery.draft;
        document.getElementById('resume-intake-draft-recovery-held').hidden = !heldDraftCopy;
        document.getElementById('resume-intake-draft-recovery-earlier').textContent = heldDraftCopy ? copyWords(heldDraftCopy.contents) : '';
    }
    function readRecoveryCopy() {
        var generation = ++draftRecoveryGeneration;
        draftRecoveryBusy = true; renderRecoveryCopy('Reading the saved copy. Your page copy is kept.');
        return send(urls.draft).then(function (result) {
            if (generation !== draftRecoveryGeneration) return null;
            if (!result.response.ok || !Object.prototype.hasOwnProperty.call(result.payload, 'draft')) throw new Error('Draft read unavailable');
            return result.payload.draft;
        }).then(function (draft) {
            if (generation === draftRecoveryGeneration) draftRecovery = {draft: draft, available: true};
            return draft;
        }).catch(function () {
            if (generation === draftRecoveryGeneration) draftRecovery = {draft: null, available: false};
        }).finally(function () {
            if (generation === draftRecoveryGeneration) { draftRecoveryBusy = false; renderRecoveryCopy(); }
        });
    }
    function retainDraftCopy(contents, runtimeAttachments) {
        heldDraftCopy = {contents: JSON.parse(JSON.stringify(contents)), attachments: runtimeAttachments};
    }
    function replacementNeedsOperationRecovery() {
        return pendingAdd || pendingDecision || interviewBusy || decisionBusy ||
            (pendingConversation && pendingConversation.request_id !== undispatchedConversationKey);
    }
    function chooseRecoveryCopy(useSaved) {
        if (draftBusy || draftRecoveryBusy || pendingDraftSave) return;
        if (useSaved && replacementNeedsOperationRecovery()) {
            setStatus('Recover the unfinished operation before replacing this page copy. Your words are kept.', 'error'); return;
        }
        var reviewed = draftRecovery && draftRecovery.available ? signatureOf(draftRecovery.draft) : null;
        var localSignature = signatureOf(draftContents());
        var submittedGeneration = conversationGeneration, navigationEpoch = conversationNavigationEpoch;
        return readRecoveryCopy().then(function (fresh) {
            if (!draftRecovery || !draftRecovery.available) return;
            // A turn may begin or reach dispatch while this read is delayed.
            // The earlier choice cannot replace that operation or new intent.
            if (useSaved && replacementNeedsOperationRecovery()) {
                setStatus('Recover the unfinished operation before replacing this page copy. Your words are kept.', 'error'); return;
            }
            if (reviewed === null || reviewed !== signatureOf(fresh) ||
                (useSaved && (localSignature !== signatureOf(draftContents()) ||
                    submittedGeneration !== conversationGeneration || navigationEpoch !== conversationNavigationEpoch))) {
                renderRecoveryCopy('A copy changed while we checked. Review the copies again before choosing.'); return;
            }
            if (useSaved) {
                if (!fresh) return;
                retainDraftCopy(draftContents(), attachments.slice());
                // The explicit saved-copy choice abandons only the never-sent
                // preparation. Return restores the words for a new turn, never
                // the abandoned request identity. Unknown dispatch is blocked.
                if (pendingConversation) heldDraftCopy.contents.guide_state.pending_conversation = null;
                applyDraftCopy(fresh, true);
                draftVersion = fresh.version; savedDraftSignature = signatureOf(draftContents());
                draftRecovery = null;
                renderRecoveryCopy('Using the saved draft. Your earlier page copy is kept below.');
                draftRecoveryKeep.disabled = true; draftRecoveryUse.disabled = true;
                setStatus('Using the saved draft. Your earlier words are still available on this page.', 'ok');
            } else {
                // A fresh read supplies the fence; the explicit choice supplies
                // intent. A second race still returns409, never a forced save.
                retainDraftCopy(fresh, null);
                draftVersion = fresh ? fresh.version : null; draftRecovery = null;
                return checkpointDraft().then(function (saved) {
                    if (saved) {
                        renderRecoveryCopy('This page copy is saved. The earlier saved copy is kept below.');
                        draftRecoveryKeep.disabled = true; draftRecoveryUse.disabled = true;
                        setStatus('Your page copy is saved privately.', 'ok');
                    }
                });
            }
        });
    }
    draftRecoveryKeep.addEventListener('click', function () { chooseRecoveryCopy(false); });
    draftRecoveryUse.addEventListener('click', function () { chooseRecoveryCopy(true); });
    document.getElementById('resume-intake-draft-recovery-return').addEventListener('click', function () {
        if (!heldDraftCopy || draftBusy || draftRecoveryBusy || pendingDraftSave || pendingAdd || pendingDecision || pendingConversation) return;
        var earlier = heldDraftCopy, latest = {contents: draftContents(), attachments: attachments.slice()};
        applyDraftCopy(earlier.contents || {}, true);
        if (earlier.attachments) { attachments = earlier.attachments; renderAttachments(); }
        heldDraftCopy = latest; draftRecovery = {draft: null, available: false};
        readRecoveryCopy();
    });
    function applyDraftCopy(draft, replace) {
        restoringDraft = true;
        if (replace || !textarea.value) textarea.value = draft.text || '';
        if (replace || !queuedFacts.length) queuedFacts = (draft.items || []).map(function (row) {
            return Object.assign({}, row, {label: row.values.role_title || row.values.title || row.values.name || row.values.wording});
        });
        if (replace || !attachments.length) attachments = (draft.attachments || []).map(function (row) {
            return Object.assign({}, row, {label: row.filename || 'Recording', status: row.source_key && !row.needs_reattach ? 'ready' : 'needs_reattach',
                message: row.source_key && !row.needs_reattach ? 'Transcript retained privately.' : 'Choose the original file again before submitting.'});
        });
        if (replace) {
            Array.prototype.forEach.call(manual.querySelectorAll('input[id],select[id],textarea[id]'), function (input) {
                if (input.type === 'checkbox') input.checked = false; else input.value = '';
            });
            selectedProposalKey = null; correctionTarget = null; correctionDraft = null; correctionInputs = {};
            proposalDrafts = {}; conversationIntent = null; pendingConversation = null;
            undispatchedConversationKey = null; navigationHistory = []; seenQuestions = [];
        }
        var state = draft.guide_state;
        if (state) {
            selectedProposalKey = state.selected_proposal_key;
            correctionTarget = proposals.find(function (row) { return row.proposal_key === state.correction_target_key; }) || null;
            correctionDraft = state.correction_draft; correctionInputs = state.correction_inputs || {};
            proposalDrafts = state.proposal_drafts || {}; conversationIntent = state.conversation_intent;
            pendingConversation = state.pending_conversation || null;
            undispatchedConversationKey = null;
            seenQuestions = state.seen_questions || []; navigationHistory = state.navigation_history || [];
            questionPrompt.textContent = state.question || 'What would you like to add or change?';
            questionContext.textContent = state.context || ''; questionContext.hidden = !questionContext.textContent;
            if (state.screen === 'next') document.getElementById('resume-intake-followup').textContent = state.question || '';
            typeSelect.value = state.manual_type || '';
            Object.keys(state.manual_fields || {}).forEach(function (id) {
                var input = document.getElementById(id);
                if (input && manual.contains(input)) {
                    if (input.type === 'checkbox') input.checked = state.manual_fields[id] === true;
                    else input.value = state.manual_fields[id];
                }
            });
            syncDirectFields();
            if ((state.screen === 'review' || state.screen === 'correction') && proposals.length) renderProposals(proposals);
            else showScreen(['review', 'correction'].indexOf(state.screen) !== -1 ? 'input' : state.screen || 'input', false);
            if (state.guide_hidden) hideGuide();
        } else if (replace) { syncDirectFields(); showScreen('input', false); }
        renderQueued(); renderAttachments(); restoringDraft = false;
    }
    function restoreDraft() {
        if (!urls.draft || !conversationSupported) { draftReady = true; return Promise.resolve(); }
        return send(urls.draft).then(function (result) {
            if (!result.response.ok) { draftReady = false; return; }
            var draft = result.payload.draft;
            draftVersion = draft ? draft.version : null;
            if (draft) applyDraftCopy(draft, false);
            draftReady = true; savedDraftSignature = signatureOf(draftContents()); refreshDraftLabel();
        });
    }
    function sendConversation(options) {
        options = options || {};
        if (interviewBusy || pendingAdd || decisionBusy) return Promise.resolve();
        if (microphonePending || (recorder && recorder.state === 'recording') || heldRecording ||
            attachments.some(function (row) { return row.kind === 'recording' && !row.source_key && row.status !== 'cancelled'; })) {
            setStatus('Stop recording and review the transcript before continuing. Your words and audio are kept.', 'error'); return Promise.resolve();
        }
        var statement = options.statement || textarea.value;
        if (!statement.trim()) { setStatus('Say or type what you would like to add or change.', 'ok'); return Promise.resolve(); }
        if (!conversationSupported || root.getAttribute('data-interview-enabled') !== 'true') {
            setStatus('Conversation is unavailable here. Your words are kept; you can edit the fields manually.', 'error'); return Promise.resolve();
        }
        var target = options.target || correctionTarget;
        var selected = options.selectedTarget || (target ? 'proposal:' + target.proposal_key : null);
        var submittedText = options.statement ? null : (pendingConversation ? pendingConversation.statement : textarea.value);
        var inputScreen = screen;
        var navigationEpoch = conversationNavigationEpoch;
        var generation = ++conversationGeneration;
        interviewBusy = true; addButton.disabled = true;
        var activity = beginActivity('add');
        setStatus('Organizing your words with your saved information and earlier suggestions…', 'ok');
        var prepare = pendingConversation ? Promise.resolve(pendingConversation) : send(editorLists.getAttribute('data-workspace-url')).then(function (result) {
            if (!result.response.ok || !Number.isInteger(result.payload.draft_version)) throw new Error('Your private context is unavailable. Your words are kept.');
            pendingConversation = {request_id: requestId(), expected_draft_version: result.payload.draft_version,
                statement: statement, selected_target: selected,
                source_keys: attachments.filter(function (row) { return row.kind === 'recording' && row.source_key; }).map(function (row) { return row.source_key; })};
            undispatchedConversationKey = pendingConversation.request_id;
            return pendingConversation;
        });
        return prepare.then(function (attempt) {
            return checkpointDraft().then(function (saved) {
                if (!saved) throw new Error('Your turn is kept here. Save recovery could not finish; try again before continuing.');
                undispatchedConversationKey = null;
                return postJson(urls.interview, attempt).then(function (result) { return {result: result, attempt: attempt}; });
            });
        }).then(function (completed) {
            var result = completed.result, attempt = completed.attempt;
            if (!result.response.ok) {
                if ([400, 404, 409].indexOf(result.response.status) !== -1) {
                    pendingConversation = null; undispatchedConversationKey = null;
                }
                throw new Error(result.payload.message || 'Your words could not be organized. Your input is kept.');
            }
            var data = result.payload;
            if (data.success !== true || data.request_id !== attempt.request_id || data.saved !== false || data.publishes !== false ||
                data.base_revision !== attempt.expected_draft_version || !Array.isArray(data.proposals) ||
                (data.topic_skipped !== undefined && typeof data.topic_skipped !== 'boolean')) throw new Error('No valid turn arrived. Retry to recover the same turn.');
            pendingConversation = null;
            undispatchedConversationKey = null;
            if (options.onSuccess) options.onSuccess(data);
            if (generation !== conversationGeneration) return;
            attachments = attachments.filter(function (row) { return attempt.source_keys.indexOf(row.source_key) === -1; });
            var currentCorrection = correctionTarget ? 'proposal:' + correctionTarget.proposal_key : null;
            var stoppedCurrent = data.topic_skipped === true && attempt.selected_target === currentCorrection;
            if (submittedText !== null && textarea.value === submittedText) textarea.value = stoppedCurrent && target ? (correctionDraft || '') : '';
            if (stoppedCurrent) {
                correctionTarget = null; correctionDraft = null; conversationIntent = null;
                questionPrompt.textContent = 'What would you like to add or change?';
                questionContext.textContent = data.response; questionContext.hidden = !data.response;
            } else if (target && data.proposals.length) {
                delete proposalDrafts[target.proposal_key]; delete correctionInputs[target.proposal_key];
                correctionTarget = null; correctionDraft = null;
            }
            newestProposalKeys = data.proposals.map(function (row) { return row.proposal_key; });
            if (newestProposalKeys.length) selectedProposalKey = newestProposalKeys[0];
            lastAcknowledgement = data.response;
            renderAttachments(); refreshDraftLabel();
            return loadParentCandidates().then(load).then(function () {
                if (generation !== conversationGeneration || navigationEpoch !== conversationNavigationEpoch || guideHidden || screen !== inputScreen) return;
                if (data.topic_skipped === true && !stoppedCurrent) return;
                if (stoppedCurrent) showScreen('input', false);
                if (textarea.value.trim()) return;
                if (data.proposals.length) renderProposals(proposals);
                else {
                    if (options.question && data.next_question && seenQuestions.indexOf(data.next_question) !== -1) {
                        showScreen('optional'); setStatus('We already covered that question. You can add another detail or continue.', 'ok'); return;
                    }
                    showScreen('input', false);
                    questionPrompt.textContent = data.next_question || 'What would you like to add or change?';
                    questionContext.textContent = data.response; questionContext.hidden = !data.response;
                    if (data.next_question) seenQuestions.push(data.next_question);
                }
                setStatus(data.response + (data.proposals.length ? ' Review and confirm the changes when they are right.' : ''), 'ok');
            }).then(checkpointDraft);
        }).catch(function (error) { setStatus(error.message || 'The response did not arrive. Your words are kept; retry the same turn to recover it.', 'error'); })
        .finally(function () {
            endActivity(activity); interviewBusy = false; addButton.disabled = false;
            document.getElementById('resume-intake-add-label').textContent = pendingConversation ? 'Recover turn' : 'Continue';
            refreshDraftLabel(); scheduleDraft();
        });
    }
    function submitCorrection() { return sendConversation(); }
    function submit(event, mode) {
        if (event) event.preventDefault();
        if (mode === 'guide' && correctionTarget) { submitCorrection(); return; }
        mode = mode || 'guide';
        if (mode === 'guide' && conversationSupported && root.getAttribute('data-interview-enabled') === 'true' && !attachments.some(function (row) { return row.kind === 'document' && row.status !== 'cancelled'; })) {
            sendConversation(); return;
        }
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
            // Documents enter source extraction; accompanying words enter
            // conversation after the document receipt so commands stay commands.
            if (mode === 'guide' && conversationSupported && root.getAttribute('data-interview-enabled') === 'true') request.text = null;
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
                ? 'I organized ' + Object.keys(groups).map(function (label) { return pluralLabel(groups[label], label); }).join(', ') + '.'
                : newestProposalKeys.length + (newestProposalKeys.length === 1 ? ' suggestion is' : ' suggestions are') + ' ready.') + ' Review before saving.';
            renderReceipt(receipt);
            var duplicate = receipt.results.some(function (row) { return row.code === 'duplicate_document'; });
            var unorganized = receipt.results.some(function (row) { return (row.organization || {}).state === 'unavailable'; });
            if (unorganized) lastAcknowledgement = '';
            if (duplicate) lastAcknowledgement = 'You’ve already uploaded this file. Let’s continue with it.';
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
            setStatus(failure.length ? (receipt.message || 'Some input still needs attention.') : duplicate ? 'You’ve already uploaded this file. Let’s continue with it.' : unorganized ? 'I read your résumé but couldn’t organize it right now. Nothing is lost.' : (attempt.mode === 'guide' ? 'I received your answer. ' + newestProposalKeys.length + ' new suggestions are ready for your review; nothing is saved yet.' : (receipt.message || 'Saved privately.')), failure.length ? 'error' : 'ok');
            return loadParentCandidates().then(load).then(function () {
                // The review overview states the counts for an uploaded résumé; a second, differently
                // counted sentence would disagree with it.
                if (lastAcknowledgement && !duplicate && batchOverview() && receipt.results.some(function (row) { return row.kind === 'document'; })) {
                    lastAcknowledgement = 'I received your résumé. Review each suggestion before anything is saved.';
                }
                if (attempt.mode === 'guide' && !guideHidden) {
                    if (failure.length || (textarea.value || '').trim()) showScreen('input');
                    else if (proposals.length) { renderProposals(proposals); showScreen(screen); }
                    else if (batchNeedsAttention()) { reviewScope = 'batch'; renderBatchOverview(); showScreen('review'); }
                    else showScreen(savedCount ? 'next' : 'input');
                    receiptBox.hidden = !failure.length;
                }
                if (attempt.mode === 'guide' && conversationSupported && !failure.length && textarea.value.trim()) return sendConversation();
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
        if (window.PeerSlateResumeFieldVoice) window.PeerSlateResumeFieldVoice.stop();
        conversationNavigationEpoch += 1;
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
        scheduleDraft();
    }
    function reopenGuide() {
        if (window.PeerSlateResumeFieldVoice) window.PeerSlateResumeFieldVoice.stop();
        guideHidden = false; root.hidden = false; reopenButton.hidden = true;
        if (editorSection) editorSection.classList.add('resume-editor--onboarding');
        document.body.classList.add('resume-onboarding-open');
        if (!root.open) root.showModal();
        renderActivity();
        if (heldRecording) setStatus('Your recording is kept here. Choose Transcribe recording when you’re ready.', 'ok');
        showScreen(screen);
        refreshActualPreview();
    }
    function setGuideStatus(status) {
        if (guideBusy) return Promise.resolve(false);
        // A new choice cannot replace an unacknowledged member choice.
        if (pendingGuide && pendingGuide.status !== status) {
            setStatus('The previous guide update still needs a response. Retry it before making a different choice.', 'error'); return Promise.resolve(false);
        }
        if (!pendingGuide) pendingGuide = {request_id: requestId(), status: status};
        var attempt = pendingGuide; guideBusy = true; completeButton.disabled = true;
        return postJson(urls.guideStatus, attempt, SAVE_TIMEOUT).then(function (result) {
            if (!result.response.ok || result.payload.success !== true || result.payload.request_id !== attempt.request_id || result.payload.status !== attempt.status) {
                if ([400, 409].indexOf(result.response.status) !== -1) pendingGuide = null;
                throw new Error(result.payload.message || 'The guide update did not finish. Try again.');
            }
            pendingGuide = null;
            if (attempt.status === 'completed') { showScreen('finish'); setStatus('', 'ok'); }
            else setStatus('You can continue the guide whenever you’re ready.', 'ok');
            return true;
        }).catch(function (error) { setStatus(error.message || 'The guide update did not finish. Try again.', 'error'); return false; })
          .finally(function () {
              guideBusy = false; completeButton.disabled = false;
              document.getElementById('resume-intake-retry-guide').hidden = !pendingGuide;
          });
    }
    function nextQuestion() {
        if (interviewBusy || correctionTarget) return;
        showScreen('input');
        if (root.getAttribute('data-interview-enabled') !== 'true' || !conversationSupported) {
            questionContext.textContent = 'AI guidance is unavailable. You can keep typing or enter details manually.';
            questionContext.hidden = false; return;
        }
        var optionalTopic = conversationIntent === 'story' || conversationIntent === 'project';
        var instruction = conversationIntent === 'story'
            ? 'Ask one concise optional question about my personal story: a hobby, turning point, or something I care about.'
            : conversationIntent === 'project'
                ? 'Ask one concise optional question about a project: what I did and what changed.'
                : 'Ask one concise optional question about a useful gap in my supplied work.';
        return sendConversation({statement: instruction + ' Keep known facts and existing suggestions unchanged.',
            selectedTarget: !optionalTopic && lastConfirmedKey ? 'record:' + lastConfirmedKey : null, question: true});
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
            if (!parentCatalogAvailable) {
                setStatus(parentUnavailableMessage, 'error');
                return;
            }
            parentKey = parentSelect ? parentSelect.value : '';
            if (!parentKey || !parentCandidates.some(function (candidate) { return candidate.record_key === parentKey; })) {
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
        scheduleDraft();
    });
    typeSelect.addEventListener('change', syncDirectFields);
    var credentialStatusInput = document.getElementById('resume-intake-credential-status');
    if (credentialStatusInput) {
        credentialStatusInput.addEventListener('change', syncDirectFields);
    }
    composer.addEventListener('submit', function (event) { submit(event, 'guide'); });
    manualSave.addEventListener('click', function () { submit(null, 'manual'); });
    textarea.addEventListener('input', function () { refreshDraftLabel(); scheduleDraft(); });
    manual.addEventListener('input', scheduleDraft);
    manual.addEventListener('change', scheduleDraft);
    proposalList.addEventListener('input', scheduleDraft);
    proposalList.addEventListener('change', scheduleDraft);
    fileInput.addEventListener('change', function () {
        Array.prototype.forEach.call(fileInput.files, function (file) {
            var retained = attachments.find(function (row) {
                return row.kind === 'document' && row.status === 'needs_reattach' && row.filename === file.name;
            });
            if (retained) {
                retained.file = file; retained.status = 'selected'; retained.message = null;
                retained.declared_content_type = file.type || 'application/octet-stream'; return;
            }
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
        scheduleDraft();
        setStatus('Attached. Nothing is uploaded until you choose Continue.', 'ok');
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
    hideButton.addEventListener('click', function () { pauseGuide('paused'); });
    on('pause', function () { pauseGuide('paused'); });
    reopenButton.addEventListener('click', reopenGuide);
    root.addEventListener('cancel', function (event) { event.preventDefault(); pauseGuide('paused'); });
    skipButton.addEventListener('click', function () { pauseGuide('skipped'); });
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
    on('back', function () {
        var frame = navigationHistory.pop();
        if (!frame) return;
        leaveCorrection();
        selectedProposalKey = frame.selected_proposal_key;
        conversationIntent = frame.conversation_intent;
        if (!textarea.value.trim()) textarea.value = frame.text || '';
        questionPrompt.textContent = frame.question; questionContext.textContent = frame.context; questionContext.hidden = !frame.context;
        if ((frame.screen === 'review' || frame.screen === 'correction') && proposals.length) {
            restoringDraft = true; renderProposals(proposals, false, frame.screen); restoringDraft = false;
        } else showScreen(frame.screen === 'review' || frame.screen === 'correction' ? 'input' : frame.screen, true, true);
        scheduleDraft();
    });
    on('next-question', function () { showScreen('input'); textarea.focus(); });
    on('new-question', nextQuestion);
    on('retry-guide', function () { if (pendingGuide) setGuideStatus(pendingGuide.status); });
    on('review-pending', function () { if (interviewBusy) return; leaveCorrection(); renderProposals(proposals); });
    on('skip-question', function () {
        seenQuestions.push(questionPrompt.textContent);
        if (correctionTarget && proposalInvitations[correctionTarget.proposal_key] === questionPrompt.textContent) {
            leaveCorrection(); renderProposals(proposals);
            setStatus('Your earlier details and any unfinished answer are kept. Review and confirm when they are right.', 'ok');
            scheduleDraft(); return;
        }
        nextQuestion();
    });
    on('input-finish', function () { if (interviewBusy) return; leaveCorrection(); showScreen('optional'); });
    on('next-finish', function () { showScreen('optional'); });
    on('optional-next', function () { showScreen('sharing'); });
    on('view', function () {
        checkpointDraft().then(function (saved) {
            if (conversationSupported && !saved) return;
            hideGuide(); refreshActualPreview();
            var documentRegion = document.getElementById('resume-intake-document');
            if (documentRegion) documentRegion.scrollIntoView({behavior: 'smooth', block: 'start'});
            else { var preview = document.getElementById('resume-editor-review'); if (preview) preview.click(); }
        });
    });
    on('keep-adding', function () { showScreen('input'); textarea.focus(); });
    on('add-example', function () { correctionTarget = null; showScreen('input'); selectedProposalKey = null; conversationIntent = 'project'; questionPrompt.textContent = 'Tell us about a project: what did you do, and what changed?'; questionContext.textContent = ''; questionContext.hidden = true; textarea.focus(); });
    on('add-story', function () { correctionTarget = null; showScreen('input'); selectedProposalKey = null; conversationIntent = 'story'; questionPrompt.textContent = 'What outside work helps people understand you?'; questionContext.textContent = 'A hobby, a turning point, or something you care about. This is optional and stays private.'; questionContext.hidden = false; textarea.focus(); });
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
    if (window.PeerSlateResumeFieldVoice) document.querySelectorAll('#resume-intake-manual textarea, #resume-intake-wording').forEach(function (field) {
        var label = document.querySelector('label[for="' + field.id + '"]');
        window.PeerSlateResumeFieldVoice.bind(field, label ? label.textContent : 'Your words', setStatus);
    });
    renderQueued();
    renderAttachments();
    document.addEventListener('resume-private-draft-changed', function () {
        // Refresh only the saved projection and target catalog. Never reload
        // the active guide or submit its unfinished text and pending choices.
        refreshActualPreview();
        loadParentCandidates().then(function () { fillParentSelect(parentSelect); });
    });
    loadParentCandidates().then(function () { fillParentSelect(parentSelect); });
    load().catch(function () { if (!initialized) showScreen('input', false); setStatus('The guide could not be loaded. You can edit manually or reopen it to try again.', 'error'); });
})();
