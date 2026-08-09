(function () {
    'use strict';

    var root = document.querySelector('[data-interview-studio]');
    if (!root) return;

    function one(selector, scope) { return (scope || root).querySelector(selector); }
    function all(selector, scope) { return Array.prototype.slice.call((scope || root).querySelectorAll(selector)); }
    function setHidden(element, hidden) { if (element) element.hidden = Boolean(hidden); }
    function text(element, value) { if (element) element.textContent = value == null ? '' : String(value); }
    function autoGrowTextarea(element) {
        if (!element || !element.matches('[data-is-autogrow]')) return;
        element.style.height = '0px';
        var minimum = parseFloat(window.getComputedStyle(element).minHeight) || 0;
        element.style.height = Math.max(element.scrollHeight, minimum) + 'px';
    }
    function refreshAutogrow(scope) {
        all('[data-is-autogrow]', scope || root).forEach(autoGrowTextarea);
    }
    root.addEventListener('input', function (event) {
        if (event.target && event.target.matches('[data-is-autogrow]')) {
            autoGrowTextarea(event.target);
        }
    });
    var autogrowResizeFrame = 0;
    window.addEventListener('resize', function () {
        if (autogrowResizeFrame) window.cancelAnimationFrame(autogrowResizeFrame);
        autogrowResizeFrame = window.requestAnimationFrame(function () {
            autogrowResizeFrame = 0;
            all('[data-is-autogrow]').forEach(function (element) {
                if (element.offsetParent !== null) autoGrowTextarea(element);
            });
        });
    });

    var profileSlug = root.getAttribute('data-profile-slug') || 'profile';
    var studioUrl = root.getAttribute('data-studio-url') || '/interview-studio';
    var live = one('[data-is-live]');
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var storagePrefix = 'peerslate:interview-studio:' + profileSlug + ':v1';
    var historyKey = storagePrefix + ':history';
    var sessionKey = storagePrefix + ':session';
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
            levels: (item.getAttribute('data-levels') || '').split(/\s+/).filter(Boolean),
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

    function cloneQuestion(item) {
        return {
            text: item.text,
            family: item.family,
            competency: item.competency,
            levels: Array.isArray(item.levels) ? item.levels.slice() : [],
            custom: Boolean(item.custom)
        };
    }

    var preferredCompetenciesByLevel = {
        entry: ['Learning', 'Teamwork', 'Communication', 'Accountability', 'Adaptability', 'Initiative'],
        experienced: ['Initiative', 'Decisions', 'Communication', 'Pressure', 'Teamwork', 'Adaptability'],
        management: ['Leadership', 'Decisions', 'Conflict', 'Teamwork', 'Communication', 'Accountability', 'Pressure'],
        leadership: ['Leadership', 'Decisions', 'Communication', 'Conflict', 'Accountability', 'Pressure', 'Teamwork']
    };

    var FAMILY_LABELS = {
        professional_intro: 'Professional introduction',
        behavioral: 'Behavioral',
        motivation_fit: 'Motivation and fit',
        situational: 'Situational',
        role_specific: 'Role-specific',
        technical_case: 'Technical or case'
    };
    var FAMILY_DIMENSIONS = {
        professional_intro: ['identity', 'relevant_proof', 'value', 'direction'],
        behavioral: ['situation_clarity', 'action_ownership', 'evidence', 'outcome', 'reflection'],
        motivation_fit: ['authentic_rationale', 'specificity', 'role_connection', 'forward_direction'],
        situational: ['problem_framing', 'judgment', 'tradeoffs', 'action_plan', 'communication'],
        role_specific: ['relevance', 'reasoning', 'evidence', 'priorities', 'execution'],
        technical_case: ['framing', 'assumptions', 'reasoning', 'tradeoffs', 'conclusion']
    };
    var DIMENSION_STATUSES = ['strong', 'clear', 'developing', 'missing'];
    var FAMILY_BLUEPRINTS = {
        professional_intro: [
            { text: 'Tell me about yourself and the value you bring to a team.', competency: 'Professional identity' },
            { text: 'What experience best prepares you for the work you want to do next?', competency: 'Relevant proof' }
        ],
        behavioral: [],
        motivation_fit: [
            { text: 'Why are you interested in this role and this kind of work now?', competency: 'Role connection' },
            { text: 'What would make this opportunity a meaningful next step for you?', competency: 'Forward direction' }
        ],
        situational: [],
        role_specific: [
            { text: 'How would you prioritize your first month in a role like this?', competency: 'Priorities' },
            { text: 'What would you need to understand before making an important decision in this role?', competency: 'Reasoning' }
        ],
        technical_case: [
            { text: 'How would you approach a new problem when the information is incomplete?', competency: 'Problem framing' },
            { text: 'Walk me through how you would make and explain a tradeoff in a complex project.', competency: 'Tradeoffs' }
        ]
    };
    var ACTIVE_FAMILIES = Object.keys(FAMILY_LABELS);

    function normalizeFamily(value) {
        return ACTIVE_FAMILIES.indexOf(value) !== -1 ? value : 'behavioral';
    }

    function labelFamily(value) {
        return FAMILY_LABELS[normalizeFamily(value)] || 'Behavioral';
    }

    function questionId(question) {
        return String(question.id || (question.family + ':' + question.text))
            .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 160);
    }

    function normalizedQuestion(item, family) {
        var question = cloneQuestion(item);
        question.family = normalizeFamily(question.family || family);
        question.id = questionId(question);
        return question;
    }

    function localBlueprintsFor(family, level) {
        family = normalizeFamily(family);
        var source = questions.filter(function (item) { return item.family === family; })
            .map(function (item) { return normalizedQuestion(item, family); });
        (FAMILY_BLUEPRINTS[family] || []).forEach(function (item) {
            source.push(normalizedQuestion({
                text: item.text,
                family: family,
                competency: item.competency,
                levels: [level],
                custom: false
            }, family));
        });
        if (!source.length) source = questions.map(function (item) { return normalizedQuestion(item, 'behavioral'); });
        var preferred = preferredCompetenciesByLevel[level] || [];
        return source.filter(function (item, index, list) {
            return list.findIndex(function (candidate) { return candidate.text === item.text; }) === index;
        }).sort(function (left, right) {
            var leftRank = preferred.indexOf(left.competency);
            var rightRank = preferred.indexOf(right.competency);
            leftRank = leftRank === -1 ? preferred.length : leftRank;
            rightRank = rightRank === -1 ? preferred.length : rightRank;
            return leftRank - rightRank || left.text.localeCompare(right.text);
        });
    }

    function articleForRole(roleTitle) {
        var raw = typeof roleTitle === 'string' ? roleTitle.trim() : '';
        var value = raw.toLowerCase();
        if (!value) return '';
        // Initialisms follow their spoken first letter, not their printed
        // vowel. This keeps role tailoring natural for HR, MBA, SRE, UX, and
        // similar titles without trying to infer a visitor's job history.
        var firstToken = raw.split(/[\s/-]+/, 1)[0].replace(/\./g, '');
        if (/^[A-Z]{2,}$/.test(firstToken)) {
            return /^[AEFHILMNORSX]/.test(firstToken) ? 'an' : 'a';
        }
        if (/^(8|11|18)\b/.test(value)) return 'an';
        if (/^(honest|hour|heir)/.test(value)) return 'an';
        if (/^(uni([^nmd]|$)|use|user|euro|one)/.test(value)) return 'a';
        return /^[aeiou]/.test(value) ? 'an' : 'a';
    }

    function roleReference(context) {
        context = context || {};
        if (context.kind === 'opportunity') return 'this opportunity';
        var title = String(context.role_title || '').trim();
        if (!title) return '';
        var role = /\brole$/i.test(title) ? title : title + ' role';
        return articleForRole(title) + ' ' + role;
    }

    function tailorQuestionForContext(question, context) {
        var tailored = cloneQuestion(question);
        /* A visitor-authored custom question is their exact words; role
           tailoring must never rewrite or append to it. */
        if (tailored.custom) return normalizedQuestion(tailored, tailored.family);
        context = context || {};
        var target = roleReference(context);
        if (!target) return normalizedQuestion(tailored, tailored.family);

        if (tailored.family === 'role_specific') {
            tailored.text = tailored.text
                .replace(/a role like this/gi, target)
                .replace(/this role/gi, target);
            if (tailored.text === question.text) {
                tailored.text += ' Focus on the needs of ' + target + '.';
            }
        } else if (tailored.family === 'professional_intro') {
            tailored.text = tailored.text.replace(
                /a team\.$/i,
                'a team, especially in ' + target + '.'
            );
        }
        return normalizedQuestion(tailored, tailored.family);
    }

    function nextLocalQuestion(family, level, trail, seen, context) {
        trail = trail || [];
        seen = seen || [];
        var candidates = localBlueprintsFor(family, level);
        var occupied = trail.map(function (question) { return question.text; }).concat(seen);
        function tailoredText(question) {
            return tailorQuestionForContext(normalizedQuestion(question, family), context).text;
        }
        var choice = candidates.filter(function (question) { return occupied.indexOf(tailoredText(question)) === -1; })[0];
        if (!choice) {
            choice = candidates.filter(function (question) {
                return !trail.length || tailoredText(question) !== trail[trail.length - 1].text;
            })[0] || candidates[0] || normalizedQuestion(defaultQuestion, family);
        }
        return tailorQuestionForContext(normalizedQuestion(choice, family), context);
    }

    var initialMode = root.getAttribute('data-initial-mode') || 'me';
    var initialView = root.getAttribute('data-initial-view') || 'me';
    function currentModeParam() { return new URLSearchParams(window.location.search).get('mode'); }
    // The public product opens directly into practice. The old orientation view
    // remains only as a defensive legacy region, never as the default path.
    var isOrientation = false;
    var legacyStoragePrefix = 'peerslate:interview-studio:' + profileSlug + ':v1';
    var legacySessionKey = legacyStoragePrefix + ':session';
    var legacyHistoryKey = legacyStoragePrefix + ':history';
    storagePrefix = 'peerslate:interview-studio:' + profileSlug + ':v2';
    historyKey = storagePrefix + ':history';
    sessionKey = storagePrefix + ':session';

    function migrateLegacyBrowserState() {
        /* V2 uses its own keys so a failed migration never destroys V1 local
           work. Copy browser-only drafts and history once, leaving the V1 copy
           intact until the visitor clears local Studio data. */
        try {
            var local = window.localStorage;
            if (local.getItem(historyKey) === null) {
                var legacyHistory = readJSON(legacyHistoryKey, []);
                if (Array.isArray(legacyHistory)) {
                    writeJSON(historyKey, legacyHistory.map(function (record) {
                        if (!record || typeof record !== 'object') return record;
                        return Object.assign({}, record, { reviewVersion: 'legacy-v1' });
                    }));
                }
            }
            Object.keys(local).filter(function (key) {
                return key.indexOf(legacyStoragePrefix + ':draft:') === 0;
            }).forEach(function (key) {
                var v2Key = storagePrefix + key.slice(legacyStoragePrefix.length);
                if (local.getItem(v2Key) === null) local.setItem(v2Key, local.getItem(key));
            });
        } catch (error) {
            /* Local storage is optional; a migration failure cannot block practice. */
        }
    }

    migrateLegacyBrowserState();

    function boundedSessionText(value, maximum) {
        return typeof value === 'string' ? value.trim().slice(0, maximum) : '';
    }

    function normalizedContextText(value) {
        return boundedSessionText(value, 4000).replace(/\s+/g, ' ').toLowerCase();
    }

    function localContextFingerprint(value) {
        /* This is a browser-local stable grouping key, not a security digest and
           never part of an AI request. It prevents unlike role contexts from
           being compared simply because they share a question family. */
        var textValue = normalizedContextText(value);
        var hash = 2166136261;
        for (var index = 0; index < textValue.length; index += 1) {
            hash ^= textValue.charCodeAt(index);
            hash = Math.imul(hash, 16777619);
        }
        return ('00000000' + (hash >>> 0).toString(16)).slice(-8);
    }

    function stableContextIdentity(context) {
        context = context || {};
        var kind = ['general', 'role', 'opportunity'].indexOf(context.kind) !== -1 ? context.kind : 'general';
        return 'ctx-' + localContextFingerprint([
            kind,
            normalizedContextText(context.role_title),
            normalizedContextText(context.opportunity_text_local)
        ].join('\u001f'));
    }

    function makeSessionContext(value) {
        value = value || {};
        var kind = ['general', 'role', 'opportunity'].indexOf(value.kind) !== -1 ? value.kind : 'general';
        var context = {
            kind: kind,
            role_title: boundedSessionText(value.role_title, 120),
            interview_stage: boundedSessionText(value.interview_stage, 80) || 'general',
            question_mix: normalizeFamily(value.question_mix || value.family || 'behavioral'),
            opportunity_text_local: boundedSessionText(value.opportunity_text_local, 4000)
        };
        context.context_identity = stableContextIdentity(context);
        context.context_id = context.context_identity;
        return context;
    }

    function newSessionInstanceId() {
        /* A session instance is deliberately distinct from the stable context
           identity used by History & Progress. Two sessions for the same role
           should be comparable, but their completion summaries must not merge. */
        return 'session-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
    }

    function safeSessionInstanceId(value, fallback) {
        return typeof value === 'string' && /^session-[a-z0-9-]{8,80}$/i.test(value)
            ? value
            : (fallback == null ? '' : fallback);
    }

    function contextLabel(context) {
        if (context.kind === 'role' && context.role_title) return context.role_title;
        if (context.kind === 'opportunity') return 'visitor-provided opportunity';
        return 'general practice';
    }

    function labelInterviewStage(value) {
        return {
            general: 'General',
            recruiter_screen: 'Recruiter screen',
            hiring_manager: 'Hiring manager',
            panel_final: 'Panel or final',
            not_sure: 'Not sure yet'
        }[value] || 'General';
    }

    // Setup stays wholly local. This bounded, plain-text context is assembled
    // only at an explicit coaching/example request, never while a visitor is
    // configuring or simply practicing a session.
    function explicitContextForAi() {
        var context = session.context || makeSessionContext();
        var details = [];
        if (context.role_title) details.push('Requested role: ' + context.role_title);
        if (context.interview_stage && context.interview_stage !== 'general') {
            details.push('Interview stage: ' + context.interview_stage.replace(/_/g, ' '));
        }
        if (context.question_mix) details.push('Question family: ' + labelFamily(context.question_mix));
        if (context.opportunity_text_local) {
            details.push('Visitor-pasted opportunity details:\n' + context.opportunity_text_local);
        }
        return details.join('\n').slice(0, 4000);
    }

    function migrateLegacySession(legacy) {
        if (!legacy || !Array.isArray(legacy.queue) || !legacy.queue.length) return null;
        var migratedTrail = legacy.queue.map(function (item) {
            return storedQuestion(item, legacy.family || 'behavioral');
        }).filter(Boolean);
        if (!migratedTrail.length) return null;
        return {
            version: 2,
            sessionId: newSessionInstanceId(),
            level: legacy.level || 'experienced',
            family: normalizeFamily(legacy.family),
            context: makeSessionContext({ family: legacy.family }),
            questionTrail: migratedTrail,
            currentQuestionIndex: Math.min(Math.max(Number(legacy.index) || 0, 0), migratedTrail.length - 1),
            reviewedQuestionIds: (legacy.completedSlots || []).map(function (index) {
                return migratedTrail[index] && migratedTrail[index].id;
            }).filter(Boolean),
            replacementSeen: Array.isArray(legacy.replacementSeen)
                ? legacy.replacementSeen.filter(function (value) { return typeof value === 'string'; })
                : []
        };
    }

    function storedQuestion(item, fallbackFamily) {
        /* Browser storage is user-controlled. Keep a malformed old or V2
           session from preventing a visitor from returning to local practice. */
        if (!item || typeof item !== 'object' || typeof item.text !== 'string') return null;
        var questionText = item.text.trim();
        if (!questionText || questionText.length > 1200) return null;
        var competency = typeof item.competency === 'string' ? item.competency.trim().slice(0, 80) : '';
        return normalizedQuestion({
            text: questionText,
            family: normalizeFamily(item.family || fallbackFamily),
            competency: competency || 'Communication',
            levels: Array.isArray(item.levels)
                ? item.levels.filter(function (level) { return typeof level === 'string'; }).slice(0, 8)
                : [],
            custom: Boolean(item.custom)
        }, fallbackFamily);
    }

    var persistedSession = readJSON(sessionKey, null);
    var restoredSession = persistedSession && Array.isArray(persistedSession.questionTrail) && persistedSession.questionTrail.length
        ? persistedSession
        : migrateLegacySession(readJSON(legacySessionKey, null));
    var shouldPersistRecoveredSession = Boolean(restoredSession) || persistedSession !== null;
    var session = {
        version: 2,
        sessionId: newSessionInstanceId(),
        mode: initialMode,
        level: 'experienced',
        family: 'behavioral',
        context: makeSessionContext(),
        questionTrail: [],
        currentQuestionIndex: 0,
        attemptNumber: 1,
        currentReview: null,
        currentAnswer: '',
        reviewSource: 'me',
        reviewRecordId: '',
        reviewDurationSeconds: 0,
        aiReference: '',
        aiReferenceQuestion: '',
        reviewedQuestionIds: [],
        replacementSeen: []
    };

    if (restoredSession) {
        session.sessionId = safeSessionInstanceId(restoredSession.sessionId, newSessionInstanceId());
        session.level = restoredSession.level || session.level;
        session.family = normalizeFamily(restoredSession.family || (restoredSession.context && restoredSession.context.question_mix));
        session.context = makeSessionContext(restoredSession.context || { family: session.family });
        session.questionTrail = restoredSession.questionTrail.map(function (item) {
            return storedQuestion(item, session.family);
        }).filter(Boolean);
        session.currentQuestionIndex = Math.min(
            Math.max(Number(restoredSession.currentQuestionIndex) || 0, 0),
            session.questionTrail.length - 1
        );
        session.reviewedQuestionIds = Array.isArray(restoredSession.reviewedQuestionIds)
            ? restoredSession.reviewedQuestionIds.filter(function (id) { return typeof id === 'string'; })
            : [];
        session.replacementSeen = Array.isArray(restoredSession.replacementSeen)
            ? restoredSession.replacementSeen.filter(function (value) { return typeof value === 'string'; })
            : [];
    }
    if (!session.questionTrail.length) {
        session.questionTrail.push(nextLocalQuestion(session.family, session.level, [], [], session.context));
    }
    /* An all-malformed stored trail restores as [] and leaves the index at -1
       from the clamp above; re-clamp after the fallback question is added. */
    session.currentQuestionIndex = Math.max(0, Math.min(session.currentQuestionIndex, session.questionTrail.length - 1));

    function persistSession() {
        writeJSON(sessionKey, {
            version: 2,
            sessionId: session.sessionId,
            level: session.level,
            family: session.family,
            context: session.context,
            questionTrail: session.questionTrail,
            currentQuestionIndex: session.currentQuestionIndex,
            reviewedQuestionIds: session.reviewedQuestionIds,
            replacementSeen: session.replacementSeen
        });
        updateSetupSummary();
    }
    if (shouldPersistRecoveredSession) persistSession();
    function updateSetupSummary() {
        var summary = one('[data-is-setup-summary-text]');
        var levelOption = levelSelect && levelSelect.options[levelSelect.selectedIndex];
        var levelLabel = levelOption ? levelOption.text : session.level;
        if (summary) {
            summary.textContent = contextLabel(session.context) + ' / ' + labelInterviewStage(session.context.interview_stage) + ' / ' + levelLabel + ' / ' + labelFamily(session.family) + ' / open session';
        }
        text(one('[data-is-session-level]'), levelLabel);
        text(one('[data-is-session-family]'), labelFamily(session.family));
        text(one('[data-is-rail-context]'), contextLabel(session.context));
        text(one('[data-is-rail-stage]'), 'Stage: ' + labelInterviewStage(session.context.interview_stage));
        text(one('[data-is-rail-mix]'), 'Mix: ' + labelFamily(session.family));
    }

    function currentQuestion() {
        return session.questionTrail[session.currentQuestionIndex] || defaultQuestion;
    }

    var modeTabs = all('[data-is-mode]');
    var modeNavigation = one('.is__modes');
    var historyLink = one('[data-is-history-link]');
    var panels = all('[data-is-panel]');
    var orientationPanel = one('[data-is-panel="orientation"]');
    var controls = one('[data-is-controls]');
    var stageRailItems = all('[data-is-workflow-progress] li');

    function currentQuestionIsCompleted() {
        return session.reviewedQuestionIds.indexOf(questionId(currentQuestion())) !== -1;
    }

    function syncQuestionChangeControls() {
        var workspaceState = root.getAttribute('data-is-workspace-state') || 'draft';
        var videoState = root.getAttribute('data-is-video-state') || 'camera-off';
        all('[data-is-different-question], [data-is-create-question]').forEach(function (button) {
            var panel = button.closest('[data-is-panel]');
            var panelMode = panel ? panel.getAttribute('data-is-panel') : '';
            var disabled = currentQuestionIsCompleted();
            if (panelMode === 'me') disabled = disabled || workspaceState !== 'draft';
            if (panelMode === 'video') {
                disabled = disabled || ['requesting', 'recording', 'stopping'].indexOf(videoState) !== -1;
            }
            button.disabled = disabled;
        });
    }

    function setStage(stage) {
        var stageNames = { 1: 'Drafting', 2: 'Processing', 3: 'Review ready', 4: 'Improving', 5: 'Continue' };
        root.setAttribute('data-is-workspace-state', stage === 2 ? 'processing' : stage === 3 ? 'review' : stage === 4 ? 'improve' : stage === 5 ? 'continue' : 'draft');
        var reviewRailActive = stage >= 3;
        setHidden(one('[data-is-ready-rail]'), reviewRailActive);
        setHidden(one('[data-is-review-rail]'), !reviewRailActive);
        text(one('[data-is-review-attempt]'), session.attemptNumber);
        text(one('[data-is-stage-label]'), stageNames[stage] || 'Drafting');
        syncQuestionChangeControls();
        stageRailItems.forEach(function (item) {
            var n = Number(item.getAttribute('data-is-workflow-step'));
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
    }
    var aiModeControl = one('[data-is-ai-mode-group]');

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
    var cancelReviewButton = one('[data-is-cancel-review]');
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
        setHidden(aiModeControl, mode !== 'ai');
    }

    function releaseMedia(discardRecording, preservePermissionRequest) {
        if (!preservePermissionRequest && media) media.permissionRequestId += 1;
        var recorder = media.recorder;
        if (recorder && discardRecording) {
            recorder.ondataavailable = null;
            recorder.onstop = null;
            media.chunks = [];
            if (media.recorder === recorder) media.recorder = null;
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
        /* Flush visible speech before any confirmation reads the old field,
           and persist Interview Me under the old question key before the
           mode/session context can change. */
        if (mode !== session.mode) {
            /* Close the trail before the panel that hosts it is hidden. A
               non-modal dialog left open would otherwise survive the switch
               and, being already open, skip the re-parent on its next use. */
            closeQueue({ restoreFocus: false });
            stopDictation('interrupted');
            if (session.mode === 'me') persistCurrentAnswerDraft();
        }
        if (session.mode === 'video' && mode !== 'video') {
            if (!prepareVideoContextChange('Discard the active recording or transcript draft and leave Video Practice?')) return false;
            releaseMedia(true);
            resetVideoUi();
        }
        if (session.mode === 'me' && mode !== 'me') clearReviewState();
        if (session.mode === 'ai' && mode !== 'ai') cancelPendingAi(true);
        session.mode = mode;
        root.setAttribute('data-is-active-mode', mode);
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
        refreshAutogrow(one('[data-is-panel="' + mode + '"]'));
        setHidden(controls, false);
        if (historyLink) historyLink.removeAttribute('aria-current');
        syncModeControls(mode);
        syncQuestionChangeControls();
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
            stopDictation('interrupted');
            if (session.mode === 'me') persistCurrentAnswerDraft();
            if (session.mode === 'video' && !prepareVideoContextChange('Discard the active recording or transcript draft and open History?')) {
                event.preventDefault();
            }
        });
    }

    function showHistoryView() {
        if (historyCapability === 'disabled') return false;
        closeQueue({ restoreFocus: false });
        stopDictation('interrupted');
        if (session.mode === 'me') persistCurrentAnswerDraft();
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
        root.setAttribute('data-is-active-mode', 'history');
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
        stopDictation('interrupted');
        if (session.mode === 'me') persistCurrentAnswerDraft();
        if (session.mode === 'video' && !prepareVideoContextChange('Discard the active recording or transcript draft and return to Interview Studio?')) {
            return false;
        }
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
        root.setAttribute('data-is-active-mode', 'orientation');
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
            setMode('me', false);
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
        session.reviewDurationSeconds = 0;
        session.attemptNumber = 1;
        setHidden(answeringBlock, false);
        answer.readOnly = false;
        answeringBlock.removeAttribute('aria-busy');
        setHidden(reviewingBlock, true);
        setHidden(submittedBlock, true);
        setHidden(feedbackBlock, true);
        setHidden(feedbackEmpty, false);
        setHidden(feedbackContent, true);
        setHidden(improveBlock, true);
        setHidden(improveEmpty, false);
        setHidden(improveContent, true);
        setHidden(reviewError, true);
        setHidden(errorActions, true);
        text(submittedLabel, 'Your submitted answer · preserved');
        setHidden(improveError, true);
        var improvedDraft = one('[data-is-improved-draft]');
        improvedDraft.value = '';
        improvedDraft.disabled = false;
        autoGrowTextarea(improvedDraft);
        var answerContext = one('[data-is-answer-context]');
        answerContext.value = '';
        autoGrowTextarea(answerContext);
        setHidden(one('[data-is-answer-context-form]'), true);
        one('[data-is-add-answer-context]').setAttribute('aria-expanded', 'false');
        setStage(1);
        syncAnswerState();
    }

    function restoreDraft() {
        var stored = readJSON(draftKey(currentQuestion().text), null);
        answer.value = stored && typeof stored.text === 'string' ? stored.text : '';
        syncAnswerState();
        text(autosave, answer.value ? 'Restored from this browser' : 'Draft ready');
    }

    function updateUpNextCount(value) {
        all('[data-is-up-next-count]').forEach(function (element) {
            text(element, value);
        });
    }

    var renderedQuestionContextKey = '';

    function renderSessionProgress() {
        var reviewed = session.reviewedQuestionIds.length;
        var trailCount = session.questionTrail.length;
        var progressCopy = reviewed
            ? reviewed + (reviewed === 1 ? ' answer reviewed · open session' : ' answers reviewed · open session')
            : 'Open session · answer as much or as little as you need';
        text(one('[data-is-question-position]'), progressCopy);
        text(one('[data-is-video-question-position]'), progressCopy);
        text(one('[data-is-review-question]'), 'Question ' + (session.currentQuestionIndex + 1) + ' in an open session');
        updateUpNextCount(Math.max(0, trailCount - session.currentQuestionIndex - 1));
        text(one('[data-is-rail-question]'), currentQuestion().text);
        var progress = one('[data-is-progress]');
        if (progress) {
            progress.textContent = 'Open session';
            progress.setAttribute('aria-label', progressCopy);
        }
        var videoProgress = one('[data-is-video-progress]');
        if (videoProgress) {
            videoProgress.textContent = progressCopy;
        }
        var nextButton = one('[data-is-next-question]');
        if (nextButton) nextButton.setAttribute('aria-label', 'Choose the next question');
    }

    function renderQuestionMetadata(question) {
        var familyLabel = question.custom ? 'Custom question' : labelFamily(question.family);
        var competencyLabel = question.custom ? 'Your question' : 'Competency: ' + question.competency;
        text(one('[data-is-family-chip]'), familyLabel);
        text(one('[data-is-competency-chip]'), competencyLabel);
        text(one('[data-is-ai-family-chip]'), familyLabel);
        text(one('[data-is-ai-competency-chip]'), competencyLabel);
        text(one('[data-is-video-family]'), familyLabel);
        text(one('[data-is-video-competency]'), competencyLabel);
        all('[data-is-framework-chip], [data-is-time-chip], [data-is-ai-framework-chip], [data-is-ai-time-chip], [data-is-video-framework-chip], [data-is-video-time-chip]').forEach(function (chip) {
            setHidden(chip, question.custom);
        });
    }

    function renderQuestion(options) {
        options = options || {};
        var question = currentQuestion();
        var questionContextKey = [question.text, session.level, question.family].join('\u001f');
        var questionContextChanged = Boolean(
            renderedQuestionContextKey && renderedQuestionContextKey !== questionContextKey
        );
        renderedQuestionContextKey = questionContextKey;
        if (questionContextChanged) resetAiAnswerForContextChange();
        text(one('[data-is-question]'), question.text);
        text(one('[data-is-ai-question-display]'), question.text);
        var aiQuestion = one('[data-is-ai-question]');
        if (aiQuestion) aiQuestion.value = question.text;
        renderQuestionMetadata(question);
        text(one('[data-is-intent]'), intentByCompetency[question.competency] || 'A clear example, your personal contribution, and an outcome.');
        text(one('[data-is-tip]'), tipByCompetency[question.competency] || 'Keep the context concise, make your action specific, and close with the result.');
        text(one('[data-is-video-question]'), question.text);
        text(one('[data-is-review-attempt]'), session.attemptNumber);
        renderSessionProgress();
        syncQuestionChangeControls();
        all('[data-is-example-link]').forEach(function (link) {
            link.href = studioUrl + '?mode=ai&question=' + encodeURIComponent(question.text);
        });
        var reference = one('[data-is-ai-reference]');
        var showReference = one('[data-is-show-reference]');
        var referenceMatches = Boolean(session.aiReference && session.aiReferenceQuestion === question.text);
        text(one('[data-is-ai-reference-text]'), referenceMatches ? session.aiReference : '');
        setHidden(reference, !referenceMatches || Boolean(showReference && !showReference.checked));
        clearReviewState();
        if (!options.keepDraft) restoreDraft();
        persistSession();
        renderQueue();
        clearNudgeState();
    }

    function syncAnswerState() {
        var value = answer.value.trim();
        var words = value ? value.split(/\s+/).length : 0;
        text(wordCount, words);
        reviewButton.disabled = !writtenPracticeEnabled || !value || Boolean(reviewController);
        if (retryCoachingButton) retryCoachingButton.disabled = Boolean(reviewController);
        autoGrowTextarea(answer);
    }

    function saveDraft(showStatus) {
        window.clearTimeout(autosaveTimer);
        autosaveTimer = null;
        if (showStatus) text(autosave, 'Saving…');
        var ok = writeJSON(draftKey(currentQuestion().text), {
            text: answer.value,
            savedAt: new Date().toISOString()
        });
        text(autosave, ok ? 'Saved in this browser' : 'Save failed — your text is still here');
        return ok;
    }

    function persistCurrentAnswerDraft() {
        window.clearTimeout(autosaveTimer);
        autosaveTimer = null;
        if (!answer) return;
        if (answer.value) {
            saveDraft(false);
        } else {
            removeStored(draftKey(currentQuestion().text));
            text(autosave, 'Draft ready');
        }
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

    function prepareAnswerContextChange() {
        stopDictation('interrupted');
        persistCurrentAnswerDraft();
        return confirmReplace();
    }

    function prepareVideoContextChange(message) {
        if (session.mode !== 'video') return true;
        stopDictation('interrupted');
        var transcriptDraft = videoTranscript && videoTranscript.value.trim();
        var pendingRecording = Boolean(media.recorder && !media.playbackUrl);
        var hasCompletedPlayback = Boolean(media.playbackUrl);
        if ((pendingRecording || hasCompletedPlayback || transcriptDraft) && !window.confirm(message || 'Discard this recording or transcript draft and change the session?')) return false;
        if (pendingRecording || hasCompletedPlayback || transcriptDraft) {
            releaseMedia(true);
            resetVideoUi();
        }
        return true;
    }

    function prepareNewSessionChange() {
        stopDictation('interrupted');
        if (session.mode === 'me') {
            persistCurrentAnswerDraft();
            if (hasDraft() && !window.confirm('Start a new session? Your typed draft stays saved in this browser, but this workspace will move to the new session.')) {
                announce('New session cancelled. Your browser-local draft is unchanged.');
                return false;
            }
        }
        if (session.mode === 'video' && !prepareVideoContextChange('Start a new session and discard the current local recording or transcript draft?')) return false;
        if (session.mode === 'ai') cancelPendingAi(true);
        cancelPendingReview();
        cancelPendingImprovement();
        return true;
    }

    function advanceQuestion(mode) {
        var nextIndex = session.currentQuestionIndex + 1;
        if (!session.questionTrail[nextIndex]) {
            session.questionTrail.push(nextLocalQuestion(
                session.family,
                session.level,
                session.questionTrail,
                session.replacementSeen,
                session.context
            ));
        }
        session.currentQuestionIndex = nextIndex;
        session.attemptNumber = 1;
        persistSession();
        renderQuestion();
        if (mode === 'video') {
            one('[data-is-video-stage]').scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
            one('[data-is-camera-enable]').focus();
        } else {
            one('[data-is-practice-stage]').scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
            answer.focus();
        }
    }

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

    var levelSelect = one('[data-is-level]');
    var familySelect = one('[data-is-family]');
    var stageSelect = one('[data-is-active-stage]');
    var newSessionForm = one('[data-is-new-session-form]');
    var sessionKindSelect = one('[data-is-session-kind]');
    var sessionRoleInput = one('[data-is-session-role]');
    var sessionOpportunityInput = one('[data-is-session-opportunity]');
    var sessionRoleField = one('[data-is-session-role-field]');
    var sessionOpportunityField = one('[data-is-session-opportunity-field]');
    var sessionStageSelect = one('[data-is-session-stage]');
    var sessionMixSelect = one('[data-is-session-mix]');

    function syncNewSessionFields() {
        if (!sessionKindSelect) return;
        var kind = sessionKindSelect.value;
        setHidden(sessionRoleField, kind !== 'role');
        setHidden(sessionOpportunityField, kind !== 'opportunity');
        if (sessionRoleInput) sessionRoleInput.required = kind === 'role';
        if (sessionOpportunityInput) sessionOpportunityInput.required = kind === 'opportunity';
    }

    function syncNewSessionInputs() {
        if (sessionKindSelect) sessionKindSelect.value = session.context.kind;
        if (sessionRoleInput) sessionRoleInput.value = session.context.role_title;
        if (sessionOpportunityInput) sessionOpportunityInput.value = session.context.opportunity_text_local;
        if (sessionStageSelect) sessionStageSelect.value = session.context.interview_stage;
        if (sessionMixSelect) sessionMixSelect.value = session.context.question_mix || session.family;
        if (stageSelect) stageSelect.value = session.context.interview_stage;
        syncNewSessionFields();
    }

    function startNewSession(event) {
        if (event) event.preventDefault();
        var kind = sessionKindSelect ? sessionKindSelect.value : 'general';
        var roleTitle = sessionRoleInput ? sessionRoleInput.value.trim() : '';
        var opportunityText = sessionOpportunityInput ? sessionOpportunityInput.value.trim() : '';
        var nextStage = sessionStageSelect ? sessionStageSelect.value : session.context.interview_stage;
        var nextFamily = normalizeFamily(sessionMixSelect ? sessionMixSelect.value : session.family);
        if (kind === 'role' && !roleTitle) {
            sessionRoleInput.focus();
            announce('Name the type of role you want to practice for.');
            return;
        }
        if (kind === 'opportunity' && !opportunityText) {
            sessionOpportunityInput.focus();
            announce('Paste the opportunity details you want to use.');
            return;
        }
        if (!prepareNewSessionChange()) return;
        var nextMode = modeIsEnabled(session.mode)
            ? session.mode
            : modeIsEnabled('me') ? 'me' : modeIsEnabled('ai') ? 'ai' : 'video';
        session.context = makeSessionContext({
            kind: kind,
            role_title: roleTitle,
            interview_stage: nextStage,
            question_mix: nextFamily,
            opportunity_text_local: opportunityText
        });
        session.sessionId = newSessionInstanceId();
        session.family = nextFamily;
        if (familySelect) familySelect.value = session.family;
        if (stageSelect) stageSelect.value = session.context.interview_stage;
        session.questionTrail = [nextLocalQuestion(session.family, session.level, [], [], session.context)];
        session.currentQuestionIndex = 0;
        session.reviewedQuestionIds = [];
        session.replacementSeen = [];
        session.attemptNumber = 1;
        clearReviewState();
        resetAiAnswerForContextChange();
        persistSession();
        if (!setMode(nextMode, true)) return;
        renderQuestion();
        if (nextMode === 'me') answer.focus();
        else if (nextMode === 'video') cameraEnable.focus();
        else if (aiQuestionInput) aiQuestionInput.focus();
        announce('New ' + contextLabel(session.context) + ' session ready. Practice as many questions as you need.');
    }

    if (levelSelect) levelSelect.value = session.level;
    if (familySelect) familySelect.value = session.family;
    syncNewSessionInputs();
    if (sessionKindSelect) sessionKindSelect.addEventListener('change', syncNewSessionFields);
    if (newSessionForm) newSessionForm.addEventListener('submit', startNewSession);
    all('[data-is-new-session-focus]').forEach(function (newSessionFocus) {
        newSessionFocus.addEventListener('click', function () {
            if (sessionKindSelect) sessionKindSelect.focus();
        });
    });

    if (levelSelect) levelSelect.addEventListener('change', function () {
        stopDictation('interrupted');
        if (session.mode === 'me') persistCurrentAnswerDraft();
        /* A level change keeps the current question and draft, so the
           question-replacement confirm ("Move to another question?") was
           wrong here — it blocked the picker with an unrelated warning and
           snapped the value back on cancel. Only an in-flight recording
           genuinely needs a guard. */
        if (!prepareVideoContextChange('Discard this recording and change experience level?')) {
            levelSelect.value = session.level;
            return;
        }
        session.level = levelSelect.value;
        session.context.question_mix = session.family;
        resetAiAnswerForContextChange();
        persistSession();
        renderQuestion();
        announce('Experience level set to ' + levelSelect.options[levelSelect.selectedIndex].textContent.trim()
            + '. Coaching and new questions now calibrate to it; your current question stays.');
    });
    if (stageSelect) stageSelect.addEventListener('change', function () {
        session.context.interview_stage = stageSelect.value || 'general';
        if (sessionStageSelect) sessionStageSelect.value = session.context.interview_stage;
        /* The stage is part of the AI context string; a stale AI answer would
           otherwise send a mismatched follow-up against its signed token. */
        resetAiAnswerForContextChange();
        persistSession();
        announce('Interview stage updated for this browser-local session.');
    });
    if (familySelect) familySelect.addEventListener('change', function () {
        if (!prepareVideoContextChange('Discard this recording and change question family?') || (session.mode === 'me' && !prepareAnswerContextChange())) {
            familySelect.value = session.family;
            return;
        }
        if (session.mode === 'ai') stopDictation('interrupted');
        resetAiAnswerForContextChange();
        session.family = normalizeFamily(familySelect.value);
        session.context.question_mix = session.family;
        if (sessionMixSelect) sessionMixSelect.value = session.family;
        session.questionTrail.push(nextLocalQuestion(session.family, session.level, session.questionTrail, session.replacementSeen, session.context));
        session.currentQuestionIndex = session.questionTrail.length - 1;
        session.attemptNumber = 1;
        persistSession();
        renderQuestion();
    });

    /* Question queue */
    var queueDialog = one('[data-is-queue]');
    var queueList = one('[data-is-queue-list]');
    var queueTriggers = all('[data-is-queue-open]');
    var queueTrigger = null;
    var queueLayoutQuery = window.matchMedia ? window.matchMedia('(max-width: 72rem)') : null;

    function queueUsesModalLayout() {
        return Boolean(queueLayoutQuery && queueLayoutQuery.matches);
    }

    function setQueueOpenState(isOpen) {
        root.setAttribute('data-is-queue-state', isOpen ? 'open' : 'closed');
        queueTriggers.forEach(function (trigger) {
            trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    }

    function closeQueue(options) {
        options = options || {};
        var focusTarget = queueTrigger;
        if (!focusTarget || focusTarget.offsetParent === null) {
            focusTarget = queueTriggers.filter(function (trigger) {
                return trigger.offsetParent !== null;
            })[0] || focusTarget;
        }
        if (queueDialog.open && typeof queueDialog.close === 'function') {
            queueDialog.close();
        } else {
            queueDialog.removeAttribute('open');
            setQueueOpenState(false);
        }
        if (options.restoreFocus !== false && focusTarget && document.contains(focusTarget)) {
            window.requestAnimationFrame(function () {
                if (document.contains(focusTarget) && focusTarget.offsetParent !== null) {
                    focusTarget.focus();
                }
            });
        }
    }

    function openQueueForCurrentLayout() {
        /* The trail only means something during active practice. The rail
           trigger stays visible in the complete and history views, where
           picking a question would change the index behind a screen that
           never returns to practice, so refuse to open it there. */
        if (['me', 'ai', 'video'].indexOf(root.getAttribute('data-is-active-mode')) === -1) return;
        setQueueOpenState(true);
        if (queueDialog.open) return;
        /* The dialog is markup-embedded in the Interview Me panel. Opened from
           the always-visible session rail while another panel is active, it
           must move to a visible host or it paints 0x0 inside the hidden
           panel subtree. */
        var activeRail = queueTrigger && queueTrigger.closest('.is__side-column');
        var host = activeRail && activeRail.offsetParent !== null
            ? activeRail
            : all('.is__side-column').filter(function (column) { return column.offsetParent !== null; })[0] || root;
        if (queueDialog.parentNode !== host) host.appendChild(queueDialog);
        if (queueUsesModalLayout() && typeof queueDialog.showModal === 'function') {
            queueDialog.showModal();
        } else if (typeof queueDialog.show === 'function') {
            queueDialog.show();
        } else {
            queueDialog.setAttribute('open', '');
        }
    }

    function renderQueue() {
        if (!queueList) return;
        queueList.replaceChildren();
        session.questionTrail.forEach(function (question, index) {
            var item = document.createElement('li');
            item.className = 'is__queue-item' + (index === session.currentQuestionIndex ? ' is-current' : '');
            var button = document.createElement('button');
            button.type = 'button';
            if (index === session.currentQuestionIndex) button.setAttribute('aria-current', 'true');
            var number = document.createElement('i');
            number.textContent = String(index + 1);
            var label = document.createElement('strong');
            label.textContent = question.text;
            var competency = document.createElement('span');
            competency.textContent = 'Competency: ' + question.competency;
            button.append(number, label, competency);
            button.addEventListener('click', function () {
                if (index === session.currentQuestionIndex) { closeQueue(); return; }
                if (!prepareCurrentQuestionChange('Move to this question in your open session?')) return;
                session.currentQuestionIndex = index;
                persistSession();
                renderQuestion();
                closeQueue({ restoreFocus: false });
                focusCurrentQuestionWorkspace();
            });
            item.appendChild(button);
            queueList.appendChild(item);
        });
    }

    queueTriggers.forEach(function (trigger) {
        trigger.setAttribute('aria-expanded', 'false');
        trigger.addEventListener('click', function () {
            queueTrigger = trigger;
            renderQueue();
            openQueueForCurrentLayout();
        });
    });
    one('[data-is-queue-close]').addEventListener('click', function () { closeQueue(); });
    queueDialog.addEventListener('close', function () {
        setQueueOpenState(queueDialog.open);
    });
    queueDialog.addEventListener('cancel', function (event) {
        event.preventDefault();
        closeQueue();
    });
    queueDialog.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !queueUsesModalLayout()) {
            event.preventDefault();
            closeQueue();
        }
    });
    queueDialog.addEventListener('click', function (event) {
        if (event.target === queueDialog && queueUsesModalLayout()) closeQueue();
    });
    if (queueLayoutQuery) {
        var refreshOpenQueueLayout = function () {
            if (!queueDialog.open) return;
            if (typeof queueDialog.close === 'function') queueDialog.close();
            else queueDialog.removeAttribute('open');
            window.requestAnimationFrame(openQueueForCurrentLayout);
        };
        if (typeof queueLayoutQuery.addEventListener === 'function') {
            queueLayoutQuery.addEventListener('change', refreshOpenQueueLayout);
        } else if (typeof queueLayoutQuery.addListener === 'function') {
            queueLayoutQuery.addListener(refreshOpenQueueLayout);
        }
    }

    function focusCurrentQuestionWorkspace() {
        if (session.mode === 'video') {
            one('[data-is-camera-enable]').focus();
        } else if (session.mode === 'ai') {
            one('.is__ai-get-answer').focus();
        } else {
            answer.focus();
        }
    }

    function prepareCurrentQuestionChange(message) {
        if (session.mode === 'video') return prepareVideoContextChange(message || 'Discard the active recording or transcript draft and change questions?');
        if (session.mode === 'me') return prepareAnswerContextChange();
        stopDictation('interrupted');
        resetAiAnswerForContextChange();
        return true;
    }

    function pickDifferentQuestion() {
        var currentText = currentQuestion().text;
        var occupied = session.questionTrail.map(function (question, index) {
            return index === session.currentQuestionIndex ? '' : question.text;
        });
        function tailored(question) {
            return tailorQuestionForContext(normalizedQuestion(question, session.family), session.context);
        }
        var pool = localBlueprintsFor(session.family, session.level).map(tailored).filter(function (question) {
            return question.text !== currentText &&
                occupied.indexOf(question.text) === -1 &&
                session.replacementSeen.indexOf(question.text) === -1;
        });
        if (!pool.length) {
            session.replacementSeen = [];
            pool = localBlueprintsFor(session.family, session.level).map(tailored).filter(function (question) {
                return question.text !== currentText && occupied.indexOf(question.text) === -1;
            });
        }
        if (!pool.length) return null;
        var preferred = preferredCompetenciesByLevel[session.level] || [];
        var preferredPool = pool.filter(function (question) {
            return preferred.indexOf(question.competency) !== -1;
        });
        if (preferredPool.length) pool = preferredPool;
        return pool[0];
    }

    function replaceCurrentQuestion(question, message) {
        if (currentQuestionIsCompleted()) {
            announce('This answer is already in your practice history. Choose the next question to keep this record intact.');
            return false;
        }
        session.replacementSeen.push(currentQuestion().text);
        session.replacementSeen = session.replacementSeen.slice(-Math.max(20, questions.length));
        /* Callers hand over final text: pickDifferentQuestion already tailored
           the bank question, and a custom question is the visitor's own words.
           Tailoring again here double-applies the role fallback sentence. */
        session.questionTrail[session.currentQuestionIndex] =
            normalizedQuestion(question, session.family);
        session.attemptNumber = 1;
        if (session.mode === 'video') {
            releaseMedia(true);
            resetVideoUi();
        }
        persistSession();
        renderQuestion();
        focusCurrentQuestionWorkspace();
        announce(message);
        return true;
    }

    all('[data-is-different-question]').forEach(function (button) {
        button.addEventListener('click', function () {
            if (currentQuestionIsCompleted()) {
                announce('Choose the next question to keep this reviewed answer in your history.');
                return;
            }
            if (!prepareCurrentQuestionChange('Discard the active recording or transcript draft and load a different question?')) return;
            var replacement = pickDifferentQuestion();
            if (!replacement) {
                announce('No other unused question matches this session yet. Change the experience or question family to widen the pool.');
                return;
            }
            replaceCurrentQuestion(replacement, 'A different ' + labelFamily(replacement.family).toLowerCase() + ' question is ready.');
        });
    });

    var customQuestionDialog = one('[data-is-custom-question-dialog]');
    var customQuestionForm = one('[data-is-custom-question-form]');
    var customQuestionInput = one('[data-is-custom-question]');
    var customQuestionTrigger = null;

    function closeCustomQuestion(options) {
        options = options || {};
        stopDictation('interrupted');
        if (customQuestionDialog.open && typeof customQuestionDialog.close === 'function') customQuestionDialog.close();
        else customQuestionDialog.removeAttribute('open');
        if (options.restoreFocus !== false && customQuestionTrigger && document.contains(customQuestionTrigger)) customQuestionTrigger.focus();
    }

    all('[data-is-create-question]').forEach(function (button) {
        button.addEventListener('click', function () {
            if (currentQuestionIsCompleted()) {
                announce('Move to an unanswered question before creating a replacement.');
                return;
            }
            stopDictation('interrupted');
            customQuestionTrigger = button;
            customQuestionInput.value = '';
            if (typeof customQuestionDialog.showModal === 'function') customQuestionDialog.showModal();
            else customQuestionDialog.setAttribute('open', '');
            window.requestAnimationFrame(function () {
                autoGrowTextarea(customQuestionInput);
                customQuestionInput.focus();
            });
        });
    });

    one('[data-is-custom-question-close]').addEventListener('click', function () { closeCustomQuestion(); });
    one('[data-is-custom-question-cancel]').addEventListener('click', function () { closeCustomQuestion(); });
    customQuestionDialog.addEventListener('cancel', function (event) {
        event.preventDefault();
        closeCustomQuestion();
    });
    customQuestionDialog.addEventListener('click', function (event) {
        if (event.target === customQuestionDialog) closeCustomQuestion();
    });
    customQuestionInput.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
        event.preventDefault();
        if (typeof customQuestionForm.requestSubmit === 'function') customQuestionForm.requestSubmit();
    });
    customQuestionForm.addEventListener('submit', function (event) {
        event.preventDefault();
        stopDictation('interrupted');
        var value = customQuestionInput.value.trim();
        if (!value) {
            customQuestionInput.focus();
            return;
        }
        if (!prepareCurrentQuestionChange('Replace the current question with your custom question?')) return;
        var custom = {
            text: value,
            family: session.family === 'mixed' ? 'behavioral' : session.family,
            competency: 'Custom',
            levels: [session.level],
            custom: true
        };
        closeCustomQuestion({ restoreFocus: false });
        replaceCurrentQuestion(custom, 'Your custom question is ready in this browser session.');
    });

    var nudgeController = null;
    var nudgeQuestion = '';

    function clearNudgeState() {
        if (nudgeController) nudgeController.abort();
        nudgeController = null;
        nudgeQuestion = '';
        all('[data-is-nudge-open]').forEach(function (button) { button.setAttribute('aria-expanded', 'false'); });
        all('[data-is-nudge-panel]').forEach(function (panel) {
            setHidden(panel, true);
            var list = one('[data-is-nudge-list]', panel);
            if (list) list.replaceChildren();
            text(one('[data-is-nudge-status]', panel), 'Hints will stay focused on this question.');
            setHidden(one('[data-is-nudge-retry]', panel), true);
        });
    }

    function renderNudges(panel, hints) {
        var list = one('[data-is-nudge-list]', panel);
        list.replaceChildren();
        hints.forEach(function (hint) {
            var item = document.createElement('li');
            item.textContent = hint;
            list.appendChild(item);
        });
        text(one('[data-is-nudge-status]', panel), 'AI-generated hints — use what helps; the answer still needs to be yours.');
        setHidden(one('[data-is-nudge-retry]', panel), true);
    }

    function requestNudges(panel) {
        if (nudgeController) nudgeController.abort();
        nudgeController = new AbortController();
        nudgeQuestion = currentQuestion().text;
        text(one('[data-is-nudge-status]', panel), 'Preparing a few question-specific hints…');
        setHidden(one('[data-is-nudge-retry]', panel), true);
        postJSON('/api/interview/nudge', {
            profile_slug: profileSlug,
            question: nudgeQuestion,
            level: session.level,
            family: currentQuestion().family,
            competency: currentQuestion().competency,
            practice_mode: session.mode,
            opportunity_context: explicitContextForAi()
        }, nudgeController.signal).then(function (payload) {
            nudgeController = null;
            if (nudgeQuestion !== currentQuestion().text) return;
            renderNudges(panel, payload.hints || []);
            announce('Question hints ready.');
        }).catch(function (error) {
            nudgeController = null;
            if (error.name === 'AbortError') return;
            text(one('[data-is-nudge-status]', panel), error.message + ' Your question is unchanged.');
            setHidden(one('[data-is-nudge-retry]', panel), false);
            announce('Question hints could not be prepared. You can try again.');
        });
    }

    all('[data-is-nudge-open]').forEach(function (button) {
        button.addEventListener('click', function () {
            var panel = one('[data-is-nudge-panel]', button.closest('.is__context-actions'));
            var opening = panel.hidden;
            all('[data-is-nudge-panel]').forEach(function (candidate) { setHidden(candidate, true); });
            all('[data-is-nudge-open]').forEach(function (candidate) { candidate.setAttribute('aria-expanded', 'false'); });
            if (!opening) return;
            setHidden(panel, false);
            button.setAttribute('aria-expanded', 'true');
            requestNudges(panel);
        });
    });
    all('[data-is-nudge-retry]').forEach(function (button) {
        button.addEventListener('click', function () { requestNudges(button.closest('[data-is-nudge-panel]')); });
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
                if (!response.ok) {
                    var error = new Error(payload.error || 'That request did not complete.');
                    error.status = response.status;
                    throw error;
                }
                return payload;
            });
        });
    }

    function postReviewWithOneRetry(body, signal) {
        return postJSON('/api/interview/review', body, signal).catch(function (error) {
            if (signal.aborted || [500, 502, 503].indexOf(error.status) === -1) throw error;
            var reviewingCopy = one('[data-is-reviewing] strong');
            text(reviewingCopy, 'The first coaching pass was incomplete. Retrying once…');
            announce('The first coaching pass was incomplete. Retrying once while your answer stays preserved.');
            return postJSON('/api/interview/review', body, signal);
        });
    }

    function readHistoryStore() {
        var stored = readJSON(historyKey, []);
        return Array.isArray(stored) ? stored : [];
    }

    function safeHistoryText(value, maximum) {
        return typeof value === 'string' ? value.trim().slice(0, maximum) : '';
    }

    function safeHistoryDimensions(value, family) {
        var expected = FAMILY_DIMENSIONS[normalizeFamily(family)] || [];
        if (!Array.isArray(value) || value.length !== expected.length) return [];
        var seen = {};
        var dimensions = [];
        for (var index = 0; index < value.length; index += 1) {
            var dimension = value[index];
            if (!dimension || typeof dimension !== 'object' || Array.isArray(dimension)) return [];
            var key = safeHistoryText(dimension.key, 80);
            var status = safeHistoryText(dimension.status, 40).toLowerCase();
            var rationale = safeHistoryText(dimension.rationale, 400);
            var nextAction = safeHistoryText(dimension.nextAction, 300);
            if (expected.indexOf(key) === -1 || seen[key] || DIMENSION_STATUSES.indexOf(status) === -1 || !rationale || !nextAction) return [];
            seen[key] = true;
            dimensions.push({ key: key, status: status, rationale: rationale, nextAction: nextAction });
        }
        return dimensions.length === expected.length ? dimensions : [];
    }

    function sanitizeHistoryRecord(record) {
        if (!record || typeof record !== 'object' || Array.isArray(record)) return null;
        var id = safeHistoryText(record.id, 160);
        var question = safeHistoryText(record.question, 1200);
        var createdAt = safeHistoryText(record.createdAt, 80);
        if (!id || !question || !createdAt || Number.isNaN(new Date(createdAt).getTime())) return null;
        var family = normalizeFamily(record.family);
        var mode = record.mode === 'video' ? 'video' : 'me';
        var context = makeSessionContext(
            record.context && typeof record.context === 'object' && !Array.isArray(record.context)
                ? record.context
                : {}
        );
        var dimensions = safeHistoryDimensions(record.dimensions, family);
        // A browser-local video take is not a legacy score. Only an explicitly
        // migrated record or a record carrying a legacy score field gets the
        // legacy label; an unreviewed local take remains a local-only state.
        var hasLegacyScore = record.reviewVersion === 'legacy-v1' ||
            ['overallScore', 'score', 'star', 'targetAverage'].some(function (key) {
                return Object.prototype.hasOwnProperty.call(record, key);
            });
        var reviewVersion = record.reviewVersion === 'v2' && dimensions.length
            ? 'v2'
            : hasLegacyScore || record.reviewVersion == null
                    ? 'legacy-v1'
                    : mode === 'video' && !record.verdict
                        ? 'local-recording'
                    : 'invalid-local';
        var experience = ['entry', 'experienced', 'management', 'leadership', 'mixed'].indexOf(record.experience) !== -1
            ? record.experience
            : ['entry', 'experienced', 'management', 'leadership', 'mixed'].indexOf(record.level) !== -1
                ? record.level
                : 'experienced';
        return {
            id: id,
            createdAt: createdAt,
            mode: mode,
            question: question,
            family: family,
            competency: safeHistoryText(record.competency, 80) || 'Communication',
            reviewVersion: reviewVersion,
            dimensions: dimensions,
            answer: safeHistoryText(record.answer, 5000),
            verdict: safeHistoryText(record.verdict, 160),
            encouragement: safeHistoryText(record.encouragement, 600),
            whatCameThroughClearly: Array.isArray(record.whatCameThroughClearly) ? record.whatCameThroughClearly.filter(function (item) { return typeof item === 'string'; }).slice(0, 4) : [],
            strengths: Array.isArray(record.strengths) ? record.strengths.filter(function (item) { return typeof item === 'string'; }).slice(0, 4) : [],
            improvements: Array.isArray(record.improvements) ? record.improvements.filter(function (item) { return typeof item === 'string'; }).slice(0, 4) : [],
            strongerApproach: safeHistoryText(record.strongerApproach, 900),
            focusedFollowUp: safeHistoryText(record.focusedFollowUp, 300),
            context: context,
            contextIdentity: stableContextIdentity(context),
            sessionContextId: safeHistoryText(record.sessionContextId, 80) || context.context_id,
            sessionId: safeSessionInstanceId(record.sessionId),
            experience: experience,
            attemptNumber: Number.isFinite(record.attemptNumber) ? Math.max(1, Math.floor(record.attemptNumber)) : 1,
            durationSeconds: Number.isFinite(record.durationSeconds) ? Math.max(0, Math.floor(record.durationSeconds)) : 0,
            status: safeHistoryText(record.status, 120) || (reviewVersion === 'v2' ? 'Completed' : 'Local browser record')
        };
    }

    // Read untrusted browser storage through one non-destructive boundary. The
    // raw V1/V2 array is never rewritten simply because one entry is malformed.
    function readHistoryRecords() {
        return readHistoryStore().map(sanitizeHistoryRecord).filter(Boolean);
    }

    function addHistoryRecord(record) {
        var records = readHistoryStore();
        records.unshift(record);
        writeJSON(historyKey, records.slice(0, 100));
    }

    function updateHistoryRecord(recordId, updates) {
        var found = false;
        var records = readHistoryStore().map(function (record) {
            if (!record || typeof record !== 'object' || Array.isArray(record) || record.id !== recordId) return record;
            found = true;
            return Object.assign({}, record, updates, { createdAt: record.createdAt });
        });
        if (found) writeJSON(historyKey, records);
        return found;
    }

    function removeHistoryRecord(recordId) {
        if (!recordId) return;
        var records = readHistoryStore().filter(function (record) {
            return !record || typeof record !== 'object' || Array.isArray(record) || record.id !== recordId;
        });
        writeJSON(historyKey, records);
    }

    // A review list can legitimately be empty: the coach sets a maximum of four
    // bullets, never a minimum, so a genuinely weak answer can return zero
    // strengths. When a caller supplies emptyMessage the absence is stated
    // plainly instead of leaving a heading above an empty box.
    function renderList(element, items, emptyMessage) {
        if (!element) return;
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

    function readableDimensionKey(key) {
        return String(key || '').replace(/_/g, ' ').replace(/(^|\s)(\S)/g, function (_match, prefix, letter) {
            return prefix + letter.toUpperCase();
        });
    }

    function renderReview(review) {
        session.currentReview = review;
        text(one('[data-is-review-focus]'), (review.improvements && review.improvements[0]) || EMPTY_IMPROVEMENTS_MESSAGE);
        text(one('[data-is-priority-improvement]'), (review.improvements && review.improvements[0]) || EMPTY_IMPROVEMENTS_MESSAGE);
        text(one('[data-is-verdict]'), review.verdict);
        text(one('[data-is-encouragement]'), review.encouragement);
        renderList(one('[data-is-clear-points]'), review.whatCameThroughClearly || [], 'The coach did not identify a clear signal yet.');
        renderList(one('[data-is-strengths]'), review.strengths, EMPTY_STRENGTHS_MESSAGE);
        renderList(one('[data-is-improvements]'), review.improvements, EMPTY_IMPROVEMENTS_MESSAGE);
        text(one('[data-is-stronger-approach]'), review.strongerApproach || '');
        text(one('[data-is-focused-follow-up]'), review.focusedFollowUp || '');

        var dimensions = one('[data-is-dimensions]');
        if (dimensions) {
            dimensions.replaceChildren();
            (review.dimensions || []).forEach(function (dimension) {
                var li = document.createElement('li');
                li.setAttribute('data-status', dimension.status);
                var name = document.createElement('strong');
                name.textContent = readableDimensionKey(dimension.key);
                var status = document.createElement('span');
                status.className = 'is__dimension-status';
                status.textContent = dimension.status;
                var rationale = document.createElement('small');
                rationale.textContent = dimension.rationale;
                var nextAction = document.createElement('small');
                nextAction.className = 'is__dimension-next';
                nextAction.textContent = 'Next: ' + dimension.nextAction;
                li.append(name, status, rationale, nextAction);
                dimensions.appendChild(li);
            });
        }

        var suggestionSection = one('[data-is-evidence-suggestions]');
        var suggestionOptions = one('[data-is-evidence-options]');
        if (!suggestionSection || !suggestionOptions) return;
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
        /* Never leave the microphone listening once the answer has been sent. */
        stopDictation('interrupted');
        var responseText = answer.value.trim();
        if (!responseText) {
            announce('Type or dictate an answer before submitting it for review.');
            answer.focus();
            return;
        }
        saveDraft(false);
        session.currentAnswer = responseText;
        text(one('[data-is-submitted-text]'), responseText);
        setHidden(answeringBlock, true);
        answer.readOnly = true;
        answeringBlock.setAttribute('aria-busy', 'true');
        reviewButton.disabled = true;
        setHidden(submittedBlock, false);
        setHidden(reviewingBlock, false);
        text(one('[data-is-reviewing] strong'), 'Preparing your coaching review');
        setHidden(feedbackBlock, true);
        setHidden(feedbackEmpty, false);
        setHidden(feedbackContent, true);
        setHidden(improveBlock, true);
        setHidden(improveEmpty, false);
        setHidden(improveContent, true);
        setHidden(reviewError, true);
        setHidden(errorActions, true);
        text(submittedLabel, 'Your submitted answer · preserved');
        setStage(2);
        cancelReviewButton.focus();
        cancelPendingReview();
        reviewController = new AbortController();
        var controller = reviewController;
        var requestId = reviewRequestId;
        var reviewSource = session.reviewSource || 'me';
        var reviewRecordId = session.reviewRecordId || '';

        var question = currentQuestion();
        postReviewWithOneRetry({
            profile_slug: profileSlug,
            question: question.text,
            answer: responseText,
            level: session.level,
            family: question.family,
            competency: question.competency,
            opportunity_context: explicitContextForAi()
        }, controller.signal).then(function (payload) {
            if (requestId !== reviewRequestId) return;
            reviewController = null;
            answer.readOnly = false;
            answeringBlock.removeAttribute('aria-busy');
            syncAnswerState();
            setHidden(reviewingBlock, true);
            setStage(3);
            renderReview(payload.review);
            if (session.reviewedQuestionIds.indexOf(questionId(question)) === -1) {
                session.reviewedQuestionIds.push(questionId(question));
                persistSession();
                renderSessionProgress();
            }
            setHidden(feedbackBlock, false);
            setHidden(feedbackEmpty, true);
            setHidden(feedbackContent, false);
            var record = {
                id: reviewRecordId || 'attempt-' + Date.now() + '-' + session.attemptNumber,
                createdAt: new Date().toISOString(),
                mode: reviewSource,
                question: question.text,
                family: question.family,
                competency: question.competency,
                reviewVersion: 'v2',
                dimensions: payload.review.dimensions,
                answer: responseText,
                verdict: payload.review.verdict,
                encouragement: payload.review.encouragement,
                whatCameThroughClearly: payload.review.whatCameThroughClearly,
                strengths: payload.review.strengths,
                improvements: payload.review.improvements,
                strongerApproach: payload.review.strongerApproach,
                focusedFollowUp: payload.review.focusedFollowUp,
                context: {
                    kind: session.context.kind,
                    role_title: session.context.role_title,
                    interview_stage: session.context.interview_stage,
                    question_mix: session.context.question_mix,
                    opportunity_text_local: session.context.opportunity_text_local,
                    context_id: session.context.context_id
                },
                contextIdentity: stableContextIdentity(session.context),
                sessionContextId: session.context.context_id,
                sessionId: session.sessionId,
                experience: session.level,
                attemptNumber: session.attemptNumber,
                durationSeconds: reviewSource === 'video' ? (session.reviewDurationSeconds || 0) : 0,
                status: reviewSource === 'video' ? 'Content reviewed' : 'Completed'
            };
            if (!reviewRecordId || !updateHistoryRecord(reviewRecordId, record)) addHistoryRecord(record);
            removeStored(draftKey(question.text));
            announce('Coach review ready. Review the clear strengths and one focused next step.');
            feedbackBlock.focus({ preventScroll: true });
            feedbackBlock.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
        }).catch(function (error) {
            if (requestId !== reviewRequestId) return;
            reviewController = null;
            if (error.name === 'AbortError') return;
            answer.readOnly = false;
            answeringBlock.removeAttribute('aria-busy');
            syncAnswerState();
            setHidden(answeringBlock, false);
            setHidden(submittedBlock, true);
            setHidden(reviewingBlock, true);
            setHidden(feedbackBlock, true);
            setHidden(feedbackEmpty, false);
            setHidden(feedbackContent, true);
            setStage(1);
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
    cancelReviewButton.addEventListener('click', function () {
        cancelPendingReview();
        answer.readOnly = false;
        answeringBlock.removeAttribute('aria-busy');
        syncAnswerState();
        setHidden(reviewingBlock, true);
        setHidden(submittedBlock, true);
        setHidden(answeringBlock, false);
        setHidden(feedbackBlock, true);
        setHidden(improveBlock, true);
        setStage(1);
        answer.focus();
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
            announce('New Video Practice attempt ready. The original answer remains in browser-local History.');
            return;
        }
        session.attemptNumber += 1;
        answer.value = '';
        syncAnswerState();
        text(autosave, 'New attempt — original preserved in History');
        setHidden(submittedBlock, true);
        setHidden(feedbackBlock, true);
        setHidden(feedbackEmpty, false);
        setHidden(feedbackContent, true);
        setHidden(improveBlock, true);
        setHidden(improveEmpty, false);
        setHidden(improveContent, true);
        setHidden(answeringBlock, false);
        setStage(1);
        answer.focus();
        announce('New attempt started. Your original answer remains in browser-local History.');
    });

    function requestImprovement(selectedIds, additionalContext, statusMessage) {
        var draft = one('[data-is-improved-draft]');
        var useDraftButton = one('[data-is-use-draft]');
        var retryOutLoudButton = one('[data-is-retry-out-loud]');
        var previousEditableDraft = draft.value.trim() || session.currentAnswer;
        setHidden(improveError, true);
        draft.value = 'The coach is preparing an editable draft…';
        draft.disabled = true;
        autoGrowTextarea(draft);
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
            family: currentQuestion().family,
            improvements: session.currentReview.improvements,
            evidence_ids: selectedIds || [],
            additional_context: additionalContext || '',
            opportunity_context: explicitContextForAi()
        }, controller.signal).then(function (payload) {
            if (requestId !== improveRequestId) return;
            improveController = null;
            draft.disabled = false;
            useDraftButton.disabled = false;
            retryOutLoudButton.disabled = false;
            draft.value = payload.improvement.draft;
            autoGrowTextarea(draft);
            renderList(one('[data-is-changes]'), payload.improvement.changes);
            text(one('[data-is-make-yours-status]'), statusMessage || 'The draft is ready to edit. Nothing has replaced your original answer.');
            announce('Coach-assisted draft ready. Review and edit it before using it.');
        }).catch(function (error) {
            if (requestId !== improveRequestId) return;
            improveController = null;
            if (error.name === 'AbortError') return;
            draft.disabled = false;
            useDraftButton.disabled = false;
            retryOutLoudButton.disabled = false;
            draft.value = previousEditableDraft;
            autoGrowTextarea(draft);
            text(improveError, error.message + ' Your original answer has not changed.');
            setHidden(improveError, false);
            text(one('[data-is-make-yours-status]'), 'That update did not complete. Your original answer and the last editable draft remain available.');
            announce('The improved draft could not be generated. Your original answer is unchanged.');
        });
    }

    one('[data-is-improve]').addEventListener('click', function () {
        if (!session.currentReview || !session.currentAnswer) return;
        setStage(4);
        setHidden(improveEmpty, true);
        setHidden(improveContent, false);
        setHidden(feedbackBlock, true);
        setHidden(submittedBlock, true);
        setHidden(improveBlock, false);
        setHidden(improveError, true);
        setHidden(one('[data-is-answer-context-form]'), true);
        one('[data-is-add-answer-context]').setAttribute('aria-expanded', 'false');
        text(one('[data-is-make-yours-status]'), 'Start with the coach-assisted structure, then choose whether to add verified context.');
        improveBlock.focus({ preventScroll: true });
        text(one('[data-is-original-answer]'), session.currentAnswer);
        requestImprovement([], '', 'Basic coach-assisted draft ready. Add only context you can verify.');
    });

    one('[data-is-use-history-context]').addEventListener('click', function () {
        var choices = all('[data-is-evidence-choice]');
        if (!choices.length) {
            text(one('[data-is-make-yours-status]'), 'No clearly relevant approved public-history item was found for this answer. Add a real detail instead, or keep editing the draft.');
            announce('No relevant approved public history was found for this answer.');
            return;
        }
        choices.forEach(function (choice) { choice.checked = true; });
        requestImprovement(choices.map(function (choice) { return choice.value; }), '', 'Draft updated with the selected approved public-history context. Verify every sentence before using it.');
    });

    one('[data-is-add-answer-context]').addEventListener('click', function (event) {
        var form = one('[data-is-answer-context-form]');
        var opening = form.hidden;
        setHidden(form, !opening);
        event.currentTarget.setAttribute('aria-expanded', opening ? 'true' : 'false');
        if (opening) one('[data-is-answer-context]').focus();
    });
    one('[data-is-answer-context-cancel]').addEventListener('click', function () {
        setHidden(one('[data-is-answer-context-form]'), true);
        one('[data-is-add-answer-context]').setAttribute('aria-expanded', 'false');
        one('[data-is-add-answer-context]').focus();
    });
    one('[data-is-answer-context-form]').addEventListener('submit', function (event) {
        event.preventDefault();
        var context = one('[data-is-answer-context]').value.trim();
        if (!context) {
            one('[data-is-answer-context]').focus();
            return;
        }
        var selectedIds = all('[data-is-evidence-choice]:checked').map(function (item) { return item.value; });
        requestImprovement(selectedIds, context, 'Draft updated with the context you supplied. Verify the wording before using it.');
        setHidden(event.currentTarget, true);
        one('[data-is-add-answer-context]').setAttribute('aria-expanded', 'false');
    });

    one('[data-is-back-feedback]').addEventListener('click', function () {
        cancelPendingImprovement();
        setHidden(improveBlock, true);
        setHidden(submittedBlock, false);
        setHidden(feedbackBlock, false);
        setStage(3);
        feedbackBlock.focus({ preventScroll: true });
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
        setHidden(improveBlock, true);
        setHidden(feedbackBlock, true);
        setHidden(submittedBlock, true);
        setHidden(answeringBlock, false);
        setStage(1);
        answer.focus();
        announce('AI-assisted draft copied into a new editable attempt. Nothing was published.');
    });

    one('[data-is-improved-draft]').addEventListener('input', function (event) {
        autoGrowTextarea(event.currentTarget);
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
        one('[data-is-camera-enable]').focus();
        announce('Video Practice opened for a new out-loud attempt.');
    });

    /* ------------------------------------------------------------------
       Speech input.

       One browser-local dictation path, shared by every Studio text field.
       Recognition, microphone permission, timers, restart handling, and
       caret insertion live in the shared static/js/dictation.js module,
       which this template loads first. What follows is only this room's
       binding of that module to the Studio's own markup and copy: the
       data-is-* attributes below are Interview Studio's contract, not the
       module's.

       Transcription is performed by the visitor's browser; no audio is sent
       to or retained by PeerSlate, and nothing here writes a canonical record.
       This deliberately remains the single dictation path on this route -
       PS-VOICE-001 private Voice Capture is a separate authenticated system
       and must not be reimplemented here.

       Behaviour contract: click to start, keep listening, stop on a second
       click, and auto-stop after the module's silence deadline.
       ------------------------------------------------------------------ */
    var dictationModule = window.PeerSlateDictation || null;

    function speechIsSupported() {
        return Boolean(dictationModule && dictationModule.isSupported());
    }
    function showMicError(kind, message) {
        var errorTarget = one('[data-is-mic-error="' + kind + '"]');
        if (!errorTarget) return;
        text(errorTarget, message);
        setHidden(errorTarget, false);
    }
    function setDictationStatus(kind, message) {
        var statusTarget = one('[data-is-dictation-status="' + kind + '"]');
        if (!statusTarget) return;
        text(statusTarget, message || '');
        setHidden(statusTarget, !message);
    }
    function setDictationInterim(kind, value) {
        var interimTarget = one('[data-is-dictation-interim="' + kind + '"]');
        if (!interimTarget) return;
        text(one('[data-is-dictation-interim-text]', interimTarget), value || '');
        setHidden(interimTarget, !value);
    }
    function dictationLabel(kind) {
        if (kind === 'custom') return 'Dictate a custom interview question';
        if (kind === 'followup') return 'Dictate a follow-up question';
        if (kind === 'video') return 'Dictate your answer transcript';
        return 'Dictate your answer';
    }
    function dictationNoun(kind) {
        if (kind === 'custom') return 'question';
        if (kind === 'followup') return 'follow-up question';
        if (kind === 'video') return 'transcript';
        return 'answer';
    }
    function dictationTarget(kind) {
        if (kind === 'custom') return one('[data-is-custom-question]');
        if (kind === 'followup') return one('[data-is-follow-up]');
        if (kind === 'video') return one('[data-is-video-transcript]');
        return answer;
    }
    /* One controller owns "at most one microphone at a time" across every
       Studio field. The module writes button state, timers, and the caret
       insertion; these callbacks are the only place that knows the Studio's
       data-is-* markup. friendlyMediaError is shared with camera rehearsal
       below, so it stays here and is handed to the module. */
    var dictation = dictationModule ? dictationModule.createController({
        announce: announce,
        mediaErrorMessage: friendlyMediaError
    }) : null;

    function stopDictation(reason) {
        if (dictation) dictation.stop(reason);
    }
    function toggleDictation(kind) {
        if (dictation) dictation.toggle(kind);
    }

    all('[data-is-mic]').forEach(function (button) {
        var kind = button.getAttribute('data-is-mic');
        button.setAttribute('aria-pressed', 'false');
        if (dictation) {
            dictation.register(kind, {
                button: button,
                resolveTarget: function () { return dictationTarget(kind); },
                label: dictationLabel(kind),
                listeningLabel: 'Stop dictation',
                noun: dictationNoun(kind),
                setStatus: function (message) { setDictationStatus(kind, message); },
                setInterim: function (value) { setDictationInterim(kind, value); },
                showError: function (message) { showMicError(kind, message); },
                hideError: function () { setHidden(one('[data-is-mic-error="' + kind + '"]'), true); },
                setButtonLabel: function (value) {
                    var labelNode = one('[data-is-mic-label]', button);
                    if (labelNode) text(labelNode, value);
                }
            });
        }
        button.addEventListener('click', function () { toggleDictation(kind); });
    });
    if (!speechIsSupported()) {
        all('[data-is-mic]').forEach(function (button) {
            button.setAttribute('aria-disabled', 'true');
            button.disabled = true;
            button.classList.add('is-unavailable');
            setDictationStatus(button.getAttribute('data-is-mic'), 'Speech input is not supported in this browser. Typing works normally.');
        });
    }
    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape' || !dictation || !dictation.isActive()) return;
        stopDictation('manual');
    });
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) stopDictation('interrupted');
    });

    /* Interview AI */
    var aiForm = one('[data-is-ai-form]');
    var aiQuestionInput = one('[data-is-ai-question]');
    var aiAnswerBlock = one('[data-is-ai-answer]');
    var aiAnswerEmpty = one('[data-is-ai-answer-empty]');
    var aiAnswerContent = one('[data-is-ai-answer-content]');
    var aiLoading = one('[data-is-ai-loading]');
    var aiError = one('[data-is-ai-error]');
    var modeGroup = aiModeControl;
    var modeSelect = one('[data-is-ai-mode]', modeGroup);
    if (modeSelect) {
        var modeNote = one('[data-is-ai-mode-note]');
        var basisLabel = one('[data-is-ai-basis-label]');
        var basisGuidance = one('[data-is-ai-basis-guidance]');
        var publicHistoryBasisLabel = basisLabel ? basisLabel.textContent : 'Approved public history';
        var modeNotes = {
            best_practice: 'A generic, clearly labeled example — no personal history is used.',
            member_history: 'Grounded only in the approved public history.',
            compare: 'Both answers, stacked — study the structural lessons.'
        };
        var modeLabels = {
            best_practice: 'Illustrative best-practice example',
            member_history: publicHistoryBasisLabel,
            compare: 'Comparison of best practice and approved public history'
        };
        var modeGuidance = {
            best_practice: 'No personal history is used.',
            member_history: 'Verify the generated wording before using it.',
            compare: 'Each answer remains separately labeled and must be verified.'
        };
        modeGroup.addEventListener('change', function (event) {
            if (event.target !== modeSelect) return;
            stopDictation('interrupted');
            if (modeNote) modeNote.textContent = modeNotes[event.target.value] || '';
            if (basisLabel) basisLabel.textContent = modeLabels[event.target.value] || '';
            if (basisGuidance) basisGuidance.textContent = modeGuidance[event.target.value] || '';
            resetAiAnswerForContextChange();
            announce((modeLabels[event.target.value] || 'Answer basis') + ' selected. Generate a new answer for this basis.');
        });
    }

    var followUpForm = one('[data-is-follow-up-form]');
    var followUpInput = one('[data-is-follow-up]');
    var followUpSubmit = one('[data-is-follow-up-submit]');
    var followUpMic = one('[data-is-mic="followup"]');
    var followUpOpen = one('[data-is-follow-up-open]');
    var followUpNote = one('[data-is-follow-up-note]');
    var followUpError = one('[data-is-follow-up-error]');
    var currentModelAnswer = null;
    var currentAiQuestion = '';
    var currentModelQuestion = '';
    var currentModelContextToken = '';
    var aiController = null;
    var aiRequestId = 0;

    function setAiState(state) {
        root.setAttribute('data-is-ai-state', state);
    }

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
        if (followUpMic) followUpMic.disabled = true;
        followUpOpen.disabled = true;
        text(followUpNote, 'Generate the first answer to unlock follow-up questions grounded in the same evidence.');
        setHidden(followUpError, true);
        setHidden(aiError, true);
        setAiState('empty');
    }

    function selectedAiMode() {
        return modeSelect ? modeSelect.value : 'member_history';
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
            heading.textContent = insufficient
                ? 'No grounded answer available'
                : generic
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
        setHidden(followUpError, true);
        setHidden(aiAnswerBlock, false);
        setHidden(aiAnswerEmpty, true);
        setHidden(aiAnswerContent, false);
        setAiState(insufficient ? 'insufficient' : 'ready');
        var followUpAvailable = !insufficient && Boolean(currentModelContextToken);
        followUpInput.disabled = !followUpAvailable;
        followUpSubmit.disabled = !followUpAvailable;
        if (followUpMic) followUpMic.disabled = !followUpAvailable || !speechIsSupported();
        followUpOpen.disabled = !followUpAvailable;
        text(followUpNote, insufficient
            ? 'Follow-up is unavailable because no approved-history example was returned.'
            : 'Ask a follow-up grounded in the current answer context.');
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
            setHidden(aiAnswerEmpty, true);
            setHidden(aiAnswerContent, true);
            followUpInput.disabled = true;
            followUpSubmit.disabled = true;
        }
        setHidden(aiError, true);
        setHidden(followUpError, true);
        setHidden(aiLoading, false);
        setAiState('generating');
        postJSON('/api/interview/model-answer', {
            profile_slug: profileSlug,
            question: currentAiQuestion,
            follow_up: followUp || '',
            context_token: followUp ? currentModelContextToken : '',
            level: session.level,
            family: session.family,
            mode: selectedAiMode(),
            opportunity_context: explicitContextForAi()
        }, controller.signal).then(function (payload) {
            if (requestId !== aiRequestId) return;
            aiController = null;
            currentModelQuestion = practiceQuestion;
            renderModelAnswer(payload);
            if (followUp && followUpInput.value.trim() === followUp) followUpInput.value = '';
        }).catch(function (error) {
            if (requestId !== aiRequestId) return;
            aiController = null;
            if (error.name === 'AbortError') return;
            setHidden(aiLoading, true);
            var failureTarget = followUp && currentModelAnswer ? followUpError : aiError;
            text(failureTarget, error.message + (followUp ? ' Your first answer is preserved. Edit the follow-up and try again.' : ''));
            setHidden(failureTarget, false);
            if (currentModelAnswer) {
                setHidden(aiAnswerEmpty, true);
                setHidden(aiAnswerContent, false);
                var followUpAvailable = currentModelAnswer.status !== 'insufficient' && Boolean(currentModelContextToken);
                followUpInput.disabled = !followUpAvailable;
                followUpSubmit.disabled = !followUpAvailable;
                if (followUpMic) followUpMic.disabled = !followUpAvailable || !speechIsSupported();
                followUpOpen.disabled = !followUpAvailable;
                if (followUp) text(followUpNote, 'The first answer is still here. Revise the follow-up or try it again.');
            } else {
                setHidden(aiAnswerEmpty, true);
                setHidden(aiAnswerContent, true);
            }
            setAiState(currentModelAnswer ? 'ready' : 'failure');
            announce('Interview AI could not complete that answer.');
        });
    }

    aiForm.addEventListener('submit', function (event) {
        event.preventDefault();
        if (!modelAnswersEnabled) {
            announce('Interview AI is not available for this profile.');
            return;
        }
        stopDictation('interrupted');
        resetAiAnswerForContextChange();
        requestModelAnswer('');
    });
    followUpOpen.addEventListener('click', function () {
        if (followUpOpen.disabled || followUpInput.disabled) {
            announce('Follow-up is unavailable for this answer.');
            return;
        }
        var followUp = followUpForm;
        followUp.classList.add('is-emphasized');
        followUp.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
        window.setTimeout(function () {
            followUpInput.focus();
            followUp.classList.remove('is-emphasized');
        }, reduceMotion ? 0 : 350);
        announce('Follow-up question field ready. It will keep the same answer source.');
    });
    followUpForm.addEventListener('submit', function (event) {
        event.preventDefault();
        stopDictation('interrupted');
        var followUp = followUpInput.value.trim();
        if (!followUp) return;
        if (!currentModelContextToken) {
            announce('Generate an answer before asking a follow-up.');
            return;
        }
        requestModelAnswer(followUp);
    });
    followUpInput.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
        event.preventDefault();
        if (typeof followUpForm.requestSubmit === 'function') followUpForm.requestSubmit();
    });
    one('[data-is-practice-answer]').addEventListener('click', function () {
        if (!currentModelAnswer) return;
        var modelAnswer = currentModelAnswer;
        var modelQuestion = currentModelQuestion || currentAiQuestion || aiQuestionInput.value.trim();
        var storedTargetDraft = readJSON(draftKey(modelQuestion), null);
        var targetDraftText = storedTargetDraft && typeof storedTargetDraft.text === 'string'
            ? storedTargetDraft.text.trim()
            : '';
        if (!targetDraftText && currentQuestion().text === modelQuestion) targetDraftText = answer.value.trim();
        var confirmationEnabled = one('[data-is-confirm-navigation]');
        if (targetDraftText && confirmationEnabled && confirmationEnabled.checked &&
                !window.confirm('Start a fresh attempt for this question? The existing browser draft will be replaced, but the model answer remains optional reference only.')) {
            announce('Practice transfer cancelled. The existing draft is unchanged.');
            return;
        }
        if (!setMode('me', true)) return;
        session.questionTrail[session.currentQuestionIndex] = normalizedQuestion({
            text: modelQuestion,
            family: session.family,
            competency: 'Communication',
            custom: true
        }, session.family);
        session.aiReference = modelAnswer.answer;
        session.aiReferenceQuestion = session.questionTrail[session.currentQuestionIndex].text;
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
        durationSeconds: 0,
        permissionRequestId: 0,
        returnFocusAfterStop: false
    };
    var cameraPreview = one('[data-is-camera-preview]');
    var cameraEmpty = one('[data-is-camera-empty]');
    var cameraStatus = one('[data-is-camera-status]');
    var microphoneStatus = one('[data-is-mic-status]');
    var videoError = one('[data-is-video-error]');
    var cameraEnable = one('[data-is-camera-enable]');
    var startRecord = one('[data-is-record-start]');
    var stopRecord = one('[data-is-record-stop]');
    var retakeRecord = one('[data-is-record-retake]');
    var discardRecord = one('[data-is-record-discard]');
    var videoResult = one('[data-is-video-result]');
    var videoResultEmpty = one('[data-is-video-result-empty]');
    var videoResultContent = one('[data-is-video-result-content]');
    var videoTranscript = one('[data-is-video-transcript]');
    var videoTranscriptForm = one('[data-is-video-transcript-form]');
    var videoReviewContent = one('[data-is-video-review-content]');

    function setVideoState(state) {
        root.setAttribute('data-is-video-state', state);
        var messages = {
            'camera-off': 'Camera and microphone have not been requested.',
            requesting: 'Your browser is requesting local camera and microphone access.',
            unavailable: 'A camera or microphone is unavailable. Transcript coaching still works.',
            denied: 'Permission was not granted. Review browser settings or use the transcript.',
            preview: 'Local preview is ready. Recording has not started.',
            recording: 'Recording is in progress on this device only.',
            stopping: 'Finalizing this recording locally. No upload is occurring.',
            playback: 'Local playback is ready until you leave or discard it.'
        };
        text(one('[data-is-video-state-copy]'), messages[state] || messages['camera-off']);
        syncQuestionChangeControls();
    }

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
        setVideoState('requesting');
        setDeviceStatus(cameraStatus, 'Requesting camera…');
        setDeviceStatus(microphoneStatus, 'Requesting microphone…');
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            text(videoError, 'Camera rehearsal is not supported in this browser.');
            setHidden(videoError, false);
            setDeviceStatus(cameraStatus, 'Camera unavailable', 'is-error');
            setDeviceStatus(microphoneStatus, 'Microphone unavailable', 'is-error');
            setVideoState('unavailable');
            videoTranscript.focus();
            return;
        }
        var permissionRequestId = ++media.permissionRequestId;
        navigator.mediaDevices.getUserMedia({
            video: true,
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        }).then(function (stream) {
            if (permissionRequestId !== media.permissionRequestId || session.mode !== 'video' || videoCapability === 'disabled') {
                stream.getTracks().forEach(function (track) { track.stop(); });
                return;
            }
            releaseMedia(false, true);
            if (!stream.getAudioTracks().some(function (track) { return track.readyState === 'live'; })) {
                stream.getTracks().forEach(function (track) { track.stop(); });
                throw { name: 'NotFoundError' };
            }
            media.stream = stream;
            cameraPreview.controls = false;
            cameraPreview.muted = true;
            cameraPreview.src = '';
            cameraPreview.srcObject = stream;
            cameraPreview.play().catch(function () { /* user gesture already granted */ });
            setHidden(cameraEmpty, true);
            setDeviceStatus(cameraStatus, 'Camera ready', 'is-ready');
            setDeviceStatus(microphoneStatus, 'Microphone ready', 'is-ready');
            setVideoState('preview');
            startRecord.disabled = !window.MediaRecorder;
            if (!window.MediaRecorder) {
                text(videoError, 'Live preview is ready, but recording is not supported in this browser.');
                setHidden(videoError, false);
            }
            if (startRecord.disabled) videoTranscript.focus();
            else startRecord.focus();
            announce('Camera and microphone ready. Recording has not started.');
        }).catch(function (error) {
            if (permissionRequestId !== media.permissionRequestId || session.mode !== 'video') return;
            var message = friendlyMediaError(error);
            text(videoError, message);
            setHidden(videoError, false);
            setDeviceStatus(cameraStatus, 'Camera unavailable', 'is-error');
            setDeviceStatus(microphoneStatus, 'Microphone unavailable', 'is-error');
            setVideoState('denied');
            cameraEnable.focus();
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
        stopDictation('interrupted');
        media.chunks = [];
        media.durationSeconds = 0;
        var mimeType = supportedMimeType();
        try {
            media.recorder = mimeType
                ? new MediaRecorder(media.stream, { mimeType: mimeType, audioBitsPerSecond: 128000, videoBitsPerSecond: 1800000 })
                : new MediaRecorder(media.stream, { audioBitsPerSecond: 128000, videoBitsPerSecond: 1800000 });
        } catch (error) {
            text(videoError, 'This browser could not create a compatible local recording.');
            setHidden(videoError, false);
            return;
        }
        media.recorder.ondataavailable = function (event) { if (event.data && event.data.size) media.chunks.push(event.data); };
        media.recorder.onstop = finishRecording;
        media.startedAt = Date.now();
        media.question = cloneQuestion(currentQuestion());
        try {
            media.recorder.start(1000);
        } catch (error) {
            media.recorder = null;
            /* Clear the take metadata set just above so a later transcript
               submit cannot attribute itself to this never-recorded question. */
            media.question = null;
            media.startedAt = 0;
            text(videoError, 'This browser could not start a compatible local recording.');
            setHidden(videoError, false);
            return;
        }
        setVideoState('recording');
        setHidden(one('[data-is-recording-badge]'), false);
        setHidden(startRecord, true);
        setHidden(stopRecord, false);
        setHidden(retakeRecord, true);
        setHidden(discardRecord, false);
        setHidden(videoResult, true);
        setHidden(videoResultEmpty, false);
        setHidden(videoResultContent, true);
        stopRecord.focus();
        media.timer = window.setInterval(function () {
            var seconds = Math.floor((Date.now() - media.startedAt) / 1000);
            text(one('[data-is-recording-time]'), formatDuration(seconds));
            if (seconds >= 180) stopRecording();
        }, 250);
        announce('Recording started. Maximum duration is three minutes.');
    }

    function stopRecording() {
        if (!media.recorder || media.recorder.state !== 'recording') return;
        media.returnFocusAfterStop = document.activeElement === stopRecord;
        setVideoState('stopping');
        stopRecord.disabled = true;
        text(stopRecord, 'Finalizing locally…');
        media.recorder.stop();
        announce('Finalizing the local recording. Nothing is being uploaded.');
    }

    function finishRecording() {
        window.clearInterval(media.timer);
        media.timer = null;
        var moveFocusToPlaybackActions = media.returnFocusAfterStop;
        media.returnFocusAfterStop = false;
        var recordedQuestion = media.question || cloneQuestion(currentQuestion());
        var durationSeconds = Math.max(1, Math.round((Date.now() - media.startedAt) / 1000));
        var blob = new Blob(media.chunks, { type: media.recorder && media.recorder.mimeType ? media.recorder.mimeType : 'video/webm' });
        if (!blob.size) {
            text(videoError, 'The browser created an empty recording. Your camera and microphone are released; enable them and try again.');
            setHidden(videoError, false);
            releaseMedia(true);
            resetVideoUi({ preserveTranscript: true });
            announce('The local recording was empty. No media was retained.');
            return;
        }
        if (media.playbackUrl) URL.revokeObjectURL(media.playbackUrl);
        media.playbackUrl = URL.createObjectURL(blob);
        if (media.stream) media.stream.getTracks().forEach(function (track) { track.stop(); });
        media.stream = null;
        cameraPreview.srcObject = null;
        cameraPreview.src = media.playbackUrl;
        cameraPreview.muted = false;
        cameraPreview.defaultMuted = false;
        cameraPreview.volume = 1;
        cameraPreview.controls = true;
        cameraPreview.addEventListener('error', function playbackError() {
            cameraPreview.removeEventListener('error', playbackError);
            text(videoError, 'This browser recorded the take but could not play that local format. Record another take in a supported browser.');
            setHidden(videoError, false);
        });
        setHidden(cameraEmpty, true);
        setHidden(one('[data-is-recording-badge]'), true);
        setHidden(stopRecord, true);
        stopRecord.disabled = false;
        text(stopRecord, 'Stop Recording');
        setHidden(startRecord, true);
        setHidden(retakeRecord, false);
        setHidden(discardRecord, false);
        text(one('[data-is-video-duration]'), formatDuration(durationSeconds));
        setHidden(videoResult, false);
        setHidden(videoResultEmpty, true);
        setHidden(videoResultContent, false);
        setDeviceStatus(cameraStatus, 'Local recording complete', 'is-ready');
        setDeviceStatus(microphoneStatus, 'Audio captured locally', 'is-ready');
        media.durationSeconds = durationSeconds;
        media.recorder = null;
        media.chunks = [];
        setVideoState('playback');
        if (moveFocusToPlaybackActions) retakeRecord.focus();
        announce('Recording complete. Local playback is ready. No upload or analysis occurred. Submit a transcript only if you want a meaningful reviewed outcome in browser-local History. Submitting the transcript removes the local recording.');
    }

    function resetVideoUi(options) {
        options = options || {};
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
        stopRecord.disabled = false;
        text(stopRecord, 'Stop Recording');
        setHidden(retakeRecord, true);
        setHidden(discardRecord, true);
        setHidden(videoResult, true);
        setHidden(videoResultEmpty, false);
        setHidden(videoResultContent, true);
        media.question = null;
        media.durationSeconds = 0;
        media.returnFocusAfterStop = false;
        if (!options.preserveTranscript) videoTranscript.value = '';
        videoReviewContent.disabled = !writtenPracticeEnabled || !videoTranscript.value.trim();
        autoGrowTextarea(videoTranscript);
        setDeviceStatus(cameraStatus, 'Camera not requested');
        setDeviceStatus(microphoneStatus, 'Microphone not requested');
        setVideoState('camera-off');
    }

    cameraEnable.addEventListener('click', enableCamera);
    one('[data-is-device-settings]').addEventListener('click', function () {
        if (!prepareVideoContextChange('Discard the current local recording or transcript draft and reopen device settings?')) return;
        releaseMedia(true);
        resetVideoUi();
        enableCamera();
    });
    startRecord.addEventListener('click', startRecording);
    stopRecord.addEventListener('click', stopRecording);
    retakeRecord.addEventListener('click', function () {
        if (!window.confirm('Record another take? The current local recording will be deleted. Transcript text will stay.')) return;
        releaseMedia(true);
        resetVideoUi({ preserveTranscript: true });
        cameraEnable.focus();
        enableCamera();
    });
    discardRecord.addEventListener('click', function () {
        if (!window.confirm('Delete this local recording? Any transcript text will stay in the composer.')) return;
        releaseMedia(true);
        resetVideoUi({ preserveTranscript: true });
        cameraEnable.focus();
        announce('Local recording discarded. No browser-history record was created. Transcript text was preserved.');
    });
    videoTranscript.addEventListener('input', function () {
        videoReviewContent.disabled = !writtenPracticeEnabled || !videoTranscript.value.trim();
        autoGrowTextarea(videoTranscript);
    });
    videoTranscriptForm.addEventListener('submit', function (event) {
        event.preventDefault();
        stopDictation('interrupted');
        var transcript = videoTranscript.value.trim();
        if (!writtenPracticeEnabled || !transcript) {
            videoTranscript.focus();
            announce('Type, paste, or dictate a transcript before submitting it for review.');
            return;
        }
        var recordedQuestion = media.question ? cloneQuestion(media.question) : cloneQuestion(currentQuestion());
        var durationSeconds = media.durationSeconds;
        videoTranscript.value = '';
        autoGrowTextarea(videoTranscript);
        /* Submitting the transcript is the explicit hand-off to coaching.
           Release the local take now so the leave-video guard cannot raise a
           misleading discard prompt in the middle of the user's own submit. */
        releaseMedia(true);
        resetVideoUi();
        if (!setMode('me', true)) {
            videoTranscript.value = transcript;
            autoGrowTextarea(videoTranscript);
            videoReviewContent.disabled = false;
            return;
        }
        session.questionTrail[session.currentQuestionIndex] = normalizedQuestion(recordedQuestion, recordedQuestion.family || session.family);
        persistSession();
        renderQuestion();
        session.reviewSource = 'video';
        session.reviewRecordId = '';
        session.reviewDurationSeconds = durationSeconds;
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
    window.addEventListener('pagehide', function () {
        releaseMedia(true);
        if (media.playbackUrl) {
            URL.revokeObjectURL(media.playbackUrl);
            media.playbackUrl = null;
        }
    });

    /* History and growth from real browser records only */
    var historyMode = one('[data-is-history-mode]');
    var historyCompetency = one('[data-is-history-competency]');
    var historyTime = one('[data-is-history-time]');
    var storageNote = one('[data-is-storage-note]');
    var storageOk = one('[data-is-storage-ok]');
    var historyDetail = one('[data-is-history-detail]');
    var historyDetailRecordId = '';
    var historyDetailOpenedWithPush = false;
    var historyRecommendation = null;

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
        text(one('[data-is-history-detail-coaching]'), record.reviewVersion === 'v2'
            ? 'Question-aware coaching'
            : record.reviewVersion === 'local-recording'
                ? 'Local recording — no coaching or analysis'
                : record.reviewVersion === 'legacy-v1'
                    ? 'Legacy scored review — excluded from V2 trends'
                    : 'Unavailable local record — excluded from trends');
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
        var records = readHistoryRecords();
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

    // V2 history deliberately avoids an overall score. It only compares
    // completed, family-aware reviews and explains when the local evidence is
    // too thin to describe a trend.
    function statusRank(status) {
        return { missing: 0, developing: 1, clear: 2, strong: 3 }[status] == null
            ? -1
            : { missing: 0, developing: 1, clear: 2, strong: 3 }[status];
    }

    function v2ReviewedRecords(records) {
        return records.filter(function (record) {
            return record && record.reviewVersion === 'v2' && Array.isArray(record.dimensions);
        });
    }

    function comparableContextKey(record) {
        var context = record && record.context ? record.context : {};
        return [
            normalizeFamily(record && record.family),
            String(record && record.experience || 'experienced'),
            String(record && record.contextIdentity || stableContextIdentity(context)),
            String(context.interview_stage || 'general'),
            String(context.question_mix || normalizeFamily(record && record.family))
        ].join('\u001f');
    }

    function comparableDimensionGroups(records) {
        var groups = {};
        records.slice().reverse().forEach(function (record) {
            record.dimensions.forEach(function (dimension) {
                if (!dimension || statusRank(dimension.status) < 0) return;
                var groupKey = comparableContextKey(record) + '\u001f' + dimension.key;
                if (!groups[groupKey]) groups[groupKey] = [];
                groups[groupKey].push({ record: record, dimension: dimension });
            });
        });
        return groups;
    }

    function renderV2History() {
        var hasStorage = storageAvailable();
        setHidden(storageNote, hasStorage);
        setHidden(storageOk, !hasStorage);
        var allRecords = readHistoryRecords();
        populateHistoryCompetencies(allRecords);
        var records = filteredHistory(allRecords);
        var reviewed = v2ReviewedRecords(records);
        var legacyCount = records.filter(function (record) { return record && record.reviewVersion === 'legacy-v1'; }).length;
        var localRecordingCount = records.filter(function (record) { return record && record.reviewVersion === 'local-recording'; }).length;
        var families = reviewed.map(function (record) { return normalizeFamily(record.family); })
            .filter(function (family, index, list) { return list.indexOf(family) === index; });
        var groups = comparableDimensionGroups(reviewed);
        var groupKeys = Object.keys(groups);
        var carryThrough = groupKeys.filter(function (key) {
            var entries = groups[key];
            if (entries.length < 2) return false;
            return statusRank(entries[0].dimension.status) < 2 &&
                statusRank(entries[entries.length - 1].dimension.status) >= 2;
        });
        var focusGroup = groupKeys.filter(function (key) { return groups[key].length >= 2; })
            .sort(function (left, right) {
                return statusRank(groups[left][groups[left].length - 1].dimension.status) -
                    statusRank(groups[right][groups[right].length - 1].dimension.status);
        })[0];
        var focusDimension = focusGroup && groups[focusGroup][groups[focusGroup].length - 1].dimension;
        var focusRecord = focusGroup && groups[focusGroup][groups[focusGroup].length - 1].record;
        var focusFamily = focusRecord ? normalizeFamily(focusRecord.family) : session.family;
        var focusContext = focusRecord ? makeSessionContext(focusRecord.context) : session.context;
        var focusExperience = focusRecord ? focusRecord.experience : session.level;
        var recommendation = nextLocalQuestion(focusFamily, focusExperience, session.questionTrail, [], focusContext);
        historyRecommendation = {
            question: recommendation,
            family: focusFamily,
            level: focusExperience,
            context: focusContext
        };
        var recommendationReason = focusDimension
            ? 'Practice ' + readableDimensionKey(focusDimension.key) + ' in another ' + labelFamily(focusFamily).toLowerCase() + ' answer.'
            : 'Not enough comparable practice yet. Try one more answer in a question family you want to strengthen.';

        text(one('[data-is-history-count]'), reviewed.length);
        text(one('[data-is-history-coverage]'), families.length + (families.length === 1 ? ' family practiced' : ' families practiced'));
        text(one('[data-is-history-carry-through]'), carryThrough.length
            ? carryThrough.length + (carryThrough.length === 1 ? ' coaching improvement carried forward' : ' coaching improvements carried forward')
            : 'Not enough comparable practice yet.');
        text(one('[data-is-history-next-focus]'), focusDimension
            ? readableDimensionKey(focusDimension.key)
            : 'Choose one question family');
        text(one('[data-is-history-summary-label]'), 'History summary: ' + reviewed.length + (reviewed.length === 1 ? ' reviewed answer, ' : ' reviewed answers, ') + families.length + (families.length === 1 ? ' question family practiced, ' : ' question families practiced, ') + (carryThrough.length ? carryThrough.length + ' coaching improvement carried forward.' : 'not enough comparable practice yet.'));
        text(one('[data-is-recommendation-reason]'), recommendationReason);
        text(one('[data-is-recommendation-question]'), recommendation.text);
        var practiceButton = one('[data-is-practice-recommendation]');
        if (practiceButton) practiceButton.dataset.question = recommendation.text;

        var empty = one('[data-is-history-empty]');
        var list = one('[data-is-session-list]');
        setHidden(empty, records.length > 0);
        setHidden(list, records.length === 0);
        if (list) {
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
                meta.textContent = (record.mode === 'video' ? 'Video Practice' : 'Interview Me') + ' / ' + labelFamily(record.family) + ' / ' + (record.status || 'Completed');
                body.append(title, meta);
                var result = document.createElement('b');
                result.textContent = record.reviewVersion === 'v2' ? 'Reviewed' : record.reviewVersion === 'local-recording' ? 'Local only' : record.reviewVersion === 'legacy-v1' ? 'Legacy' : 'Unavailable';
                row.append(date, body, result);
                row.addEventListener('click', function (event) {
                    event.preventDefault();
                    openHistoryDetail(record, true);
                });
                list.appendChild(row);
            });
        }

        var growthEmpty = one('[data-is-growth-empty]');
        var growthList = one('[data-is-growth-list]');
        if (growthList) {
            growthList.replaceChildren();
            var trendGroups = groupKeys.filter(function (key) { return groups[key].length >= 2; });
            setHidden(growthEmpty, trendGroups.length > 0);
            trendGroups.slice(0, 5).forEach(function (key) {
                var entries = groups[key];
                var first = entries[0].dimension;
                var last = entries[entries.length - 1].dimension;
                var row = document.createElement('div');
                row.className = 'is__growth-row';
                var label = document.createElement('span');
                label.textContent = labelFamily(entries[entries.length - 1].record.family) + ': ' + readableDimensionKey(last.key);
                var value = document.createElement('b');
                var changed = statusRank(last.status) - statusRank(first.status);
                value.textContent = changed > 0 ? 'Improving' : changed < 0 ? 'Needs attention' : 'Holding steady';
                var detail = document.createElement('i');
                detail.textContent = first.status + ' to ' + last.status;
                detail.setAttribute('aria-label', label.textContent + ': ' + detail.textContent);
                row.append(label, value, detail);
                growthList.appendChild(row);
            });
        }
        var legacyNote = one('[data-is-history-legacy-note]');
        if (legacyNote) {
            text(legacyNote, legacyCount
                ? legacyCount + (legacyCount === 1 ? ' legacy scored review is kept for reference but excluded from new trends.' : ' legacy scored reviews are kept for reference but excluded from new trends.')
                : localRecordingCount
                    ? localRecordingCount + (localRecordingCount === 1 ? ' local recording is kept without coaching and excluded from trends.' : ' local recordings are kept without coaching and excluded from trends.')
                    : 'Only score-free, question-aware reviews are used for these trends.');
        }
    }

    function renderHistory() {
        renderV2History();
    }

    function completedSessionRecords() {
        var sessionId = session.sessionId;
        return readHistoryRecords().filter(function (record) {
            return record.reviewVersion === 'v2' && record.sessionId === sessionId;
        });
    }

    function renderSessionComplete() {
        closeQueue({ restoreFocus: false });
        var records = completedSessionRecords();
        var completeTitle = contextLabel(session.context) + ' session complete.';
        text(one('[data-is-complete-title]'), completeTitle);
        text(one('[data-is-complete-summary]'), records.length
            ? 'You completed an open-ended practice session with ' + records.length + (records.length === 1 ? ' reviewed answer.' : ' reviewed answers.')
            : 'You finished an open-ended practice session. No reviewed answer was added, and any typed draft remains in this browser.');
        text(one('[data-is-complete-reviewed]'), records.length);
        text(one('[data-is-complete-questions]'), session.questionTrail.length);
        text(one('[data-is-complete-context]'), contextLabel(session.context));
        var list = one('[data-is-complete-list]');
        var empty = one('[data-is-complete-empty]');
        setHidden(empty, records.length > 0);
        setHidden(list, records.length === 0);
        if (list) {
            list.replaceChildren();
            records.forEach(function (record) {
                var item = document.createElement('li');
                var question = document.createElement('strong');
                question.textContent = record.question;
                var status = document.createElement('span');
                status.textContent = record.status + ' · ' + labelFamily(record.family);
                item.append(question, status);
                list.appendChild(item);
            });
        }
        var latest = records[0];
        text(one('[data-is-complete-next-focus]'), latest && latest.improvements && latest.improvements[0]
            ? latest.improvements[0]
            : 'Complete a reviewed answer to see one focused next practice suggestion.');
        panels.forEach(function (panel) { panel.hidden = panel.getAttribute('data-is-panel') !== 'complete'; });
        root.setAttribute('data-is-active-mode', 'complete');
        if (historyLink) historyLink.removeAttribute('aria-current');
        var title = one('[data-is-complete-title]');
        if (title) {
            title.setAttribute('tabindex', '-1');
            title.focus();
        }
        announce('Session complete. Your reviewed answers remain only in this browser.');
    }

    function finishCurrentSession() {
        stopDictation('interrupted');
        if (session.mode === 'me') {
            persistCurrentAnswerDraft();
            cancelPendingReview();
            cancelPendingImprovement();
        }
        if (session.mode === 'video' && !prepareVideoContextChange('Finish this session and discard the current local recording or transcript draft?')) return;
        if (session.mode === 'video') {
            /* A live camera preview passes the discard guard untouched; the
               camera must still stop when the session ends. */
            releaseMedia(true);
            resetVideoUi();
        }
        if (session.mode === 'ai') cancelPendingAi(true);
        renderSessionComplete();
    }

    all('[data-is-finish-session]').forEach(function (button) {
        button.addEventListener('click', finishCurrentSession);
    });
    var completePracticeNext = one('[data-is-complete-practice-next]');
    if (completePracticeNext) completePracticeNext.addEventListener('click', function () {
        var mode = modeIsEnabled(session.mode) ? session.mode : 'me';
        if (!setMode(mode, true)) return;
        if (currentQuestionIsCompleted()) advanceQuestion(mode);
        else renderQuestion();
        if (mode === 'me') answer.focus();
        else if (mode === 'video') cameraEnable.focus();
    });
    var completeNewSession = one('[data-is-complete-new-session]');
    if (completeNewSession) completeNewSession.addEventListener('click', function () {
        if (sessionKindSelect) {
            sessionKindSelect.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
            sessionKindSelect.focus();
        }
    });

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

    one('[data-is-practice-recommendation]').addEventListener('click', function (event) {
        var recommendation = historyRecommendation || {
            question: defaultQuestion,
            family: session.family,
            level: session.level,
            context: session.context
        };
        if (!setMode('me', true)) return;
        session.family = normalizeFamily(recommendation.family);
        session.level = recommendation.level;
        session.context = makeSessionContext(recommendation.context);
        if (familySelect) familySelect.value = session.family;
        if (levelSelect) levelSelect.value = session.level;
        if (stageSelect) stageSelect.value = session.context.interview_stage;
        if (sessionStageSelect) sessionStageSelect.value = session.context.interview_stage;
        if (sessionMixSelect) sessionMixSelect.value = session.family;
        syncNewSessionInputs();
        session.questionTrail.push(normalizedQuestion(recommendation.question, session.family));
        session.currentQuestionIndex = session.questionTrail.length - 1;
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
        removeHistoryRecord(historyDetailRecordId);
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
    var settingsOpen = one('[data-is-settings-open]');
    var settingsClose = one('[data-is-settings-close]');
    if (settingsOpen && settingsDialog) {
        settingsOpen.addEventListener('click', function () {
            if (typeof settingsDialog.showModal === 'function') settingsDialog.showModal();
            else settingsDialog.setAttribute('open', '');
        });
    }
    if (settingsClose && settingsDialog) settingsClose.addEventListener('click', function () { settingsDialog.close(); });
    if (settingsDialog) settingsDialog.addEventListener('click', function (event) { if (event.target === settingsDialog) settingsDialog.close(); });
    function clearLocalData() {
        if (!window.confirm('Clear Interview Studio drafts and history stored in this browser, and discard any active local recording?')) return;
        stopDictation('interrupted');
        cancelPendingReview();
        cancelPendingImprovement();
        cancelPendingAi(true);
        releaseMedia(true);
        resetVideoUi();
        try {
            Object.keys(window.localStorage).forEach(function (key) {
                if (key.indexOf(storagePrefix) === 0 || key.indexOf(legacyStoragePrefix) === 0) {
                    window.localStorage.removeItem(key);
                }
            });
        } catch (error) { /* storage unavailable */ }
        session.questionTrail = [nextLocalQuestion('behavioral', 'experienced', [], [], makeSessionContext())];
        session.currentQuestionIndex = 0;
        session.level = 'experienced';
        session.family = 'behavioral';
        session.context = makeSessionContext();
        session.sessionId = newSessionInstanceId();
        session.aiReference = '';
        session.aiReferenceQuestion = '';
        session.reviewedQuestionIds = [];
        session.replacementSeen = [];
        levelSelect.value = session.level;
        familySelect.value = session.family;
        resetAiAnswerForContextChange();
        /* The New Session form and rail selects must mirror the reset context,
           or the next start would silently re-apply the cleared choices. */
        syncNewSessionInputs();
        renderQuestion();
        renderHistory();
        if (settingsDialog) settingsDialog.close();
        announce('Interview Studio browser data cleared.');
    }
    all('[data-is-clear-local], [data-is-history-clear-local]').forEach(function (button) {
        button.addEventListener('click', clearLocalData);
    });

    /* A Need an example link may open Interview AI in a new tab. Carry the
       exact current question through the URL without exposing any answer text. */
    var incomingQuestion = new URLSearchParams(window.location.search).get('question');
    if (initialMode === 'ai' && incomingQuestion && incomingQuestion.trim() && incomingQuestion.length <= 300) {
        var incomingMatch = questions.filter(function (item) { return item.text === incomingQuestion.trim(); })[0];
        session.questionTrail[session.currentQuestionIndex] = incomingMatch
            ? cloneQuestion(incomingMatch)
            : {
                text: incomingQuestion.trim(),
                family: normalizeFamily(session.family),
                competency: 'Custom',
                levels: [session.level],
                custom: true,
                id: questionId({ family: session.family, text: incomingQuestion.trim() })
            };
    }

    /* Initial render */
    renderQuestion();
    refreshAutogrow();
    syncModeControls(initialMode);
    if (initialView === 'history') {
        showHistoryView();
    } else if (!isOrientation) {
        // Orientation is server-rendered correctly (panel visible, tabs
        // deselected/unroled, controls hidden) and needs no JS patch-up.
        setMode(initialMode, false);
    }
})();
