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
    /* PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001 slice 2: an opaque,
       per-member browser storage namespace the server renders only once an
       identity is resolved (data-storage-scope absent on the public page).
       This value is trusted for namespacing only — a cache scope, never an
       authorization input. */
    var storageScope = root.getAttribute('data-storage-scope') || '';
    /* PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001 slices 3-4: selects
       the append-only consequence-stack rendering path and the authenticated
       shell's copy/behavior deltas. Absent (false) on the public flag-off
       page -- every branch below is additive and leaves that page's
       behavior byte-for-byte unchanged. */
    var authenticated = root.hasAttribute('data-authenticated');
    var studioUrl = root.getAttribute('data-studio-url') || '/interview-studio';
    var live = one('[data-is-live]');
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var storagePrefix = storageScope
        ? 'peerslate:interview-studio:' + storageScope + ':v3'
        : 'peerslate:interview-studio:' + profileSlug + ':v1';
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
    /* PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001 slice 2: a scoped
       (signed-in) render keeps the v3 member namespace computed above — it
       is never re-derived from the anonymous v1/v2 profileSlug prefix here.
       The public (unscoped) page keeps advancing to its own v2 namespace,
       unchanged. */
    if (!storageScope) {
        storagePrefix = 'peerslate:interview-studio:' + profileSlug + ':v2';
        historyKey = storagePrefix + ':history';
        sessionKey = storagePrefix + ':session';
    }

    function migrateLegacyBrowserState() {
        /* V2 uses its own keys so a failed migration never destroys V1 local
           work. Copy browser-only drafts and history once, leaving the V1 copy
           intact until the visitor clears local Studio data.

           A scoped (member) namespace never adopts, reads, or deletes the
           anonymous v1/v2 records (owner decision Q-B) — this returns before
           touching a single legacy key when a scope is present. */
        if (storageScope) return;
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

    /* Slice 3: the authenticated rail's CURRENT SESSION summary rows need a
       readable experience-level label even though that composition drops
       the standalone [data-is-level] select (not part of the locked rail;
       see SLICE_NOTES.md). Mirrors the retired select's own option text. */
    function labelExperienceLevel(value) {
        return {
            entry: 'Entry level',
            experienced: 'Experienced',
            management: 'Management',
            leadership: 'Leadership',
            mixed: 'Mixed'
        }[value] || 'Experienced';
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
    // A scoped (member) namespace never reads the anonymous v1 session key —
    // no adoption of legacy browser records into a signed-in account.
    var restoredSession = persistedSession && Array.isArray(persistedSession.questionTrail) && persistedSession.questionTrail.length
        ? persistedSession
        : (storageScope ? null : migrateLegacySession(readJSON(legacySessionKey, null)));
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
        /* Page-local and deliberately not persisted: it only has to separate
           requests made by this page in this browsing session. */
        requestSeq: 0,
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
        // PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001 slice 2: reuse the
        // draft-save failure pattern (capture the write result, do not drop
        // it) rather than silently continuing as if the session had saved.
        // Full visual states for this come in slice 5; this is the minimal
        // truthful surface for now.
        var saved = writeJSON(sessionKey, {
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
        if (!saved) announce('Your session progress could not be saved in this browser right now.');
        updateSetupSummary();
        return saved;
    }
    if (shouldPersistRecoveredSession) persistSession();
    function updateSetupSummary() {
        var summary = one('[data-is-setup-summary-text]');
        var levelOption = levelSelect && levelSelect.options[levelSelect.selectedIndex];
        var levelLabel = levelOption ? levelOption.text : labelExperienceLevel(session.level);
        if (summary) {
            summary.textContent = contextLabel(session.context) + ' / ' + labelInterviewStage(session.context.interview_stage) + ' / ' + levelLabel + ' / ' + labelFamily(session.family) + ' / open session';
        }
        text(one('[data-is-session-level]'), levelLabel);
        text(one('[data-is-session-family]'), labelFamily(session.family));
        text(one('[data-is-rail-context]'), contextLabel(session.context));
        text(one('[data-is-rail-stage]'), 'Stage: ' + labelInterviewStage(session.context.interview_stage));
        text(one('[data-is-rail-mix]'), 'Mix: ' + labelFamily(session.family));
        /* Slice 3 authenticated rail: five discrete CURRENT SESSION rows
           (visuals 01-12, 15-17) instead of the public page's one
           slash-joined summary line. */
        text(one('[data-is-rail-summary-context]'), contextLabel(session.context));
        text(one('[data-is-rail-summary-stage]'), labelInterviewStage(session.context.interview_stage) + ' stage');
        text(one('[data-is-rail-summary-level]'), levelLabel);
        text(one('[data-is-rail-summary-family]'), labelFamily(session.family));
    }

    function currentQuestion() {
        return session.questionTrail[session.currentQuestionIndex] || defaultQuestion;
    }

    var modeTabs = all('[data-is-mode]');
    /* The public header uses .is__modes; the authenticated rail's tablist is
       .is-auth__modes (never both in the same render). Falling back keeps
       the existing role="tablist" bookkeeping (below, and in
       showHistoryView()/showOrientationView()) and roving-tabindex arrow-key
       navigation working for the authenticated branch too -- slice 3 left
       this null for authenticated, which silently dropped both. */
    var modeNavigation = one('.is__modes') || one('.is-auth__modes');
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
        /* The action band's question/coaching groups belong to the drafting and
           processing stages. Deriving that from the stage machine (rather than
           toggling it at each individual call site) is what keeps it from being
           left hidden when a member moves to the next question -- the defect
           that stranded the page with no visible way to submit after the first
           review. The send control itself now lives inside the composer, so it
           can never be orphaned by this again. */
        if (authenticated) {
            var stageBand = one('.is-auth__band');
            if (stageBand) setHidden(stageBand, stage >= 3);
        }
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
    /* Slice 4 (visual 03): "We couldn't review this answer right now." vs
       the flag-off "Coaching could not be completed." No new data-is-*
       attribute is added to this shared, unconditional element (it would
       change the byte-comparable public render) -- the heading is found
       structurally instead, exactly like the JS already does for the
       error text next to it. */
    var reviewErrorHeading = reviewError ? one('strong', reviewError) : null;
    var errorActions = one('[data-is-error-actions]');
    var retryCoachingButton = one('[data-is-retry-coaching]');
    var keepEditingButton = one('[data-is-keep-editing]');
    if (authenticated) {
        text(retryCoachingButton, 'Try review again');
        text(keepEditingButton, 'Continue editing');
    }
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
        /* Architecture 03 section 4, item 2: releaseMedia() itself must
           guarantee playbackUrl revocation on every discard/teardown path
           rather than relying on every caller to separately remember to call
           resetVideoUi() afterward (every current call site already does,
           but that is caller discipline, not a structural guarantee -- a
           future call site that discards media without resetting the UI
           would otherwise leak the object URL until pagehide). Revoking here
           too is a harmless no-op wherever resetVideoUi() already revoked it
           (media.playbackUrl is already null by then). */
        if (discardRecording && media.playbackUrl) {
            URL.revokeObjectURL(media.playbackUrl);
            media.playbackUrl = null;
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
        /* Slice 3: the authenticated setup form is a focused attached
           surface that starts (and stays, across mode switches) hidden
           until "Change setup"/"New session"/"Session" explicitly opens it
           -- unlike the public page, where this bar is always shown. */
        if (!authenticated) setHidden(controls, false);
        if (historyLink) historyLink.removeAttribute('aria-current');
        syncModeControls(mode);
        syncModeToggle(mode);
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

    /* R1 (slice 5-6 review): below the rail breakpoint, the mode nav is a
       collapsed "Interview Me ▾" dropdown (locked visual 13), not three
       reflowed pills. This wraps the SAME tablist markup (no duplicate
       data-is-mode elements, so the click/keydown wiring above already
       covers activation) -- only visible below the CSS breakpoint; on the
       desktop rail modeToggle stays display:none and modePicker never opens. */
    var modePicker = one('[data-is-mode-picker]');
    var modeToggle = one('[data-is-mode-toggle]');
    var modeToggleLabel = one('[data-is-mode-toggle-label]');
    var modeToggleIcon = one('[data-is-mode-toggle-icon]');

    function closeModePicker(returnFocus) {
        if (!modePicker) return;
        modePicker.setAttribute('data-is-open', 'false');
        if (modeToggle) modeToggle.setAttribute('aria-expanded', 'false');
        if (returnFocus && modeToggle) modeToggle.focus();
    }
    function modePickerIsOpen() {
        return Boolean(modePicker && modePicker.getAttribute('data-is-open') === 'true');
    }
    function syncModeToggle(mode) {
        if (!modeToggle) return;
        var activeTab = modeTabs.filter(function (tab) { return tab.getAttribute('data-is-mode') === mode; })[0];
        if (!activeTab) return;
        var label = one('span', activeTab);
        if (modeToggleLabel && label) modeToggleLabel.textContent = label.textContent.trim();
        var sourceIcon = one('svg', activeTab);
        if (modeToggleIcon && sourceIcon) modeToggleIcon.innerHTML = sourceIcon.innerHTML;
    }
    if (modeToggle && modePicker) {
        modeToggle.addEventListener('click', function () {
            if (modePickerIsOpen()) {
                closeModePicker(false);
                return;
            }
            modePicker.setAttribute('data-is-open', 'true');
            modeToggle.setAttribute('aria-expanded', 'true');
        });
        document.addEventListener('click', function (event) {
            if (!modePickerIsOpen() || modePicker.contains(event.target)) return;
            closeModePicker(false);
        });
        modePicker.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && modePickerIsOpen()) {
                event.preventDefault();
                closeModePicker(true);
            }
        });
        modeTabs.forEach(function (tab) {
            tab.addEventListener('click', function () { closeModePicker(false); });
        });
        syncModeToggle(session.mode);
    }

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
        setAuthPendingBand(false);
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
        if (authenticated) resetConsequenceStack();
        setStage(1);
        syncAnswerState();
    }

    function restoreDraft() {
        var stored = readJSON(draftKey(currentQuestion().text), null);
        answer.value = stored && typeof stored.text === 'string' ? stored.text : '';
        syncAnswerState();
        if (answer.value) {
            setAutosaveState('restored', 'Restored from this browser');
        } else {
            setAutosaveState('ready', 'Draft ready');
        }
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
            /* The href is kept current on both branches. On the
               authenticated page the click is intercepted below and the
               example opens in place, but leaving a real destination here
               means the control still works without JavaScript, and the
               public branch keeps its existing navigation untouched. */
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

    // The locked authenticated card shows only the word count in steady
    // state; the autosave line surfaces visually only while saving or on a
    // real failure (state attribute consumed by the authenticated CSS —
    // public rendering is unchanged because public CSS ignores it).
    function setAutosaveState(state, message) {
        if (!autosave) return;
        autosave.setAttribute('data-autosave-state', state);
        text(autosave, message);
    }

    function saveDraft(showStatus) {
        window.clearTimeout(autosaveTimer);
        autosaveTimer = null;
        if (showStatus) setAutosaveState('saving', 'Saving…');
        var ok = writeJSON(draftKey(currentQuestion().text), {
            text: answer.value,
            savedAt: new Date().toISOString()
        });
        if (ok) {
            setAutosaveState('saved', 'Saved in this browser');
        } else {
            setAutosaveState('failed', 'Save failed — your text is still here');
        }
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
            setAutosaveState('ready', 'Draft ready');
        }
    }

    answer.addEventListener('input', function () {
        syncAnswerState();
        setAutosaveState('saving', 'Saving…');
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
        if (authenticated) {
            if (sessionSetupSection) setHidden(sessionSetupSection, true);
            setFinishSessionCompleted(false);
        }
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
    var sessionSetupSection = one('[data-is-session-setup]');
    all('[data-is-new-session-focus]').forEach(function (newSessionFocus) {
        newSessionFocus.addEventListener('click', function () {
            /* Slice 3: the authenticated rail's "Change setup"/"New
               session"/"Session" controls are the only way to reach the
               setup form -- it starts hidden (architecture 03 section 6,
               "focused attached surface") instead of sitting permanently
               above the question like the public page. */
            if (authenticated && sessionSetupSection) {
                setHidden(sessionSetupSection, false);
                sessionSetupSection.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
            }
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

    // PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001 slice 2: each mutator
    // now returns the real write outcome (the draft-save failure pattern)
    // instead of discarding it, so a caller can surface a truthful result
    // rather than claim a save/delete that did not happen. Full visual
    // states for this come in slice 5.
    function addHistoryRecord(record) {
        var records = readHistoryStore();
        records.unshift(record);
        return writeJSON(historyKey, records.slice(0, 100));
    }

    function updateHistoryRecord(recordId, updates) {
        var found = false;
        var records = readHistoryStore().map(function (record) {
            if (!record || typeof record !== 'object' || Array.isArray(record) || record.id !== recordId) return record;
            found = true;
            return Object.assign({}, record, updates, { createdAt: record.createdAt });
        });
        if (!found) return false;
        return writeJSON(historyKey, records);
    }

    function removeHistoryRecord(recordId) {
        if (!recordId) return true;
        var records = readHistoryStore().filter(function (record) {
            return !record || typeof record !== 'object' || Array.isArray(record) || record.id !== recordId;
        });
        return writeJSON(historyKey, records);
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

    /* =======================================================================
       Slice 4: the authenticated Interview Me append-only consequence stack
       (architecture 03 section 1-2). Everything in this block only runs
       when `authenticated` is true. It is purely additive: renderReview,
       requestImprovement, and every fixed-slot element above remain exactly
       as written for the flag-off public page, and this block never edits
       them -- it builds separate DOM nodes fed by the same validated
       server payloads and appends them into the stack instead.
       ======================================================================= */

    /* Request binding (slice 4 item 6): extends the existing epoch counters
       (reviewRequestId/improveRequestId) with the session/context/question/
       attempt identity that was active when the request was made. A late
       response is dropped if ANY element changed, not only the epoch --
       closing the mode/question-change races a bare integer counter alone
       cannot see. */
    /* requestSeq is a strictly monotonic counter for THIS page's review
       requests. It exists so the binding no longer has to lean on
       attemptNumber to tell two submissions apart.

       That distinction is what made the attempt-counter drift awkward to fix.
       attemptNumber used to be incremented speculatively before a revision was
       sent, and a failed review left it incremented, so a retry labelled the
       snapshot one attempt high. Rolling it back on failure would have made
       two consecutive submissions produce an identical binding, which would
       re-open the stale-response acceptance path the binding exists to close.
       With a counter that only ever goes up, the two concerns are separated:
       requestSeq keeps late responses out, and attemptNumber is free to mean
       what it says -- the number of the attempt that has actually been
       reviewed. */
    function currentRequestBinding() {
        return {
            sessionId: session.sessionId,
            contextId: session.context.context_id,
            questionId: questionId(currentQuestion()),
            attemptNumber: session.attemptNumber,
            requestSeq: session.requestSeq
        };
    }
    function bindingStillCurrent(binding) {
        var now = currentRequestBinding();
        return binding.sessionId === now.sessionId
            && binding.contextId === now.contextId
            && binding.questionId === now.questionId
            && binding.attemptNumber === now.attemptNumber
            && binding.requestSeq === now.requestSeq;
    }

    function resetDraftBadge() {
        var badge = one('[data-is-draft-badge]');
        text(badge, 'Draft');
        if (badge) badge.classList.remove('is-auth__badge--warning');
    }

    /* Lock 03 failure composition: the retry pair replaces the primary
       INSIDE the action band ("Try review again" first, then "Continue
       editing"), and the red banner sits directly below the band. The
       public layout keeps its own arrangement, so this is a one-time
       authenticated DOM relocation, not shared-markup churn. */
    if (authenticated) (function () {
        var band = one('.is-auth__band');
        var errActions = one('[data-is-error-actions]');
        var alertBox = one('[data-is-review-error]');
        var retryBtn = one('[data-is-retry-coaching]');
        var keepBtn = one('[data-is-keep-editing]');
        /* The band is a sibling of the form (lock order: composer/submitted
           card first, band beneath), so it survives the pending state's
           form hide. The submit button keeps its form association by id. */
        var submittedCard = one('[data-is-submitted]');
        if (band && submittedCard) submittedCard.insertAdjacentElement('afterend', band);
        /* The send control now lives inside the composer, so it is inside the
           form already and needs no form association. */
        if (band && errActions) band.insertBefore(errActions, band.firstChild);
        if (band && alertBox) band.insertAdjacentElement('afterend', alertBox);
        if (retryBtn) retryBtn.textContent = 'Try review again';
        if (keepBtn) keepBtn.textContent = 'Continue editing';
        /* Lock order: card, band, then the transmission truth and the quiet
           dictation note beneath the band. */
        var transmitLine = one('.is-auth__transmit-line');
        var dictationNote = one('.is__dictation-note');
        if (band && transmitLine) band.insertAdjacentElement('afterend', transmitLine);
        if (transmitLine && dictationNote) transmitLine.insertAdjacentElement('afterend', dictationNote);

        /* Lock 02 pending composition: the band stays visible — a
           Reviewing cell (spinner + the exact lock copy) replaces the
           primary, Cancel stays live beside it, and the question/coaching
           groups render disabled. The shared processing banner is the
           public page's surface; the authenticated one is this cell. */
        if (band) {
            var pendingCell = document.createElement('div');
            pendingCell.className = 'is-auth__pending-cell';
            pendingCell.hidden = true;
            pendingCell.innerHTML =
                '<span class="is__spinner" aria-hidden="true"></span>' +
                '<span class="is-auth__pending-copy"><strong>Reviewing your answer…</strong>' +
                '<small>Your answer stays here while coaching is prepared.</small></span>';
            band.insertBefore(pendingCell, band.firstChild);
            var cancelBtn = one('[data-is-cancel-review]');
            if (cancelBtn) pendingCell.appendChild(cancelBtn);
        }
    })();

    function setAuthPendingBand(pending) {
        if (!authenticated) return;
        var band = one('.is-auth__band');
        if (!band) return;
        band.classList.toggle('is-auth__band--pending', pending);
        var cell = one('.is-auth__pending-cell', band);
        if (cell) setHidden(cell, !pending);
        all('.is-auth__group-btn', band).forEach(function (button) {
            button.disabled = pending;
        });
    }

    /* The stack is not a new wrapper element (that would add bytes to the
       shared, byte-comparable answering-form markup) -- it is simply the
       existing parent that already holds the live composer/submitted/
       reviewing/error group. New permanent blocks are inserted directly
       before that group, in causal (append) order; the group itself is
       always the last, currently-live thing in the stack. */
    function stackAnchor() { return answeringBlock.parentNode; }
    function appendStackNode(node) {
        stackAnchor().insertBefore(node, answeringBlock);
        return node;
    }

    function resetConsequenceStack() {
        var anchor = stackAnchor();
        all('[data-is-stack-node]', anchor).forEach(function (node) { node.remove(); });
        /* The inline example belongs to the question that was on screen when
           it was requested, so it leaves with that question rather than
           lingering over the next one. */
        clearInlineExample();
        resetDraftBadge();
        /* Review finding P1-2d (lock 11): the rail's "Completed questions"
           group only makes sense while the Session Complete panel is
           showing; clearReviewState() (which calls this) already fires on
           every path that leaves it (a new question, a new session), so
           clearing it here removes it exactly when the lock implies. */
        var railCompleted = one('[data-is-rail-completed]');
        if (railCompleted) {
            setHidden(railCompleted, true);
            var railCompletedList = one('[data-is-rail-completed-list]');
            if (railCompletedList) railCompletedList.replaceChildren();
        }
    }

    function appendAnswerSnapshot(label, answerText) {
        var card = document.createElement('div');
        card.className = 'is-stack__answer-snapshot';
        card.setAttribute('data-is-stack-node', '');
        var badge = document.createElement('p');
        badge.className = 'is-stack__answer-label';
        badge.textContent = label;
        var body = document.createElement('p');
        body.textContent = answerText;
        card.append(badge, body);
        return appendStackNode(card);
    }

    function makeActionButton(kind, label, onClick) {
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'is-stack__action-btn is-stack__action-btn--' + kind;
        button.textContent = label;
        if (onClick) button.addEventListener('click', onClick);
        return button;
    }
    function makeCompletedChip(label) {
        var span = document.createElement('span');
        span.className = 'is-stack__action-chip';
        span.textContent = label;
        return span;
    }

    /* -----------------------------------------------------------------
       Inline example (owner restoration 2026-08-13)

       Historical commit 6936881 put a sample-answer action beneath the
       Interview Me answer field: one click produced an answer to the same
       question in the current canvas, with its why-it-works breakdown
       directly underneath. The intervening build routed both entry points
       into Interview AI instead, so the member lost their place and had to
       act again. That mode switch is the regression this restores.

       One disclosure serves both entry points. It is ephemeral by
       construction: the payload is rendered straight into the DOM and is
       never assigned to session state, a draft, History, or any storage, so
       there is nothing to leak into the member's own answer and nothing to
       clear beyond removing the node. The request reuses the existing
       model-answer endpoint exactly -- same provider, prompt, identity,
       entitlement and evidence contracts -- so this adds no new claim. */
    var inlineExampleSeq = 0;
    var inlineExampleController = null;
    var inlineExampleHost = null;
    /* The question the visible example belongs to. Held only to recognise a
       repeat click, never read back as content. */
    var inlineExampleQuestion = '';

    function clearInlineExample() {
        /* Bumping the sequence first is what makes an in-flight response
           stale: the handler compares against it before touching the DOM,
           so a late answer for a question the member has already left can
           never paint. */
        inlineExampleSeq += 1;
        if (inlineExampleController) inlineExampleController.abort();
        inlineExampleController = null;
        if (inlineExampleHost && inlineExampleHost.parentNode) {
            inlineExampleHost.parentNode.removeChild(inlineExampleHost);
        }
        inlineExampleHost = null;
        inlineExampleQuestion = '';
    }

    /* The member is drafting on this surface, so their caret outranks ours.
       Generation takes seconds; if they went back to typing while they
       waited, moving focus would send their next keystrokes into a
       non-editable node where they are silently lost. Announce instead --
       they already know they asked for this. */
    function memberIsTyping() {
        var active = document.activeElement;
        if (!active) return false;
        var tag = active.tagName;
        return tag === 'TEXTAREA' || tag === 'INPUT' || active.isContentEditable;
    }

    function focusInlineExample(host) {
        if (!host || memberIsTyping()) return;
        host.focus({ preventScroll: true });
    }

    function inlineExampleSection(anchor) {
        var host = document.createElement('section');
        host.className = 'is-stack__coaching is-stack__example';
        host.setAttribute('data-is-inline-example', '');
        /* Deliberately NOT a live region. announce() already sends a short
           summary to the page's own status region; making this card live as
           well would read the whole generated answer, the truth label and
           every why-item aloud on arrival, then repeat it on focus and again
           whenever the card moves between anchors. Summary announcements
           only, which is how the Interview AI panel already behaves. */
        host.setAttribute('tabindex', '-1');
        host.setAttribute('aria-label', 'Strong example');
        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(host, anchor.nextSibling);
        } else {
            appendStackNode(host);
        }
        return host;
    }

    function inlineExampleMessage(host, message, retryHandler) {
        host.replaceChildren();
        var eyebrow = document.createElement('p');
        eyebrow.className = 'is-stack__eyebrow';
        eyebrow.textContent = 'Strong example';
        var body = document.createElement('p');
        body.className = 'is-stack__example-status';
        body.textContent = message;
        host.append(eyebrow, body);
        if (retryHandler) {
            var actions = document.createElement('div');
            actions.className = 'is-stack__actions';
            var retry = makeActionButton('secondary', 'Try again', retryHandler);
            retry.setAttribute('data-is-inline-example-retry', '');
            actions.appendChild(retry);
            host.appendChild(actions);
        }
    }

    function renderInlineExample(host, payload) {
        var model = (payload && payload.modelAnswer) || {};
        var insufficient = model.status === 'insufficient';
        var generic = !!model.generic;
        host.replaceChildren();

        var eyebrow = document.createElement('p');
        eyebrow.className = 'is-stack__eyebrow';
        eyebrow.textContent = 'Strong example';
        host.appendChild(eyebrow);

        if (insufficient) {
            /* Preserve the existing insufficiency behaviour exactly: say
               there is no grounded example rather than inventing member
               history to fill the space. */
            var none = document.createElement('p');
            none.className = 'is-stack__example-status';
            none.textContent = 'There is no strong example in the approved '
                + 'history for this question yet. Nothing has been invented '
                + 'to fill the gap.';
            host.appendChild(none);
            announce('No grounded example is available for this question.');
            focusInlineExample(host);
            return;
        }

        var answer = document.createElement('p');
        answer.className = 'is__ai-answer-text is-stack__example-answer';
        answer.textContent = model.answer || '';
        host.appendChild(answer);

        /* The truth label is not decoration: it is the difference between
           an illustration and a claim about this member's history. */
        var truth = document.createElement('p');
        truth.className = 'is-stack__example-truth';
        truth.textContent = generic
            ? 'Illustrative example — no personal history used.'
            : 'Built from approved public evidence, not invented.';
        host.appendChild(truth);

        var why = document.createElement('div');
        why.className = 'is__why is-stack__example-why';
        var whyHeading = document.createElement('h4');
        whyHeading.textContent = 'Why this works';
        why.appendChild(whyHeading);
        var list = document.createElement('ul');
        (model.whyItWorks || []).forEach(function (item) {
            if (!item) return;
            var li = document.createElement('li');
            li.textContent = item;
            list.appendChild(li);
        });
        why.appendChild(list);
        host.appendChild(why);

        announce('A strong example is shown below your work.');
        focusInlineExample(host);
    }

    /* Both entry points land here. `anchor` is the element the disclosure
       opens beneath, so the pre-answer reveal sits under the composer and
       the post-review reveal sits under that coaching section. */
    function revealInlineExample(anchor) {
        if (!modelAnswersEnabled) return;
        var question = currentQuestion();
        if (!question || !question.text) return;
        /* A second click while a request is in flight is ignored rather
           than queued, so repeated clicks cannot stack requests. */
        if (inlineExampleController) return;
        /* And once an example for THIS question is already on screen, a
           repeat click returns the member to it instead of spending another
           generation on the same question. Both entry points share the one
           disclosure, so clicking either after the other simply moves focus
           to what is already there. */
        if (inlineExampleHost && inlineExampleQuestion === question.text) {
            if (anchor && anchor.parentNode
                && inlineExampleHost.previousSibling !== anchor) {
                anchor.parentNode.insertBefore(
                    inlineExampleHost, anchor.nextSibling);
            }
            inlineExampleHost.focus({ preventScroll: true });
            inlineExampleHost.scrollIntoView({
                behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest'
            });
            return;
        }

        /* "Try again" lives inside the card it is about to replace, so
           removing that card would drop the keyboard user at the top of the
           document mid-reload. Carry their place onto the replacement. */
        var carriedFocus = Boolean(
            inlineExampleHost
            && document.activeElement
            && inlineExampleHost.contains(document.activeElement)
        );

        clearInlineExample();
        var host = inlineExampleSection(anchor);
        inlineExampleHost = host;
        inlineExampleMessage(host, 'Drafting a strong example…');
        host.setAttribute('aria-busy', 'true');
        if (carriedFocus) host.focus({ preventScroll: true });
        announce('Drafting a strong example.');

        inlineExampleSeq += 1;
        var seq = inlineExampleSeq;
        inlineExampleController = new AbortController();
        var controller = inlineExampleController;

        postJSON('/api/interview/model-answer', {
            question: question.text,
            follow_up: '',
            context_token: '',
            level: session.level,
            family: session.family,
            mode: selectedAiMode(),
            opportunity_context: explicitContextForAi()
        }, controller.signal).then(function (payload) {
            if (seq !== inlineExampleSeq) return;
            inlineExampleController = null;
            host.removeAttribute('aria-busy');
            inlineExampleQuestion = question.text;
            renderInlineExample(host, payload);
        }).catch(function (error) {
            if (seq !== inlineExampleSeq) return;
            inlineExampleController = null;
            if (error.name === 'AbortError') return;
            host.removeAttribute('aria-busy');
            inlineExampleMessage(
                host,
                error.message + ' Your answer and coaching are untouched.',
                function () { revealInlineExample(anchor); }
            );
            announce('The example could not be generated.');
        });
    }

    /* Post-review entry point. A button, not a link: the whole point of
       this round is that it no longer navigates away. */
    function appendModelAnswerAction(actions) {
        if (!actions || !modelAnswersEnabled) return null;
        var question = currentQuestion();
        if (!question || !question.text) return null;
        var button = makeActionButton(
            'secondary',
            'See a strong answer + why it works',
            function () {
                var section = button.closest
                    ? button.closest('.is-stack__coaching')
                    : null;
                revealInlineExample(section || actions);
            }
        );
        button.setAttribute('data-is-model-answer-action', '');
        actions.appendChild(button);
        return button;
    }

    function buildCoachingList(container, label, items, emptyMessage) {
        var col = document.createElement('div');
        col.className = 'is-stack__summary-col';
        var h5 = document.createElement('h5');
        h5.textContent = label;
        var ul = document.createElement('ul');
        (items && items.length ? items : [emptyMessage]).forEach(function (item) {
            var li = document.createElement('li');
            li.textContent = item;
            ul.appendChild(li);
        });
        col.append(h5, ul);
        container.appendChild(col);
    }

    /* Builds one appended CoachingSection (first attempt, visuals 04a/04b)
       or RevisedCoachingSection (a later attempt, visual 06). Returns the
       section element and its still-empty FINAL ACTIONS row so the caller
       (which knows the causal state -- first review vs. a revision) wires
       the right buttons. */
    function buildCoachingSection(review, revised) {
        var section = document.createElement('section');
        section.className = 'is-stack__coaching';
        section.setAttribute('data-is-stack-node', '');
        section.tabIndex = -1;

        var eyebrow = document.createElement('p');
        eyebrow.className = 'is-stack__eyebrow';
        eyebrow.textContent = revised ? 'Revised coaching' : 'Coaching review';
        var heading = document.createElement('h3');
        heading.className = 'is-stack__heading';
        heading.textContent = review.verdict || (revised ? 'Your revision is reviewed.' : 'Your answer is reviewed.');
        section.append(eyebrow, heading);

        var grid = document.createElement('div');
        grid.className = 'is-stack__summary-grid';
        if (revised) {
            buildCoachingList(grid, 'What changed', review.strengths, review.encouragement || EMPTY_STRENGTHS_MESSAGE);
            buildCoachingList(grid, 'What still needs work', review.improvements, EMPTY_IMPROVEMENTS_MESSAGE);
            buildCoachingList(grid, 'Next focus', [review.focusedFollowUp || (review.improvements && review.improvements[0]) || 'Keep refining the strongest example you have.']);
        } else {
            /* Lock 04a column semantics: WHAT'S WORKING carries what came
               through plus named strengths; TRY THIS NEXT carries forward
               guidance (the next actions of not-yet-clear dimensions, falling
               back to the focused follow-up) -- never the what-came-through
               list. */
            var working = [];
            (review.whatCameThroughClearly || []).concat(review.strengths || []).forEach(function (item) {
                if (item && working.indexOf(item) === -1 && working.length < 4) working.push(item);
            });
            var tryNext = (review.dimensions || [])
                .filter(function (d) { return d.status !== 'clear' && d.status !== 'strong'; })
                .map(function (d) { return d.nextAction; })
                .filter(Boolean)
                .slice(0, 3);
            if (!tryNext.length && review.focusedFollowUp) tryNext = [review.focusedFollowUp];
            buildCoachingList(grid, "What's working", working, EMPTY_STRENGTHS_MESSAGE);
            buildCoachingList(grid, 'Strengthen it', review.improvements, EMPTY_IMPROVEMENTS_MESSAGE);
            buildCoachingList(grid, 'Try this next', tryNext, 'Keep refining the strongest example you have.');
        }
        section.appendChild(grid);

        if (!revised) {
            var approach = document.createElement('p');
            approach.className = 'is-stack__approach';
            var approachLabel = document.createElement('strong');
            approachLabel.textContent = 'Stronger approach. ';
            approach.append(approachLabel, document.createTextNode(review.strongerApproach || ''));
            section.appendChild(approach);

            var table = document.createElement('table');
            table.className = 'is-stack__table';
            var tableBody = document.createElement('tbody');
            (review.dimensions || []).forEach(function (dimension) {
                var row = document.createElement('tr');
                var th = document.createElement('th');
                th.textContent = readableDimensionKey(dimension.key);
                var statusCell = document.createElement('td');
                var statusSpan = document.createElement('span');
                statusSpan.className = 'is-stack__status';
                statusSpan.setAttribute('data-status', dimension.status);
                statusSpan.textContent = readableDimensionKey(dimension.status);
                statusCell.appendChild(statusSpan);
                var explainCell = document.createElement('td');
                /* Lock 04b's third column reads as guidance ("Add a concrete
                   example…"), which is the dimension's next action; the
                   rationale backs the status and travels in the tooltip. */
                explainCell.textContent = dimension.nextAction || dimension.rationale;
                if (dimension.rationale) explainCell.title = dimension.rationale;
                row.append(th, statusCell, explainCell);
                tableBody.appendChild(row);
            });
            table.appendChild(tableBody);
            section.appendChild(table);

            var evidenceEyebrow = document.createElement('p');
            evidenceEyebrow.className = 'is-stack__eyebrow is-stack__eyebrow--sub';
            evidenceEyebrow.textContent = 'Relevant evidence';
            var evidence = document.createElement('p');
            evidence.className = 'is-stack__evidence';
            evidence.textContent =
                (review.evidenceSuggestions && review.evidenceSuggestions.length)
                    ? 'A relevant evidence suggestion is available in your practice history.'
                    : 'No authorized evidence suggestion is available for this answer.';
            section.append(evidenceEyebrow, evidence);

            var actionsEyebrow = document.createElement('p');
            actionsEyebrow.className = 'is-stack__eyebrow is-stack__eyebrow--sub';
            actionsEyebrow.textContent = 'Final actions';
            section.appendChild(actionsEyebrow);
        }

        var actions = document.createElement('div');
        actions.className = 'is-stack__actions';
        section.appendChild(actions);

        var authority = document.createElement('p');
        authority.className = 'is-stack__authority';
        authority.textContent = 'Coaching is guidance. Your answer remains yours.';
        section.appendChild(authority);

        return { section: section, actions: actions, heading: heading };
    }

    function revealAppendedSection(target) {
        if (!target) return;
        target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
        target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
    }

    function goToNextQuestion() {
        var source = session.reviewSource;
        if (source === 'video') {
            if (!setMode('video', true)) return;
            resetVideoUi();
            advanceQuestion('video');
            return;
        }
        advanceQuestion();
    }

    /* Appends the frozen AnswerCard snapshot and its CoachingSection for one
       validated attempt (architecture 03 section 1). `attemptNumber` is the
       attempt this answer belongs to (1 = the original answer, 2+ = a
       reviewed revision). */
    function appendAuthenticatedAttempt(answerText, review, attemptNumber) {
        var revised = attemptNumber > 1;
        setHidden(submittedBlock, true);

        if (revised) {
            var context = document.createElement('p');
            context.className = 'is-stack__context-note';
            context.setAttribute('data-is-stack-node', '');
            context.textContent = 'Original answer and first coaching remain above.';
            appendStackNode(context);
        }

        appendAnswerSnapshot(
            revised ? 'Reviewed revision · Attempt ' + attemptNumber : 'Reviewed answer',
            answerText
        );

        var built = buildCoachingSection(review, revised);
        appendStackNode(built.section);

        if (revised) {
            built.actions.append(
                makeActionButton('primary', 'Next question', function () { goToNextQuestion(); }),
                makeActionButton('secondary', 'Revise again', function () { startAuthenticatedImprove(review); }),
                makeActionButton('secondary', 'Finish session', function () { finishCurrentSession(); }),
                makeCompletedChip('Revision reviewed')
            );
        } else {
            var improveButton = makeActionButton('primary', 'Improve My Answer', function () {
                improveButton.replaceWith(makeCompletedChip('Improvement draft created'));
                startAuthenticatedImprove(review);
            });
            built.actions.append(
                improveButton,
                makeActionButton('secondary', 'Next question', function () { goToNextQuestion(); })
            );
        }

        /* Owner directive 2026-08-12: the optional model answer lost its
           discoverability once the rail's "Need an example?" affordance
           stopped being the obvious next step after a review. Offer it here,
           at the moment it is actually useful, on the same reviewed question.
           It only NAVIGATES to the existing Interview AI surface -- it never
           writes to, replaces, or saves the member's own answer, and it is
           hidden entirely when the account is not entitled to model answers,
           so no one is shown a door that will not open. */
        appendModelAnswerAction(built.actions);

        revealAppendedSection(built.heading);
    }

    /* ---------------------------------------------------------------------
       Slice 4 marker contract (architecture 03 section 2). Matches the same
       narrow imperative-sentence-in-brackets shape the server extracts into
       `confirmations` (app.py _IMPROVEMENT_MARKER_PATTERN) so client-side
       counting and the server-side re-validation agree on what counts as an
       unresolved marker; a candidate's own incidental bracket use never
       matches.
       --------------------------------------------------------------------- */
    var IMPROVEMENT_MARKER_PATTERN = /\[[A-Z][a-zA-Z]*\s[^[\]]*\.\]/g;
    function unresolvedMarkerCount(draftText) {
        var matches = String(draftText || '').match(IMPROVEMENT_MARKER_PATTERN);
        return matches ? matches.length : 0;
    }

    /* R2 (slice 5-6 review): "Add context or evidence" is a PRESERVED
       capability (handoff: "improve/add context" may not disappear; visuals
       05/14b show it). Builds the same 1,200-char confirmed-context field
       and evidence-suggestion checkboxes the public "Make it more yours"
       flow already has (data-is-answer-context / data-is-evidence-choice),
       as new stack-appended nodes fed by the SAME review.evidenceSuggestions
       payload buildCoachingSection's "Relevant evidence" line already uses.
       Owner-only in practice: a non-owner's #is-evidence-data island is
       empty (slice 2), so evidenceById never resolves a suggestion id and
       the fallback copy renders instead -- no separate owner check needed
       here. */
    function buildImproveContextForm(review, onSubmit) {
        var toggle = makeActionButton('secondary', 'Add context or evidence', function () {
            var opening = form.hidden;
            setHidden(form, !opening);
            toggle.setAttribute('aria-expanded', opening ? 'true' : 'false');
            if (opening) textarea.focus();
        });
        toggle.classList.add('is-stack__context-toggle');
        toggle.setAttribute('aria-expanded', 'false');

        var form = document.createElement('form');
        form.className = 'is-stack__context-form';
        form.hidden = true;

        var suggestions = (review.evidenceSuggestions || []).filter(function (suggestion) {
            return Boolean(evidenceById[suggestion.evidenceId]);
        });
        if (suggestions.length) {
            var fieldsetLabel = document.createElement('p');
            fieldsetLabel.className = 'is-stack__context-form-label';
            fieldsetLabel.textContent = 'Relevant history you may have missed';
            form.appendChild(fieldsetLabel);
            var options = document.createElement('div');
            options.className = 'is-stack__context-evidence-options';
            suggestions.forEach(function (suggestion) {
                var item = evidenceById[suggestion.evidenceId];
                var label = document.createElement('label');
                label.className = 'is-stack__context-evidence-option';
                label.title = suggestion.opportunity;
                var input = document.createElement('input');
                input.type = 'checkbox';
                input.value = item.id;
                input.setAttribute('data-is-stack-evidence-choice', '');
                var chip = document.createElement('span');
                chip.textContent = item.metric + ' — ' + item.label;
                label.append(input, chip);
                options.appendChild(label);
            });
            form.appendChild(options);
        } else {
            var noEvidence = document.createElement('p');
            noEvidence.className = 'is-stack__evidence';
            noEvidence.textContent = 'No authorized evidence suggestion is available for this answer.';
            form.appendChild(noEvidence);
        }

        var textareaLabel = document.createElement('label');
        textareaLabel.textContent = 'A real detail to include';
        var textarea = document.createElement('textarea');
        textarea.maxLength = 1200;
        textarea.setAttribute('data-is-stack-answer-context', '');
        textarea.placeholder = 'Add a responsibility, action, result, or detail that is true for you…';
        form.append(textareaLabel, textarea);

        var formActions = document.createElement('div');
        formActions.className = 'is-stack__actions';
        var updateButton = makeActionButton('primary', 'Update the draft', null);
        updateButton.type = 'submit';
        var cancelButton = makeActionButton('secondary', 'Cancel', function () {
            setHidden(form, true);
            toggle.setAttribute('aria-expanded', 'false');
        });
        formActions.append(updateButton, cancelButton);
        form.appendChild(formActions);

        form.addEventListener('submit', function (event) {
            event.preventDefault();
            if (updateButton.disabled) return;
            var selectedIds = all('[data-is-stack-evidence-choice]', form)
                .filter(function (input) { return input.checked; })
                .map(function (input) { return input.value; });
            var contextText = textarea.value.trim();
            updateButton.disabled = true;
            onSubmit(selectedIds, contextText, function () {
                updateButton.disabled = false;
            });
        });

        return { toggle: toggle, form: form };
    }

    function appendAuthenticatedImprovement(payload, review, question, priorAnswer) {
        var section = document.createElement('section');
        section.className = 'is-stack__coaching is-stack__improve';
        section.setAttribute('data-is-stack-node', '');
        section.tabIndex = -1;

        /* Review finding P2-2: confirmations[] (app.py
           validate_interview_improvement, the same extraction the server
           re-validates a revision against) is the canonical marker list --
           counting by literal string containment against the draft can
           never disagree with what the server actually found in this
           exact draft, unlike the client regex re-deriving its own
           opinion. The regex (IMPROVEMENT_MARKER_PATTERN, still matched to
           the server's pattern shape) is now only a fallback for the
           unexpected case confirmations is absent. Re-assigned below
           whenever a new payload arrives (the R2 "Add context or
           evidence" resubmission gets its own confirmations list). */
        var confirmations = Array.isArray(payload.confirmations) ? payload.confirmations : null;

        var eyebrow = document.createElement('p');
        eyebrow.className = 'is-stack__eyebrow';
        eyebrow.textContent = 'Improve your answer';
        var heading = document.createElement('h3');
        heading.className = 'is-stack__heading';
        heading.textContent = 'Strengthen your answer with a real detail.';
        var basis = document.createElement('p');
        basis.className = 'is-stack__evidence';
        function setBasis(currentPayload) {
            basis.textContent = 'Based on: your submitted answer' + (
                currentPayload.evidenceUsed && currentPayload.evidenceUsed.length ? ' · approved evidence selected' : ' · no approved evidence selected'
            );
        }
        setBasis(payload);
        section.append(eyebrow, heading, basis);

        var contextParts = buildImproveContextForm(review, function (selectedIds, contextText, done) {
            startAuthenticatedImprove(review, selectedIds, contextText, function (updatedPayload) {
                done();
                draft.value = updatedPayload.draft;
                confirmations = Array.isArray(updatedPayload.confirmations) ? updatedPayload.confirmations : null;
                setBasis(updatedPayload);
                syncMarkers();
                autoGrowTextarea(draft);
                setHidden(contextParts.form, true);
                contextParts.toggle.setAttribute('aria-expanded', 'false');
                announce('Coach-assisted draft updated with the context you supplied. Verify the wording before using it.');
            }, function () {
                done();
                announce('That update did not complete. Your previous draft is unchanged.');
            });
        });
        section.append(contextParts.toggle, contextParts.form);

        /* Lock 05/14b draft box: a bordered container whose header row holds
           the confirmation chip (left) and Dictate + live word count (right);
           the editable draft grows with its content like every other Studio
           field (data-is-autogrow + the shared delegated listener). */
        var draftBox = document.createElement('div');
        draftBox.className = 'is-stack__draft-box';
        var draftHead = document.createElement('div');
        draftHead.className = 'is-stack__draft-head';
        var markerChip = document.createElement('p');
        markerChip.className = 'is-stack__marker-chip';
        var draftLabel = document.createElement('p');
        draftLabel.className = 'is-stack__draft-label';
        draftLabel.textContent = 'Coach-assisted draft · editable';
        var draftTools = document.createElement('div');
        draftTools.className = 'is-stack__draft-tools';
        var micButton = document.createElement('button');
        micButton.type = 'button';
        micButton.className = 'is__button is__mic-labeled is-stack__draft-mic';
        micButton.setAttribute('data-is-mic', 'improve');
        micButton.setAttribute('aria-pressed', 'false');
        micButton.setAttribute('aria-label', 'Dictate into the improved draft');
        micButton.innerHTML = '<span class="is__mic is__mic--inline" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3M9 21h6"/></svg></span><span data-is-mic-label>Dictate</span>';
        var draftCount = document.createElement('span');
        draftCount.className = 'is-stack__draft-count';
        draftTools.append(micButton, draftCount);
        draftHead.append(markerChip, draftLabel, draftTools);
        draftBox.appendChild(draftHead);

        var draft = document.createElement('textarea');
        draft.className = 'is-stack__improve-draft';
        draft.value = payload.draft;
        draft.setAttribute('aria-label', 'Editable improved draft');
        draft.setAttribute('data-is-autogrow', '');
        draftBox.appendChild(draft);

        var dictationStatus = document.createElement('p');
        dictationStatus.className = 'is__dictation-live';
        dictationStatus.setAttribute('data-is-dictation-status', 'improve');
        dictationStatus.hidden = true;
        var dictationInterim = document.createElement('p');
        dictationInterim.className = 'is__dictation-interim';
        dictationInterim.setAttribute('data-is-dictation-interim', 'improve');
        dictationInterim.hidden = true;
        dictationInterim.innerHTML = '<span class="is__dictation-interim-label">Heard so far</span><span data-is-dictation-interim-text></span>';
        var dictationError = document.createElement('p');
        dictationError.className = 'is__error';
        dictationError.setAttribute('data-is-mic-error', 'improve');
        dictationError.hidden = true;
        draftBox.append(dictationStatus, dictationInterim, dictationError);
        section.appendChild(draftBox);

        if (dictation) {
            dictation.register('improve', {
                button: micButton,
                resolveTarget: function () { return draft; },
                label: 'Dictate into the improved draft',
                listeningLabel: 'Stop dictation',
                noun: 'draft',
                setStatus: function (message) { setDictationStatus('improve', message); },
                setInterim: function (value) { setDictationInterim('improve', value); },
                showError: function (message) { showMicError('improve', message); },
                hideError: function () { setHidden(dictationError, true); },
                setButtonLabel: function (value) {
                    var labelNode = one('[data-is-mic-label]', micButton);
                    if (labelNode) text(labelNode, value);
                }
            });
            micButton.addEventListener('click', function () { toggleDictation('improve'); });
        }
        if (!speechIsSupported()) {
            micButton.setAttribute('aria-disabled', 'true');
            micButton.disabled = true;
            micButton.classList.add('is-unavailable');
        }

        var markerHelp = document.createElement('p');
        markerHelp.className = 'is-stack__marker-help';
        markerHelp.textContent = 'Replace or remove every bracketed prompt before review.';
        section.appendChild(markerHelp);

        var actions = document.createElement('div');
        actions.className = 'is-stack__actions';
        var reviewRevisedButton = makeActionButton('primary', 'Review Revised Answer', function () {
            if (reviewRevisedButton.disabled) return;
            answer.value = draft.value.trim();
            saveDraft(false);
            syncAnswerState();
            /* The attempt number is no longer bumped here. submitReview works
               out the attempt being sent and commits it only if the review
               succeeds, so a failure leaves the counter untouched. */
            submitReview({ isRevision: true });
        });
        var keepOriginalButton = makeActionButton('secondary', 'Keep original answer', function () {
            section.remove();
        });
        actions.append(reviewRevisedButton, keepOriginalButton);
        section.appendChild(actions);

        var transmitLine = document.createElement('p');
        transmitLine.className = 'is-stack__authority';
        transmitLine.textContent = 'Your revised answer is sent only when you click Review Revised Answer.';
        section.appendChild(transmitLine);

        function syncMarkers() {
            /* Review finding P2-2: confirmations[] is the canonical list
               when present -- an unresolved marker is one whose exact
               string still literally appears in the draft. Falls back to
               the regex only when the server did not return confirmations
               (e.g. an older cached payload shape). */
            var count = confirmations
                ? confirmations.filter(function (marker) { return draft.value.indexOf(marker) !== -1; }).length
                : unresolvedMarkerCount(draft.value);
            markerChip.textContent = count ? 'Needs your confirmation (' + count + ' remaining)' : '';
            setHidden(markerChip, !count);
            setHidden(draftLabel, Boolean(count));
            reviewRevisedButton.disabled = count > 0;
            var words = draft.value.trim() ? draft.value.trim().split(/\s+/).length : 0;
            draftCount.textContent = words + ' words';
        }
        draft.addEventListener('input', syncMarkers);
        syncMarkers();

        appendStackNode(section);
        autoGrowTextarea(draft);
        revealAppendedSection(heading);
    }

    /* Requests one coach-assisted improvement draft, either appending it
       (first call, no onSuccess override) or -- via the R2 "Add context or
       evidence" sub-flow above -- updating an already-appended draft in
       place (onSuccess/onError supplied). selectedIds/additionalContext
       default to the plain "Improve My Answer" click's empty payload. */
    function startAuthenticatedImprove(review, selectedIds, additionalContext, onSuccess, onError) {
        var question = currentQuestion();
        var priorAnswer = session.currentAnswer;
        cancelPendingImprovement();
        improveController = new AbortController();
        var controller = improveController;
        var requestId = improveRequestId;
        var binding = currentRequestBinding();
        postJSON('/api/interview/improve', {
            question: question.text,
            answer: priorAnswer,
            family: question.family,
            improvements: review.improvements,
            evidence_ids: selectedIds || [],
            additional_context: additionalContext || '',
            opportunity_context: explicitContextForAi()
        }, controller.signal).then(function (payload) {
            if (requestId !== improveRequestId || !bindingStillCurrent(binding)) return;
            improveController = null;
            if (onSuccess) {
                onSuccess(payload.improvement);
            } else {
                appendAuthenticatedImprovement(payload.improvement, review, question, priorAnswer);
                announce('Coach-assisted draft ready. Review and edit it before requesting a revised review.');
            }
        }).catch(function (error) {
            if (requestId !== improveRequestId || !bindingStillCurrent(binding)) return;
            improveController = null;
            if (error.name === 'AbortError') return;
            if (onError) {
                onError(error);
            } else {
                announce('The improved draft could not be generated. Your original answer is unchanged.');
            }
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

    /* options.isRevision marks a re-review of an improved answer. The attempt
       being submitted is computed here and kept local until the review comes
       back; session.attemptNumber only advances on success, so a failed
       revision leaves nothing to roll back and a retry is labelled correctly. */
    function submitReview(options) {
        if (reviewController) return;
        /* Never leave the microphone listening once the answer has been sent. */
        stopDictation('interrupted');
        var responseText = answer.value.trim();
        if (!responseText) {
            announce('Type or dictate an answer before submitting it for review.');
            answer.focus();
            return;
        }
        var isRevision = Boolean(options && options.isRevision);
        var attemptAtSubmit = session.attemptNumber + (isRevision ? 1 : 0);
        session.requestSeq += 1;
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
        text(submittedLabel, authenticated
            ? (attemptAtSubmit > 1 ? 'Submitted revised answer · Attempt ' + attemptAtSubmit : 'Submitted answer')
            : 'Your submitted answer · preserved');
        setAuthPendingBand(true);
        setStage(2);
        cancelReviewButton.focus();
        cancelPendingReview();
        reviewController = new AbortController();
        var controller = reviewController;
        var requestId = reviewRequestId;
        var reviewSource = session.reviewSource || 'me';
        var reviewRecordId = session.reviewRecordId || '';
        var binding = currentRequestBinding();

        var question = currentQuestion();
        var reviewRequestBody = {
            question: question.text,
            answer: responseText,
            level: session.level,
            family: question.family,
            competency: question.competency,
            opportunity_context: explicitContextForAi()
        };
        /* Review finding P2-2: the authenticated client reports which
           attempt this is so the server's marker gate (P2-1: rejection
           applies only to attempt >= 2) can tell a revision from a first
           attempt. Advisory UX truth only -- the improve contract (what
           actually produces a bracket marker) remains the real boundary,
           and the server independently validates/bounds this value. */
        if (authenticated) reviewRequestBody.attempt = attemptAtSubmit;
        postReviewWithOneRetry(reviewRequestBody, controller.signal).then(function (payload) {
            if (requestId !== reviewRequestId || !bindingStillCurrent(binding)) return;
            reviewController = null;
            answer.readOnly = false;
            answeringBlock.removeAttribute('aria-busy');
            syncAnswerState();
            setHidden(reviewingBlock, true);
            setAuthPendingBand(false);
            setStage(3);
            renderReview(payload.review);
            if (session.reviewedQuestionIds.indexOf(questionId(question)) === -1) {
                session.reviewedQuestionIds.push(questionId(question));
                persistSession();
                renderSessionProgress();
            }
            /* The attempt is only real once it has been reviewed. Committing
               here rather than at submit time is what keeps a retry after a
               failed revision from being labelled an attempt too high. */
            session.attemptNumber = attemptAtSubmit;
            if (authenticated) {
                appendAuthenticatedAttempt(responseText, payload.review, attemptAtSubmit);
            } else {
                setHidden(feedbackBlock, false);
                setHidden(feedbackEmpty, true);
                setHidden(feedbackContent, false);
            }
            var record = {
                id: reviewRecordId || 'attempt-' + Date.now() + '-' + attemptAtSubmit,
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
                attemptNumber: attemptAtSubmit,
                durationSeconds: reviewSource === 'video' ? (session.reviewDurationSeconds || 0) : 0,
                status: reviewSource === 'video' ? 'Content reviewed' : 'Completed'
            };
            var savedToHistory = Boolean(reviewRecordId) && updateHistoryRecord(reviewRecordId, record);
            if (!savedToHistory) savedToHistory = addHistoryRecord(record);
            removeStored(draftKey(question.text));
            announce(savedToHistory
                ? 'Coach review ready. Review the clear strengths and one focused next step.'
                : 'Coach review ready, but this attempt could not be saved to History in this browser.');
            if (!authenticated) {
                feedbackBlock.focus({ preventScroll: true });
                feedbackBlock.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
            }
        }).catch(function (error) {
            if (requestId !== reviewRequestId || !bindingStillCurrent(binding)) return;
            reviewController = null;
            if (error.name === 'AbortError') return;
            answer.readOnly = false;
            answeringBlock.removeAttribute('aria-busy');
            syncAnswerState();
            setHidden(answeringBlock, false);
            setHidden(submittedBlock, true);
            setHidden(reviewingBlock, true);
            setAuthPendingBand(false);
            setHidden(feedbackBlock, true);
            setHidden(feedbackEmpty, false);
            setHidden(feedbackContent, true);
            setStage(1);
            if (authenticated) {
                var draftBadge = one('[data-is-draft-badge]');
                text(draftBadge, 'Review unavailable');
                if (draftBadge) draftBadge.classList.add('is-auth__badge--warning');
                var failedBand = one('.is-auth__band');
                if (failedBand) failedBand.classList.add('is-auth__band--failed');
                text(reviewErrorHeading, "We couldn't review this answer right now.");
                text(reviewErrorText, 'Your answer is still here. You can try again or continue editing.');
            } else {
                text(submittedLabel, 'Your answer · preserved and editable');
                text(reviewErrorText, error.message + ' Your answer is still here. Edit it or retry the coaching request without re-entering your work.');
            }
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

    /* Pre-answer entry point. Delegated from the root so it keeps working
       across the re-renders that rebuild these controls, and scoped to the
       authenticated page: the public branch keeps its existing navigation,
       which is what its byte-comparability contract fixes. The href stays
       real underneath, so this degrades to the old behaviour rather than to
       a dead control if the script never runs. */
    if (authenticated && modelAnswersEnabled) {
        root.addEventListener('click', function (event) {
            var target = event.target;
            var trigger = target && target.closest
                ? target.closest('[data-is-example-link]')
                : null;
            if (!trigger) return;
            /* The trigger is still a real link, so a modifier click means
               "open the Interview AI page in a new tab" and that intent is
               the member's to keep. Only a plain left click becomes the
               inline reveal. */
            if (event.button !== 0 || event.ctrlKey || event.metaKey
                || event.shiftKey || event.altKey) return;
            event.preventDefault();
            revealInlineExample(answeringBlock);
        });
    }
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
        setAuthPendingBand(false);
        setHidden(submittedBlock, true);
        setHidden(answeringBlock, false);
        setHidden(feedbackBlock, true);
        setHidden(improveBlock, true);
        if (authenticated) {
            resetDraftBadge();
            var recoveredBand = one('.is-auth__band');
            if (recoveredBand) recoveredBand.classList.remove('is-auth__band--failed');
        }
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
        var applyAiModeChange = function (value) {
            stopDictation('interrupted');
            if (modeNote) modeNote.textContent = modeNotes[value] || '';
            if (basisLabel) basisLabel.textContent = modeLabels[value] || '';
            if (basisGuidance) basisGuidance.textContent = modeGuidance[value] || '';
            resetAiAnswerForContextChange();
            announce((modeLabels[value] || 'Answer basis') + ' selected. Generate a new answer for this basis.');
        };
        modeGroup.addEventListener('change', function (event) {
            if (event.target !== modeSelect) return;
            applyAiModeChange(event.target.value);
        });
        /* Slice 5-6 review item 1 (visual 07/08): the authenticated SOURCE
           radio cards are a second control over the same modeSelect value
           (architecture 03 section 3 keeps the public dropdown as the
           setup-form field; the radios are new markup, not a replacement).
           Keeping modeSelect as the single source of truth means
           selectedAiMode() and every other reader need no changes. */
        var aiSourceRadios = all('[data-is-ai-source-radio]');
        if (aiSourceRadios.length) {
            aiSourceRadios.forEach(function (radio) {
                radio.checked = radio.value === modeSelect.value;
                radio.addEventListener('change', function () {
                    if (!radio.checked) return;
                    modeSelect.value = radio.value;
                    applyAiModeChange(radio.value);
                });
            });
        }
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
        /* A context or mode change invalidates the inline example for the
           same reason it invalidates the panel's answer: it was generated
           for a question and grounding that no longer apply. */
        clearInlineExample();
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
        var practiceAnswerButton = one('[data-is-practice-answer]');
        if (authenticated) {
            /* Review finding P1-2b (lock 08): the insufficiency composition's
               dominant action is an enabled "Use best practice" primary,
               not a disabled "Practice This Answer" -- the same button is
               relabeled and re-enabled rather than adding a fourth control,
               mirroring how the sibling "New question"/"Change question"
               label swap below already reuses one element for both states. */
            text(practiceAnswerButton, insufficient ? 'Use best practice' : 'Practice This Answer');
            practiceAnswerButton.disabled = false;
        } else {
            practiceAnswerButton.disabled = insufficient;
        }
        text(one('[data-is-ai-name]'), payload.profile.firstName || 'Candidate');
        text(one('[data-is-ai-answer-text]'), payload.modelAnswer.answer);
        renderList(one('[data-is-ai-why]'), payload.modelAnswer.whyItWorks);
        var generic = !!payload.modelAnswer.generic;
        var genericFlag = one('[data-is-ai-generic]');
        if (genericFlag) setHidden(genericFlag, !generic);
        var heading = one('[data-is-ai-answer-heading]');
        if (heading) {
            heading.textContent = authenticated
                ? (generic ? 'Generic best-practice example' : (payload.profile.firstName || 'Candidate') + '\u2019s approved public example')
                : insufficient
                    ? 'No grounded answer available'
                    : generic
                        ? 'Best-practice example'
                        : (payload.profile.firstName || 'Candidate') + '\u2019s answer';
        }
        if (authenticated) {
            /* Slice 5-6 review item 1: the insufficiency lock (visual 08) is a
               separate composition from the generic/grounded ready card
               (visual 07), toggled on the same insufficient flag. */
            setHidden(one('[data-is-ai-insufficient]'), !insufficient);
            setHidden(one('[data-is-ai-answer-ready]'), insufficient);
            setHidden(one('[data-is-ai-generic-truth]'), !generic);
            /* Final-review Finding 1: target the visible ACTION-ROW control by
               its own hook. The plain [data-is-different-question] selector
               resolved to the CSS-hidden chip-row button first, so the lock 08
               relabel never reached the button a member can see (and text()
               would have stripped that chip button's icon). */
            var newQuestionButton = one('#is-panel-ai [data-is-ai-action-question]');
            if (newQuestionButton) text(newQuestionButton, insufficient ? 'Change question' : 'New question');
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
        /* Architecture 03 section 3, item 2: follow-up stays visibly
           unavailable for authenticated regardless of token availability
           until the scoped finding interview_followup_mode_provenance
           closes -- the token plumbing keeps computing followUpAvailable
           (untouched below) so the public branch is unaffected; only the
           four follow-up controls are forced disabled for authenticated. */
        var followUpAvailable = !authenticated && !insufficient && Boolean(currentModelContextToken);
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
                var followUpAvailable = !authenticated && currentModelAnswer.status !== 'insufficient' && Boolean(currentModelContextToken);
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
        if (authenticated && root.getAttribute('data-is-ai-state') === 'insufficient') {
            /* Review finding P1-2b: the same control, relabeled "Use best
               practice" for this state (see renderModelAnswer above),
               selects the best_practice source and re-requests the
               example -- the same two steps a member could otherwise take
               by hand (click the Best practice radio, then Get example). */
            var bestPracticeRadio = all('[data-is-ai-source-radio]').filter(function (radioEl) {
                return radioEl.value === 'best_practice';
            })[0];
            if (bestPracticeRadio) {
                bestPracticeRadio.checked = true;
                if (modeSelect) modeSelect.value = 'best_practice';
            }
            if (typeof applyAiModeChange === 'function') applyAiModeChange('best_practice');
            stopDictation('interrupted');
            resetAiAnswerForContextChange();
            requestModelAnswer('');
            return;
        }
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
        if (authenticated) syncVideoRecoveryState(state);
    }

    /* Slice 5-6 review item 2 (visual 15): the recovery lock replaces the
       normal camera-off placeholder and normal controls whenever a
       permission request failed ('denied') or the device/browser cannot
       support camera rehearsal at all ('unavailable') -- both states
       enableCamera() already sets; this only changes what's visible. */
    function syncVideoRecoveryState(state) {
        var recovery = one('[data-is-video-recovery]');
        if (!recovery) return;
        var inRecovery = state === 'denied' || state === 'unavailable';
        setHidden(recovery, !inRecovery);
        if (inRecovery) {
            setHidden(cameraEmpty, true);
            [startRecord, stopRecord, retakeRecord, discardRecord].forEach(function (button) { button.hidden = true; });
        } else if (state === 'camera-off') {
            setHidden(cameraEmpty, false);
        }
        var cameraOffButton = one('[data-is-camera-off]');
        var useTranscriptButton = one('[data-is-video-use-transcript]');
        var cameraRetryButton = one('[data-is-camera-retry]');
        var cameraHelpButton = one('[data-is-camera-help]');
        var deviceSettingsButton = one('[data-is-device-settings]');
        setHidden(cameraOffButton, inRecovery || state === 'camera-off');
        setHidden(useTranscriptButton, !inRecovery);
        setHidden(cameraRetryButton, !inRecovery);
        setHidden(cameraHelpButton, !inRecovery);
        /* Lock 09: Device settings is part of the live-preview control row. */
        setHidden(deviceSettingsButton, state !== 'preview');
        /* Lock 10: an explicit green Play affordance alongside the native
           element controls. */
        var playButton = one('[data-is-play-recording]');
        if (playButton && !playButton.hasAttribute('data-is-play-wired')) {
            playButton.setAttribute('data-is-play-wired', '');
            playButton.addEventListener('click', function () {
                if (cameraPreview && cameraPreview.play) cameraPreview.play();
            });
        }
        setHidden(playButton, state !== 'playback');
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
        /* Lock 10 chip copy. */
        var playbackClock = Math.floor(durationSeconds / 60) + ':' + ('0' + Math.floor(durationSeconds % 60)).slice(-2);
        setDeviceStatus(cameraStatus, authenticated ? 'Local recording ready · ' + playbackClock : 'Local recording complete', 'is-ready');
        setDeviceStatus(microphoneStatus, authenticated ? 'Audio available · Local playback' : 'Audio captured locally', 'is-ready');
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
    if (authenticated) {
        /* Slice 5-6 review item 2 (visuals 09/15): copy/actions the
           authenticated composition needs that the shared public markup
           does not carry -- runtime-only overrides (never touch the
           server-rendered flag-off bytes) plus the new recovery-lock
           controls. */
        var startIcon = one('svg', startRecord);
        text(startRecord, 'Start recording');
        if (startIcon) startRecord.insertBefore(startIcon, startRecord.firstChild);
        text(discardRecord, 'Discard recording');
        var cameraOffButton = one('[data-is-camera-off]');
        if (cameraOffButton) {
            cameraOffButton.addEventListener('click', function () {
                releaseMedia(true);
                resetVideoUi();
                announce('Camera turned off. No recording was created.');
            });
        }
        var cameraRetryButton = one('[data-is-camera-retry]');
        if (cameraRetryButton) {
            cameraRetryButton.addEventListener('click', function () {
                resetVideoUi();
                enableCamera();
            });
        }
        var cameraHelpButton = one('[data-is-camera-help]');
        if (cameraHelpButton) {
            cameraHelpButton.addEventListener('click', function (event) {
                event.preventDefault();
                announce('Check your browser’s site settings for camera and microphone permission, and confirm no other application is using the camera.');
            });
        }
        var useTranscriptButton = one('[data-is-video-use-transcript]');
        if (useTranscriptButton) {
            useTranscriptButton.addEventListener('click', function (event) {
                event.preventDefault();
                videoTranscript.focus();
                videoTranscript.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
            });
        }
    }
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
    /* Slice 5-6 review item 4 (visuals 12/16/17): the authenticated History
       filters are Mode/Question family/Most recent, not the public page's
       Mode/Competency/Time-window trio -- these two are only ever present
       in the authenticated branch (null-guarded exactly like
       historyCompetency/historyTime above are for the public branch). */
    var historyFamily = one('[data-is-history-family]');
    var historySort = one('[data-is-history-sort]');
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
        var family = historyFamily ? historyFamily.value : 'all';
        var days = historyTime ? Number(historyTime.value) : 0;
        var cutoff = days ? Date.now() - days * 86400000 : 0;
        var filtered = records.filter(function (record) {
            return (mode === 'all' || record.mode === mode) &&
                (competency === 'all' || record.competency === competency) &&
                (family === 'all' || normalizeFamily(record.family) === family) &&
                (!cutoff || new Date(record.createdAt).getTime() >= cutoff);
        });
        // addHistoryRecord() unshifts, so records already arrive newest-first;
        // "Oldest first" is the only sort that needs an explicit reverse.
        if (historySort && historySort.value === 'oldest') filtered = filtered.slice().reverse();
        return filtered;
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

    /* Slice 5-6 review item 4 (visuals 12/16/17): the authenticated History
       view's four truth states (populated / genuinely-empty-with-storage /
       filtered-empty / storage-unavailable). Reuses the same
       storageAvailable/readHistoryRecords/filteredHistory/
       v2ReviewedRecords/comparableDimensionGroups/statusRank helpers
       renderV2History() already uses for the public page -- no duplicated
       comparison-gate logic, only a different rendered composition. */
    function renderAuthenticatedHistory() {
        var hasStorage = storageAvailable();
        var railTruth = one('.is-auth__rail-truth');
        if (railTruth) {
            railTruth.classList.toggle('is-auth__rail-truth--warning', !hasStorage);
            text(one('span', railTruth), hasStorage
                ? 'Drafts and History stay in this browser for this account. They do not sync across devices.'
                : 'Browser storage is unavailable. Drafts and History may not be retained. They do not sync across devices.');
        }

        var rows = one('[data-is-history-rows]');
        var emptyState = one('[data-is-history-empty-state]');
        var filteredEmptyState = one('[data-is-history-filtered-empty]');
        var unavailableState = one('[data-is-history-unavailable-state]');
        var cards = one('[data-is-history-cards]');
        var filterRow = one('[data-is-history-filter-row]');

        /* Lock 12 vs lock 17: the page sub-line states the truthful claim
           for the storage state it is actually in. */
        var historySub = one('#is-panel-history .is__sub');
        if (historySub) {
            text(historySub, hasStorage
                ? 'Reviewed answers stay in this browser for this account. They do not sync across devices.'
                : 'History is unavailable in this browser right now. Practice can continue without it.');
        }

        if (!hasStorage) {
            setHidden(rows, true);
            setHidden(emptyState, true);
            setHidden(filteredEmptyState, true);
            setHidden(unavailableState, false);
            setHidden(cards, true);
            if (filterRow) all('select', filterRow).forEach(function (select) { select.disabled = true; });
            text(one('[data-is-history-summary-label]'), 'History summary: browser storage is unavailable.');
            announce('History is unavailable in this browser right now. Practice can continue without it.');
            return;
        }
        if (filterRow) all('select', filterRow).forEach(function (select) { select.disabled = false; });

        var allRecords = readHistoryRecords();
        var records = filteredHistory(allRecords);
        var reviewed = v2ReviewedRecords(records);

        if (!allRecords.length) {
            setHidden(rows, true);
            setHidden(emptyState, false);
            setHidden(filteredEmptyState, true);
            setHidden(unavailableState, true);
            setHidden(cards, true);
            text(one('[data-is-history-summary-label]'), 'History summary: no reviewed answers yet.');
            return;
        }
        if (!records.length) {
            setHidden(rows, true);
            setHidden(emptyState, true);
            setHidden(filteredEmptyState, false);
            setHidden(unavailableState, true);
            setHidden(cards, true);
            text(one('[data-is-history-summary-label]'), 'History summary: no practice matches the current filters.');
            return;
        }

        setHidden(rows, false);
        setHidden(emptyState, true);
        setHidden(filteredEmptyState, true);
        setHidden(unavailableState, true);
        setHidden(cards, false);

        if (rows) {
            rows.replaceChildren();
            records.slice(0, 100).forEach(function (record) {
                var item = document.createElement('li');
                item.className = 'is-history__row';
                var icon = document.createElement('span');
                icon.className = 'is-history__row-icon';
                icon.setAttribute('aria-hidden', 'true');
                icon.innerHTML = record.mode === 'video'
                    ? '<svg viewBox="0 0 24 24"><rect x="3" y="6" width="13" height="12" rx="2"/><path d="m16 10 5-3v10l-5-3z"/></svg>'
                    : '<svg viewBox="0 0 24 24"><path d="M4 5.5h16v11H9l-5 4z"/><path d="M8 9h8M8 12.5h5"/></svg>';
                var body = document.createElement('div');
                body.className = 'is-history__row-body';
                var question = document.createElement('strong');
                question.textContent = record.question;
                body.append(question);
                /* Lock 12: mode·family sits over the date as one right-side
                   meta column, not stacked under the title -- a distinct
                   grid cell from the title so both stay aligned row to row. */
                var meta = document.createElement('div');
                meta.className = 'is-history__row-meta';
                var metaLine = document.createElement('span');
                metaLine.textContent = (record.mode === 'video' ? 'Video transcript' : 'Interview Me') + ' · ' + labelFamily(record.family);
                var date = document.createElement('time');
                date.className = 'is-history__row-date';
                date.dateTime = record.createdAt;
                date.textContent = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(record.createdAt));
                meta.append(metaLine, date);
                var chip = document.createElement('span');
                chip.className = 'is-history__row-chip';
                chip.textContent = record.reviewVersion === 'v2' ? 'Reviewed' : record.reviewVersion === 'local-recording' ? 'Local only' : record.reviewVersion === 'legacy-v1' ? 'Legacy' : 'Unavailable';
                var view = document.createElement('a');
                view.className = 'is__button is__button--quiet is-history__row-view';
                view.href = historyDetailUrl(record.id);
                view.textContent = 'View review';
                view.addEventListener('click', function (event) {
                    event.preventDefault();
                    openHistoryDetail(record, true);
                });
                var deleteButton = document.createElement('button');
                deleteButton.type = 'button';
                deleteButton.className = 'is-history__row-delete';
                deleteButton.setAttribute('aria-label', 'Delete this browser record');
                deleteButton.textContent = '⋮';
                deleteButton.addEventListener('click', function () {
                    if (!window.confirm('Delete this Interview Studio record from this browser?')) return;
                    var removed = removeHistoryRecord(record.id);
                    renderHistory();
                    announce(removed
                        ? 'Session record deleted from this browser.'
                        : 'This record could not be deleted in this browser right now. It may still be visible below.');
                });
                /* Reviewed chip + View review + overflow cluster together as
                   one grid cell so the row template only needs four columns
                   (icon/title/meta/actions) and the three controls wrap as a
                   unit on narrow viewports instead of each needing its own
                   named grid area. */
                var actions = document.createElement('div');
                actions.className = 'is-history__row-actions';
                actions.append(chip, view, deleteButton);
                item.append(icon, body, meta, actions);
                rows.appendChild(item);
            });
        }

        // Comparison gate (architecture 03 section 5, item 2): the exact
        // locked string unless >=2 comparable reviewed attempts exist for
        // the same question family and mode -- same threshold/grouping
        // renderV2History() already uses.
        var groups = comparableDimensionGroups(reviewed);
        var groupKeys = Object.keys(groups);
        var comparableGroup = groupKeys.filter(function (key) { return groups[key].length >= 2; })[0];
        var statusEl = one('[data-is-history-comparison-status]');
        var detailEl = one('[data-is-history-comparison-detail]');
        if (comparableGroup) {
            var entries = groups[comparableGroup];
            var latestEntry = entries[entries.length - 1];
            var changed = statusRank(latestEntry.dimension.status) - statusRank(entries[0].dimension.status);
            text(statusEl, (changed > 0 ? 'Improving: ' : changed < 0 ? 'Needs attention: ' : 'Holding steady: ') + readableDimensionKey(latestEntry.dimension.key));
            text(detailEl, labelFamily(latestEntry.record.family) + ' · ' + entries.length + ' comparable reviewed answers.');
        } else {
            text(statusEl, 'Not enough comparable practice yet.');
            text(detailEl, 'More like-for-like reviewed answers are needed before PeerSlate shows a pattern.');
        }

        var latest = reviewed[0];
        var labelEl = one('[data-is-history-single-review-label]');
        var headlineEl = one('[data-is-history-single-review-headline]');
        if (latest) {
            text(labelEl, 'From your ' + new Intl.DateTimeFormat(undefined, { month: 'long', day: 'numeric' }).format(new Date(latest.createdAt)) + ' review');
            text(headlineEl, (latest.improvements && latest.improvements[0]) || (latest.encouragement) || 'Add one observable outcome when you have a real example.');
        } else {
            text(labelEl, 'From your recent review');
            text(headlineEl, 'Complete a reviewed answer to see a suggestion here.');
        }

        text(one('[data-is-history-summary-label]'), 'History summary: ' + reviewed.length + (reviewed.length === 1 ? ' reviewed answer.' : ' reviewed answers.'));
    }

    function renderHistory() {
        renderV2History();
        if (authenticated) renderAuthenticatedHistory();
    }

    var historyRetryButton = one('[data-is-history-retry]');
    if (historyRetryButton) {
        historyRetryButton.addEventListener('click', function () {
            renderHistory();
            announce(storageAvailable()
                ? 'Browser storage is available again.'
                : 'Browser storage is still unavailable in this browser.');
        });
    }
    var historyStorageHelpButton = one('[data-is-history-storage-help]');
    if (historyStorageHelpButton) {
        historyStorageHelpButton.addEventListener('click', function () {
            announce('Check that this browser allows site storage and that you are not in private or incognito browsing, then choose Try History again.');
        });
    }
    var historyResetFiltersButton = one('[data-is-history-reset-filters]');
    if (historyResetFiltersButton) {
        historyResetFiltersButton.addEventListener('click', function () {
            if (historyMode) historyMode.value = 'all';
            if (historyFamily) historyFamily.value = 'all';
            if (historySort) historySort.value = 'recent';
            window.history.replaceState({}, '', root.getAttribute('data-history-url'));
            renderHistory();
            announce('Filters cleared. Showing all practice in this browser.');
        });
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
        if (authenticated) {
            /* Slice 5-6 review item 3 (visual 11): "You finished this
               practice session." is a fixed heading (not context-labeled --
               the rail already names the current session); the summary
               keeps practiced and reviewed counts explicitly distinct
               (architecture 03 section 5, "distinct practiced vs. reviewed
               counts"), matching the exact locked sentence shape. */
            text(one('[data-is-complete-title]'), 'You finished this practice session.');
            text(one('[data-is-complete-summary]'),
                session.questionTrail.length + (session.questionTrail.length === 1 ? ' question was' : ' questions were') + ' practiced. ' +
                records.length + (records.length === 1 ? ' answer was' : ' answers were') + ' reviewed in this browser.');
            var latestForClearer = records[0];
            text(one('[data-is-complete-clearer]'), latestForClearer && latestForClearer.encouragement
                ? latestForClearer.encouragement
                : 'Complete a reviewed answer to see what became clearer.');
        } else {
            var completeTitle = contextLabel(session.context) + ' session complete.';
            text(one('[data-is-complete-title]'), completeTitle);
            text(one('[data-is-complete-summary]'), records.length
                ? 'You completed an open-ended practice session with ' + records.length + (records.length === 1 ? ' reviewed answer.' : ' reviewed answers.')
                : 'You finished an open-ended practice session. No reviewed answer was added, and any typed draft remains in this browser.');
        }
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
        if (authenticated) {
            /* Review finding P1-2d (lock 11): the rail's "Completed
               questions" group lists the same reviewed-answer records as
               the main "Questions reviewed" card above (checkmark +
               truncated title) -- built on session finish, cleared by
               resetConsequenceStack() when the completion view is left. */
            var railCompleted = one('[data-is-rail-completed]');
            var railCompletedList = one('[data-is-rail-completed-list]');
            if (railCompleted && railCompletedList) {
                setHidden(railCompleted, records.length === 0);
                railCompletedList.replaceChildren();
                records.forEach(function (record) {
                    var item = document.createElement('li');
                    var icon = document.createElement('svg');
                    icon.setAttribute('viewBox', '0 0 24 24');
                    icon.setAttribute('aria-hidden', 'true');
                    icon.innerHTML = '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>';
                    var label = document.createElement('span');
                    label.textContent = record.question;
                    label.title = record.question;
                    item.append(icon, label);
                    railCompletedList.appendChild(item);
                });
            }
        }
        var latest = records[0];
        text(one('[data-is-complete-next-focus]'), latest && latest.improvements && latest.improvements[0]
            ? latest.improvements[0]
            : 'Complete a reviewed answer to see one focused next practice suggestion.');
        panels.forEach(function (panel) { panel.hidden = panel.getAttribute('data-is-panel') !== 'complete'; });
        root.setAttribute('data-is-active-mode', 'complete');
        if (historyLink) historyLink.removeAttribute('aria-current');
        if (authenticated) setFinishSessionCompleted(true);
        var title = one('[data-is-complete-title]');
        if (title) {
            title.setAttribute('tabindex', '-1');
            title.focus();
        }
        announce('Session complete. Your reviewed answers remain only in this browser.');
    }

    /* Slice 4 item 7: the rail's "Finish session" becomes a completed,
       non-interactive "Session finished" chip (visual 11) plus the
       session-stored truth line, once the session actually finishes; a
       fresh session restores the active control. */
    function setFinishSessionCompleted(completed) {
        all('[data-is-finish-session]').forEach(function (button) {
            button.disabled = completed;
            text(one('[data-is-finish-session-label]', button), completed ? 'Session finished' : 'Finish session');
        });
        setHidden(one('[data-is-finish-session-truth]'), !completed);
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

    /* historyCompetency/historyTime only exist for the public branch;
       historyFamily/historySort only exist for the authenticated branch
       (never all five at once) -- each reference below is null-guarded so
       whichever pair is absent for the current branch cannot throw. */
    [historyMode, historyCompetency, historyTime, historyFamily, historySort].forEach(function (select) {
        if (!select) return;
        select.addEventListener('change', function () {
            var params = new URLSearchParams();
            if (historyMode && historyMode.value !== 'all') params.set('mode', historyMode.value);
            if (historyCompetency && historyCompetency.value !== 'all') params.set('competency', historyCompetency.value);
            if (historyTime && historyTime.value !== 'all') params.set('days', historyTime.value);
            if (historyFamily && historyFamily.value !== 'all') params.set('family', historyFamily.value);
            if (historySort && historySort.value !== 'recent') params.set('sort', historySort.value);
            window.history.replaceState({}, '', root.getAttribute('data-history-url') + (params.toString() ? '?' + params.toString() : ''));
            renderHistory();
        });
    });

    var practiceRecommendationButton = one('[data-is-practice-recommendation]');
    if (practiceRecommendationButton) {
        /* data-is-practice-recommendation only exists in the public History
           & Progress card -- the authenticated History composition (slice
           5-6 review item 4) does not carry a like-for-like "Practice this
           focus" shortcut, so this whole handler is null-guarded rather
           than assumed to always exist. */
        practiceRecommendationButton.addEventListener('click', function (event) {
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
    }

    function restoreHistoryFilters() {
        if (initialView !== 'history' && window.location.pathname.indexOf('/history') === -1) return;
        var params = new URLSearchParams(window.location.search);
        if (historyMode && ['all', 'me', 'video'].indexOf(params.get('mode')) !== -1) historyMode.value = params.get('mode');
        if (historyTime && ['all', '7', '30'].indexOf(params.get('days')) !== -1) historyTime.value = params.get('days');
        if (historySort && ['recent', 'oldest'].indexOf(params.get('sort')) !== -1) historySort.value = params.get('sort');
        renderHistory();
        var competency = params.get('competency');
        if (historyCompetency && competency && all('option', historyCompetency).some(function (option) { return option.value === competency; })) historyCompetency.value = competency;
        var family = params.get('family');
        if (historyFamily && family && all('option', historyFamily).some(function (option) { return option.value === family; })) historyFamily.value = family;
        renderHistory();
        openHistoryDetailFromLocation();
    }

    one('[data-is-history-detail-close]').addEventListener('click', closeHistoryDetail);
    historyDetail.addEventListener('cancel', function (event) { event.preventDefault(); closeHistoryDetail(); });
    historyDetail.addEventListener('click', function (event) { if (event.target === historyDetail) closeHistoryDetail(); });
    one('[data-is-history-detail-delete]').addEventListener('click', function () {
        if (!historyDetailRecordId || !window.confirm('Delete this Interview Studio record from this browser?')) return;
        var removed = removeHistoryRecord(historyDetailRecordId);
        historyDetailOpenedWithPush = false;
        if (historyDetail.open) historyDetail.close();
        historyDetailRecordId = '';
        var params = new URLSearchParams(window.location.search);
        params.delete('session');
        window.history.replaceState({}, '', root.getAttribute('data-history-url') + (params.toString() ? '?' + params.toString() : ''));
        renderHistory();
        announce(removed
            ? 'Session record deleted from this browser.'
            : 'This record could not be deleted in this browser right now. It may still be visible below.');
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
            // A scoped (member) namespace only ever clears its own v3 keys —
            // the anonymous v1/v2 records are never touched, let alone
            // deleted, once a member is signed in (owner decision Q-B).
            Object.keys(window.localStorage).forEach(function (key) {
                if (key.indexOf(storagePrefix) === 0 || (!storageScope && key.indexOf(legacyStoragePrefix) === 0)) {
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
        if (levelSelect) levelSelect.value = session.level;
        if (familySelect) familySelect.value = session.family;
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
