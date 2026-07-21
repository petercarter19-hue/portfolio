(function () {
    'use strict';

    var root = document.querySelector('[data-interview-studio]');
    if (!root) return;

    function one(selector, scope) { return (scope || root).querySelector(selector); }
    function all(selector, scope) { return Array.prototype.slice.call((scope || root).querySelectorAll(selector)); }
    function setHidden(element, hidden) { if (element) element.hidden = Boolean(hidden); }
    function text(element, value) { if (element) element.textContent = value == null ? '' : String(value); }

    var profileSlug = root.getAttribute('data-profile-slug') || 'profile';
    var studioUrl = root.getAttribute('data-studio-url') || '/interview-studio';
    var live = one('[data-is-live]');
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var storagePrefix = 'peerslate:interview-studio:' + profileSlug + ':v1';
    var historyKey = storagePrefix + ':history';
    var sessionKey = storagePrefix + ':session';
    var goalKey = storagePrefix + ':goal';
    var writtenPracticeEnabled = root.getAttribute('data-written-practice') === 'enabled';
    var modelAnswersEnabled = root.getAttribute('data-model-answers') === 'enabled';
    var videoCapability = root.getAttribute('data-video-capability') || 'disabled';
    var historyCapability = root.getAttribute('data-history-capability') || 'disabled';

    function modeIsEnabled(mode) {
        if (mode === 'me') return writtenPracticeEnabled;
        if (mode === 'ai') return modelAnswersEnabled;
        if (mode === 'video') return videoCapability !== 'disabled';
        return false;
    }

    function announce(message) {
        text(live, '');
        window.setTimeout(function () { text(live, message); }, 20);
    }

    function readJSON(key, fallback) {
        try {
            var value = window.localStorage.getItem(key);
            return value ? JSON.parse(value) : fallback;
        } catch (error) {
            return fallback;
        }
    }

    function writeJSON(key, value) {
        try {
            window.localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            return false;
        }
    }

    function removeStored(key) {
        try { window.localStorage.removeItem(key); } catch (error) { /* storage unavailable */ }
    }

    function storageAvailable() {
        try {
            var probeKey = storagePrefix + ':probe';
            window.localStorage.setItem(probeKey, '1');
            window.localStorage.removeItem(probeKey);
            return true;
        } catch (error) {
            return false;
        }
    }

    function draftKey(question) {
        var compact = String(question || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 96);
        return storagePrefix + ':draft:' + compact;
    }

    var evidence = [];
    try {
        evidence = JSON.parse(one('#is-evidence-data', document).textContent || '[]');
    } catch (error) {
        evidence = [];
    }
    var evidenceById = {};
    evidence.forEach(function (item) { evidenceById[item.id] = item; });

    var questions = all('#is-question-bank .iq-item', document).map(function (item) {
        var legacyMode = item.getAttribute('data-mode');
        return {
            text: item.textContent.trim(),
            family: item.getAttribute('data-family') || (legacyMode === 'behavioral' ? 'situational' : 'behavioral'),
            competency: item.getAttribute('data-competency') || item.getAttribute('data-topic') || 'Communication',
            custom: false
        };
    });

    var defaultQuestionText = 'Tell me about a time you disagreed with a supervisor.';
    var defaultQuestion = questions.filter(function (item) { return item.text === defaultQuestionText; })[0] || questions[0] || {
        text: defaultQuestionText,
        family: 'behavioral',
        competency: 'Conflict',
        custom: false
    };

    var intentByCompetency = {
        Conflict: 'Professional disagreement, sound judgment, and a constructive outcome.',
        Leadership: 'Clear ownership, thoughtful decisions, and how others moved with you.',
        Communication: 'Audience awareness, clarity, influence, and a result.',
        Teamwork: 'Collaboration, self-awareness, and a shared outcome.',
        Decisions: 'A sound decision process, tradeoffs, and accountable follow-through.',
        Adaptability: 'How you assessed change, adjusted your approach, and protected the outcome.',
        Initiative: 'What you noticed, what you personally did, and the value created.',
        Pressure: 'Prioritization, calm execution, and responsible communication.',
        Learning: 'Self-awareness, a deliberate learning approach, and applied growth.',
        Accountability: 'Ownership, transparency, corrective action, and prevention.',
        Failure: 'Honest reflection, responsibility, learning, and changed behavior.'
    };

    var tipByCompetency = {
        Conflict: 'For conflict questions, explain the disagreement, how you handled it professionally, and the outcome.',
        Leadership: 'Name the decision you owned, how you brought people with you, and what changed.',
        Communication: 'Clarify the audience, the message you adapted, and how you knew it landed.',
        Teamwork: 'Show what you contributed personally while keeping the team outcome visible.',
        Decisions: 'Explain the options, evidence, tradeoffs, and why your final choice was reasonable.',
        Adaptability: 'Describe what changed, how you adjusted, and what stayed protected.',
        Initiative: 'Make the gap, your action, and the measurable result easy to distinguish.',
        Pressure: 'Keep the answer focused on priorities, communication, and the result—not the stress itself.',
        Learning: 'Connect what you learned to a specific change in how you work.',
        Accountability: 'Own the issue directly, then show the fix and how you prevented a repeat.',
        Failure: 'Spend less time defending the miss and more time on learning and changed behavior.'
    };

    function labelFamily(value) {
        return value ? value.charAt(0).toUpperCase() + value.slice(1) : 'Behavioral';
    }

    function cloneQuestion(item) {
        return {
            text: item.text,
            family: item.family,
            competency: item.competency,
            custom: Boolean(item.custom)
        };
    }

    function buildQueue(family, length) {
        var source = questions.filter(function (item) {
            return family === 'mixed' || item.family === family;
        });
        if (!source.length) source = questions.slice();

        var ordered = [];
        if (family === 'mixed') {
            var behavioral = source.filter(function (item) { return item.family === 'behavioral'; });
            var situational = source.filter(function (item) { return item.family === 'situational'; });
            var firstBehavioral = behavioral.filter(function (item) { return item.text === defaultQuestion.text; })[0] || behavioral[0];
            if (firstBehavioral) ordered.push(cloneQuestion(firstBehavioral));
            behavioral = behavioral.filter(function (item) { return !firstBehavioral || item.text !== firstBehavioral.text; });
            var pairCount = Math.max(behavioral.length, situational.length);
            for (var pairIndex = 0; pairIndex < pairCount; pairIndex += 1) {
                if (situational[pairIndex]) ordered.push(cloneQuestion(situational[pairIndex]));
                if (behavioral[pairIndex]) ordered.push(cloneQuestion(behavioral[pairIndex]));
            }
            return ordered.slice(0, Math.max(1, length));
        }
        if (family !== 'situational' && source.some(function (item) { return item.text === defaultQuestion.text; })) {
            ordered.push(cloneQuestion(defaultQuestion));
        }
        source.forEach(function (item) {
            if (!ordered.some(function (existing) { return existing.text === item.text; })) ordered.push(cloneQuestion(item));
        });
        return ordered.slice(0, Math.max(1, length));
    }

    var initialMode = root.getAttribute('data-initial-mode') || 'me';
    var initialView = root.getAttribute('data-initial-view') || 'me';
    function currentModeParam() { return new URLSearchParams(window.location.search).get('mode'); }
    var isOrientation = initialView !== 'history' && !currentModeParam();
    var persistedSession = readJSON(sessionKey, null);
    var session = {
        mode: isOrientation ? 'orientation' : initialMode,
        level: 'experienced',
        family: 'behavioral',
        format: '5',
        queue: [],
        index: 0,
        attemptNumber: 1,
        currentReview: null,
        currentAnswer: '',
        reviewSource: 'me',
        reviewRecordId: '',
        aiReference: '',
        aiReferenceQuestion: ''
    };

    if (persistedSession && Array.isArray(persistedSession.queue) && persistedSession.queue.length) {
        session.level = persistedSession.level || session.level;
        session.family = persistedSession.family || session.family;
        session.format = persistedSession.format || session.format;
        session.queue = persistedSession.queue.map(cloneQuestion);
        session.index = Math.min(Math.max(Number(persistedSession.index) || 0, 0), session.queue.length - 1);
    } else {
        session.queue = buildQueue(session.family, 5);
    }

    function persistSession() {
        writeJSON(sessionKey, {
            level: session.level,
            family: session.family,
            format: session.format,
            queue: session.queue,
            index: session.index
        });
        updateSetupSummary();
    }

    function updateSetupSummary() {
        var summary = one('[data-is-setup-summary]');
        if (!summary) return;
        var levelOption = levelSelect.options[levelSelect.selectedIndex];
        var levelLabel = levelOption ? levelOption.text : session.level;
        var formatLabelText = session.format === 'single' ? 'Single question' : session.format === '10' ? '10-question mock' : '5-question mock';
        summary.textContent = 'Session setup · ' + levelLabel + ' · ' + labelFamily(session.family) + ' · ' + formatLabelText;
    }

    function currentQuestion() {
        return session.queue[session.index] || defaultQuestion;
    }

    var modeTabs = all('[data-is-mode]');
    var modeNavigation = one('.is__modes');
    var historyLink = one('[data-is-history-link]');
    var panels = all('[data-is-panel]');
    var orientationPanel = one('[data-is-panel="orientation"]');
    var controls = one('[data-is-controls]');
    var stageRailItems = all('[data-is-stage-rail] li');

    function setStage(stage) {
        stageRailItems.forEach(function (item) {
            var n = Number(item.getAttribute('data-is-stage'));
            var current = n === stage;
            item.classList.toggle('is-done', n < stage);
            item.classList.toggle('is-current', current);
            // Exactly one step carries aria-current at any time, kept in
            // sync with the visual current state.
            if (current) {
                item.setAttribute('aria-current', 'step');
            } else {
                item.removeAttribute('aria-current');
            }
        });
        setCoachingStatus(stage);
    }

    var coachingRows = all('[data-is-coaching-row]');
    function setCoachingStatus(stage) {
        coachingRows.forEach(function (row) {
            var n = Number(row.getAttribute('data-is-coaching-row'));
            var done = stage >= 3 || (stage === 2 && n === 1);
            var current = stage === 2 && n === 2;
            row.classList.toggle('is-done', done);
            row.classList.toggle('is-current', current);
            var dot = row.querySelector('.is__status-dot');
            if (dot) dot.textContent = done ? '✓' : String(n);
        });
    }
    var formatControl = one('[data-is-format-control]');
    var formatSelect = one('[data-is-format]');
    var formatLabel = formatControl ? formatControl.querySelector('span') : null;
    var formatOptions = formatSelect ? formatSelect.innerHTML : '';

    var answer = one('[data-is-answer]');
    var answerForm = one('[data-is-answer-form]');
    var reviewButton = one('[data-is-review]');
    var autosave = one('[data-is-autosave]');
    var wordCount = one('[data-is-word-count]');
    var answeringBlock = one('[data-is-answering]');
    var reviewingBlock = one('[data-is-reviewing]');
    var submittedBlock = one('[data-is-submitted]');
    var feedbackBlock = one('[data-is-feedback]');
    var feedbackEmpty = one('[data-is-feedback-empty]');
    var feedbackContent = one('[data-is-feedback-content]');
    var improveBlock = one('[data-is-improve-panel]');
    var improveEmpty = one('[data-is-improve-empty]');
    var improveContent = one('[data-is-improve-content]');
    var reviewError = one('[data-is-review-error]');
    var reviewErrorText = one('[data-is-review-error-text]');
    var errorActions = one('[data-is-error-actions]');
    var retryCoachingButton = one('[data-is-retry-coaching]');
    var keepEditingButton = one('[data-is-keep-editing]');
    var submittedLabel = one('[data-is-submitted-label]');
    var improveError = one('[data-is-improve-error]');
    var reviewController = null;
    var reviewRequestId = 0;
    var improveController = null;
    var improveRequestId = 0;
    var autosaveTimer = null;

    function cancelPendingReview() {
        reviewRequestId += 1;
        if (reviewController) reviewController.abort();
        reviewController = null;
    }

    function cancelPendingImprovement() {
        improveRequestId += 1;
        if (improveController) improveController.abort();
        improveController = null;
    }

    function syncModeControls(mode) {
        if (!formatControl || !formatSelect || !formatLabel) return;
        if (mode === 'ai') {
            // Public demo: the basis is the named public profile's approved
            // résumé history, never the visitor's own or any account data.
            formatLabel.textContent = 'Answer basis';
            formatSelect.replaceChildren(new Option('Approved public résumé history', 'public-profile-history'));
            formatSelect.disabled = true;
        } else {
            if (formatLabel.textContent !== 'Session') {
                formatLabel.textContent = 'Session';
                formatSelect.innerHTML = formatOptions;
                formatSelect.value = session.format;
                formatSelect.disabled = false;
            }
        }
    }

    function releaseMedia(discardRecording, preservePermissionRequest) {
        if (!preservePermissionRequest && media) media.permissionRequestId += 1;
        var recorder = media.recorder;
        if (recorder && discardRecording) {
            recorder.onstop = function () {
                media.chunks = [];
                if (media.recorder === recorder) media.recorder = null;
            };
        }
        if (recorder && recorder.state !== 'inactive') {
            recorder.stop();
        }
        if (media.stream) {
            media.stream.getTracks().forEach(function (track) { track.stop(); });
            media.stream = null;
        }
    }

    function setMode(mode, updateUrl) {
        if (['me', 'ai', 'video'].indexOf(mode) === -1) mode = 'me';
        if (!modeIsEnabled(mode)) {
            announce('That Interview Studio mode is not available for this profile.');
            return false;
        }
        if (session.mode === 'video' && mode !== 'video') {
            if (!prepareVideoContextChange('Discard the active recording or transcript draft and leave Video Practice?')) return false;
            releaseMedia(true);
            resetVideoUi();
        }
        if (session.mode === 'me' && mode !== 'me') clearReviewState();
        if (session.mode === 'ai' && mode !== 'ai') cancelPendingAi(true);
        session.mode = mode;
        isOrientation = false;
        if (modeNavigation) modeNavigation.setAttribute('role', 'tablist');
        modeTabs.forEach(function (tab) {
            var tabMode = tab.getAttribute('data-is-mode');
            var enabled = modeIsEnabled(tabMode);
            var active = tabMode === mode;
            tab.setAttribute('role', 'tab');
            tab.setAttribute('aria-controls', 'is-panel-' + tabMode);
            tab.setAttribute('aria-disabled', enabled ? 'false' : 'true');
            tab.setAttribute('aria-selected', active ? 'true' : 'false');
            tab.tabIndex = enabled && active ? 0 : -1;
        });
        panels.forEach(function (panel) { panel.hidden = panel.getAttribute('data-is-panel') !== mode; });
        setHidden(controls, false);
        if (historyLink) historyLink.removeAttribute('aria-current');
        syncModeControls(mode);
        if (updateUrl) window.history.pushState({ interviewMode: mode }, '', studioUrl + '?mode=' + encodeURIComponent(mode));
        announce(mode === 'ai' ? 'Interview AI selected.' : mode === 'video' ? 'Video Practice selected.' : 'Interview Me selected.');
        return true;
    }

    modeTabs.forEach(function (tab) {
        tab.addEventListener('click', function (event) {
            event.preventDefault();
            setMode(tab.getAttribute('data-is-mode'), true);
        });
        tab.addEventListener('keydown', function (event) {
            if (!modeNavigation || modeNavigation.getAttribute('role') !== 'tablist') return;
            var delta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
            if (!delta) return;
            event.preventDefault();
            var enabledTabs = modeTabs.filter(function (candidate) {
                return modeIsEnabled(candidate.getAttribute('data-is-mode'));
            });
            var index = enabledTabs.indexOf(tab);
            var target = enabledTabs[(index + delta + enabledTabs.length) % enabledTabs.length];
            if (target && setMode(target.getAttribute('data-is-mode'), true)) target.focus();
        });
    });

    if (historyLink) {
        historyLink.addEventListener('click', function (event) {
            if (historyCapability === 'disabled') {
                event.preventDefault();
                announce('Interview History is not available for this profile.');
                return;
            }
            if (session.mode === 'video' && !prepareVideoContextChange('Discard the active recording or transcript draft and open History?')) {
                event.preventDefault();
            }
        });
    }

    function showHistoryView() {
        if (historyCapability === 'disabled') return false;
        if (session.mode === 'video' && !prepareVideoContextChange('Discard the active recording or transcript draft and return to History?')) {
            return false;
        }
        clearReviewState();
        cancelPendingAi(true);
        if (session.mode === 'video') {
            releaseMedia(true);
            resetVideoUi();
        }
        isOrientation = false;
        panels.forEach(function (panel) { panel.hidden = panel.getAttribute('data-is-panel') !== 'history'; });
        setHidden(controls, true);
        if (modeNavigation) modeNavigation.removeAttribute('role');
        modeTabs.forEach(function (tab) {
            tab.removeAttribute('role');
            tab.removeAttribute('aria-controls');
            tab.removeAttribute('aria-selected');
            tab.removeAttribute('tabindex');
        });
        if (historyLink) historyLink.setAttribute('aria-current', 'page');
        restoreHistoryFilters();
        announce('Interview History selected.');
        return true;
    }

    function showOrientationView() {
        if (!orientationPanel) return false;
        clearReviewState();
        cancelPendingAi(true);
        if (session.mode === 'video') {
            releaseMedia(true);
            resetVideoUi();
        }
        panels.forEach(function (panel) { panel.hidden = panel.getAttribute('data-is-panel') !== 'orientation'; });
        setHidden(controls, true);
        if (modeNavigation) modeNavigation.removeAttribute('role');
        modeTabs.forEach(function (tab) {
            tab.removeAttribute('role');
            tab.removeAttribute('aria-controls');
            tab.removeAttribute('aria-selected');
            tab.removeAttribute('tabindex');
        });
        if (historyLink) historyLink.removeAttribute('aria-current');
        session.mode = 'orientation';
        isOrientation = true;
        announce('Interview Studio orientation selected.');
        return true;
    }

    all('[data-is-orientation-link]').forEach(function (link) {
        link.addEventListener('click', function (event) {
            var target = link.getAttribute('data-is-orientation-link');
            if (link.getAttribute('aria-disabled') === 'true') {
                event.preventDefault();
                announce('That Interview Studio mode is not available for this profile.');
                return;
            }
            if (target === 'history') {
                if (historyCapability === 'disabled') {
                    event.preventDefault();
                    announce('Interview History is not available for this profile.');
                }
                return;
            }
            event.preventDefault();
            setMode(target, true);
        });
    });

    window.addEventListener('popstate', function () {
        if (window.location.pathname.indexOf('/history') !== -1) {
            if (!showHistoryView()) window.history.forward();
            return;
        }
        if (!currentModeParam()) {
            if (!showOrientationView()) window.history.forward();
            return;
        }
        isOrientation = false;
        var mode = currentModeParam() || 'me';
        if (!setMode(mode, false)) {
            var fallback = modeTabs.filter(function (tab) {
                return modeIsEnabled(tab.getAttribute('data-is-mode'));
            })[0];
            if (fallback) {
                var fallbackMode = fallback.getAttribute('data-is-mode');
                if (setMode(fallbackMode, false)) {
                    window.history.replaceState({}, '', fallbackMode === 'me' ? studioUrl : studioUrl + '?mode=' + encodeURIComponent(fallbackMode));
                }
            }
        }
    });

    function clearReviewState() {
        cancelPendingReview();
        cancelPendingImprovement();
        session.currentReview = null;
        session.currentAnswer = '';
        session.reviewSource = 'me';
        session.reviewRecordId = '';
        session.attemptNumber = 1;
        setHidden(answeringBlock, false);
        answer.readOnly = false;
        answeringBlock.removeAttribute('aria-busy');
        setHidden(reviewingBlock, true);
        setHidden(submittedBlock, true);
        setHidden(feedbackBlock, false);
        setHidden(feedbackEmpty, false);
        setHidden(feedbackContent, true);
        setHidden(improveBlock, false);
        setHidden(improveEmpty, false);
        setHidden(improveContent, true);
        setHidden(reviewError, true);
        setHidden(errorActions, true);
        text(submittedLabel, 'Your submitted answer · preserved');
        setHidden(improveError, true);
        setStage(1);
        syncAnswerState();
    }

    function restoreDraft() {
        var stored = readJSON(draftKey(currentQuestion().text), null);
        answer.value = stored && typeof stored.text === 'string' ? stored.text : '';
        syncAnswerState();
        text(autosave, answer.value ? 'Restored from this browser' : 'Draft ready');
    }

    function renderQuestion(options) {
        options = options || {};
        var question = currentQuestion();
        var total = session.queue.length || 1;
        var number = session.index + 1;
        var percent = Math.round((number / total) * 100);
        text(one('[data-is-question]'), question.text);
        text(one('[data-is-family-chip]'), labelFamily(question.family));
        text(one('[data-is-competency-chip]'), 'Competency: ' + question.competency);
        text(one('[data-is-intent]'), intentByCompetency[question.competency] || 'A clear example, your personal contribution, and an outcome.');
        text(one('[data-is-tip]'), tipByCompetency[question.competency] || 'Keep the context concise, make your action specific, and close with the result.');
        text(one('[data-is-question-position]'), 'Question ' + number + ' of ' + total);
        text(one('[data-is-progress-percent]'), percent + '%');
        text(one('[data-is-up-next-count]'), Math.max(0, total - number));
        setHidden(one('[data-is-est-chip]'), total < 5);
        var progress = one('[data-is-progress]');
        if (progress) { progress.value = percent; progress.textContent = percent + '%'; }
        text(one('[data-is-video-question]'), question.text);
        text(one('[data-is-video-family]'), labelFamily(question.family));
        text(one('[data-is-video-competency]'), 'Competency: ' + question.competency);
        text(one('[data-is-video-question-position]'), 'Question ' + number + ' of ' + total);
        text(one('[data-is-video-progress-percent]'), percent + '%');
        var videoProgress = one('[data-is-video-progress]');
        if (videoProgress) { videoProgress.value = percent; videoProgress.textContent = percent + '%'; }
        var reference = one('[data-is-ai-reference]');
        var showReference = one('[data-is-show-reference]');
        var referenceMatches = Boolean(session.aiReference && session.aiReferenceQuestion === question.text);
        text(one('[data-is-ai-reference-text]'), referenceMatches ? session.aiReference : '');
        setHidden(reference, !referenceMatches || Boolean(showReference && !showReference.checked));
        clearReviewState();
        if (!options.keepDraft) restoreDraft();
        persistSession();
        renderQueue();
    }

    function syncAnswerState() {
        var value = answer.value.trim();
        var words = value ? value.split(/\s+/).length : 0;
        text(wordCount, words);
        reviewButton.disabled = !writtenPracticeEnabled || !value || Boolean(reviewController);
        if (retryCoachingButton) retryCoachingButton.disabled = Boolean(reviewController);
    }

    function saveDraft(showStatus) {
        if (showStatus) text(autosave, 'Saving…');
        var ok = writeJSON(draftKey(currentQuestion().text), {
            text: answer.value,
            savedAt: new Date().toISOString()
        });
        text(autosave, ok ? 'Saved in this browser' : 'Save failed — your text is still here');
        return ok;
    }

    answer.addEventListener('input', function () {
        syncAnswerState();
        text(autosave, 'Saving…');
        window.clearTimeout(autosaveTimer);
        autosaveTimer = window.setTimeout(function () { saveDraft(false); }, 700);
    });
    answer.addEventListener('blur', function () { if (answer.value) saveDraft(false); });

    function hasDraft() { return answer.value.trim().length > 0; }
    function confirmReplace() {
        var enabled = one('[data-is-confirm-navigation]');
        return !hasDraft() || !enabled || !enabled.checked || window.confirm('Move to another question? This draft will stay saved in this browser.');
    }

    function prepareVideoContextChange(message) {
        if (session.mode !== 'video') return true;
        var transcriptDraft = videoTranscript && videoTranscript.value.trim();
        var pendingRecording = Boolean(media.recorder && !media.playbackUrl);
        var hasCompletedPlayback = Boolean(media.playbackUrl);
        if ((pendingRecording || transcriptDraft) && !window.confirm(message || 'Discard this recording or transcript draft and change the session?')) return false;
        if (pendingRecording || hasCompletedPlayback || transcriptDraft) {
            releaseMedia(true);
            resetVideoUi();
        }
        return true;
    }

    function advanceQuestion(mode) {
        if (session.index < session.queue.length - 1) {
            session.index += 1;
        } else {
            session.index = 0;
            session.queue = buildQueue(session.family, Number(session.format) || 1);
        }
        renderQuestion();
        if (mode === 'video') {
            one('[data-is-video-stage]').scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
            one('[data-is-camera-enable]').focus();
        } else {
            one('[data-is-practice-stage]').scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
            answer.focus();
        }
    }

    one('[data-is-new-question]').addEventListener('click', function () { if (confirmReplace()) advanceQuestion(); });
    one('[data-is-next-question]').addEventListener('click', function () {
        var source = session.reviewSource;
        if (source === 'video') {
            if (!setMode('video', true)) return;
            resetVideoUi();
            advanceQuestion('video');
            return;
        }
        advanceQuestion();
    });
    one('[data-is-video-new-question]').addEventListener('click', function () {
        if (!prepareVideoContextChange('Discard the active recording or transcript draft and load another question?')) return;
        releaseMedia(true);
        resetVideoUi();
        advanceQuestion('video');
    });

    var levelSelect = one('[data-is-level]');
    var familySelect = one('[data-is-family]');
    levelSelect.value = session.level;
    familySelect.value = session.family;
    formatSelect.value = session.format;

    levelSelect.addEventListener('change', function () {
        if (!prepareVideoContextChange('Discard this recording and change experience level?')) {
            levelSelect.value = session.level;
            return;
        }
        clearReviewState();
        resetAiAnswerForContextChange();
        session.level = levelSelect.value;
        persistSession();
    });
    familySelect.addEventListener('change', function () {
        if (!prepareVideoContextChange('Discard this recording and change question family?') || (session.mode === 'me' && !confirmReplace())) {
            familySelect.value = session.family;
            return;
        }
        resetAiAnswerForContextChange();
        session.family = familySelect.value;
        session.index = 0;
        session.queue = buildQueue(session.family, Number(session.format) || 1);
        renderQuestion();
    });
    formatSelect.addEventListener('change', function () {
        if (session.mode === 'ai') return;
        if (!prepareVideoContextChange('Discard this recording and change session length?') || (session.mode === 'me' && !confirmReplace())) {
            formatSelect.value = session.format;
            return;
        }
        session.format = formatSelect.value;
        session.index = 0;
        session.queue = buildQueue(session.family, Number(session.format) || 1);
        renderQuestion();
    });

    /* Question queue */
    var queueDialog = one('[data-is-queue]');
    var queueList = one('[data-is-queue-list]');

    function renderQueue() {
        if (!queueList) return;
        queueList.replaceChildren();
        session.queue.forEach(function (question, index) {
            var item = document.createElement('li');
            item.className = 'is__queue-item' + (index === session.index ? ' is-current' : '');
            var button = document.createElement('button');
            button.type = 'button';
            if (index === session.index) button.setAttribute('aria-current', 'true');
            var number = document.createElement('i');
            number.textContent = String(index + 1);
            var label = document.createElement('strong');
            label.textContent = question.text;
            var competency = document.createElement('span');
            competency.textContent = 'Competency: ' + question.competency;
            button.append(number, label, competency);
            button.addEventListener('click', function () {
                if (index === session.index) { queueDialog.close(); return; }
                if (!confirmReplace()) return;
                session.index = index;
                renderQuestion();
                queueDialog.close();
                answer.focus();
            });
            item.appendChild(button);
            queueList.appendChild(item);
        });
    }

    one('[data-is-queue-open]').addEventListener('click', function () {
        renderQueue();
        if (typeof queueDialog.showModal === 'function') queueDialog.showModal();
        else queueDialog.setAttribute('open', '');
    });
    one('[data-is-queue-close]').addEventListener('click', function () { queueDialog.close(); });
    queueDialog.addEventListener('click', function (event) {
        if (event.target === queueDialog) queueDialog.close();
    });

    one('[data-is-custom-question-form]').addEventListener('submit', function (event) {
        event.preventDefault();
        var input = one('[data-is-custom-question]');
        var value = input.value.trim();
        if (!value) return;
        session.queue.push({ text: value, family: session.family === 'mixed' ? 'behavioral' : session.family, competency: 'Custom', custom: true });
        input.value = '';
        persistSession();
        renderQueue();
        text(one('[data-is-up-next-count]'), Math.max(0, session.queue.length - session.index - 1));
        announce('Custom question added to this session.');
    });

    /* Review, feedback, retry, and improvement */
    function postJSON(url, body, signal) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify(body),
            signal: signal
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (payload) {
                if (!response.ok) throw new Error(payload.error || 'That request did not complete.');
                return payload;
            });
        });
    }

    function addHistoryRecord(record) {
        var records = readJSON(historyKey, []);
        records.unshift(record);
        writeJSON(historyKey, records.slice(0, 100));
    }

    function updateHistoryRecord(recordId, updates) {
        var found = false;
        var records = readJSON(historyKey, []).map(function (record) {
            if (record.id !== recordId) return record;
            found = true;
            return Object.assign({}, record, updates, { createdAt: record.createdAt });
        });
        if (found) writeJSON(historyKey, records);
        return found;
    }

    function removeHistoryRecord(recordId) {
        if (!recordId) return;
        var records = readJSON(historyKey, []).filter(function (record) { return record.id !== recordId; });
        writeJSON(historyKey, records);
    }

    // A review list can legitimately be empty: the coach sets a maximum of four
    // bullets, never a minimum, so a genuinely weak answer can return zero
    // strengths. When a caller supplies emptyMessage the absence is stated
    // plainly instead of leaving a heading above an empty box.
    function renderList(element, items, emptyMessage) {
        element.replaceChildren();
        var list = items || [];
        if (!list.length) {
            if (emptyMessage) {
                var empty = document.createElement('li');
                empty.className = 'is__bullets-empty';
                empty.textContent = emptyMessage;
                element.appendChild(empty);
            }
            return;
        }
        list.forEach(function (item) {
            var li = document.createElement('li');
            li.textContent = item;
            element.appendChild(li);
        });
    }

    // ---------------------------------------------------------------------
    // SINGLE EDIT POINT for the empty-strengths wording.
    //
    // A review may legitimately carry zero strengths (owner decision,
    // 2026-07-20), and this is the one line the reader sees when that happens.
    // Pete is still choosing the final wording, so change ONLY this string --
    // every place that needs it references this constant.
    //
    // Improvements are now server-required and can never be empty in a rendered
    // review, so EMPTY_IMPROVEMENTS_MESSAGE is a defensive fallback for
    // browser-local history records only (localStorage is not server-validated).
    // ---------------------------------------------------------------------
    var EMPTY_STRENGTHS_MESSAGE = 'No clear strength stood out yet — start with the improvements.';
    var EMPTY_IMPROVEMENTS_MESSAGE = 'The coach did not list an improvement for this answer.';

    function renderReview(review) {
        session.currentReview = review;
        var score = Number(review.overallScore) || 0;
        text(one('[data-is-score]'), score);
        var ring = one('[data-is-score-ring]');
        ring.style.setProperty('--score', score);
        ring.setAttribute('aria-label', 'Overall interview score: ' + score + ' out of 100');
        text(one('[data-is-verdict]'), review.verdict);
        text(one('[data-is-encouragement]'), review.encouragement);
        renderList(one('[data-is-strengths]'), review.strengths, EMPTY_STRENGTHS_MESSAGE);
        renderList(one('[data-is-improvements]'), review.improvements, EMPTY_IMPROVEMENTS_MESSAGE);

        var starList = one('[data-is-star]');
        var starDisplayStatus = { strong: 'strong', present: 'clear', partial: 'needs more', missing: 'missing' };
        starList.replaceChildren();
        ['situation', 'task', 'action', 'result'].forEach(function (part) {
            var item = review.star[part];
            var partLabel = part.charAt(0).toUpperCase() + part.slice(1);
            var tile = document.createElement('li');
            tile.className = 'is__star-item';
            tile.setAttribute('data-status', item.status);
            tile.title = item.reason;
            var letter = document.createElement('span');
            letter.className = 'is__star-letter';
            letter.setAttribute('aria-hidden', 'true');
            letter.textContent = part.charAt(0).toUpperCase();
            var label = document.createElement('span');
            label.className = 'is__star-label';
            label.setAttribute('aria-hidden', 'true');
            label.textContent = partLabel + ' · ' + (starDisplayStatus[item.status] || item.status);
            var srText = document.createElement('span');
            srText.className = 'is__sr-only';
            srText.textContent = partLabel + ' — ' + item.status.charAt(0).toUpperCase() + item.status.slice(1) + ': ' + item.reason;
            tile.append(letter, label, srText);
            starList.appendChild(tile);
        });

        var dimensions = one('[data-is-dimensions]');
        dimensions.replaceChildren();
        review.dimensions.forEach(function (dimension) {
            var li = document.createElement('li');
            var name = document.createElement('strong');
            name.textContent = dimension.key.charAt(0).toUpperCase() + dimension.key.slice(1);
            var value = document.createElement('span');
            value.textContent = dimension.score + ' / 20';
            var rationale = document.createElement('small');
            rationale.textContent = dimension.rationale;
            li.append(name, value, rationale);
            dimensions.appendChild(li);
        });

        var suggestionSection = one('[data-is-evidence-suggestions]');
        var suggestionOptions = one('[data-is-evidence-options]');
        suggestionOptions.replaceChildren();
        (review.evidenceSuggestions || []).forEach(function (suggestion) {
            var item = evidenceById[suggestion.evidenceId];
            if (!item) return;
            var label = document.createElement('label');
            label.className = 'is__evidence-option';
            label.title = suggestion.opportunity;
            var input = document.createElement('input');
            input.type = 'checkbox';
            input.value = item.id;
            input.setAttribute('data-is-evidence-choice', '');
            var chip = document.createElement('span');
            chip.textContent = item.metric + ' — ' + item.label;
            label.append(input, chip);
            suggestionOptions.appendChild(label);
        });
        suggestionSection.hidden = !suggestionOptions.children.length;
    }

    function submitReview() {
        if (reviewController) return;
        var responseText = answer.value.trim();
        if (!responseText) {
            announce('Type or dictate an answer before submitting it for review.');
            answer.focus();
            return;
        }
        saveDraft(false);
        session.currentAnswer = responseText;
        text(one('[data-is-submitted-text]'), responseText);
        setHidden(answeringBlock, false);
        answer.readOnly = true;
        answeringBlock.setAttribute('aria-busy', 'true');
        reviewButton.disabled = true;
        setHidden(submittedBlock, false);
        setHidden(reviewingBlock, false);
        setHidden(feedbackBlock, false);
        setHidden(feedbackEmpty, false);
        setHidden(feedbackContent, true);
        setHidden(improveBlock, false);
        setHidden(improveEmpty, false);
        setHidden(improveContent, true);
        setHidden(reviewError, true);
        setHidden(errorActions, true);
        text(submittedLabel, 'Your submitted answer · preserved');
        setStage(2);
        cancelPendingReview();
        reviewController = new AbortController();
        var controller = reviewController;
        var requestId = reviewRequestId;
        var reviewSource = session.reviewSource || 'me';
        var reviewRecordId = session.reviewRecordId || '';

        var question = currentQuestion();
        postJSON('/api/interview/review', {
            profile_slug: profileSlug,
            question: question.text,
            answer: responseText,
            level: session.level,
            family: question.family,
            competency: question.competency
        }, controller.signal).then(function (payload) {
            if (requestId !== reviewRequestId) return;
            reviewController = null;
            answer.readOnly = false;
            answeringBlock.removeAttribute('aria-busy');
            syncAnswerState();
            setHidden(reviewingBlock, true);
            setStage(3);
            renderReview(payload.review);
            setHidden(feedbackEmpty, true);
            setHidden(feedbackContent, false);
            var record = {
                id: reviewRecordId || 'attempt-' + Date.now() + '-' + session.attemptNumber,
                createdAt: new Date().toISOString(),
                mode: reviewSource,
                question: question.text,
                family: question.family,
                competency: question.competency,
                score: payload.review.overallScore,
                dimensions: payload.review.dimensions.reduce(function (result, item) { result[item.key] = item.score; return result; }, {}),
                answer: responseText,
                verdict: payload.review.verdict,
                encouragement: payload.review.encouragement,
                strengths: payload.review.strengths,
                improvements: payload.review.improvements,
                star: payload.review.star,
                attemptNumber: session.attemptNumber,
                status: reviewSource === 'video' ? 'Content reviewed' : 'Completed'
            };
            if (!reviewRecordId || !updateHistoryRecord(reviewRecordId, record)) addHistoryRecord(record);
            removeStored(draftKey(question.text));
            announce('Coach review ready. Score ' + payload.review.overallScore + ' out of 100.');
            feedbackBlock.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
        }).catch(function (error) {
            if (requestId !== reviewRequestId) return;
            reviewController = null;
            if (error.name === 'AbortError') return;
            answer.readOnly = false;
            answeringBlock.removeAttribute('aria-busy');
            syncAnswerState();
            setHidden(reviewingBlock, true);
            setHidden(feedbackEmpty, false);
            setHidden(feedbackContent, true);
            text(submittedLabel, 'Your answer · preserved and editable');
            text(reviewErrorText, error.message + ' Your answer is still here. Edit it or retry the coaching request without re-entering your work.');
            setHidden(reviewError, false);
            setHidden(errorActions, false);
            if (reviewError) reviewError.focus();
            announce('The review could not be completed. Your answer is safe.');
        });
    }

    answerForm.addEventListener('submit', function (event) {
        event.preventDefault();
        submitReview();
    });
    answer.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter' || (!event.ctrlKey && !event.metaKey)) return;
        event.preventDefault();
        if (typeof answerForm.requestSubmit === 'function') answerForm.requestSubmit();
        else submitReview();
    });
    one('[data-is-cancel-review]').addEventListener('click', function () {
        cancelPendingReview();
        answer.readOnly = false;
        answeringBlock.removeAttribute('aria-busy');
        syncAnswerState();
        setHidden(reviewingBlock, true);
        setHidden(submittedBlock, true);
        setHidden(answeringBlock, false);
        setStage(1);
        announce('Review cancelled. Your draft is still editable.');
    });

    if (keepEditingButton) {
        keepEditingButton.addEventListener('click', function () {
            answer.readOnly = false;
            answer.focus();
        });
    }

    if (retryCoachingButton) {
        retryCoachingButton.addEventListener('click', function () {
            submitReview();
        });
    }

    one('[data-is-retry]').addEventListener('click', function () {
        if (session.reviewSource === 'video') {
            if (!setMode('video', true)) return;
            resetVideoUi();
            one('[data-is-camera-enable]').focus();
            announce('New Video Practice attempt ready. The original score remains in History.');
            return;
        }
        session.attemptNumber += 1;
        answer.value = '';
        syncAnswerState();
        text(autosave, 'New attempt — original preserved in History');
        setHidden(submittedBlock, true);
        setHidden(feedbackEmpty, false);
        setHidden(feedbackContent, true);
        setHidden(improveEmpty, false);
        setHidden(improveContent, true);
        setHidden(answeringBlock, false);
        setStage(1);
        answer.focus();
        announce('New attempt started. Your original answer and score remain in History.');
    });

    one('[data-is-improve]').addEventListener('click', function () {
        if (!session.currentReview || !session.currentAnswer) return;
        setStage(4);
        var selectedIds = all('[data-is-evidence-choice]:checked').map(function (item) { return item.value; });
        setHidden(improveEmpty, true);
        setHidden(improveContent, false);
        setHidden(improveError, true);
        text(one('[data-is-original-answer]'), session.currentAnswer);
        var draft = one('[data-is-improved-draft]');
        var useDraftButton = one('[data-is-use-draft]');
        var retryOutLoudButton = one('[data-is-retry-out-loud]');
        draft.value = 'The coach is preparing an editable draft…';
        draft.disabled = true;
        useDraftButton.disabled = true;
        retryOutLoudButton.disabled = true;
        renderList(one('[data-is-changes]'), ['Reviewing the answer against the coach priorities']);
        cancelPendingImprovement();
        improveController = new AbortController();
        var controller = improveController;
        var requestId = improveRequestId;
        postJSON('/api/interview/improve', {
            profile_slug: profileSlug,
            question: currentQuestion().text,
            answer: session.currentAnswer,
            improvements: session.currentReview.improvements,
            evidence_ids: selectedIds
        }, controller.signal).then(function (payload) {
            if (requestId !== improveRequestId) return;
            improveController = null;
            draft.disabled = false;
            useDraftButton.disabled = false;
            retryOutLoudButton.disabled = false;
            draft.value = payload.improvement.draft;
            renderList(one('[data-is-changes]'), payload.improvement.changes);
            announce('Coach-assisted draft ready. Review and edit it before using it.');
        }).catch(function (error) {
            if (requestId !== improveRequestId) return;
            improveController = null;
            if (error.name === 'AbortError') return;
            draft.disabled = false;
            useDraftButton.disabled = false;
            retryOutLoudButton.disabled = false;
            draft.value = session.currentAnswer;
            text(improveError, error.message + ' Your original answer has not changed.');
            setHidden(improveError, false);
            announce('The improved draft could not be generated. Your original answer is unchanged.');
        });
    });

    one('[data-is-back-feedback]').addEventListener('click', function () {
        cancelPendingImprovement();
        feedbackBlock.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
    });

    one('[data-is-use-draft]').addEventListener('click', function () {
        var draftElement = one('[data-is-improved-draft]');
        if (draftElement.disabled) return;
        var draft = draftElement.value.trim();
        if (!draft) return;
        session.attemptNumber += 1;
        answer.value = draft;
        saveDraft(false);
        syncAnswerState();
        setHidden(improveEmpty, false);
        setHidden(improveContent, true);
        setHidden(submittedBlock, true);
        setHidden(answeringBlock, false);
        setStage(1);
        answer.focus();
        announce('AI-assisted draft copied into a new editable attempt. Nothing was published.');
    });

    one('[data-is-retry-out-loud]').addEventListener('click', function () {
        var draftElement = one('[data-is-improved-draft]');
        if (draftElement.disabled) return;
        var draft = draftElement.value.trim();
        if (!setMode('video', true)) return;
        if (draft) {
            session.aiReference = draft;
            session.aiReferenceQuestion = currentQuestion().text;
        }
        announce('Video Practice opened for a new out-loud attempt.');
    });

    /* Speech input */
    var activeRecognition = null;
    function friendlySpeechError(code) {
        if (code === 'not-allowed' || code === 'service-not-allowed') return 'Microphone permission was denied. Allow microphone access in your browser’s site settings, then try again.';
        if (code === 'no-speech') return 'No speech was detected. Try again and speak clearly into your microphone.';
        if (code === 'audio-capture') return 'No microphone was found, or it is being used by another app.';
        if (code === 'network') return 'Dictation lost its network connection. Check your connection and try again.';
        return 'Dictation stopped before it captured a transcript. Try again, or keep typing.';
    }
    function showMicError(kind, message) {
        var errorTarget = one('[data-is-mic-error="' + kind + '"]');
        if (!errorTarget) return;
        text(errorTarget, message);
        setHidden(errorTarget, false);
    }
    function startDictation(kind, button) {
        var errorTarget = one('[data-is-mic-error="' + kind + '"]');
        var Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) {
            var unsupported = 'Speech input is not supported in this browser. You can keep typing.';
            announce(unsupported);
            showMicError(kind, unsupported);
            return;
        }
        if (activeRecognition) {
            activeRecognition.stop();
            return;
        }
        setHidden(errorTarget, true);
        var target = kind === 'ai' ? one('[data-is-ai-question]') : kind === 'video' ? one('[data-is-video-transcript]') : answer;
        var recognition = new Recognition();
        activeRecognition = recognition;
        recognition.lang = document.documentElement.lang || 'en-US';
        recognition.interimResults = false;
        recognition.continuous = false;
        button.classList.add('is-listening');
        button.setAttribute('aria-label', 'Stop dictation');
        announce('Listening. Speak your answer now.');
        recognition.onresult = function (event) {
            var transcript = Array.prototype.map.call(event.results, function (result) { return result[0].transcript; }).join(' ').trim();
            if (target === answer || kind === 'video') {
                target.value = (target.value.trim() ? target.value.trim() + ' ' : '') + transcript;
                target.dispatchEvent(new Event('input', { bubbles: true }));
            } else {
                target.value = transcript;
            }
        };
        recognition.onerror = function (event) {
            var code = event && event.error;
            if (code === 'aborted') return;
            var message = friendlySpeechError(code);
            announce(message);
            showMicError(kind, message);
        };
        recognition.onend = function () {
            activeRecognition = null;
            button.classList.remove('is-listening');
            button.setAttribute('aria-label', kind === 'ai' ? 'Dictate an interview question' : kind === 'video' ? 'Dictate your answer transcript' : 'Dictate your answer');
        };
        recognition.start();
    }

    all('[data-is-mic]').forEach(function (button) {
        button.addEventListener('click', function () { startDictation(button.getAttribute('data-is-mic'), button); });
    });

    /* Interview AI */
    var aiForm = one('[data-is-ai-form]');
    var aiQuestionInput = one('[data-is-ai-question]');
    var aiAnswerBlock = one('[data-is-ai-answer]');
    var aiAnswerEmpty = one('[data-is-ai-answer-empty]');
    var aiAnswerContent = one('[data-is-ai-answer-content]');
    var aiLoading = one('[data-is-ai-loading]');
    var aiError = one('[data-is-ai-error]');
    var modeGroup = one('[data-is-ai-mode-group]');
    if (modeGroup) {
        var modeNote = one('[data-is-ai-mode-note]');
        var modeNotes = {
            best_practice: 'A generic, clearly labeled example — no personal history is used.',
            member_history: 'Grounded only in the approved public history.',
            compare: 'Both answers, stacked — study the structural lessons.'
        };
        modeGroup.addEventListener('change', function (event) {
            if (event.target.name !== 'is-ai-mode') return;
            modeGroup.querySelectorAll('.is__mode-option').forEach(function (label) {
                label.classList.toggle('is__mode-option--selected',
                    label.querySelector('input').checked);
            });
            if (modeNote) modeNote.textContent = modeNotes[event.target.value] || '';
        });
    }

    var followUpForm = one('[data-is-follow-up-form]');
    var followUpInput = one('[data-is-follow-up]');
    var followUpSubmit = one('[data-is-follow-up-submit]');
    var currentModelAnswer = null;
    var currentAiQuestion = '';
    var currentModelQuestion = '';
    var currentModelContextToken = '';
    var aiController = null;
    var aiRequestId = 0;

    function cancelPendingAi(resetLoading) {
        aiRequestId += 1;
        if (aiController) aiController.abort();
        aiController = null;
        if (resetLoading) setHidden(aiLoading, true);
    }

    function resetAiAnswerForContextChange() {
        cancelPendingAi(true);
        currentModelAnswer = null;
        currentAiQuestion = '';
        currentModelQuestion = '';
        currentModelContextToken = '';
        setHidden(aiAnswerBlock, false);
        setHidden(aiAnswerEmpty, false);
        setHidden(aiAnswerContent, true);
        followUpInput.value = '';
        followUpInput.disabled = true;
        followUpSubmit.disabled = true;
        setHidden(aiError, true);
    }

    function selectedAiMode() {
        var checked = document.querySelector('[data-is-ai-mode-group] input[name="is-ai-mode"]:checked');
        return checked ? checked.value : 'member_history';
    }

    function renderModelAnswer(payload) {
        currentModelAnswer = payload.modelAnswer;
        currentModelContextToken = payload.contextToken || '';
        var insufficient = payload.modelAnswer.status === 'insufficient';
        one('[data-is-practice-answer]').disabled = insufficient;
        text(one('[data-is-ai-name]'), payload.profile.firstName || 'Candidate');
        text(one('[data-is-ai-answer-text]'), payload.modelAnswer.answer);
        renderList(one('[data-is-ai-why]'), payload.modelAnswer.whyItWorks);
        var generic = !!payload.modelAnswer.generic;
        var genericFlag = one('[data-is-ai-generic]');
        if (genericFlag) setHidden(genericFlag, !generic);
        var heading = one('[data-is-ai-answer-heading]');
        if (heading) {
            heading.textContent = generic
                ? 'Best-practice example'
                : (payload.profile.firstName || 'Candidate') + '\u2019s answer';
        }
        var compareBlock = one('[data-is-ai-compare]');
        if (compareBlock) {
            var hasCompare = !!(payload.bestPractice && payload.bestPractice.answer);
            setHidden(compareBlock, !hasCompare);
            if (hasCompare) {
                text(one('[data-is-ai-compare-text]'), payload.bestPractice.answer);
                renderList(one('[data-is-ai-compare-why]'), payload.bestPractice.whyItWorks);
            }
        }
        var evidenceHolder = one('[data-is-ai-evidence]');
        evidenceHolder.replaceChildren();
        if (generic) {
            var flag = document.createElement('span');
            flag.className = 'is__evidence-chip';
            flag.textContent = 'Illustrative example — no personal history used';
            evidenceHolder.appendChild(flag);
        } else if (!payload.modelAnswer.evidenceUsed.length) {
            var none = document.createElement('span');
            none.className = 'is__evidence-chip';
            none.textContent = insufficient
                ? 'There is no strong example in the approved history for this question yet — adding your own arrives with PeerSlate accounts. Try the best-practice example instead.'
                : 'No approved history references returned — verify this draft';
            evidenceHolder.appendChild(none);
        } else {
            payload.modelAnswer.evidenceUsed.forEach(function (item) {
                var chip = document.createElement('span');
                chip.className = 'is__evidence-chip';
                chip.textContent = item.metric + ' — ' + item.label;
                chip.title = item.summary || item.label;
                evidenceHolder.appendChild(chip);
            });
        }
        setHidden(aiLoading, true);
        setHidden(aiError, true);
        setHidden(aiAnswerBlock, false);
        setHidden(aiAnswerEmpty, true);
        setHidden(aiAnswerContent, false);
        followUpInput.disabled = insufficient;
        followUpSubmit.disabled = insufficient;
        announce(insufficient ? 'No strong example exists in the approved history for that question yet.' : (payload.modelAnswer.generic ? 'Best-practice example ready.' : 'Draft grounded in approved history ready.'));
    }

    function requestModelAnswer(followUp) {
        var question = aiQuestionInput.value.trim();
        if (!question) { aiQuestionInput.focus(); return; }
        currentAiQuestion = currentAiQuestion || question;
        var practiceQuestion = followUp || currentAiQuestion;
        cancelPendingAi(false);
        aiController = new AbortController();
        var controller = aiController;
        var requestId = aiRequestId;
        setHidden(aiAnswerBlock, false);
        if (!followUp) {
            setHidden(aiAnswerEmpty, false);
            setHidden(aiAnswerContent, true);
            followUpInput.disabled = true;
            followUpSubmit.disabled = true;
        }
        setHidden(aiError, true);
        setHidden(aiLoading, false);
        postJSON('/api/interview/model-answer', {
            profile_slug: profileSlug,
            question: currentAiQuestion,
            follow_up: followUp || '',
            context_token: followUp ? currentModelContextToken : '',
            level: session.level,
            family: session.family,
            mode: followUp ? 'member_history' : selectedAiMode()
        }, controller.signal).then(function (payload) {
            if (requestId !== aiRequestId) return;
            aiController = null;
            currentModelQuestion = practiceQuestion;
            renderModelAnswer(payload);
        }).catch(function (error) {
            if (requestId !== aiRequestId) return;
            aiController = null;
            if (error.name === 'AbortError') return;
            setHidden(aiLoading, true);
            text(aiError, error.message);
            setHidden(aiError, false);
            if (currentModelAnswer) {
                setHidden(aiAnswerEmpty, true);
                setHidden(aiAnswerContent, false);
                var followUpAvailable = currentModelAnswer.status !== 'insufficient' && Boolean(currentModelContextToken);
                followUpInput.disabled = !followUpAvailable;
                followUpSubmit.disabled = !followUpAvailable;
            } else {
                setHidden(aiAnswerEmpty, false);
                setHidden(aiAnswerContent, true);
            }
            announce('Interview AI could not complete that answer.');
        });
    }

    aiForm.addEventListener('submit', function (event) {
        event.preventDefault();
        if (!modelAnswersEnabled) {
            announce('Interview AI is not available for this profile.');
            return;
        }
        resetAiAnswerForContextChange();
        requestModelAnswer('');
    });
    one('[data-is-follow-up-open]').addEventListener('click', function () { followUpInput.focus(); });
    followUpForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var followUp = followUpInput.value.trim();
        if (!followUp) return;
        if (!currentModelContextToken) {
            announce('Generate an answer before asking a follow-up.');
            return;
        }
        requestModelAnswer(followUp);
        followUpInput.value = '';
    });
    one('[data-is-ai-new]').addEventListener('click', function () {
        resetAiAnswerForContextChange();
        aiQuestionInput.value = '';
        aiQuestionInput.focus();
    });
    one('[data-is-practice-answer]').addEventListener('click', function () {
        if (!currentModelAnswer) return;
        var modelAnswer = currentModelAnswer;
        var modelQuestion = currentModelQuestion || currentAiQuestion || aiQuestionInput.value.trim();
        if (!setMode('me', true)) return;
        session.queue[session.index] = {
            text: modelQuestion,
            family: session.family === 'mixed' ? 'behavioral' : session.family,
            competency: 'Communication',
            custom: true
        };
        session.aiReference = modelAnswer.answer;
        session.aiReferenceQuestion = session.queue[session.index].text;
        persistSession();
        renderQuestion();
        removeStored(draftKey(currentQuestion().text));
        answer.value = '';
        syncAnswerState();
        answer.focus();
        announce('Practice opened with the same question and a fresh empty attempt. The model answer is optional reference only.');
    });

    /* Video rehearsal */
    var media = {
        stream: null,
        recorder: null,
        chunks: [],
        startedAt: 0,
        timer: null,
        playbackUrl: null,
        question: null,
        historyRecordId: '',
        permissionRequestId: 0
    };
    var cameraPreview = one('[data-is-camera-preview]');
    var cameraEmpty = one('[data-is-camera-empty]');
    var cameraStatus = one('[data-is-camera-status]');
    var microphoneStatus = one('[data-is-mic-status]');
    var videoError = one('[data-is-video-error]');
    var startRecord = one('[data-is-record-start]');
    var stopRecord = one('[data-is-record-stop]');
    var discardRecord = one('[data-is-record-discard]');
    var videoResult = one('[data-is-video-result]');
    var videoResultEmpty = one('[data-is-video-result-empty]');
    var videoResultContent = one('[data-is-video-result-content]');
    var videoTranscript = one('[data-is-video-transcript]');
    var videoTranscriptForm = one('[data-is-video-transcript-form]');
    var videoReviewContent = one('[data-is-video-review-content]');

    function setDeviceStatus(element, message, status) {
        element.classList.remove('is-ready', 'is-error');
        if (status) element.classList.add(status);
        var marker = document.createElement('i');
        marker.setAttribute('aria-hidden', 'true');
        element.replaceChildren(marker, document.createTextNode(message));
    }

    function friendlyMediaError(error) {
        if (!error) return 'Camera or microphone access is unavailable.';
        if (error.name === 'NotAllowedError' || error.name === 'SecurityError') return 'Camera or microphone permission was denied. Use your browser site settings to allow access, then try again.';
        if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') return 'No usable camera or microphone was found.';
        if (error.name === 'NotReadableError') return 'Another application may be using the camera or microphone.';
        return 'The camera or microphone could not be started in this browser.';
    }

    function enableCamera() {
        if (videoCapability === 'disabled') {
            announce('Video Practice is not available for this profile.');
            return;
        }
        setHidden(videoError, true);
        setDeviceStatus(cameraStatus, 'Requesting camera…');
        setDeviceStatus(microphoneStatus, 'Requesting microphone…');
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            text(videoError, 'Camera rehearsal is not supported in this browser.');
            setHidden(videoError, false);
            setDeviceStatus(cameraStatus, 'Camera unavailable', 'is-error');
            setDeviceStatus(microphoneStatus, 'Microphone unavailable', 'is-error');
            return;
        }
        var permissionRequestId = ++media.permissionRequestId;
        navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(function (stream) {
            if (permissionRequestId !== media.permissionRequestId || session.mode !== 'video' || videoCapability === 'disabled') {
                stream.getTracks().forEach(function (track) { track.stop(); });
                return;
            }
            releaseMedia(false, true);
            media.stream = stream;
            cameraPreview.controls = false;
            cameraPreview.muted = true;
            cameraPreview.src = '';
            cameraPreview.srcObject = stream;
            cameraPreview.play().catch(function () { /* user gesture already granted */ });
            setHidden(cameraEmpty, true);
            setDeviceStatus(cameraStatus, 'Camera ready', 'is-ready');
            setDeviceStatus(microphoneStatus, 'Microphone ready', 'is-ready');
            startRecord.disabled = !window.MediaRecorder;
            if (!window.MediaRecorder) {
                text(videoError, 'Live preview is ready, but recording is not supported in this browser.');
                setHidden(videoError, false);
            }
            announce('Camera and microphone ready. Recording has not started.');
        }).catch(function (error) {
            if (permissionRequestId !== media.permissionRequestId || session.mode !== 'video') return;
            var message = friendlyMediaError(error);
            text(videoError, message);
            setHidden(videoError, false);
            setDeviceStatus(cameraStatus, 'Camera unavailable', 'is-error');
            setDeviceStatus(microphoneStatus, 'Microphone unavailable', 'is-error');
            announce(message);
        });
    }

    function supportedMimeType() {
        if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return '';
        return ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4'].filter(function (type) { return MediaRecorder.isTypeSupported(type); })[0] || '';
    }

    function formatDuration(seconds) {
        var minutes = Math.floor(seconds / 60);
        var remainder = Math.floor(seconds % 60);
        return String(minutes).padStart(2, '0') + ':' + String(remainder).padStart(2, '0');
    }

    function startRecording() {
        if (!media.stream || !window.MediaRecorder) return;
        media.chunks = [];
        media.historyRecordId = '';
        var mimeType = supportedMimeType();
        try {
            media.recorder = mimeType ? new MediaRecorder(media.stream, { mimeType: mimeType }) : new MediaRecorder(media.stream);
        } catch (error) {
            text(videoError, 'This browser could not create a compatible local recording.');
            setHidden(videoError, false);
            return;
        }
        media.recorder.ondataavailable = function (event) { if (event.data && event.data.size) media.chunks.push(event.data); };
        media.recorder.onstop = finishRecording;
        media.startedAt = Date.now();
        media.question = cloneQuestion(currentQuestion());
        media.recorder.start(1000);
        setHidden(one('[data-is-recording-badge]'), false);
        setHidden(startRecord, true);
        setHidden(stopRecord, false);
        setHidden(discardRecord, false);
        setHidden(videoResult, false);
        setHidden(videoResultEmpty, false);
        setHidden(videoResultContent, true);
        media.timer = window.setInterval(function () {
            var seconds = Math.floor((Date.now() - media.startedAt) / 1000);
            text(one('[data-is-recording-time]'), formatDuration(seconds));
            if (seconds >= 180 && media.recorder && media.recorder.state === 'recording') media.recorder.stop();
        }, 250);
        announce('Recording started. Maximum duration is three minutes.');
    }

    function finishRecording() {
        window.clearInterval(media.timer);
        var recordedQuestion = media.question || cloneQuestion(currentQuestion());
        var durationSeconds = Math.max(1, Math.round((Date.now() - media.startedAt) / 1000));
        var blob = new Blob(media.chunks, { type: media.recorder && media.recorder.mimeType ? media.recorder.mimeType : 'video/webm' });
        if (media.playbackUrl) URL.revokeObjectURL(media.playbackUrl);
        media.playbackUrl = URL.createObjectURL(blob);
        if (media.stream) media.stream.getTracks().forEach(function (track) { track.stop(); });
        media.stream = null;
        cameraPreview.srcObject = null;
        cameraPreview.src = media.playbackUrl;
        cameraPreview.muted = false;
        cameraPreview.controls = true;
        setHidden(cameraEmpty, true);
        setHidden(one('[data-is-recording-badge]'), true);
        setHidden(stopRecord, true);
        setHidden(startRecord, true);
        setHidden(discardRecord, false);
        text(one('[data-is-video-duration]'), formatDuration(durationSeconds));
        setHidden(videoResult, false);
        setHidden(videoResultEmpty, true);
        setHidden(videoResultContent, false);
        setDeviceStatus(cameraStatus, 'Local recording complete', 'is-ready');
        setDeviceStatus(microphoneStatus, 'Audio captured locally', 'is-ready');
        media.historyRecordId = 'video-' + Date.now();
        addHistoryRecord({
            id: media.historyRecordId,
            createdAt: new Date().toISOString(),
            mode: 'video',
            question: recordedQuestion.text,
            family: recordedQuestion.family,
            competency: recordedQuestion.competency,
            score: null,
            durationSeconds: durationSeconds,
            status: 'Recorded locally'
        });
        media.recorder = null;
        media.chunks = [];
        announce('Recording complete. Local playback is ready. No upload or analysis occurred.');
    }

    function resetVideoUi() {
        window.clearInterval(media.timer);
        if (media.playbackUrl) { URL.revokeObjectURL(media.playbackUrl); media.playbackUrl = null; }
        cameraPreview.pause();
        cameraPreview.removeAttribute('src');
        cameraPreview.srcObject = null;
        cameraPreview.controls = false;
        cameraPreview.muted = true;
        setHidden(cameraEmpty, false);
        setHidden(one('[data-is-recording-badge]'), true);
        setHidden(startRecord, false);
        startRecord.disabled = true;
        setHidden(stopRecord, true);
        setHidden(discardRecord, true);
        setHidden(videoResult, false);
        setHidden(videoResultEmpty, false);
        setHidden(videoResultContent, true);
        media.question = null;
        media.historyRecordId = '';
        videoTranscript.value = '';
        videoReviewContent.disabled = true;
        setDeviceStatus(cameraStatus, 'Camera not requested');
        setDeviceStatus(microphoneStatus, 'Microphone not requested');
    }

    one('[data-is-camera-enable]').addEventListener('click', enableCamera);
    one('[data-is-device-settings]').addEventListener('click', function () {
        if (!prepareVideoContextChange('Discard the active recording or transcript draft and reopen device settings?')) return;
        releaseMedia(true);
        resetVideoUi();
        enableCamera();
    });
    startRecord.addEventListener('click', startRecording);
    stopRecord.addEventListener('click', function () { if (media.recorder && media.recorder.state === 'recording') media.recorder.stop(); });
    discardRecord.addEventListener('click', function () {
        var recordId = media.historyRecordId;
        releaseMedia(true);
        resetVideoUi();
        removeHistoryRecord(recordId);
        announce('Local recording and its browser record discarded.');
    });
    videoTranscript.addEventListener('input', function () {
        videoReviewContent.disabled = !writtenPracticeEnabled || !videoTranscript.value.trim();
    });
    videoTranscriptForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var transcript = videoTranscript.value.trim();
        if (!writtenPracticeEnabled || !transcript) {
            videoTranscript.focus();
            announce('Type, paste, or dictate a transcript before submitting it for review.');
            return;
        }
        var recordedQuestion = media.question ? cloneQuestion(media.question) : cloneQuestion(currentQuestion());
        var recordId = media.historyRecordId;
        videoTranscript.value = '';
        if (!setMode('me', true)) {
            videoTranscript.value = transcript;
            videoReviewContent.disabled = false;
            return;
        }
        session.queue[session.index] = recordedQuestion;
        renderQuestion();
        session.reviewSource = 'video';
        session.reviewRecordId = recordId;
        answer.value = transcript;
        syncAnswerState();
        saveDraft(false);
        submitReview();
        announce('Reviewing the transcript with the shared Interview Studio content coach.');
    });
    window.addEventListener('beforeunload', function (event) {
        var hasActiveRecording = Boolean(media.recorder && !media.playbackUrl);
        var hasTranscriptDraft = Boolean(videoTranscript && videoTranscript.value.trim());
        if (session.mode === 'video' && (hasActiveRecording || hasTranscriptDraft)) {
            event.preventDefault();
            event.returnValue = '';
        }
    });
    window.addEventListener('pagehide', function () { releaseMedia(true); });

    /* History and growth from real browser records only */
    var historyMode = one('[data-is-history-mode]');
    var historyCompetency = one('[data-is-history-competency]');
    var historyTime = one('[data-is-history-time]');
    var storageNote = one('[data-is-storage-note]');
    var storageOk = one('[data-is-storage-ok]');
    var historyDetail = one('[data-is-history-detail]');
    var historyDetailRecordId = '';
    var historyDetailOpenedWithPush = false;

    function historyDetailUrl(recordId) {
        var params = new URLSearchParams(window.location.search);
        params.set('session', recordId);
        return root.getAttribute('data-history-url') + '?' + params.toString();
    }

    function openHistoryDetail(record, updateUrl) {
        if (!record || !historyDetail) return;
        historyDetailRecordId = record.id;
        text(one('[data-is-history-detail-mode]'), record.mode === 'video' ? 'Video Practice attempt' : 'Interview Me attempt');
        text(one('[data-is-history-detail-date]'), new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(record.createdAt)));
        text(one('[data-is-history-detail-score]'), record.score == null ? 'Not scored' : record.score + ' / 100');
        text(one('[data-is-history-detail-question]'), record.question);
        text(one('[data-is-history-detail-context]'), labelFamily(record.family) + ' · Competency: ' + record.competency + ' · ' + record.status);

        var answerSection = one('[data-is-history-detail-answer]');
        var reviewSection = one('[data-is-history-detail-review]');
        var videoSection = one('[data-is-history-detail-video]');
        setHidden(answerSection, !record.answer);
        setHidden(reviewSection, !record.verdict);
        setHidden(videoSection, record.mode !== 'video');
        text(one('[data-is-history-detail-answer-text]'), record.answer || '');
        text(one('[data-is-history-detail-verdict]'), record.verdict || '');
        text(one('[data-is-history-detail-encouragement]'), record.encouragement || '');
        renderList(one('[data-is-history-detail-strengths]'), record.strengths || [], EMPTY_STRENGTHS_MESSAGE);
        renderList(one('[data-is-history-detail-improvements]'), record.improvements || [], EMPTY_IMPROVEMENTS_MESSAGE);
        text(one('[data-is-history-detail-duration]'), record.durationSeconds ? formatDuration(record.durationSeconds) : 'A local rehearsal');

        if (!historyDetail.open) {
            if (typeof historyDetail.showModal === 'function') historyDetail.showModal();
            else historyDetail.setAttribute('open', '');
        }
        if (updateUrl) {
            window.history.pushState({ interviewSession: record.id }, '', historyDetailUrl(record.id));
            historyDetailOpenedWithPush = true;
        }
    }

    function openHistoryDetailFromLocation() {
        if (!historyDetail) return;
        var recordId = new URLSearchParams(window.location.search).get('session');
        if (!recordId) {
            historyDetailRecordId = '';
            historyDetailOpenedWithPush = false;
            if (historyDetail.open) historyDetail.close();
            return;
        }
        var records = readJSON(historyKey, []);
        var record = records.filter(function (item) { return item.id === recordId; })[0];
        if (record) openHistoryDetail(record, false);
    }

    function closeHistoryDetail() {
        if (!historyDetail) return;
        if (historyDetail.open) historyDetail.close();
        historyDetailRecordId = '';
        if (historyDetailOpenedWithPush) {
            historyDetailOpenedWithPush = false;
            window.history.back();
            return;
        }
        var params = new URLSearchParams(window.location.search);
        params.delete('session');
        window.history.replaceState({}, '', root.getAttribute('data-history-url') + (params.toString() ? '?' + params.toString() : ''));
    }

    function average(values) {
        return values.length ? Math.round(values.reduce(function (sum, value) { return sum + value; }, 0) / values.length) : null;
    }

    function populateHistoryCompetencies(records) {
        if (!historyCompetency) return;
        var current = historyCompetency.value;
        var names = records.map(function (record) { return record.competency; }).filter(Boolean).filter(function (name, index, list) { return list.indexOf(name) === index; }).sort();
        historyCompetency.innerHTML = '<option value="all">All competencies</option>';
        names.forEach(function (name) {
            var option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            historyCompetency.appendChild(option);
        });
        if (names.indexOf(current) !== -1) historyCompetency.value = current;
    }

    function filteredHistory(records) {
        var mode = historyMode ? historyMode.value : 'all';
        var competency = historyCompetency ? historyCompetency.value : 'all';
        var days = historyTime ? Number(historyTime.value) : 0;
        var cutoff = days ? Date.now() - days * 86400000 : 0;
        return records.filter(function (record) {
            return (mode === 'all' || record.mode === mode) &&
                (competency === 'all' || record.competency === competency) &&
                (!cutoff || new Date(record.createdAt).getTime() >= cutoff);
        });
    }

    function renderHistory() {
        var hasStorage = storageAvailable();
        setHidden(storageNote, hasStorage);
        setHidden(storageOk, !hasStorage);
        var allRecords = readJSON(historyKey, []);
        populateHistoryCompetencies(allRecords);
        var records = filteredHistory(allRecords);
        var scored = records.filter(function (record) {
            return (record.mode === 'me' || record.mode === 'video') && record.score != null && Number.isFinite(Number(record.score));
        });
        var avg = average(scored.map(function (record) { return Number(record.score); }));
        text(one('[data-is-history-count]'), records.length);
        text(one('[data-is-history-average]'), avg == null ? '—' : avg + '%');

        var byCompetency = {};
        scored.forEach(function (record) {
            if (!byCompetency[record.competency]) byCompetency[record.competency] = [];
            byCompetency[record.competency].push(record);
        });
        var comparable = Object.keys(byCompetency).filter(function (name) { return byCompetency[name].length >= 2; });
        var strongest = comparable.sort(function (a, b) {
            return average(byCompetency[b].map(function (record) { return Number(record.score); })) - average(byCompetency[a].map(function (record) { return Number(record.score); }));
        })[0];
        text(one('[data-is-history-strongest]'), strongest || 'Not enough practice yet');

        var dimensionNames = ['relevance', 'structure', 'specificity', 'evidence', 'impact'];
        var dimensionAverages = dimensionNames.map(function (name) {
            var values = scored.map(function (record) { return record.dimensions && Number(record.dimensions[name]); }).filter(Number.isFinite);
            return { name: name, value: average(values) };
        }).filter(function (item) { return item.value != null; }).sort(function (a, b) { return a.value - b.value; });
        var lowest = dimensionAverages[0];
        text(one('[data-is-history-improvement]'), scored.length >= 2 && lowest ? lowest.name.charAt(0).toUpperCase() + lowest.name.slice(1) : 'Complete another scored answer');

        var recommendation = defaultQuestion;
        var reason = 'Start with one focused answer';
        if (scored.length && lowest) {
            var lastCompetency = scored[0].competency;
            recommendation = questions.filter(function (question) { return question.competency === lastCompetency && question.text !== scored[0].question; })[0] || defaultQuestion;
            reason = 'Practice ' + lastCompetency + ' to strengthen ' + lowest.name;
        }
        text(one('[data-is-recommendation-reason]'), reason);
        text(one('[data-is-recommendation-question]'), recommendation.text);
        one('[data-is-practice-recommendation]').dataset.question = recommendation.text;

        var empty = one('[data-is-history-empty]');
        var list = one('[data-is-session-list]');
        setHidden(empty, records.length > 0);
        setHidden(list, records.length === 0);
        list.replaceChildren();
        records.slice(0, 12).forEach(function (record) {
            var row = document.createElement('a');
            row.className = 'is__session-row';
            row.href = historyDetailUrl(record.id);
            var date = document.createElement('time');
            date.dateTime = record.createdAt;
            date.textContent = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(record.createdAt));
            var body = document.createElement('span');
            var title = document.createElement('strong');
            title.textContent = record.question;
            var meta = document.createElement('small');
            meta.textContent = (record.mode === 'video' ? 'Video Practice' : 'Interview Me') + ' · ' + record.competency + ' · ' + record.status;
            body.append(title, meta);
            var result = document.createElement('b');
            result.textContent = record.score == null ? '—' : record.score + '%';
            row.append(date, body, result);
            row.addEventListener('click', function (event) {
                event.preventDefault();
                openHistoryDetail(record, true);
            });
            list.appendChild(row);
        });

        var growthEmpty = one('[data-is-growth-empty]');
        var growthList = one('[data-is-growth-list]');
        growthList.replaceChildren();
        setHidden(growthEmpty, comparable.length > 0);
        comparable.forEach(function (name) {
            var score = average(byCompetency[name].map(function (record) { return Number(record.score); }));
            var row = document.createElement('div');
            row.className = 'is__growth-row';
            row.style.setProperty('--growth', score + '%');
            var label = document.createElement('span');
            label.textContent = name;
            var value = document.createElement('b');
            value.textContent = score + '%';
            var bar = document.createElement('i');
            bar.setAttribute('aria-label', name + ' average ' + score + ' percent');
            row.append(label, value, bar);
            growthList.appendChild(row);
        });

        var goal = Number(readJSON(goalKey, 85)) || 85;
        one('[data-is-goal-score]').value = goal;
        var progressValue = avg == null ? 0 : Math.min(100, Math.round((avg / goal) * 100));
        text(one('[data-is-goal-progress]'), avg == null ? 'No scored attempts yet.' : avg + '% average toward a ' + goal + '% target.');
        var progress = one('progress[data-is-goal-progress]');
        progress.value = progressValue;
        progress.textContent = progressValue + '%';
    }

    [historyMode, historyCompetency, historyTime].forEach(function (select) {
        if (!select) return;
        select.addEventListener('change', function () {
            var params = new URLSearchParams();
            if (historyMode.value !== 'all') params.set('mode', historyMode.value);
            if (historyCompetency.value !== 'all') params.set('competency', historyCompetency.value);
            if (historyTime.value !== 'all') params.set('days', historyTime.value);
            window.history.replaceState({}, '', root.getAttribute('data-history-url') + (params.toString() ? '?' + params.toString() : ''));
            renderHistory();
        });
    });

    one('[data-is-goal-save]').addEventListener('click', function () {
        var goal = Math.min(100, Math.max(1, Number(one('[data-is-goal-score]').value) || 85));
        writeJSON(goalKey, goal);
        renderHistory();
        announce('Practice goal saved in this browser.');
    });

    one('[data-is-practice-recommendation]').addEventListener('click', function (event) {
        var questionText = event.currentTarget.dataset.question;
        var match = questions.filter(function (question) { return question.text === questionText; })[0] || defaultQuestion;
        if (!setMode('me', true)) return;
        session.queue[session.index] = cloneQuestion(match);
        persistSession();
        renderQuestion();
        answer.focus();
    });

    function restoreHistoryFilters() {
        if (initialView !== 'history' && window.location.pathname.indexOf('/history') === -1) return;
        var params = new URLSearchParams(window.location.search);
        if (historyMode && ['all', 'me', 'video'].indexOf(params.get('mode')) !== -1) historyMode.value = params.get('mode');
        if (historyTime && ['all', '7', '30'].indexOf(params.get('days')) !== -1) historyTime.value = params.get('days');
        renderHistory();
        var competency = params.get('competency');
        if (competency && all('option', historyCompetency).some(function (option) { return option.value === competency; })) historyCompetency.value = competency;
        renderHistory();
        openHistoryDetailFromLocation();
    }

    one('[data-is-history-detail-close]').addEventListener('click', closeHistoryDetail);
    historyDetail.addEventListener('cancel', function (event) { event.preventDefault(); closeHistoryDetail(); });
    historyDetail.addEventListener('click', function (event) { if (event.target === historyDetail) closeHistoryDetail(); });
    one('[data-is-history-detail-delete]').addEventListener('click', function () {
        if (!historyDetailRecordId || !window.confirm('Delete this Interview Studio record from this browser?')) return;
        var records = readJSON(historyKey, []).filter(function (record) { return record.id !== historyDetailRecordId; });
        writeJSON(historyKey, records);
        historyDetailOpenedWithPush = false;
        if (historyDetail.open) historyDetail.close();
        historyDetailRecordId = '';
        var params = new URLSearchParams(window.location.search);
        params.delete('session');
        window.history.replaceState({}, '', root.getAttribute('data-history-url') + (params.toString() ? '?' + params.toString() : ''));
        renderHistory();
        announce('Session record deleted from this browser.');
    });

    /* Settings */
    var settingsDialog = one('[data-is-settings]');
    one('[data-is-settings-open]').addEventListener('click', function () {
        if (typeof settingsDialog.showModal === 'function') settingsDialog.showModal();
        else settingsDialog.setAttribute('open', '');
    });
    one('[data-is-settings-close]').addEventListener('click', function () { settingsDialog.close(); });
    settingsDialog.addEventListener('click', function (event) { if (event.target === settingsDialog) settingsDialog.close(); });
    function clearLocalData() {
        if (!window.confirm('Clear Interview Studio drafts, sessions, and goals stored in this browser?')) return;
        try {
            Object.keys(window.localStorage).forEach(function (key) { if (key.indexOf(storagePrefix) === 0) window.localStorage.removeItem(key); });
        } catch (error) { /* storage unavailable */ }
        session.queue = buildQueue('behavioral', 5);
        session.index = 0;
        session.level = 'experienced';
        session.family = 'behavioral';
        session.format = '5';
        session.aiReference = '';
        session.aiReferenceQuestion = '';
        levelSelect.value = session.level;
        familySelect.value = session.family;
        formatSelect.value = session.format;
        resetAiAnswerForContextChange();
        renderQuestion();
        renderHistory();
        settingsDialog.close();
        announce('Interview Studio browser data cleared.');
    }
    all('[data-is-clear-local], [data-is-history-clear-local]').forEach(function (button) {
        button.addEventListener('click', clearLocalData);
    });

    /* Initial render */
    renderQuestion();
    syncModeControls(initialMode);
    if (initialView === 'history') {
        showHistoryView();
    } else if (!isOrientation) {
        // Orientation is server-rendered correctly (panel visible, tabs
        // deselected/unroled, controls hidden) and needs no JS patch-up.
        setMode(initialMode, false);
    }
})();
