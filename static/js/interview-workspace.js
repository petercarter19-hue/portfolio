/* INTERVIEW WORKSPACE (2026-07-13)
   Chrome around the original practice studio. interview.js runs the studio
   itself (questions, drafts, recording, feedback, mock interviews) exactly
   as before — this layer adds: mode/view switching, the question library,
   the session queue, live stat mirrors, the Answer Lab comparison + rewrite
   tools, and the honest Video Studio shell (local preview only; nothing is
   uploaded, stored, or analyzed). */
(function () {
    'use strict';

    var root = document.querySelector('[data-ivw]');
    if (!root) return;

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var live = root.querySelector('[data-ivw-live]');

    function announce(text) { if (live) live.textContent = text; }

    /* ------------------------------------------------------------------
       Views + modes
       ------------------------------------------------------------------ */
    var views = Array.prototype.slice.call(root.querySelectorAll('[data-ivw-view]'));
    var modeTabs = Array.prototype.slice.call(root.querySelectorAll('[data-ivw-mode]'));
    var viewLinks = Array.prototype.slice.call(root.querySelectorAll('.ivw-view-link'));

    function showView(name) {
        views.forEach(function (v) {
            v.classList.toggle('is-active', v.getAttribute('data-ivw-view') === name);
        });
        viewLinks.forEach(function (l) {
            l.classList.toggle('is-active', l.getAttribute('data-ivw-goto') === name);
        });
        if (!reduceMotion) window.scrollTo({ top: 0, behavior: 'auto' });
    }

    function setMode(mode) {
        modeTabs.forEach(function (t) {
            t.setAttribute('aria-selected', String(t.getAttribute('data-ivw-mode') === mode));
        });
        root.setAttribute('data-ivw-active-mode', mode);
        if (mode === 'video') {
            showView('video');
            announce('Video Studio. Local preview only — nothing is uploaded or analyzed.');
            return;
        }
        showView('practice');
        // Drive the ORIGINAL direction tabs so interview.js behavior follows.
        var target = document.getElementById(mode === 'you' ? 'iv-dir-ai' : 'iv-dir-me');
        if (target && target.getAttribute('aria-selected') !== 'true') target.click();
        var rewrites = root.querySelector('[data-ivw-rewrites]');
        if (rewrites) rewrites.hidden = mode !== 'you';
        announce(mode === 'you' ? 'Answer Lab: ask a question, compare with the model answer.' : 'Focused practice: answer and get coached.');
    }

    modeTabs.forEach(function (t) {
        t.addEventListener('click', function () { setMode(t.getAttribute('data-ivw-mode')); });
    });
    root.addEventListener('click', function (event) {
        var goto = event.target.closest('[data-ivw-goto]');
        if (goto) showView(goto.getAttribute('data-ivw-goto'));
    });

    /* ------------------------------------------------------------------
       Question bank access (same data island interview.js reads)
       ------------------------------------------------------------------ */
    var bank = Array.prototype.slice.call(document.querySelectorAll('.iq-item')).map(function (btn) {
        return { text: btn.textContent.trim(), mode: btn.dataset.mode, topic: btn.dataset.topic };
    });

    function setStudioQuestion(text, topic) {
        var q = document.getElementById('iv-question');
        var chip = document.getElementById('iv-topic-chip');
        if (q) q.textContent = text;
        if (chip && topic) chip.textContent = topic;
        var draft = document.getElementById('iv-answer');
        if (draft) draft.focus({ preventScroll: true });
    }

    /* ------------------------------------------------------------------
       Home: Continue Practice + Question Library
       ------------------------------------------------------------------ */
    var continueQ = root.querySelector('[data-ivw-continue-question]');
    var continueTopic = root.querySelector('[data-ivw-continue-topic]');
    var continueDraft = root.querySelector('[data-ivw-continue-draft]');

    function syncContinueCard() {
        var q = document.getElementById('iv-question');
        var chip = document.getElementById('iv-topic-chip');
        if (continueQ && q) continueQ.textContent = q.textContent.trim();
        if (continueTopic && chip) continueTopic.textContent = chip.textContent.trim();
        if (continueDraft) {
            var hasDraft = false;
            try {
                var key = 'iv-draft::' + (q ? q.textContent.trim() : '');
                hasDraft = !!window.localStorage.getItem(key);
            } catch (e) { /* private mode */ }
            continueDraft.hidden = !hasDraft;
        }
    }

    var startBtn = root.querySelector('[data-ivw-start]');
    if (startBtn) startBtn.addEventListener('click', function () { setMode('me'); });
    var startModel = root.querySelector('[data-ivw-start-model]');
    if (startModel) startModel.addEventListener('click', function () { setMode('you'); });

    // Library: search + topic filter over the real 60-question bank.
    var libraryList = root.querySelector('[data-ivw-library]');
    var libraryCount = root.querySelector('[data-ivw-library-count]');
    var librarySearch = document.getElementById('ivw-library-search');
    var libraryFilters = Array.prototype.slice.call(root.querySelectorAll('[data-ivw-filter]'));
    var activeFilter = 'all';

    function renderLibrary() {
        if (!libraryList) return;
        var term = (librarySearch && librarySearch.value || '').toLowerCase();
        var matches = bank.filter(function (q) {
            if (activeFilter !== 'all' && q.topic !== activeFilter) return false;
            return !term || q.text.toLowerCase().indexOf(term) !== -1;
        });
        libraryList.innerHTML = '';
        matches.slice(0, 6).forEach(function (q) {
            var li = document.createElement('li');
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.innerHTML = '<span>' + q.text + '</span><small>' + q.topic +
                ' · ' + (q.mode === 'star' ? 'STAR' : 'Behavioral') + '</small>';
            btn.addEventListener('click', function () {
                setStudioQuestion(q.text, q.topic);
                setMode('me');
            });
            li.appendChild(btn);
            libraryList.appendChild(li);
        });
        if (libraryCount) {
            libraryCount.textContent = matches.length + ' of ' + bank.length + ' questions' +
                (matches.length > 6 ? ' — showing 6' : '');
        }
    }

    if (librarySearch) librarySearch.addEventListener('input', renderLibrary);
    libraryFilters.forEach(function (f) {
        f.addEventListener('click', function () {
            activeFilter = f.getAttribute('data-ivw-filter');
            libraryFilters.forEach(function (b) { b.classList.toggle('is-active', b === f); });
            renderLibrary();
        });
    });

    /* ------------------------------------------------------------------
       Session queue (practice view)
       ------------------------------------------------------------------ */
    var queueList = root.querySelector('[data-ivw-queue]');
    var queuePanel = root.querySelector('[data-ivw-queue-panel]');
    var queueToggle = root.querySelector('[data-ivw-queue-toggle]');

    function renderQueue() {
        if (!queueList) return;
        var current = (document.getElementById('iv-question') || {}).textContent || '';
        current = current.trim();
        queueList.innerHTML = '';
        var upcoming = bank.filter(function (q) { return q.text !== current; }).slice(0, 5);
        var head = document.createElement('li');
        head.className = 'is-current';
        head.innerHTML = '<b>Now</b><span>' + current + '</span>';
        queueList.appendChild(head);
        upcoming.forEach(function (q) {
            var li = document.createElement('li');
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.innerHTML = '<span>' + q.text + '</span><small>' + q.topic + '</small>';
            btn.addEventListener('click', function () { setStudioQuestion(q.text, q.topic); });
            li.appendChild(btn);
            queueList.appendChild(li);
        });
    }

    if (queueToggle && queuePanel) {
        queueToggle.addEventListener('click', function () {
            var open = queuePanel.classList.toggle('is-collapsed') === false;
            queueToggle.setAttribute('aria-expanded', String(open));
            queueToggle.textContent = open ? 'Hide' : 'Show';
        });
    }

    var queueAdd = root.querySelector('[data-ivw-queue-add]');
    if (queueAdd) {
        queueAdd.addEventListener('submit', function (event) {
            event.preventDefault();
            var input = document.getElementById('ivw-custom-question');
            var text = (input.value || '').trim();
            if (!text) return;
            setStudioQuestion(text, 'Custom');
            input.value = '';
        });
    }

    /* ------------------------------------------------------------------
       Live mirrors: watch the studio's own outputs and reflect them in
       Home, Review Room, and Progress. No duplicate logic — the studio
       remains the single source of truth.
       ------------------------------------------------------------------ */
    function mirror() {
        var session = (document.getElementById('iv-session') || {}).textContent || '';
        var answeredMatch = session.match(/(\d+)\s+answered/);
        var answered = answeredMatch ? answeredMatch[1] : '0';
        var avgMatch = session.match(/avg\s+(\d+)/i);
        var scoreNum = (document.getElementById('iv-score-num') || {}).textContent || '–';
        var scoreTier = (document.getElementById('iv-score-tier') || {}).textContent || 'Not rated';

        ['[data-ivw-stat-answered]', '[data-ivw-stat-answered2]'].forEach(function (sel) {
            var el = root.querySelector(sel); if (el) el.textContent = answered;
        });
        ['[data-ivw-stat-average]', '[data-ivw-stat-average2]'].forEach(function (sel) {
            var el = root.querySelector(sel);
            if (el) el.textContent = avgMatch ? avgMatch[1] : (scoreNum !== '–' ? scoreNum : '–');
        });
        var modeEl = root.querySelector('[data-ivw-stat-mode]');
        if (modeEl) {
            var m = root.getAttribute('data-ivw-active-mode') || 'me';
            modeEl.textContent = m === 'you' ? 'Answer Lab' : (m === 'video' ? 'Video' : 'Practice');
        }

        var rs = root.querySelector('[data-ivw-review-score]');
        var rt = root.querySelector('[data-ivw-review-tier]');
        var rsess = root.querySelector('[data-ivw-review-session]');
        if (rs) rs.textContent = scoreNum;
        if (rt) rt.textContent = scoreTier;
        if (rsess) rsess.textContent = session.replace('This session: ', '');

        var fb = document.getElementById('iv-feedback');
        var rfb = root.querySelector('[data-ivw-review-feedback]');
        if (fb && rfb && !fb.querySelector('.iv-feedback__empty')) {
            rfb.innerHTML = fb.innerHTML;
        }
        syncContinueCard();
        renderQueue();
    }

    var observed = ['iv-session', 'iv-score-num', 'iv-question', 'iv-feedback'];
    if ('MutationObserver' in window) {
        observed.forEach(function (id) {
            var el = document.getElementById(id);
            if (!el) return;
            new MutationObserver(mirror).observe(el, { childList: true, characterData: true, subtree: true });
        });
    }

    /* ------------------------------------------------------------------
       Answer Lab rewrite tools — real /api/chat calls, clearly labeled as
       AI suggestions about the USER'S OWN draft. Never presented as
       Pete's experience.
       ------------------------------------------------------------------ */
    var REWRITES = {
        concise: 'Rewrite the following interview answer draft to be more concise while keeping its facts unchanged. Do not invent any new experience or numbers.',
        impact: 'Rewrite the following interview answer draft to lead with impact and results, keeping every fact unchanged. Do not invent new experience or numbers.',
        specific: 'Rewrite the following interview answer draft to be more specific and concrete, keeping every fact unchanged. Where a detail is missing, insert a bracketed placeholder like [add metric] instead of inventing one.',
        star: 'Restructure the following interview answer draft into STAR format (Situation, Task, Action, Result) with clear labels, keeping every fact unchanged. Do not invent new experience or numbers.'
    };

    var rewriteOut = root.querySelector('[data-ivw-rewrite-out]');
    Array.prototype.slice.call(root.querySelectorAll('[data-ivw-rewrite]')).forEach(function (btn) {
        btn.addEventListener('click', function () {
            var draft = (document.getElementById('iv-answer') || {}).value || '';
            if (!draft.trim()) {
                if (rewriteOut) {
                    rewriteOut.hidden = false;
                    rewriteOut.textContent = 'Write a draft first — the rewrite tools work on your own words.';
                }
                return;
            }
            if (rewriteOut) {
                rewriteOut.hidden = false;
                rewriteOut.textContent = 'Rewriting…';
            }
            btn.disabled = true;
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: REWRITES[btn.getAttribute('data-ivw-rewrite')] + '\n\nDraft:\n' + draft })
            }).then(function (r) { return r.json(); }).then(function (data) {
                if (rewriteOut) rewriteOut.textContent = (data.reply || data.response || 'No suggestion returned.');
            }).catch(function () {
                if (rewriteOut) rewriteOut.textContent = 'The rewrite service is unavailable right now.';
            }).finally(function () { btn.disabled = false; });
        });
    });

    /* ------------------------------------------------------------------
       Video Studio — honest local-only shell.
       getUserMedia preview + device labels + mic level. No recording, no
       upload, no analysis. Explicit permission/error states.
       ------------------------------------------------------------------ */
    var camVideo = root.querySelector('[data-ivw-camera]');
    var camState = root.querySelector('[data-ivw-camera-state]');
    var camStart = root.querySelector('[data-ivw-camera-start]');
    var camStop = root.querySelector('[data-ivw-camera-stop]');
    var camSelect = root.querySelector('[data-ivw-camera-select]');
    var micLevel = root.querySelector('[data-ivw-miclevel]');
    var checkCam = root.querySelector('[data-ivw-check-camera]');
    var checkMic = root.querySelector('[data-ivw-check-mic]');
    var rehearseBtn = root.querySelector('[data-ivw-rehearse]');
    var timerEl = root.querySelector('[data-ivw-timer]');
    var stream = null;
    var audioCtx = null;
    var rafId = null;
    var timerId = null;

    function camMessage(title, body) {
        if (!camState) return;
        camState.hidden = false;
        camState.innerHTML = '<p><strong>' + title + '</strong></p><p>' + body + '</p>';
    }

    function stopPreview() {
        if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
        if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
        if (rafId) cancelAnimationFrame(rafId);
        if (timerId) { clearInterval(timerId); timerId = null; }
        if (camVideo) { camVideo.srcObject = null; }
        if (camStop) camStop.hidden = true;
        if (camStart) camStart.hidden = false;
        if (micLevel) micLevel.hidden = true;
        if (timerEl) timerEl.hidden = true;
        if (rehearseBtn) { rehearseBtn.disabled = true; rehearseBtn.textContent = 'Start local rehearsal timer'; }
        camMessage('Camera is off.', 'Start the device check to see a local preview. Your browser will ask for permission.');
        if (checkCam) checkCam.textContent = 'Not checked';
        if (checkMic) checkMic.textContent = 'Not checked';
    }

    function startPreview() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            camMessage('This browser cannot open the camera.', 'Try a current version of Chrome, Edge, or Safari.');
            return;
        }
        camMessage('Requesting permission…', 'Allow camera and microphone access to run the device check.');
        navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(function (media) {
            stream = media;
            if (camVideo) {
                camVideo.srcObject = media;
                camVideo.play().catch(function () {});
            }
            if (camState) camState.hidden = true;
            if (camStart) camStart.hidden = true;
            if (camStop) camStop.hidden = false;
            if (rehearseBtn) rehearseBtn.disabled = false;
            if (checkCam) checkCam.textContent = 'Working';
            if (checkMic) checkMic.textContent = 'Working';

            // Populate camera choices with real device labels.
            if (camSelect && navigator.mediaDevices.enumerateDevices) {
                navigator.mediaDevices.enumerateDevices().then(function (devices) {
                    var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
                    if (cams.length > 1) {
                        camSelect.hidden = false;
                        camSelect.innerHTML = '';
                        cams.forEach(function (d, i) {
                            var opt = document.createElement('option');
                            opt.value = d.deviceId;
                            opt.textContent = d.label || ('Camera ' + (i + 1));
                            camSelect.appendChild(opt);
                        });
                    }
                });
            }

            // Simple mic level meter (observable behavior only).
            try {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                var source = audioCtx.createMediaStreamSource(media);
                var analyser = audioCtx.createAnalyser();
                analyser.fftSize = 256;
                source.connect(analyser);
                var data = new Uint8Array(analyser.frequencyBinCount);
                if (micLevel) micLevel.hidden = false;
                (function tick() {
                    analyser.getByteFrequencyData(data);
                    var sum = 0;
                    for (var i = 0; i < data.length; i++) sum += data[i];
                    var level = Math.min(100, Math.round((sum / data.length) / 1.2));
                    if (micLevel) micLevel.style.setProperty('--level', level + '%');
                    rafId = requestAnimationFrame(tick);
                })();
            } catch (e) { /* meter is optional */ }
        }).catch(function (err) {
            if (err && (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')) {
                camMessage('Permission was denied.', 'Enable camera access for this site in your browser settings, then try again.');
            } else if (err && err.name === 'NotFoundError') {
                camMessage('No camera found.', 'Connect a camera or check that another app is not using it.');
            } else {
                camMessage('The camera could not start.', 'Close other apps using the camera and try again.');
            }
            if (checkCam) checkCam.textContent = 'Unavailable';
            if (checkMic) checkMic.textContent = 'Unavailable';
        });
    }

    if (camStart) camStart.addEventListener('click', startPreview);
    if (camStop) camStop.addEventListener('click', stopPreview);

    if (camSelect) {
        camSelect.addEventListener('change', function () {
            if (!stream) return;
            var id = camSelect.value;
            navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: id } }, audio: true })
                .then(function (media) {
                    stream.getTracks().forEach(function (t) { t.stop(); });
                    stream = media;
                    if (camVideo) camVideo.srcObject = media;
                });
        });
    }

    if (rehearseBtn) {
        rehearseBtn.addEventListener('click', function () {
            if (timerId) { clearInterval(timerId); timerId = null; timerEl.hidden = true; rehearseBtn.textContent = 'Start local rehearsal timer'; return; }
            var start = new Date().getTime();
            timerEl.hidden = false;
            rehearseBtn.textContent = 'Stop rehearsal timer';
            timerId = setInterval(function () {
                var s = Math.floor((new Date().getTime() - start) / 1000);
                var mm = String(Math.floor(s / 60)); if (mm.length < 2) mm = '0' + mm;
                var ss = String(s % 60); if (ss.length < 2) ss = '0' + ss;
                timerEl.textContent = mm + ':' + ss;
            }, 500);
        });
    }

    // Session-type chips (visual state only — prompt drives the rehearsal).
    Array.prototype.slice.call(root.querySelectorAll('[data-ivw-videotype]')).forEach(function (chip) {
        chip.addEventListener('click', function () {
            Array.prototype.slice.call(root.querySelectorAll('[data-ivw-videotype]')).forEach(function (c) {
                c.classList.toggle('is-active', c === chip);
            });
        });
    });

    // Keep the video prompt in step with the current studio question.
    var videoPrompt = root.querySelector('[data-ivw-video-prompt]');
    function syncVideoPrompt() {
        var q = document.getElementById('iv-question');
        if (videoPrompt && q && !videoPrompt.dataset.touched) videoPrompt.value = q.textContent.trim();
    }
    if (videoPrompt) videoPrompt.addEventListener('input', function () { videoPrompt.dataset.touched = '1'; });

    // Stop the camera when leaving the video view or the page.
    root.addEventListener('click', function (event) {
        var goto = event.target.closest('[data-ivw-goto], [data-ivw-mode]');
        if (!goto) return;
        var name = goto.getAttribute('data-ivw-goto') || goto.getAttribute('data-ivw-mode');
        if (name !== 'video') stopPreview();
        if (name === 'video') syncVideoPrompt();
    });
    window.addEventListener('pagehide', stopPreview);

    /* ------------------------------------------------------------------
       Progress: recommended next session from under-practiced topics
       (computed from the real bank — not fake analytics).
       ------------------------------------------------------------------ */
    var recTitle = root.querySelector('[data-ivw-recommend-title]');
    var recStart = root.querySelector('[data-ivw-recommend-start]');
    var recommended = null;
    (function computeRecommendation() {
        var counts = {};
        bank.forEach(function (q) { counts[q.topic] = (counts[q.topic] || 0) + 1; });
        var topics = Object.keys(counts).sort(function (a, b) { return counts[a] - counts[b]; });
        var topic = topics[0];
        recommended = bank.filter(function (q) { return q.topic === topic; })[0] || bank[0];
        if (recTitle && recommended) recTitle.textContent = recommended.text;
    })();
    if (recStart) {
        recStart.addEventListener('click', function () {
            if (recommended) setStudioQuestion(recommended.text, recommended.topic);
            setMode('me');
        });
    }

    /* ------------------------------------------------------------------
       Escape closes the collapsible drawers on small screens.
       ------------------------------------------------------------------ */
    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') return;
        Array.prototype.slice.call(root.querySelectorAll('details.ivw-tool[open]')).forEach(function (d) {
            if (window.matchMedia('(max-width: 62rem)').matches) d.removeAttribute('open');
        });
    });

    /* Boot: land on Home with Interview Me armed underneath. */
    setMode('me');
    showView('home');
    mirror();
    renderLibrary();
    renderQueue();
    syncContinueCard();
})();
