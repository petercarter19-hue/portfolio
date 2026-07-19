(() => {
    "use strict";

    const modeButtons = Array.from(document.querySelectorAll("[data-capture-mode]"));
    const panels = Array.from(document.querySelectorAll("[data-capture-panel]"));
    const voicePanel = document.querySelector("[data-capture-panel='voice']");
    const textPanel = document.querySelector("[data-capture-panel='text']");
    if (!modeButtons.length || !voicePanel || !textPanel) return;

    const reviewStage = document.getElementById("voice-review-stage");

    const status = voicePanel.querySelector("[data-voice-status]");
    const timer = voicePanel.querySelector("[data-voice-timer]");
    const stateTitle = voicePanel.querySelector("[data-voice-state-title]");
    const stateHelp = voicePanel.querySelector("[data-voice-state-help]");
    const startButton = voicePanel.querySelector("[data-voice-action='start']");
    const stopButton = voicePanel.querySelector("[data-voice-action='stop']");
    const cancelButton = voicePanel.querySelector("[data-voice-action='cancel']");
    const textButton = voicePanel.querySelector("[data-voice-action='text']");
    const dismissButton = voicePanel.querySelector("[data-voice-action='dismiss']");
    const maxBytes = Number(voicePanel.dataset.maxBytes || 20971520);
    const maxSeconds = Number(voicePanel.dataset.maxSeconds || 180);
    const supportedTypes = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
    ];

    const STATE_COPY = {
        ready: {
            title: "Ready when you are",
            help: "Your browser asks for microphone permission when you start. You can edit or discard everything before anything is saved.",
        },
        requesting: {
            title: "Requesting microphone access",
            help: "Allow microphone access in your browser to continue.",
        },
        recording: {
            title: "Listening…",
            help: "Speak naturally. You can edit everything before anything is saved.",
        },
        processing: {
            title: "Preparing your private draft…",
            help: "Uploading the private recording, then transcribing it. Keep this page open.",
        },
        error: {
            title: "Something needs your attention",
            help: "See the message below, or switch to Type.",
        },
    };

    let recorder = null;
    let stream = null;
    let chunks = [];
    let startedAt = 0;
    let elapsedSeconds = 0;
    let ticker = null;
    let cancelled = false;
    let submitting = false;

    /* ---------- body-level portal (fixed overlays inside <main
       class="main-content"> paint below the sticky global-header because
       main-content establishes its own stacking context via
       isolation:isolate; see docs/initiatives/PS-VOICE-VISUAL-PARITY-001/
       DESIGN_INSTRUCTIONS.md section 7.1). ---------- */

    let overlayRoot = document.getElementById("voice-overlay-root");
    if (!overlayRoot) {
        overlayRoot = document.createElement("div");
        overlayRoot.id = "voice-overlay-root";
        document.body.appendChild(overlayRoot);
    }

    const portalPositions = new WeakMap();
    const portalBackdrops = new WeakMap();
    let scrollLockCount = 0;

    const lockScroll = () => {
        scrollLockCount += 1;
        document.body.style.overflow = "hidden";
    };

    const unlockScroll = () => {
        scrollLockCount = Math.max(0, scrollLockCount - 1);
        if (scrollLockCount === 0) document.body.style.overflow = "";
    };

    // While a modal is open, make everything except the overlay inert and
    // aria-hidden so keyboard and assistive-tech users cannot reach the page
    // behind it. Uses the `inert` attribute (removes the subtree from tab
    // order + AT) plus aria-hidden for older AT, and restores prior values.
    let backgroundInertEls = [];
    const setBackgroundInert = (on) => {
        if (on) {
            if (backgroundInertEls.length) return;
            backgroundInertEls = Array.prototype.filter.call(
                document.body.children,
                (el) => el !== overlayRoot && el.tagName !== "SCRIPT" && el.tagName !== "TEMPLATE"
            );
            backgroundInertEls.forEach((el) => {
                el.__hadInert = el.hasAttribute("inert");
                el.__hadAriaHidden = el.getAttribute("aria-hidden");
                el.setAttribute("inert", "");
                el.setAttribute("aria-hidden", "true");
            });
        } else {
            backgroundInertEls.forEach((el) => {
                if (!el.__hadInert) el.removeAttribute("inert");
                if (el.__hadAriaHidden === null) el.removeAttribute("aria-hidden");
                else el.setAttribute("aria-hidden", el.__hadAriaHidden);
                delete el.__hadInert;
                delete el.__hadAriaHidden;
            });
            backgroundInertEls = [];
        }
    };

    const anyModalOpen = () =>
        overlayRoot.querySelector(".owner-app__voice-backdrop") !== null;

    // <summary> is keyboard-focusable but matches none of the usual control
    // selectors, and a closed <details> hides its content via
    // content-visibility (which offsetParent does NOT reflect) rather than
    // display:none — so both the provider-transcript and delete-draft
    // disclosures would otherwise be mis-counted as trap boundaries. Include
    // summary, and prefer checkVisibility() (accounts for content-visibility)
    // over offsetParent, so the focus trap's first/last are the real ones.
    const FOCUSABLE_SELECTOR =
        "button, [href], input, textarea, select, summary, audio[controls], [tabindex]:not([tabindex='-1'])";
    const isReallyVisible = (el) =>
        typeof el.checkVisibility === "function"
            ? el.checkVisibility({ checkVisibilityCSS: true, contentVisibilityAuto: true })
            : el.offsetParent !== null;
    const focusableItems = (container) =>
        Array.prototype.filter.call(
            container.querySelectorAll(FOCUSABLE_SELECTOR),
            (el) => !el.disabled && el.tabIndex !== -1 && isReallyVisible(el)
        );

    const trapFocus = (event, container) => {
        if (event.key !== "Tab") return;
        const items = focusableItems(container);
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    };

    // opts.restoreFocus: element or () => element to focus after close (falls
    // back to the invoker that was focused when the modal opened).
    const portalIn = (el, onEscape, opts = {}) => {
        if (!el || portalPositions.has(el)) return;
        const invoker = document.activeElement;
        portalPositions.set(el, {
            parent: el.parentNode,
            next: el.nextSibling,
            invoker,
            restoreFocus: opts.restoreFocus,
        });
        const backdrop = document.createElement("div");
        backdrop.className = "owner-app__voice-backdrop";
        backdrop.appendChild(el);
        overlayRoot.appendChild(backdrop);
        portalBackdrops.set(el, backdrop);
        el.hidden = false;
        // Dialog semantics belong to the modal presentation only. They are
        // added here (and removed in portalOut) so the same section rendered
        // inline — without JavaScript, or after Close — is not falsely
        // announced as a modal dialog.
        el.setAttribute("role", "dialog");
        el.setAttribute("aria-modal", "true");
        lockScroll();
        setBackgroundInert(true);

        const keydownHandler = (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                onEscape();
                return;
            }
            trapFocus(event, el);
        };
        el.addEventListener("keydown", keydownHandler);
        el.__voiceKeydownHandler = keydownHandler;

        const preferred = el.querySelector("[data-autofocus]") || focusableItems(el)[0];
        if (preferred) preferred.focus();
    };

    const portalOut = (el) => {
        const pos = portalPositions.get(el);
        if (!pos) return;
        if (el.__voiceKeydownHandler) {
            el.removeEventListener("keydown", el.__voiceKeydownHandler);
            delete el.__voiceKeydownHandler;
        }
        el.removeAttribute("role");
        el.removeAttribute("aria-modal");
        const backdrop = portalBackdrops.get(el);
        if (pos.next && pos.next.parentNode === pos.parent) {
            pos.parent.insertBefore(el, pos.next);
        } else {
            pos.parent.appendChild(el);
        }
        if (backdrop && backdrop.parentNode) backdrop.remove();
        portalPositions.delete(el);
        portalBackdrops.delete(el);
        unlockScroll();
        if (!anyModalOpen()) setBackgroundInert(false);

        // Restore focus to the invoker (e.g. the Speak button) or an explicit
        // target, so keyboard/screen-reader users are not dropped at the top
        // of the document.
        let target = pos.restoreFocus;
        if (typeof target === "function") target = target();
        if (!target || !document.contains(target)) {
            target = pos.invoker && document.contains(pos.invoker) ? pos.invoker : null;
        }
        if (target && typeof target.focus === "function") target.focus();
    };

    /* ---------- voice recording lifecycle ---------- */

    const setVoiceState = (state) => {
        voicePanel.dataset.voiceState = state;
        const copy = STATE_COPY[state];
        if (copy && stateTitle) stateTitle.textContent = copy.title;
        if (copy && stateHelp) stateHelp.textContent = copy.help;
    };

    const announce = (message, isError = false, state = null) => {
        status.textContent = message;
        status.classList.toggle("owner-app__voice-status--error", isError);
        if (state) setVoiceState(state);
    };

    const formatTime = (seconds) => {
        const bounded = Math.max(0, Math.min(maxSeconds, Math.floor(seconds)));
        return `${Math.floor(bounded / 60)}:${String(bounded % 60).padStart(2, "0")}`;
    };

    const updateTimer = () => {
        elapsedSeconds = (Date.now() - startedAt) / 1000;
        timer.textContent = `${formatTime(elapsedSeconds)} / ${formatTime(maxSeconds)}`;
        if (elapsedSeconds >= maxSeconds && recorder?.state === "recording") {
            announce("Three-minute limit reached. Preparing the private draft.", false, "processing");
            recorder.stop();
        }
    };

    const stopTracks = () => {
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
    };

    const resetControls = () => {
        window.clearInterval(ticker);
        ticker = null;
        stopTracks();
        recorder = null;
        stopButton.disabled = true;
        cancelButton.disabled = true;
        submitting = false;
        setVoiceState("ready");
    };

    const chooseMimeType = () => {
        if (!window.MediaRecorder || typeof window.MediaRecorder.isTypeSupported !== "function") {
            return "";
        }
        return supportedTypes.find((type) => window.MediaRecorder.isTypeSupported(type)) || "";
    };

    const voiceModeButton = modeButtons.find((button) => button.dataset.captureMode === "voice");

    // Stop and clean up any in-progress recording without touching the portal.
    const teardownRecording = () => {
        if (recorder?.state === "recording") {
            cancelled = true;
            recorder.stop();
        }
        resetControls();
    };

    const switchMode = (mode, focus = true) => {
        // Leaving Voice closes the modal first; portalOut restores focus to
        // the Speak button. Done before re-entering switchMode so there is no
        // recursion between switchMode and the modal-close path.
        if (mode !== "voice" && portalPositions.has(voicePanel)) {
            teardownRecording();
            portalOut(voicePanel);
        }
        modeButtons.forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.captureMode === mode));
        });
        panels.forEach((panel) => {
            panel.hidden = panel.dataset.capturePanel !== mode;
        });
        if (mode === "voice") {
            portalIn(
                voicePanel,
                () => switchMode("text", false),
                { restoreFocus: () => voiceModeButton }
            );
        } else if (focus && mode === "text") {
            document.querySelector("#capture-body")?.focus();
        }
    };

    const uploadRecording = async (blob, duration) => {
        if (submitting) return;
        if (!navigator.onLine) {
            announce("You appear to be offline. The recording was not uploaded. Use text or record again when online.", true, "error");
            resetControls();
            return;
        }
        if (blob.size > maxBytes) {
            announce("The recording exceeded 20 MB and was not uploaded. Use text or make a shorter recording.", true, "error");
            resetControls();
            return;
        }
        submitting = true;
        announce("Uploading the private recording, then transcribing it. Keep this page open.", false, "processing");
        const formData = new FormData();
        formData.append("audio", blob, "recording");
        formData.append("duration_seconds", String(Math.min(duration, maxSeconds)));
        try {
            const response = await window.fetch(voicePanel.dataset.uploadUrl, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: { "X-Requested-With": "fetch" },
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok || !result.review_url) {
                if (result.review_url) {
                    window.location.assign(result.review_url);
                    return;
                }
                const message = result.error === "transcription-failed"
                    ? "The recording stayed private, but transcription failed. Open the saved draft to retry or delete it."
                    : "The private recording could not be completed. Nothing was saved as a Capture.";
                announce(message, true, "error");
                resetControls();
                return;
            }
            announce("Transcription is ready for your review. Nothing has been saved as a Capture yet.");
            window.location.assign(result.review_url);
        } catch (_error) {
            announce("The upload did not finish. Nothing was saved as a Capture. Use text or try again.", true, "error");
            resetControls();
        }
    };

    const startRecording = async () => {
        if (submitting || recorder?.state === "recording") return;
        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            announce("Voice recording is not supported in this browser. Text Capture remains available.", true, "error");
            textButton.focus();
            return;
        }
        const mimeType = chooseMimeType();
        if (!mimeType) {
            announce("This browser cannot make a supported recording. Text Capture remains available.", true, "error");
            textButton.focus();
            return;
        }
        announce("Requesting microphone permission.", false, "requesting");
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            chunks = [];
            cancelled = false;
            elapsedSeconds = 0;
            recorder = new MediaRecorder(stream, { mimeType });
            recorder.addEventListener("dataavailable", (event) => {
                if (event.data?.size) chunks.push(event.data);
                const totalBytes = chunks.reduce((sum, chunk) => sum + chunk.size, 0);
                if (totalBytes > maxBytes && recorder?.state === "recording") {
                    cancelled = true;
                    announce("The recording exceeded 20 MB and was stopped without uploading.", true, "error");
                    recorder.stop();
                }
            });
            recorder.addEventListener("stop", () => {
                window.clearInterval(ticker);
                ticker = null;
                stopTracks();
                const duration = Math.min((Date.now() - startedAt) / 1000, maxSeconds);
                if (cancelled) {
                    chunks = [];
                    resetControls();
                    return;
                }
                const blob = new Blob(chunks, { type: recorder.mimeType });
                chunks = [];
                uploadRecording(blob, duration);
            }, { once: true });
            recorder.start(1000);
            startedAt = Date.now();
            timer.textContent = `0:00 / ${formatTime(maxSeconds)}`;
            ticker = window.setInterval(updateTimer, 250);
            stopButton.disabled = false;
            cancelButton.disabled = false;
            announce("Recording. Select Stop when you are finished.", false, "recording");
            stopButton.focus();
        } catch (_error) {
            resetControls();
            announce("Microphone access was denied or unavailable. Text Capture remains available.", true, "error");
            textButton.focus();
        }
    };

    modeButtons.forEach((button) => {
        button.addEventListener("click", () => switchMode(button.dataset.captureMode));
    });
    startButton.addEventListener("click", startRecording);
    stopButton.addEventListener("click", () => {
        if (recorder?.state === "recording") {
            announce("Recording stopped. Preparing the private upload.", false, "processing");
            recorder.stop();
        }
    });
    // Cancel abandons an in-progress recording and closes the modal.
    cancelButton.addEventListener("click", () => {
        announce("Recording cancelled. No audio was uploaded.", false, "ready");
        switchMode("text", false);
    });
    // Switch to Type closes the modal and moves to the text form.
    textButton.addEventListener("click", () => switchMode("text"));
    // Close (X) and Escape keep nothing recorded and return to the Type surface.
    if (dismissButton) {
        dismissButton.addEventListener("click", () => switchMode("text", false));
    }

    // Opening choice: Speak and Type are both first-class. The page lands on
    // the Type surface (server-rendered, works without JavaScript). Choosing
    // Speak opens the focused Voice modal; the Voice modal is NEVER auto-opened
    // on ordinary page load (manager decision 2026-07-19,
    // docs/initiatives/PS-VOICE-001/06_VISUAL_PARITY_CORRECTION.md). When a
    // voice draft is pending, the review stage below is what opens instead.
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !chooseMimeType()) {
        startButton.disabled = true;
        announce("Voice recording is not supported in this browser. Text Capture remains available.", true, "error");
    }

    /* ---------- review stage: auto-opens on load (a voice_draft exists),
       de-portals (not discards) on close — the draft is real, server-
       persisted content either way. ---------- */

    if (reviewStage) {
        const closeReview = () => portalOut(reviewStage);
        const reviewDismiss = reviewStage.querySelector("[data-voice-action='dismiss']");
        if (reviewDismiss) reviewDismiss.addEventListener("click", closeReview);
        // Auto-opens as a modal (the page was loaded specifically to review a
        // pending draft). On Close it de-portals to an inline, non-dialog view
        // — the draft is server-persisted and stays on the page — and focus
        // lands on the now-inline review heading so it can be resumed.
        portalIn(reviewStage, closeReview, {
            restoreFocus: () => reviewStage.querySelector("#voice-review-title"),
        });

        // "More ways to use this" ships open (server-rendered, so it works
        // with or without JS). On mobile only, collapse it by default for
        // progressive disclosure — Chromium's native <details> disclosure-
        // content sizing can't be reliably forced open via author CSS once
        // collapsed, so JS drives the open attribute directly instead of
        // fighting that with CSS.
        const more = reviewStage.querySelector(".owner-app__voice-more");
        if (more) {
            const mobileQuery = window.matchMedia("(max-width: 540px)");
            const syncMoreOpenState = (event) => {
                if (event.matches) more.removeAttribute("open");
                else more.setAttribute("open", "");
            };
            syncMoreOpenState(mobileQuery);
            mobileQuery.addEventListener("change", syncMoreOpenState);
        }
    }
})();
