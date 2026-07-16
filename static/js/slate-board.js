// Slate Board living whiteboard — note CRUD, private capture review,
// completion, priority, drag/reorder, zoom, and responsive accordion.

(function () {
    'use strict';

    var root = document.querySelector('[data-board-root]');
    if (!root) { return; }

    var workspace = root.querySelector('[data-board-workspace]');
    var canvas = root.querySelector('[data-board-canvas]');
    var scaleElement = root.querySelector('[data-board-scale]');
    var statusElement = document.getElementById('sb-board-status');
    var noteDialog = document.getElementById('sb-note-dialog');
    var noteForm = document.getElementById('sb-note-form');
    var statsDialog = document.getElementById('sb-stats-dialog');
    var shareDialog = document.getElementById('sb-share-dialog');
    var captureLayer = root.querySelector('[data-capture-layer]');
    var captureForm = document.getElementById('sb-capture-form');
    var captureTranscript = document.getElementById('sb-capture-transcript');
    var proposalPanel = root.querySelector('[data-proposal-panel]');
    var proposalList = root.querySelector('[data-proposal-list]');
    var focusPanel = root.querySelector('[data-focus-panel]');
    var apiEnabled = root.dataset.boardApi === 'true';

    var storageScope = root.dataset.boardStorageScope || 'petec-preview';
    var STORAGE_KEY = 'peerslateSlateBoardLivingWhiteboardV2:' + storageScope;
    var LEGACY_STORAGE_KEY = 'peerslateSlateBoardConcept1:' + storageScope;
    var STORAGE_VERSION = 3;
    var SECTION_ORDER = ['short', 'projects', 'long', 'work'];
    var SECTION_LABELS = {
        short: 'Short Term',
        projects: 'Projects',
        long: 'Long Term',
        work: 'Work'
    };
    var SECTION_COLORS = {
        short: '#4ea3ff',
        projects: '#4f5bd5',
        long: '#2ec8d3',
        work: '#d7a33e'
    };
    var TAG_STYLES = {
        work: 'work',
        personal: 'personal',
        goal: 'goal',
        growth: 'growth',
        health: 'health',
        finance: 'finance',
        career: 'career',
        creative: 'creative',
        lifestyle: 'lifestyle',
        adventure: 'adventure'
    };

    var seedNotes = Array.prototype.map.call(
        root.querySelectorAll('.sb-note[data-note-id]'),
        function (card) {
            var checklist = [];
            try { checklist = JSON.parse(card.dataset.checklist || '[]'); }
            catch (error) { checklist = []; }
            return normalizeNote({
                id: card.dataset.noteId,
                section: card.dataset.section,
                title: card.dataset.title,
                timeline: card.dataset.timeline,
                tag: card.dataset.tag,
                tagStyle: card.dataset.tagStyle,
                starred: card.dataset.starred === 'true',
                completed: card.dataset.completed === 'true',
                overdue: card.dataset.overdue === 'true',
                description: card.dataset.description || '',
                checklist: checklist.map(function (text) {
                    return { text: String(text), completed: false };
                }),
                comments: [],
                link: '',
                attachment: ''
            });
        }
    );

    var state = loadState();
    var zoom = 100;
    var history = [];
    var draggingId = null;
    var pointerDrag = null;
    var suppressCardClick = false;
    var editingNoteId = null;
    var workingComments = [];
    var existingAttachment = '';
    var lastDialogTrigger = null;
    var deleteTimer = null;
    var pendingCreates = {};
    var remoteWriteQueues = {};
    var pendingProposals = [];
    var proposalSourceText = '';
    var panelReturnTarget = null;
    var focusedNoteId = null;
    var mobileQuery = window.matchMedia('(max-width: 759px)');
    var lastResponsiveMobile = null;

    function normalizeNote(raw) {
        raw = raw || {};
        var section = SECTION_ORDER.indexOf(raw.section) >= 0 ? raw.section : 'short';
        var title = typeof raw.title === 'string' && raw.title.trim()
            ? raw.title.trim().slice(0, 120)
            : 'Untitled note';
        var tag = typeof raw.tag === 'string' && raw.tag.trim()
            ? raw.tag.trim().slice(0, 24)
            : 'Note';
        var checklist = Array.isArray(raw.checklist) ? raw.checklist : [];
        var comments = Array.isArray(raw.comments) ? raw.comments : [];

        return {
            id: String(raw.id || ('note-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7))),
            apiId: raw.apiId ? Number(raw.apiId) : null,
            section: section,
            title: title,
            timeline: typeof raw.timeline === 'string' ? raw.timeline.slice(0, 40) : '',
            tag: tag,
            tagStyle: validTagStyle(raw.tagStyle || tag),
            starred: Boolean(raw.starred),
            completed: Boolean(raw.completed),
            overdue: Boolean(raw.overdue),
            description: typeof raw.description === 'string' ? raw.description.slice(0, 800) : '',
            checklist: checklist.slice(0, 20).map(function (item) {
                if (typeof item === 'string') {
                    return { text: item.slice(0, 160), completed: false };
                }
                return {
                    text: String(item && item.text || '').slice(0, 160),
                    completed: Boolean(item && item.completed)
                };
            }).filter(function (item) { return item.text.trim(); }),
            comments: comments.slice(0, 50).map(function (comment) {
                return {
                    text: String(comment && comment.text || '').slice(0, 240),
                    author: String(comment && comment.author || 'You').slice(0, 60),
                    timestamp: String(comment && comment.timestamp || '')
                };
            }).filter(function (comment) { return comment.text.trim(); }),
            link: typeof raw.link === 'string' ? raw.link.slice(0, 500) : '',
            attachment: typeof raw.attachment === 'string' ? raw.attachment.slice(0, 180) : ''
        };
    }

    function validTagStyle(value) {
        var key = String(value || '').toLowerCase();
        return TAG_STYLES[key] || 'work';
    }

    function loadState() {
        var saved = null;
        try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY)); }
        catch (error) { saved = null; }

        if (!saved) {
            try { saved = JSON.parse(localStorage.getItem(LEGACY_STORAGE_KEY)); }
            catch (error) { saved = null; }
        }

        if (!saved || !Array.isArray(saved.notes)) {
            return {
                version: STORAGE_VERSION,
                notes: seedNotes.slice(),
                collaborators: [],
                view: 'board'
            };
        }

        var legacySections = {
            todo: 'short',
            short: 'projects',
            long: 'long',
            someday: 'work'
        };
        var notes = saved.notes.map(function (note) {
            var migrated = Object.assign({}, note);
            if (saved.version === 2 && legacySections[migrated.section]) {
                migrated.section = legacySections[migrated.section];
            }
            return normalizeNote(migrated);
        });
        return {
            version: STORAGE_VERSION,
            notes: notes,
            collaborators: Array.isArray(saved.collaborators) ? saved.collaborators.slice(0, 20) : [],
            view: saved.view === 'list' ? 'list' : 'board'
        };
    }

    function saveState() {
        state.version = STORAGE_VERSION;
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
            setSaveStatus(apiEnabled ? 'Saved locally; private sync pending' : 'Saved in this browser', 'saved');
        } catch (error) {
            setSaveStatus('Visible for this visit only', 'warning');
            announce('Your change is visible for this visit, but browser storage is unavailable.');
        }
    }

    function setSaveStatus(message, status) {
        root.querySelectorAll('[data-save-status]').forEach(function (element) {
            element.textContent = message;
            element.dataset.status = status || 'saved';
        });
    }

    function cloneNotes(notes) {
        return JSON.parse(JSON.stringify(notes));
    }

    function pushHistory(label) {
        history.push({ label: label, notes: cloneNotes(state.notes) });
        if (history.length > 30) { history.shift(); }
    }

    function undoLastChange() {
        if (apiEnabled) {
            announce('Undo is limited to the browser-only baseline while private server sync is enabled.');
            return;
        }
        var previous = history.pop();
        if (!previous) {
            announce('There is nothing to undo yet.');
            return;
        }
        state.notes = previous.notes.map(normalizeNote);
        saveState();
        renderBoard();
        announce('Undid ' + previous.label + '.');
    }

    function announce(message) {
        if (statusElement) { statusElement.textContent = message; }
    }

    function findNote(noteId) {
        return state.notes.find(function (note) { return note.id === noteId; }) || null;
    }

    function findCardControl(noteId, selector) {
        var card = Array.prototype.find.call(
            root.querySelectorAll('.sb-note[data-note-id]'),
            function (candidate) { return candidate.dataset.noteId === noteId; }
        );
        return card ? card.querySelector(selector) : null;
    }

    function createSvg(path, viewBox) {
        var namespace = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(namespace, 'svg');
        var pathNode = document.createElementNS(namespace, 'path');
        svg.setAttribute('viewBox', viewBox || '0 0 24 24');
        svg.setAttribute('aria-hidden', 'true');
        pathNode.setAttribute('d', path);
        svg.appendChild(pathNode);
        return svg;
    }

    function createCard(note) {
        var article = document.createElement('article');
        article.className = 'sb-note';
        article.draggable = true;
        article.dataset.noteId = note.id;
        article.dataset.section = note.section;
        if (note.starred) { article.classList.add('is-starred'); }
        if (note.completed) { article.classList.add('is-completed'); }

        var openButton = document.createElement('button');
        openButton.className = 'sb-note__open';
        openButton.type = 'button';
        openButton.setAttribute('aria-label', 'Open note: ' + note.title);
        article.appendChild(openButton);

        var top = document.createElement('div');
        top.className = 'sb-note__top';

        var complete = document.createElement('button');
        complete.className = 'sb-note__complete';
        complete.type = 'button';
        complete.setAttribute('role', 'checkbox');
        complete.setAttribute('aria-checked', String(note.completed));
        complete.setAttribute('aria-label', (note.completed ? 'Mark incomplete: ' : 'Mark complete: ') + note.title);
        complete.appendChild(document.createElement('span'));

        var heading = document.createElement('h3');
        heading.textContent = note.title;

        var star = document.createElement('button');
        star.className = 'sb-note__star';
        star.type = 'button';
        star.setAttribute('aria-pressed', String(note.starred));
        star.setAttribute('aria-label', (note.starred ? 'Remove important marker from ' : 'Mark as important: ') + note.title);
        star.appendChild(createSvg('m12 3 2.75 5.58 6.16.9-4.46 4.34 1.05 6.13L12 17.05 6.5 19.95l1.05-6.13L3.09 9.48l6.16-.9L12 3Z'));

        top.appendChild(complete);
        top.appendChild(heading);
        top.appendChild(star);
        article.appendChild(top);

        if (note.description) {
            var summary = document.createElement('p');
            summary.className = 'sb-note__summary';
            summary.textContent = note.description;
            article.appendChild(summary);
        }

        var meta = document.createElement('div');
        meta.className = 'sb-note__meta';
        var timeline = document.createElement('span');
        timeline.className = 'sb-note__timeline';
        timeline.textContent = note.timeline || 'No timeline';
        var tag = document.createElement('span');
        tag.className = 'sb-tag sb-tag--' + note.tagStyle;
        tag.textContent = note.tag;
        meta.appendChild(timeline);
        meta.appendChild(tag);
        article.appendChild(meta);
        return article;
    }

    function renderBoard() {
        SECTION_ORDER.forEach(function (section) {
            var list = root.querySelector('[data-note-list="' + section + '"]');
            var column = root.querySelector('[data-column="' + section + '"]');
            if (!list || !column) { return; }
            list.replaceChildren();
            var notes = state.notes.filter(function (note) { return note.section === section; });
            notes.forEach(function (note) {
                var item = document.createElement('li');
                item.appendChild(createCard(note));
                list.appendChild(item);
            });
            var count = column.querySelector('[data-column-count]');
            if (count) { count.textContent = String(notes.length); }
        });
        updateStats();
        if (focusedNoteId && !findNote(focusedNoteId)) { closeFocusPanel(false); }
    }

    function updateStats() {
        var total = state.notes.length;
        var completed = state.notes.filter(function (note) { return note.completed; }).length;
        var starred = state.notes.filter(function (note) { return note.starred; }).length;
        var overdue = state.notes.filter(function (note) { return note.overdue && !note.completed; }).length;
        setText('[data-stat-total]', total);
        setText('[data-stat-completed]', completed);
        setText('[data-stat-starred]', starred);
        setText('[data-stat-overdue]', overdue);
        setText('[data-donut-total]', total);

        var percentages = [];
        var start = 0;
        SECTION_ORDER.forEach(function (section) {
            var count = state.notes.filter(function (note) { return note.section === section; }).length;
            var legend = root.querySelector('[data-legend-count="' + section + '"]');
            if (legend) { legend.textContent = String(count); }
            var end = total ? start + (count / total * 100) : start;
            percentages.push(SECTION_COLORS[section] + ' ' + start.toFixed(2) + '% ' + end.toFixed(2) + '%');
            start = end;
        });

        var donut = root.querySelector('[data-donut]');
        if (donut) {
            donut.style.background = total
                ? 'conic-gradient(' + percentages.join(', ') + ')'
                : '#e7eaf0';
            donut.setAttribute('aria-label', SECTION_ORDER.map(function (section) {
                var count = state.notes.filter(function (note) { return note.section === section; }).length;
                return SECTION_LABELS[section] + ': ' + count;
            }).join(', '));
        }
    }

    function setText(selector, value) {
        var element = root.querySelector(selector);
        if (element) { element.textContent = String(value); }
    }

    function setBoardView(view, trigger, silent) {
        var nextView = view === 'list' ? 'list' : 'board';
        state.view = nextView;
        workspace.dataset.boardViewState = nextView;
        workspace.classList.toggle('is-list-view', nextView === 'list');
        root.querySelectorAll('[data-board-view]').forEach(function (button) {
            button.setAttribute('aria-pressed', String(button.dataset.boardView === nextView));
        });
        root.querySelectorAll('[data-toggle-board-view]').forEach(function (button) {
            var listActive = nextView === 'list';
            button.setAttribute('aria-pressed', String(listActive));
            button.setAttribute('aria-label', listActive
                ? 'Show physical whiteboard view'
                : 'Show accessible list view');
            var label = button.querySelector('span');
            if (label) { label.textContent = listActive ? 'Board view' : 'List view'; }
        });
        if (nextView === 'list') { updateZoom(100, true); }
        saveState();
        if (!silent) {
            announce(nextView === 'list'
                ? 'Structured list view active. The same board records and actions remain available.'
                : 'Physical whiteboard view active.');
        }
        if (trigger && typeof trigger.focus === 'function') { trigger.focus(); }
    }

    function updatePanelClass() {
        var panelOpen = (proposalPanel && !proposalPanel.hidden) || (focusPanel && !focusPanel.hidden);
        workspace.classList.toggle('has-panel', Boolean(panelOpen));
    }

    function stopListeningPreview() {
        workspace.classList.remove('is-listening');
        var listenButton = root.querySelector('[data-capture-listen]');
        var stopButton = root.querySelector('[data-capture-stop]');
        var stateLabel = root.querySelector('[data-capture-state]');
        var trustLabel = root.querySelector('[data-capture-trust]');
        if (listenButton) { listenButton.hidden = false; }
        if (stopButton) { stopButton.hidden = true; }
        if (stateLabel) { stateLabel.textContent = 'Ready'; }
        if (trustLabel) {
            trustLabel.textContent = 'Private draft. Nothing has been saved or shared yet.';
        }
    }

    function openCaptureLayer(trigger) {
        if (!captureLayer || !captureTranscript) { return; }
        closeProposalPanel(false);
        closeFocusPanel(false);
        panelReturnTarget = trigger || panelReturnTarget || document.activeElement;
        captureLayer.hidden = false;
        workspace.classList.add('has-capture');
        stopListeningPreview();
        window.setTimeout(function () { captureTranscript.focus(); }, 0);
        announce('Chalk It Up private draft opened. Type a thought or inspect the listening-state preview.');
    }

    function closeCaptureLayer(returnFocus) {
        if (!captureLayer) { return; }
        stopListeningPreview();
        captureLayer.hidden = true;
        workspace.classList.remove('has-capture');
        if (returnFocus !== false && panelReturnTarget && typeof panelReturnTarget.focus === 'function') {
            panelReturnTarget.focus();
        }
    }

    function startListeningPreview() {
        if (!captureTranscript) { return; }
        if (!captureTranscript.value.trim()) {
            captureTranscript.value = 'I need to finish the PMP by September. I want to study Saturday mornings, take two practice exams, and have Danielle review my plan.';
        }
        workspace.classList.add('is-listening');
        var listenButton = root.querySelector('[data-capture-listen]');
        var stopButton = root.querySelector('[data-capture-stop]');
        var stateLabel = root.querySelector('[data-capture-state]');
        var trustLabel = root.querySelector('[data-capture-trust]');
        if (listenButton) { listenButton.hidden = true; }
        if (stopButton) { stopButton.hidden = false; stopButton.focus(); }
        if (stateLabel) { stateLabel.textContent = 'Listening preview'; }
        if (trustLabel) {
            trustLabel.textContent = 'Visual preview only. The microphone is not recording. Edit the sample or switch to typing.';
        }
        announce('Listening-state preview active. The microphone is not recording and nothing has been saved.');
    }

    function inferSection(text) {
        var value = String(text || '').toLowerCase();
        if (/project|build|launch|prototype|studio/.test(value)) { return 'projects'; }
        if (/work|review|mbse|evidence|job|role/.test(value)) { return 'work'; }
        if (/long term|future|ph\.?d|degree|community|mentor/.test(value)) { return 'long'; }
        return 'short';
    }

    function buildProposals(text) {
        var clean = String(text || '').replace(/\s+/g, ' ').trim();
        if (/pmp|certification/i.test(clean)) {
            return [
                {
                    typeLabel: 'G',
                    title: 'PMP Certification',
                    section: 'short',
                    tag: 'Goal',
                    tagStyle: 'goal',
                    timeline: 'Target: September',
                    description: clean,
                    canSave: true
                },
                {
                    typeLabel: 'M',
                    title: 'Saturday study routine',
                    section: 'short',
                    tag: 'Milestone',
                    tagStyle: 'growth',
                    timeline: 'Saturday mornings',
                    description: 'Proposed milestone linked to the PMP goal.',
                    canSave: true
                },
                {
                    typeLabel: 'M',
                    title: 'Complete two practice exams',
                    section: 'short',
                    tag: 'Milestone',
                    tagStyle: 'work',
                    timeline: 'Before September',
                    description: 'Proposed milestone linked to the PMP goal.',
                    canSave: true
                },
                {
                    typeLabel: 'P',
                    title: 'Danielle reviews the plan',
                    section: 'projects',
                    tag: 'Proposed relationship',
                    tagStyle: 'personal',
                    timeline: 'Not invited',
                    description: 'Relationship preview only. No invitation will be sent.',
                    canSave: false
                }
            ];
        }

        return [{
            typeLabel: 'N',
            title: clean.length > 80 ? clean.slice(0, 77) + '...' : clean,
            section: inferSection(clean),
            tag: 'Private note',
            tagStyle: 'work',
            timeline: 'Captured now',
            description: clean,
            canSave: true
        }];
    }

    function renderProposalList() {
        if (!proposalList) { return; }
        proposalList.replaceChildren();
        pendingProposals.forEach(function (proposal, index) {
            var article = document.createElement('article');
            article.className = 'sb-proposal-item';

            var type = document.createElement('span');
            type.className = 'sb-proposal-item__type';
            type.textContent = proposal.typeLabel;

            var copy = document.createElement('div');
            var title = document.createElement('strong');
            title.textContent = proposal.title;
            var detail = document.createElement('small');
            detail.textContent = proposal.canSave
                ? proposal.tag + ' - ' + SECTION_LABELS[proposal.section]
                : proposal.tag + ' - no invitation or relationship will be saved';
            copy.appendChild(title);
            copy.appendChild(detail);

            var remove = document.createElement('button');
            remove.className = 'sb-proposal-item__remove';
            remove.type = 'button';
            remove.dataset.proposalRemove = String(index);
            remove.setAttribute('aria-label', 'Remove proposal: ' + proposal.title);
            remove.textContent = '×';

            article.appendChild(type);
            article.appendChild(copy);
            article.appendChild(remove);
            proposalList.appendChild(article);
        });

        var approve = root.querySelector('[data-approve-proposals]');
        if (approve) {
            var saveable = pendingProposals.filter(function (proposal) { return proposal.canSave; }).length;
            approve.disabled = saveable === 0;
            approve.textContent = saveable === 1
                ? 'Approve 1 private item'
                : 'Approve ' + saveable + ' private items';
        }
    }

    function openProposalPanel() {
        if (!proposalPanel) { return; }
        closeCaptureLayer(false);
        closeFocusPanel(false);
        renderProposalList();
        proposalPanel.hidden = false;
        updatePanelClass();
        var close = proposalPanel.querySelector('[data-close-proposal]');
        if (close) { close.focus(); }
        announce('Structured proposal review opened. Nothing has been saved, shared, or published.');
    }

    function closeProposalPanel(returnFocus) {
        if (!proposalPanel) { return; }
        proposalPanel.hidden = true;
        updatePanelClass();
        if (returnFocus !== false && panelReturnTarget && typeof panelReturnTarget.focus === 'function') {
            panelReturnTarget.focus();
        }
    }

    function reviewCapture(event) {
        if (event) { event.preventDefault(); }
        if (!captureTranscript) { return; }
        var text = captureTranscript.value.trim();
        if (!text) {
            announce('Type or edit a private capture before reviewing it.');
            captureTranscript.focus();
            return;
        }
        stopListeningPreview();
        proposalSourceText = text;
        pendingProposals = buildProposals(text);
        openProposalPanel();
    }

    function approveProposals() {
        var saveable = pendingProposals.filter(function (proposal) { return proposal.canSave; });
        if (!saveable.length) {
            announce('No private record proposals remain to approve.');
            return;
        }
        pushHistory('capture approval');
        var addedIds = [];
        saveable.forEach(function (proposal, index) {
            var note = normalizeNote({
                id: 'capture-' + Date.now() + '-' + index,
                section: proposal.section,
                title: proposal.title,
                timeline: proposal.timeline,
                tag: proposal.tag,
                tagStyle: proposal.tagStyle,
                description: proposal.description,
                checklist: [],
                comments: [],
                starred: false,
                completed: false,
                overdue: false
            });
            state.notes.push(note);
            addedIds.push(note.id);
        });
        saveState();
        renderBoard();
        closeProposalPanel(false);
        captureTranscript.value = '';
        pendingProposals = [];
        proposalSourceText = '';
        var firstControl = addedIds.length ? findCardControl(addedIds[0], '.sb-note__open') : null;
        if (firstControl) { firstControl.focus(); }
        announce('Added ' + addedIds.length + ' private browser ' + (addedIds.length === 1 ? 'item' : 'items') + '. No relationship was invited or published.');
    }

    function setFocusValue(selector, value) {
        if (!focusPanel) { return; }
        var element = focusPanel.querySelector(selector);
        if (element) { element.textContent = value; }
    }

    function openFocusPanel(note, trigger) {
        if (!focusPanel || !note) { return; }
        closeCaptureLayer(false);
        closeProposalPanel(false);
        panelReturnTarget = trigger || document.activeElement;
        focusedNoteId = note.id;
        setFocusValue('[data-focus-eyebrow]', note.tag + ' - private');
        setFocusValue('[data-focus-title]', note.title);
        setFocusValue('[data-focus-description]', note.description || 'Open Edit note to add context, dates, evidence links, and next steps.');
        setFocusValue('[data-focus-timeline]', note.timeline || 'Not set');
        setFocusValue('[data-focus-section]', SECTION_LABELS[note.section]);

        var progress = note.completed ? 100 : (note.id === 'peerslate-alpha' ? 64 : 30);
        if (note.checklist.length) {
            var complete = note.checklist.filter(function (item) { return item.completed; }).length;
            progress = Math.round(complete / note.checklist.length * 100);
        }
        setFocusValue('[data-focus-progress]', progress + '%');
        var bar = focusPanel.querySelector('[data-focus-progress-bar]');
        if (bar) { bar.style.width = progress + '%'; }

        focusPanel.hidden = false;
        updatePanelClass();
        var close = focusPanel.querySelector('[data-close-focus]');
        if (close) { close.focus(); }
        announce('Focus details opened for ' + note.title + '. Connected records are labeled as preview states.');
    }

    function closeFocusPanel(returnFocus) {
        if (!focusPanel) { return; }
        focusPanel.hidden = true;
        focusedNoteId = null;
        updatePanelClass();
        if (returnFocus !== false && panelReturnTarget && typeof panelReturnTarget.focus === 'function') {
            panelReturnTarget.focus();
        }
    }

    function openDialog(dialog, trigger) {
        if (!dialog) { return; }
        lastDialogTrigger = trigger || document.activeElement;
        dialog.dataset.openedAt = String(Date.now());
        if (typeof dialog.showModal === 'function') { dialog.showModal(); }
        else { dialog.setAttribute('open', ''); }
    }

    function closeDialog(dialog) {
        if (!dialog) { return; }
        if (typeof dialog.close === 'function') { dialog.close(); }
        else { dialog.removeAttribute('open'); }
    }

    function openEditor(note, section, trigger, focusAttachment) {
        if (!noteDialog || !noteForm) { return; }
        editingNoteId = note ? note.id : null;
        workingComments = note && Array.isArray(note.comments)
            ? note.comments.map(function (comment) { return Object.assign({}, comment); })
            : [];
        existingAttachment = note ? note.attachment : '';
        noteForm.reset();
        document.getElementById('sb-note-id').value = note ? note.id : '';
        document.getElementById('sb-note-title').value = note ? note.title : '';
        document.getElementById('sb-note-description').value = note ? note.description : '';
        document.getElementById('sb-note-section').value = note ? note.section : (section || 'short');
        document.getElementById('sb-note-timeline').value = note ? note.timeline : '';
        document.getElementById('sb-note-tag').value = note ? note.tag : '';
        document.getElementById('sb-note-link').value = note ? note.link : '';

        var starButton = document.getElementById('sb-note-star');
        starButton.setAttribute('aria-pressed', String(Boolean(note && note.starred)));
        var style = note ? note.tagStyle : sectionDefaultStyle(section || 'short');
        var color = noteForm.querySelector('input[name="tagStyle"][value="' + style + '"]')
            || noteForm.querySelector('input[name="tagStyle"]');
        if (color) { color.checked = true; }

        document.getElementById('sb-note-dialog-mode').textContent = note ? 'Edit note' : 'New note';
        document.getElementById('sb-note-dialog-title').textContent = note ? note.title : 'Capture an idea';
        var deleteButton = document.getElementById('sb-delete-note');
        deleteButton.hidden = !note;
        resetDeleteButton();
        renderChecklist(note ? note.checklist : []);
        document.getElementById('sb-checklist-section').open = Boolean(note && note.checklist.length);
        renderComments();
        updateAttachmentLabel(existingAttachment || 'Choose a file');
        document.getElementById('sb-note-more').open = Boolean(
            focusAttachment || (note && (note.link || note.attachment || workingComments.length))
        );
        document.getElementById('sb-comments').open = workingComments.length > 0;
        openDialog(noteDialog, trigger);

        window.setTimeout(function () {
            var target = focusAttachment
                ? document.getElementById('sb-note-attachment')
                : document.getElementById('sb-note-title');
            if (target) { target.focus(); }
        }, 20);
    }

    function sectionDefaultStyle(section) {
        if (section === 'projects') { return 'goal'; }
        if (section === 'long') { return 'finance'; }
        if (section === 'work') { return 'health'; }
        return 'work';
    }

    function createChecklistRow(item) {
        var row = document.createElement('div');
        row.className = 'sb-checklist__row';

        var checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = Boolean(item && item.completed);
        checkbox.setAttribute('aria-label', 'Checklist item complete');

        var input = document.createElement('input');
        input.type = 'text';
        input.maxLength = 160;
        input.value = item && item.text ? item.text : '';
        input.placeholder = 'Next step';
        input.setAttribute('aria-label', 'Checklist item');

        var remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'sb-checklist__remove';
        remove.setAttribute('aria-label', 'Remove checklist item');
        remove.appendChild(createSvg('m7 7 10 10M17 7 7 17'));
        remove.addEventListener('click', function () {
            row.remove();
            ensureChecklistEmptyState();
        });

        row.appendChild(checkbox);
        row.appendChild(input);
        row.appendChild(remove);
        return row;
    }

    function renderChecklist(items) {
        var container = document.getElementById('sb-checklist-items');
        container.replaceChildren();
        (items || []).forEach(function (item) { container.appendChild(createChecklistRow(item)); });
        var count = noteDialog.querySelector('[data-checklist-count]');
        if (count) { count.textContent = String((items || []).length); }
        ensureChecklistEmptyState();
    }

    function ensureChecklistEmptyState() {
        var container = document.getElementById('sb-checklist-items');
        var rows = container.querySelectorAll('.sb-checklist__row');
        var count = noteDialog.querySelector('[data-checklist-count]');
        if (count) { count.textContent = String(rows.length); }
        var empty = container.querySelector('.sb-checklist__empty');
        if (!rows.length && !empty) {
            empty = document.createElement('p');
            empty.className = 'sb-checklist__empty';
            empty.textContent = 'No checklist yet. Add the first small step when it helps.';
            container.appendChild(empty);
        } else if (rows.length && empty) {
            empty.remove();
        }
    }

    function collectChecklist() {
        return Array.prototype.map.call(
            document.querySelectorAll('#sb-checklist-items .sb-checklist__row'),
            function (row) {
                return {
                    text: row.querySelector('input[type="text"]').value.trim(),
                    completed: row.querySelector('input[type="checkbox"]').checked
                };
            }
        ).filter(function (item) { return item.text; });
    }

    function renderComments() {
        var thread = document.getElementById('sb-comment-thread');
        var count = noteDialog.querySelector('[data-comment-count]');
        thread.replaceChildren();
        count.textContent = String(workingComments.length);
        if (!workingComments.length) {
            var empty = document.createElement('p');
            empty.className = 'sb-comments__empty';
            empty.textContent = 'No comments yet.';
            thread.appendChild(empty);
            return;
        }
        workingComments.forEach(function (comment) {
            var item = document.createElement('div');
            item.className = 'sb-comment';
            var author = document.createElement('strong');
            author.textContent = comment.author || 'You';
            var text = document.createElement('span');
            text.textContent = comment.text;
            item.appendChild(author);
            item.appendChild(text);
            thread.appendChild(item);
        });
    }

    function addComment() {
        var input = document.getElementById('sb-comment-input');
        var text = input.value.trim();
        if (!text) { input.focus(); return; }
        workingComments.push({
            text: text.slice(0, 240),
            author: 'You',
            timestamp: new Date().toISOString()
        });
        input.value = '';
        renderComments();
        input.focus();
    }

    function updateAttachmentLabel(value) {
        var label = document.getElementById('sb-attachment-label');
        if (label) { label.textContent = value || 'Choose a file'; }
    }

    function submitNote(event) {
        event.preventDefault();
        if (!noteForm.reportValidity()) { return; }

        var existing = editingNoteId ? findNote(editingNoteId) : null;
        var selectedColor = noteForm.querySelector('input[name="tagStyle"]:checked');
        var attachmentInput = document.getElementById('sb-note-attachment');
        var attachment = attachmentInput.files && attachmentInput.files[0]
            ? attachmentInput.files[0].name
            : existingAttachment;
        var note = normalizeNote({
            id: existing ? existing.id : undefined,
            apiId: existing ? existing.apiId : null,
            section: document.getElementById('sb-note-section').value,
            title: document.getElementById('sb-note-title').value,
            timeline: document.getElementById('sb-note-timeline').value.trim(),
            tag: document.getElementById('sb-note-tag').value.trim() || 'Note',
            tagStyle: selectedColor ? selectedColor.value : 'work',
            starred: document.getElementById('sb-note-star').getAttribute('aria-pressed') === 'true',
            completed: existing ? existing.completed : false,
            overdue: existing ? existing.overdue : false,
            description: document.getElementById('sb-note-description').value,
            checklist: collectChecklist(),
            comments: workingComments,
            link: document.getElementById('sb-note-link').value.trim(),
            attachment: attachment
        });

        pushHistory(existing ? 'note edit' : 'note creation');
        if (existing) {
            var index = state.notes.indexOf(existing);
            state.notes.splice(index, 1, note);
        } else {
            state.notes.push(note);
        }
        saveState();
        renderBoard();
        lastDialogTrigger = findCardControl(note.id, '.sb-note__open') || lastDialogTrigger;
        closeDialog(noteDialog);
        announce((existing ? 'Updated ' : 'Added ') + note.title + ' in ' + SECTION_LABELS[note.section] + '.');
        syncNoteToApi(note);
    }

    function resetDeleteButton() {
        var button = document.getElementById('sb-delete-note');
        if (!button) { return; }
        if (deleteTimer) { window.clearTimeout(deleteTimer); }
        deleteTimer = null;
        button.classList.remove('is-confirming');
        button.textContent = 'Delete note';
    }

    function deleteCurrentNote() {
        var button = document.getElementById('sb-delete-note');
        var note = editingNoteId ? findNote(editingNoteId) : null;
        if (!note) { return; }
        if (!button.classList.contains('is-confirming')) {
            button.classList.add('is-confirming');
            button.textContent = 'Confirm delete';
            deleteTimer = window.setTimeout(resetDeleteButton, 3500);
            return;
        }
        pushHistory('note deletion');
        state.notes = state.notes.filter(function (candidate) { return candidate.id !== note.id; });
        saveState();
        renderBoard();
        lastDialogTrigger = mobileQuery.matches
            ? root.querySelector('.sb-mobile-add')
            : root.querySelector('[data-add-note][data-section="' + note.section + '"]');
        closeDialog(noteDialog);
        announce('Deleted ' + note.title + '.');
        archiveNoteFromApi(note);
    }

    function toggleComplete(noteId) {
        var note = findNote(noteId);
        if (!note) { return; }
        pushHistory('completion change');
        note.completed = !note.completed;
        saveState();
        renderBoard();
        var completeControl = findCardControl(noteId, '.sb-note__complete');
        if (completeControl) { completeControl.focus(); }
        announce(note.title + (note.completed ? ' completed.' : ' returned to active work.'));
        syncNoteToApi(note);
    }

    function toggleStar(noteId) {
        var note = findNote(noteId);
        if (!note) { return; }
        pushHistory('important marker change');
        note.starred = !note.starred;
        saveState();
        renderBoard();
        var starControl = findCardControl(noteId, '.sb-note__star');
        if (starControl) { starControl.focus(); }
        announce(note.starred ? note.title + ' marked important.' : 'Important marker removed from ' + note.title + '.');
        syncNoteToApi(note);
    }

    function setActiveTool(tool) {
        workspace.dataset.activeTool = tool;
        workspace.querySelectorAll('[data-tool]').forEach(function (button) {
            var active = button.dataset.tool === tool;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });
    }

    function handleTool(button) {
        var tool = button.dataset.tool;
        setActiveTool(tool);
        if (tool === 'chalk') {
            openCaptureLayer(button);
        } else if (tool === 'add') {
            openEditor(null, 'short', button, false);
        } else if (tool === 'more') {
            updateStats();
            openDialog(statsDialog, button);
        } else if (tool === 'draw') {
            announce('Draw tool selected as a visual preview. Freehand strokes are not saved in this baseline.');
        } else if (tool === 'connector') {
            announce('Connect tool selected. Semantic relationships remain preview-only until canonical records are integrated.');
        } else if (tool === 'undo') {
            undoLastChange();
            setActiveTool('select');
        } else {
            announce('Select tool active. Drag notes to organize them.');
        }
    }

    function updateZoom(next, silent) {
        zoom = Math.max(50, Math.min(160, next));
        var ratio = zoom / 100;
        scaleElement.style.setProperty('--sb-scale', String(ratio));
        root.querySelectorAll('[data-zoom-value]').forEach(function (output) {
            output.value = zoom + '%';
            output.textContent = zoom + '%';
        });
        if (!silent) { announce('Board zoom ' + zoom + ' percent.'); }
    }

    function applyResponsiveColumns() {
        workspace.classList.add('is-enhanced');
        var enteringMobile = mobileQuery.matches && lastResponsiveMobile !== true;
        root.querySelectorAll('[data-column]').forEach(function (column, index) {
            var toggle = column.querySelector('[data-column-toggle]');
            if (mobileQuery.matches) {
                if (enteringMobile) { column.classList.toggle('is-open', index === 0); }
                toggle.disabled = false;
                toggle.setAttribute('aria-expanded', String(column.classList.contains('is-open')));
            } else {
                column.classList.add('is-open');
                toggle.disabled = true;
                toggle.setAttribute('aria-expanded', 'true');
            }
        });
        lastResponsiveMobile = mobileQuery.matches;
    }

    function toggleMobileColumn(column) {
        if (!mobileQuery.matches) { return; }
        var open = !column.classList.contains('is-open');
        if (open) {
            root.querySelectorAll('[data-column]').forEach(function (candidate) {
                if (candidate === column) { return; }
                candidate.classList.remove('is-open');
                var candidateToggle = candidate.querySelector('[data-column-toggle]');
                if (candidateToggle) { candidateToggle.setAttribute('aria-expanded', 'false'); }
            });
        }
        column.classList.toggle('is-open', open);
        var toggle = column.querySelector('[data-column-toggle]');
        toggle.setAttribute('aria-expanded', String(open));
    }

    function dragStart(event) {
        var card = event.target.closest('.sb-note[data-note-id]');
        if (!card) { return; }
        draggingId = card.dataset.noteId;
        card.classList.add('is-dragging');
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', draggingId);
        }
    }

    function dragOver(event) {
        if (!draggingId) { return; }
        var list = event.target.closest('[data-note-list]');
        if (!list) { return; }
        event.preventDefault();
        root.querySelectorAll('[data-note-list]').forEach(function (candidate) {
            candidate.classList.toggle('is-drop-target', candidate === list);
        });
        var card = Array.prototype.find.call(root.querySelectorAll('.sb-note'), function (candidate) {
            return candidate.dataset.noteId === draggingId;
        });
        if (!card) { return; }
        var item = card.closest('li');
        var after = dragAfterElement(list, event.clientY, item);
        if (after) { list.insertBefore(item, after); }
        else { list.appendChild(item); }
    }

    function dragAfterElement(list, pointerY, draggingItem) {
        var items = Array.prototype.filter.call(list.children, function (item) {
            return item !== draggingItem;
        });
        var closest = { offset: Number.NEGATIVE_INFINITY, element: null };
        items.forEach(function (item) {
            var rect = item.getBoundingClientRect();
            var offset = pointerY - rect.top - rect.height / 2;
            if (offset < 0 && offset > closest.offset) {
                closest = { offset: offset, element: item };
            }
        });
        return closest.element;
    }

    function dropNote(event) {
        var list = event.target.closest('[data-note-list]');
        if (!draggingId || !list) { return; }
        event.preventDefault();
        var moved = findNote(draggingId);
        var nextOrder = [];
        pushHistory('note move');
        SECTION_ORDER.forEach(function (section) {
            var sectionList = root.querySelector('[data-note-list="' + section + '"]');
            if (!sectionList) { return; }
            sectionList.querySelectorAll('.sb-note[data-note-id]').forEach(function (card) {
                var note = findNote(card.dataset.noteId);
                if (note) {
                    note.section = section;
                    nextOrder.push(note);
                }
            });
        });
        state.notes = nextOrder;
        saveState();
        clearDragState();
        renderBoard();
        if (moved) {
            announce('Moved ' + moved.title + ' to ' + SECTION_LABELS[moved.section] + '.');
            syncNoteToApi(moved);
        }
    }

    function clearDragState() {
        draggingId = null;
        root.querySelectorAll('.is-dragging').forEach(function (card) { card.classList.remove('is-dragging'); });
        root.querySelectorAll('.is-drop-target').forEach(function (list) { list.classList.remove('is-drop-target'); });
        root.querySelectorAll('.is-touch-drop-target').forEach(function (column) {
            column.classList.remove('is-touch-drop-target');
        });
    }

    function cancelDrag() {
        var shouldRestore = Boolean(draggingId);
        clearDragState();
        if (shouldRestore) { renderBoard(); }
    }

    function pointerDragStart(event) {
        if (event.pointerType === 'mouse') { return; }
        if (event.target.closest('.sb-note__complete, .sb-note__star')) { return; }
        var card = event.target.closest('.sb-note[data-note-id]');
        if (!card) { return; }
        pointerDrag = {
            pointerId: event.pointerId,
            noteId: card.dataset.noteId,
            startX: event.clientX,
            startY: event.clientY,
            active: false,
            targetList: null,
            card: card
        };
        if (typeof card.setPointerCapture === 'function') {
            card.setPointerCapture(event.pointerId);
        }
    }

    function pointerDragMove(event) {
        if (!pointerDrag || pointerDrag.pointerId !== event.pointerId) { return; }
        var distance = Math.hypot(
            event.clientX - pointerDrag.startX,
            event.clientY - pointerDrag.startY
        );
        if (!pointerDrag.active && distance < 10) { return; }
        if (!pointerDrag.active) {
            pointerDrag.active = true;
            draggingId = pointerDrag.noteId;
            pointerDrag.card.classList.add('is-dragging');
        }
        event.preventDefault();
        var beneath = document.elementFromPoint(event.clientX, event.clientY);
        var column = beneath && beneath.closest ? beneath.closest('[data-column]') : null;
        var list = column ? column.querySelector('[data-note-list]') : null;
        pointerDrag.targetList = list;
        root.querySelectorAll('[data-column]').forEach(function (candidate) {
            candidate.classList.toggle('is-touch-drop-target', candidate === column);
        });
    }

    function commitPointerDrop(list) {
        var moved = draggingId ? findNote(draggingId) : null;
        if (!moved || !list) { cancelDrag(); return; }
        var targetSection = list.dataset.noteList;
        if (SECTION_ORDER.indexOf(targetSection) < 0) { cancelDrag(); return; }
        pushHistory('note move');
        var reordered = state.notes.filter(function (note) { return note !== moved; });
        moved.section = targetSection;
        var insertAt = reordered.reduce(function (latest, note, index) {
            return note.section === targetSection ? index + 1 : latest;
        }, reordered.length);
        reordered.splice(insertAt, 0, moved);
        state.notes = reordered;
        saveState();
        clearDragState();
        renderBoard();
        announce('Moved ' + moved.title + ' to ' + SECTION_LABELS[moved.section] + '.');
        syncNoteToApi(moved);
    }

    function pointerDragEnd(event) {
        if (!pointerDrag || pointerDrag.pointerId !== event.pointerId) { return; }
        var wasActive = pointerDrag.active;
        var targetList = pointerDrag.targetList;
        pointerDrag = null;
        if (!wasActive) { return; }
        event.preventDefault();
        suppressCardClick = true;
        commitPointerDrop(targetList);
        window.setTimeout(function () { suppressCardClick = false; }, 0);
    }

    function pointerDragCancel(event) {
        if (!pointerDrag || pointerDrag.pointerId !== event.pointerId) { return; }
        var wasActive = pointerDrag.active;
        pointerDrag = null;
        if (wasActive) { cancelDrag(); }
    }

    function renderCollaborators() {
        var list = document.getElementById('sb-invite-list');
        list.replaceChildren();
        state.collaborators.forEach(function (collaborator) {
            var row = document.createElement('div');
            row.className = 'sb-invite-person';
            var name = document.createElement('strong');
            name.textContent = String(collaborator.name || '').slice(0, 120);
            var permission = document.createElement('span');
            permission.textContent = collaborator.permission === 'edit' ? 'Can edit · preview' : 'Can view · preview';
            row.appendChild(name);
            row.appendChild(permission);
            list.appendChild(row);
        });
    }

    function addCollaborator(event) {
        event.preventDefault();
        var input = document.getElementById('sb-invite-person');
        var permission = document.getElementById('sb-invite-permission');
        var name = input.value.trim();
        if (!name) { input.focus(); return; }
        state.collaborators.push({ name: name.slice(0, 120), permission: permission.value });
        state.collaborators = state.collaborators.slice(-20);
        saveState();
        renderCollaborators();
        input.value = '';
        document.getElementById('sb-share-notice').textContent =
            'Collaboration preview added. Nothing has been sent; this board remains local to your browser.';
    }

    function copyBoardLink(button) {
        var notice = document.getElementById('sb-share-notice');
        var text = window.location.href;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(function () {
                notice.textContent = 'Page link copied. Local note changes are not included in the link.';
                button.textContent = 'Link copied';
            }).catch(function () {
                notice.textContent = 'Copy was unavailable. The page address remains in your browser address bar.';
            });
        } else {
            notice.textContent = 'Copy was unavailable. The page address remains in your browser address bar.';
        }
    }

    function api(url, options) {
        var settings = options || {};
        settings.headers = Object.assign({}, settings.headers || {}, {
            'X-PeerSlate-Request': 'same-origin'
        });
        if (settings.body) { settings.headers['Content-Type'] = 'application/json'; }
        return fetch(url, settings).then(function (response) {
            return response.json().then(function (payload) {
                if (!response.ok || !payload.success) {
                    throw new Error(payload.message || 'PeerSlate could not complete the request.');
                }
                return payload;
            });
        });
    }

    function apiPayload(note) {
        var isoDate = /^\d{4}-\d{2}-\d{2}$/.test(note.timeline) ? note.timeline : null;
        return {
            title: note.title,
            body: note.description,
            category: note.section,
            status: note.completed ? 'completed' : 'active',
            priority: note.starred ? 'important' : 'normal',
            progress_percent: note.completed ? 100 : 0,
            target_date: isoDate,
            color_label: note.tagStyle,
            update_note: 'Updated from the Slate Board.'
        };
    }

    function queueRemoteWrite(noteId, operation) {
        var previous = remoteWriteQueues[noteId] || Promise.resolve();
        var queued = previous.catch(function () { return null; }).then(operation);
        var tracked = queued.finally(function () {
            if (remoteWriteQueues[noteId] === tracked) {
                delete remoteWriteQueues[noteId];
            }
        });
        remoteWriteQueues[noteId] = tracked;
        return tracked;
    }

    function syncNoteToApi(note) {
        if (!apiEnabled || !note) { return; }
        if (note.apiId) {
            queueRemoteWrite(note.id, function () {
                var current = findNote(note.id);
                if (!current || !current.apiId) { return null; }
                return api('/api/slate-items/' + current.apiId, {
                    method: 'PATCH',
                    body: JSON.stringify(apiPayload(current))
                }).then(function (payload) {
                    setSaveStatus('Saved privately', 'saved');
                    return payload;
                });
            }).catch(function () {
                setSaveStatus('Browser copy only', 'warning');
                announce('The board is updated here, but the private account copy could not be reached.');
            });
            return;
        }

        if (pendingCreates[note.id]) { return; }
        var localId = note.id;

        pendingCreates[localId] = api('/api/slate-items', {
            method: 'POST',
            body: JSON.stringify({
                space_name: 'Slate Board',
                space_type: 'board',
                item_type: note.tag || 'note',
                title: note.title,
                body: note.description,
                category: note.section,
                target_date: /^\d{4}-\d{2}-\d{2}$/.test(note.timeline) ? note.timeline : null
            })
        }).then(function (payload) {
            var saved = payload.items && payload.items[0];
            var apiId = saved && (saved.slate_item_id || saved.id);
            var current = findNote(localId);
            if (!apiId) { return null; }
            if (!current) {
                return queueRemoteWrite(localId, function () {
                    return api('/api/slate-items/' + apiId + '/archive', {
                        method: 'POST',
                        body: JSON.stringify({ note: 'Archived after local deletion.' })
                    });
                });
            }
            current.apiId = apiId;
            saveState();
            return queueRemoteWrite(localId, function () {
                var latest = findNote(localId);
                if (!latest || !latest.apiId) { return null; }
                return api('/api/slate-items/' + latest.apiId, {
                    method: 'PATCH',
                    body: JSON.stringify(apiPayload(latest))
                }).then(function (patchPayload) {
                    setSaveStatus('Saved privately', 'saved');
                    return patchPayload;
                });
            });
        }).catch(function () {
            setSaveStatus('Browser copy only', 'warning');
            announce('The board is updated here, but the private account copy could not be reached.');
        }).finally(function () {
            delete pendingCreates[localId];
        });
    }

    function archiveNoteFromApi(note) {
        if (!apiEnabled || !note || !note.apiId) { return; }
        var apiId = note.apiId;
        queueRemoteWrite(note.id, function () {
            return api('/api/slate-items/' + apiId + '/archive', {
                method: 'POST',
                body: JSON.stringify({ note: 'Archived from the Slate Board.' })
            });
        }).catch(function () {
            setSaveStatus('Browser copy only', 'warning');
            announce('The note is removed here, but its private account copy could not be archived.');
        });
    }

    function loadRemoteNotes() {
        if (!apiEnabled) { return; }
        api('/api/slate-spaces/Slate%20Board').then(function (payload) {
            var items = payload.slate_space && payload.slate_space.items || [];
            var createsInFlight = Object.keys(pendingCreates).map(function (noteId) {
                return pendingCreates[noteId];
            });
            return Promise.all(createsInFlight).then(function () {
                if (!items.length) {
                    setSaveStatus('Saved privately', 'saved');
                    announce('Your private board is ready. New notes are saved privately.');
                    return;
                }
                var remoteIds = {};
                state.notes.forEach(function (note) {
                    if (note.apiId) { remoteIds[note.apiId] = true; }
                });
                items.forEach(function (item) {
                    var id = item.slate_item_id || item.id;
                    if (!id || remoteIds[id]) { return; }
                    state.notes.push(normalizeNote({
                        id: 'private-' + id,
                        apiId: id,
                        section: SECTION_ORDER.indexOf(item.category) >= 0 ? item.category : 'short',
                        title: item.title,
                        description: item.body,
                        timeline: item.target_date || '',
                        tag: item.item_type || 'Private',
                        tagStyle: item.color_label || 'work',
                        starred: item.priority === 'important',
                        completed: item.status === 'completed'
                    }));
                    remoteIds[id] = true;
                });
                saveState();
                renderBoard();
                setSaveStatus('Saved privately', 'saved');
                announce('Your private Slate Board is loaded.');
            });
        }).catch(function () {
            setSaveStatus('Browser copy only', 'warning');
            announce('The private account board could not be reached. Your changes still stay saved in this browser.');
        });
    }

    root.addEventListener('click', function (event) {
        if (suppressCardClick) {
            event.preventDefault();
            suppressCardClick = false;
            return;
        }

        var viewButton = event.target.closest('[data-board-view]');
        if (viewButton) {
            setBoardView(viewButton.dataset.boardView, viewButton, false);
            return;
        }

        var viewToggle = event.target.closest('[data-toggle-board-view]');
        if (viewToggle) {
            setBoardView(state.view === 'list' ? 'board' : 'list', viewToggle, false);
            return;
        }

        if (event.target.closest('[data-fit-view]')) {
            updateZoom(100);
            announce('Board fit reset to 100 percent.');
            return;
        }

        if (event.target.closest('[data-capture-listen]')) {
            startListeningPreview();
            return;
        }

        if (event.target.closest('[data-capture-stop]')) {
            stopListeningPreview();
            if (captureTranscript) { captureTranscript.focus(); }
            announce('Listening-state preview stopped. The editable private draft is still available.');
            return;
        }

        if (event.target.closest('[data-capture-cancel]')) {
            closeCaptureLayer(true);
            announce('Private capture cancelled. Nothing was saved.');
            return;
        }

        var proposalRemove = event.target.closest('[data-proposal-remove]');
        if (proposalRemove) {
            pendingProposals.splice(Number(proposalRemove.dataset.proposalRemove), 1);
            renderProposalList();
            announce('Proposal removed from this review.');
            return;
        }

        if (event.target.closest('[data-approve-proposals]')) {
            approveProposals();
            return;
        }

        if (event.target.closest('[data-edit-capture]')) {
            closeProposalPanel(false);
            if (captureTranscript) { captureTranscript.value = proposalSourceText; }
            openCaptureLayer(null);
            return;
        }

        if (event.target.closest('[data-close-proposal]')) {
            closeProposalPanel(true);
            announce('Proposal review closed. Nothing was saved.');
            return;
        }

        var currentFocus = event.target.closest('[data-open-current-focus]');
        if (currentFocus) {
            openFocusPanel(findNote(currentFocus.dataset.noteId), currentFocus);
            return;
        }

        if (event.target.closest('[data-close-focus]')) {
            closeFocusPanel(true);
            return;
        }

        if (event.target.closest('[data-edit-focused-note]')) {
            var focused = focusedNoteId ? findNote(focusedNoteId) : null;
            var focusTrigger = panelReturnTarget;
            closeFocusPanel(false);
            if (focused) { openEditor(focused, null, focusTrigger, false); }
            return;
        }

        var addButton = event.target.closest('[data-add-note]');
        if (addButton) {
            openEditor(null, addButton.dataset.section || 'short', addButton, false);
            return;
        }

        var completeButton = event.target.closest('.sb-note__complete');
        if (completeButton) {
            toggleComplete(completeButton.closest('.sb-note').dataset.noteId);
            return;
        }

        var starButton = event.target.closest('.sb-note__star');
        if (starButton) {
            toggleStar(starButton.closest('.sb-note').dataset.noteId);
            return;
        }

        var cardTarget = event.target.closest('.sb-note[data-note-id]');
        if (cardTarget) {
            var cardOpenButton = cardTarget.querySelector('.sb-note__open');
            openFocusPanel(findNote(cardTarget.dataset.noteId), cardOpenButton);
            return;
        }

        var columnToggle = event.target.closest('[data-column-toggle]');
        if (columnToggle) {
            toggleMobileColumn(columnToggle.closest('[data-column]'));
            return;
        }

        var tool = event.target.closest('[data-tool]');
        if (tool) {
            handleTool(tool);
            return;
        }

        var close = event.target.closest('[data-close-dialog]');
        if (close) {
            closeDialog(close.closest('dialog'));
            return;
        }

        if (event.target.closest('[data-open-share]')) {
            renderCollaborators();
            openDialog(shareDialog, event.target.closest('[data-open-share]'));
            return;
        }

        if (event.target.closest('[data-open-stats]')) {
            updateStats();
            openDialog(statsDialog, event.target.closest('[data-open-stats]'));
            return;
        }

        if (event.target.closest('[data-zoom-out]')) { updateZoom(zoom - 10); return; }
        if (event.target.closest('[data-zoom-in]')) { updateZoom(zoom + 10); return; }

        var copy = event.target.closest('[data-copy-board-link]');
        if (copy) { copyBoardLink(copy); }
    });

    root.addEventListener('dragstart', dragStart);
    root.addEventListener('dragover', dragOver);
    root.addEventListener('drop', dropNote);
    root.addEventListener('dragend', cancelDrag);
    root.addEventListener('pointerdown', pointerDragStart);
    root.addEventListener('pointermove', pointerDragMove);
    root.addEventListener('pointerup', pointerDragEnd);
    root.addEventListener('pointercancel', pointerDragCancel);

    [noteDialog, statsDialog, shareDialog].forEach(function (dialog) {
        if (!dialog) { return; }
        dialog.addEventListener('click', function (event) {
            var openedAt = Number(dialog.dataset.openedAt || 0);
            if (event.target === dialog && Date.now() - openedAt > 250) {
                closeDialog(dialog);
            }
        });
        dialog.addEventListener('close', function () {
            if (lastDialogTrigger && typeof lastDialogTrigger.focus === 'function') {
                lastDialogTrigger.focus();
            }
        });
    });

    noteForm.addEventListener('submit', submitNote);
    if (captureForm) { captureForm.addEventListener('submit', reviewCapture); }
    document.getElementById('sb-note-star').addEventListener('click', function (event) {
        var pressed = event.currentTarget.getAttribute('aria-pressed') === 'true';
        event.currentTarget.setAttribute('aria-pressed', String(!pressed));
    });
    document.getElementById('sb-delete-note').addEventListener('click', deleteCurrentNote);
    document.querySelector('[data-add-checklist]').addEventListener('click', function () {
        var container = document.getElementById('sb-checklist-items');
        var empty = container.querySelector('.sb-checklist__empty');
        if (empty) { empty.remove(); }
        var row = createChecklistRow({ text: '', completed: false });
        container.appendChild(row);
        var count = noteDialog.querySelector('[data-checklist-count]');
        if (count) { count.textContent = String(container.querySelectorAll('.sb-checklist__row').length); }
        row.querySelector('input[type="text"]').focus();
    });
    document.querySelector('[data-add-comment]').addEventListener('click', addComment);
    document.getElementById('sb-comment-input').addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && !event.isComposing) {
            event.preventDefault();
            addComment();
        }
    });
    document.getElementById('sb-note-attachment').addEventListener('change', function (event) {
        var file = event.target.files && event.target.files[0];
        updateAttachmentLabel(file ? file.name : existingAttachment || 'Choose a file');
        if (file) {
            announce(file.name + ' is remembered as a local filename reference. The file was not uploaded.');
        }
    });
    document.getElementById('sb-note-tag').addEventListener('input', function (event) {
        var style = TAG_STYLES[event.target.value.trim().toLowerCase()];
        var radio = style && noteForm.querySelector('input[name="tagStyle"][value="' + style + '"]');
        if (radio) { radio.checked = true; }
    });
    document.getElementById('sb-invite-form').addEventListener('submit', addCollaborator);

    document.addEventListener('keydown', function (event) {
        var active = document.activeElement;
        var typing = active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName);
        var dialogOpen = root.querySelector('dialog[open]');

        if (active === captureTranscript && (event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            reviewCapture(event);
            return;
        }

        if (active && active.classList && active.classList.contains('sb-note__open')
                && event.altKey && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')) {
            var card = active.closest('.sb-note[data-note-id]');
            var note = card ? findNote(card.dataset.noteId) : null;
            if (note) {
                event.preventDefault();
                var currentIndex = SECTION_ORDER.indexOf(note.section);
                var direction = event.key === 'ArrowRight' ? 1 : -1;
                var nextIndex = Math.max(0, Math.min(SECTION_ORDER.length - 1, currentIndex + direction));
                if (nextIndex !== currentIndex) {
                    pushHistory('keyboard section move');
                    note.section = SECTION_ORDER[nextIndex];
                    saveState();
                    renderBoard();
                    var movedControl = findCardControl(note.id, '.sb-note__open');
                    if (movedControl) { movedControl.focus(); }
                    announce('Moved ' + note.title + ' to ' + SECTION_LABELS[note.section] + '.');
                    syncNoteToApi(note);
                }
            }
            return;
        }

        if (event.key === 'Escape' && captureLayer && !captureLayer.hidden) {
            event.preventDefault();
            closeCaptureLayer(true);
            return;
        }
        if (event.key === 'Escape' && proposalPanel && !proposalPanel.hidden) {
            event.preventDefault();
            closeProposalPanel(true);
            return;
        }
        if (event.key === 'Escape' && focusPanel && !focusPanel.hidden) {
            event.preventDefault();
            closeFocusPanel(true);
            return;
        }

        if (!typing && !dialogOpen && event.key.toLowerCase() === 'n') {
            event.preventDefault();
            openEditor(null, 'short', root.querySelector('[data-add-note]'), false);
        }
    });

    if (typeof mobileQuery.addEventListener === 'function') {
        mobileQuery.addEventListener('change', applyResponsiveColumns);
    } else if (typeof mobileQuery.addListener === 'function') {
        mobileQuery.addListener(applyResponsiveColumns);
    }

    renderBoard();
    renderCollaborators();
    applyResponsiveColumns();
    updateZoom(100, true);
    setBoardView(state.view, null, true);
    setActiveTool('select');
    saveState();
    loadRemoteNotes();
})();
