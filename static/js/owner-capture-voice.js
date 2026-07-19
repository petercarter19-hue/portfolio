(() => {
    "use strict";

    const modeButtons = Array.from(document.querySelectorAll("[data-capture-mode]"));
    const panels = Array.from(document.querySelectorAll("[data-capture-panel]"));
    const voicePanel = document.querySelector("[data-capture-panel='voice']");
    const textPanel = document.querySelector("[data-capture-panel='text']");
    if (!modeButtons.length || !voicePanel || !textPanel) return;

    const status = voicePanel.querySelector("[data-voice-status]");
    const timer = voicePanel.querySelector("[data-voice-timer]");
    const startButton = voicePanel.querySelector("[data-voice-action='start']");
    const stopButton = voicePanel.querySelector("[data-voice-action='stop']");
    const cancelButton = voicePanel.querySelector("[data-voice-action='cancel']");
    const textButton = voicePanel.querySelector("[data-voice-action='text']");
    const maxBytes = Number(voicePanel.dataset.maxBytes || 20971520);
    const maxSeconds = Number(voicePanel.dataset.maxSeconds || 180);
    const supportedTypes = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
    ];

    let recorder = null;
    let stream = null;
    let chunks = [];
    let startedAt = 0;
    let elapsedSeconds = 0;
    let ticker = null;
    let cancelled = false;
    let submitting = false;

    const setVoiceState = (state) => {
        voicePanel.dataset.voiceState = state;
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
        startButton.disabled = false;
        stopButton.disabled = true;
        cancelButton.disabled = true;
        submitting = false;
    };

    const chooseMimeType = () => {
        if (!window.MediaRecorder || typeof window.MediaRecorder.isTypeSupported !== "function") {
            return "";
        }
        return supportedTypes.find((type) => window.MediaRecorder.isTypeSupported(type)) || "";
    };

    const switchMode = (mode, focus = true) => {
        modeButtons.forEach((button) => {
            const selected = button.dataset.captureMode === mode;
            button.setAttribute("aria-pressed", String(selected));
        });
        panels.forEach((panel) => {
            panel.hidden = panel.dataset.capturePanel !== mode;
        });
        if (focus) {
            if (mode === "text") document.querySelector("#capture-body")?.focus();
            else startButton.focus();
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
        startButton.disabled = true;
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
            startButton.disabled = true;
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

    const cancelRecording = () => {
        if (recorder?.state === "recording") {
            cancelled = true;
            recorder.stop();
        } else {
            resetControls();
        }
        announce("Recording cancelled. No audio was uploaded.", false, "idle");
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
    cancelButton.addEventListener("click", cancelRecording);
    textButton.addEventListener("click", () => {
        if (recorder?.state === "recording") cancelRecording();
        switchMode("text");
    });

    // Voice is the production-intent opening path when JavaScript is available.
    // The server-rendered Type form remains the no-script fallback and its choice stays visible.
    switchMode("voice", false);

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !chooseMimeType()) {
        startButton.disabled = true;
        announce("Voice recording is not supported in this browser. Text Capture remains available.", true, "error");
    }
})();
