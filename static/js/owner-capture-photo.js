(() => {
    "use strict";

    const panel = document.querySelector("[data-capture-panel='photo']");
    if (!panel) return;

    const modeButtons = Array.from(document.querySelectorAll("[data-capture-mode]"));
    const photoButton = modeButtons.find((button) => button.dataset.captureMode === "photo");
    const views = Array.from(panel.querySelectorAll("[data-photo-view]"));
    const inputs = Array.from(panel.querySelectorAll("[data-photo-input]"));
    const localPreview = panel.querySelector("[data-photo-local-preview]");
    const serverPreviews = Array.from(panel.querySelectorAll("[data-photo-server-preview], [data-photo-confirmed-preview]"));
    const downloadLinks = Array.from(panel.querySelectorAll("[data-photo-download]"));
    const progress = panel.querySelector("[data-photo-progress]");
    const progressLabel = panel.querySelector("[data-photo-progress-label]");
    const statusHeading = panel.querySelector("[data-photo-status-heading]");
    const statusKicker = panel.querySelector("[data-photo-status-kicker]");
    const statusCopy = panel.querySelector("[data-photo-status-copy]");
    const statusLine = panel.querySelector("[data-photo-status]");
    const globalStatus = panel.querySelector("[data-photo-global-status]");
    const confirmForm = panel.querySelector("[data-photo-confirm-form]");
    const note = panel.querySelector("[data-photo-note]");

    const uploadUrl = panel.dataset.uploadUrl;
    const captureUrl = panel.dataset.captureUrl;
    const maxBytes = Number(panel.dataset.maxBytes || 10 * 1024 * 1024);
    const allowedTypes = new Set(["image/jpeg", "image/png"]);
    const maxPolls = 60;

    let selectedFile = null;
    let localObjectUrl = "";
    let activeUpload = null;
    let pollTimer = null;
    let pollCount = 0;
    let sourceKey = panel.dataset.sourceKey || "";
    let sourceState = panel.dataset.sourceState || "entry";
    let rowVersion = panel.dataset.rowVersion || "";
    let statusUrl = panel.dataset.statusUrl || "";
    let previewUrl = panel.dataset.previewUrl || "";
    let downloadUrl = panel.dataset.downloadUrl || "";

    const ERROR_COPY = {
        required: "Choose one JPEG or PNG photo before continuing.",
        unsupported: "That file could not be accepted as a complete JPEG or PNG. Choose another photo.",
        "too-large": "That photo is larger than 10 MB. Choose a smaller JPEG or PNG.",
        "draft-limit": "You have reached the private photo draft limit. Delete an unfinished draft before adding another.",
        "upload-failed": "The private upload did not finish. You can retry with the same local selection.",
        "upload-recovery": "The upload result could not be confirmed. The server may hold a private draft; check its status before trying again.",
        "scan-unavailable": "The security result is temporarily unavailable. The original remains private and no preview or Capture was created.",
        scan_unavailable: "The security result is temporarily unavailable. The original remains private and no preview or Capture was created.",
        scan_error: "The security service did not return an accepted result. No preview or Capture was created.",
        not_scanned: "The photo did not receive a successful security result. No preview or Capture was created.",
        malicious: "The security check did not pass. PeerSlate did not create a preview or Capture.",
        changed: "This private photo draft changed in another request. Refresh its status before continuing.",
        dimensions: "The photo dimensions are outside the supported limits. Delete this draft and choose another photo.",
        "invalid-image": "The image could not be safely decoded. Delete this draft and choose another photo.",
        "integrity-failed": "PeerSlate could not verify the uploaded bytes. No preview or Capture was created.",
        "processing-failed": "A safe preview could not be prepared. The original remains private until you delete the draft.",
        "processing-unavailable": "Photo processing is temporarily unavailable. The original remains private until you delete the draft.",
        processing_failed: "A safe preview could not be prepared. The original remains private until you delete the draft.",
        unavailable: "Private Photo Capture is temporarily unavailable. Nothing was reported as saved or deleted.",
        "too-long": "Keep the private Capture note to the displayed character limit.",
        "confirm-delete": "Confirm permanent deletion before deleting this private photo draft.",
        "delete-retry": "The private photo could not be deleted yet. Nothing was reported as deleted; try again.",
    };

    const STATE_COPY = {
        initial: {
            kicker: "Private photo draft",
            heading: "Preparing your private upload",
            copy: "PeerSlate is establishing the private draft. It is not a Capture and nothing is shared or published.",
            line: "Preparing the private draft.",
        },
        uploading: {
            kicker: "Private photo draft",
            heading: "Finishing your private upload",
            copy: "The original is being placed in private storage. It cannot be previewed or saved as a Capture yet.",
            line: "Waiting for the private upload to finish.",
        },
        scanning: {
            kicker: "Private photo draft",
            heading: "Scanning your private photo",
            copy: "Microsoft Defender is checking the private original. PeerSlate will not preview or save it as a Capture unless the scan succeeds.",
            line: "Scanning\u2026 Nothing is shared or published.",
        },
        processing: {
            kicker: "Security check passed",
            heading: "Preparing a safe preview",
            copy: "PeerSlate is creating a separate review image with embedded metadata removed. The original remains private.",
            line: "Preparing a safe preview.",
        },
        failed: {
            kicker: "Private draft needs attention",
            heading: "The photo is not ready for review",
            copy: "The original remains private. No preview or Capture was created.",
            line: "Review the options below.",
        },
        rejected: {
            kicker: "Security check did not pass",
            heading: "This photo cannot be opened or saved",
            copy: "PeerSlate did not create a preview. Delete the private draft, then choose a different photo if you want to continue.",
            line: "No preview or Capture was created.",
        },
    };

    let overlayRoot = document.getElementById("photo-overlay-root");
    if (!overlayRoot) {
        overlayRoot = document.createElement("div");
        overlayRoot.id = "photo-overlay-root";
        document.body.appendChild(overlayRoot);
    }

    let portalPosition = null;
    let backdrop = null;
    let backgroundState = [];
    let keydownHandler = null;

    const isVisible = (element) => {
        if (typeof element.checkVisibility === "function") {
            return element.checkVisibility({ checkVisibilityCSS: true, contentVisibilityAuto: true });
        }
        return element.offsetParent !== null;
    };

    const focusableItems = () => Array.from(panel.querySelectorAll(
        "button, [href], input, textarea, select, summary, [tabindex]:not([tabindex='-1'])"
    )).filter((element) => !element.disabled && element.tabIndex !== -1 && isVisible(element));

    const trapFocus = (event) => {
        if (event.key !== "Tab") return;
        const items = focusableItems();
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

    const setBackgroundInert = (on) => {
        if (on) {
            if (backgroundState.length) return;
            backgroundState = Array.from(document.body.children)
                .filter((element) => element !== overlayRoot && element.tagName !== "SCRIPT" && element.tagName !== "TEMPLATE")
                .map((element) => ({
                    element,
                    hadInert: element.hasAttribute("inert"),
                    ariaHidden: element.getAttribute("aria-hidden"),
                }));
            backgroundState.forEach(({ element }) => {
                element.setAttribute("inert", "");
                element.setAttribute("aria-hidden", "true");
            });
            return;
        }
        backgroundState.forEach(({ element, hadInert, ariaHidden }) => {
            if (!hadInert) element.removeAttribute("inert");
            if (ariaHidden === null) element.removeAttribute("aria-hidden");
            else element.setAttribute("aria-hidden", ariaHidden);
        });
        backgroundState = [];
    };

    const openPhoto = () => {
        if (portalPosition) return;
        portalPosition = {
            parent: panel.parentNode,
            next: panel.nextSibling,
            invoker: document.activeElement,
        };
        backdrop = document.createElement("div");
        backdrop.className = "owner-app__photo-backdrop";
        backdrop.appendChild(panel);
        overlayRoot.appendChild(backdrop);
        panel.hidden = false;
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-modal", "true");
        document.body.style.overflow = "hidden";
        setBackgroundInert(true);
        keydownHandler = (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                switchTo("text");
                return;
            }
            trapFocus(event);
        };
        panel.addEventListener("keydown", keydownHandler);
        window.requestAnimationFrame(() => {
            const heading = panel.querySelector("[data-photo-view]:not([hidden]) h3") || panel.querySelector("#photo-capture-title");
            heading?.focus({ preventScroll: true });
        });
    };

    const closePhoto = () => {
        if (!portalPosition) return;
        if (keydownHandler) panel.removeEventListener("keydown", keydownHandler);
        panel.removeAttribute("role");
        panel.removeAttribute("aria-modal");
        const { parent, next, invoker } = portalPosition;
        if (next && next.parentNode === parent) parent.insertBefore(panel, next);
        else parent.appendChild(panel);
        backdrop?.remove();
        backdrop = null;
        portalPosition = null;
        keydownHandler = null;
        document.body.style.overflow = "";
        setBackgroundInert(false);
        panel.hidden = sourceKey ? false : true;
        const target = photoButton || (document.contains(invoker) ? invoker : null);
        target?.focus();
    };

    const announce = (message, isError = false) => {
        globalStatus.textContent = message;
        globalStatus.classList.toggle("is-error", isError);
    };

    const focusViewHeading = (view) => {
        if (!portalPosition) return;
        window.requestAnimationFrame(() => view.querySelector("h3")?.focus({ preventScroll: true }));
    };

    const showView = (name, focus = true) => {
        let active = null;
        views.forEach((view) => {
            const selected = view.dataset.photoView === name;
            view.hidden = !selected;
            if (selected) active = view;
        });
        panel.dataset.photoState = name;
        if (focus && active) focusViewHeading(active);
        return active;
    };

    const clearPoll = () => {
        if (pollTimer) window.clearTimeout(pollTimer);
        pollTimer = null;
    };

    const clearLocal = () => {
        selectedFile = null;
        inputs.forEach((input) => { input.value = ""; });
        if (localObjectUrl) URL.revokeObjectURL(localObjectUrl);
        localObjectUrl = "";
        localPreview.removeAttribute("src");
    };

    const setMediaLinks = () => {
        serverPreviews.forEach((image) => {
            if (previewUrl) image.setAttribute("src", previewUrl);
            else image.removeAttribute("src");
        });
        downloadLinks.forEach((link) => {
            if (downloadUrl) link.setAttribute("href", downloadUrl);
            else link.removeAttribute("href");
        });
    };

    const endpoint = (action) => statusUrl ? `${statusUrl}/${action}` : "";

    const updateSource = (payload) => {
        if (payload.source_key) sourceKey = String(payload.source_key);
        if (payload.state) sourceState = String(payload.state);
        if (payload.row_version) rowVersion = String(payload.row_version);
        if (payload.status_url) statusUrl = String(payload.status_url);
        previewUrl = payload.preview_url ? String(payload.preview_url) : "";
        downloadUrl = payload.original_download_url ? String(payload.original_download_url) : "";
        panel.dataset.sourceKey = sourceKey;
        panel.dataset.sourceState = sourceState;
        panel.dataset.rowVersion = rowVersion;
        panel.dataset.statusUrl = statusUrl;
        setMediaLinks();
    };

    const renderStatus = (state, errorCode = "", focus = true) => {
        clearPoll();
        sourceState = state || sourceState || "failed";
        panel.dataset.sourceState = sourceState;
        if (sourceState === "needs_review") {
            showView("review", focus);
            announce("Safe preview ready. Review it, add the required private note, and choose whether to save.");
            return;
        }
        if (sourceState === "confirmed") {
            showView("confirmed", focus);
            announce("Private Capture saved. Nothing was shared or published.");
            return;
        }

        const copy = STATE_COPY[sourceState] || STATE_COPY.failed;
        const activeView = showView("status", focus);
        statusKicker.textContent = copy.kicker;
        statusHeading.textContent = copy.heading;
        statusCopy.textContent = errorCode && ERROR_COPY[errorCode] ? ERROR_COPY[errorCode] : copy.copy;
        statusLine.textContent = copy.line;
        const isError = ["failed", "rejected"].includes(sourceState) || Boolean(errorCode);
        activeView?.classList.toggle("is-error", isError);
        statusLine.classList.toggle("is-error", isError);
        announce(statusLine.textContent, isError);

        if (["initial", "uploading", "scanning", "processing"].includes(sourceState)) {
            schedulePoll();
        }
    };

    const readJson = async (response) => {
        try {
            return await response.json();
        } catch (_error) {
            return {};
        }
    };

    const postForm = async (url, form) => {
        const response = await fetch(url, {
            method: "POST",
            body: form,
            credentials: "same-origin",
            headers: { "X-Requested-With": "fetch" },
        });
        const payload = await readJson(response);
        if (!response.ok) {
            const error = new Error(payload.error || "unavailable");
            error.code = payload.error || "unavailable";
            error.payload = payload;
            throw error;
        }
        return payload;
    };

    const getCurrentStatus = async () => {
        if (!statusUrl) throw Object.assign(new Error("unavailable"), { code: "unavailable" });
        const response = await fetch(statusUrl, {
            credentials: "same-origin",
            headers: { "X-Requested-With": "fetch" },
            cache: "no-store",
        });
        const payload = await readJson(response);
        if (!response.ok) throw Object.assign(new Error(payload.error || "unavailable"), { code: payload.error || "unavailable" });
        updateSource(payload);
        return payload;
    };

    const reconcile = async (manual = false) => {
        clearPoll();
        if (!sourceKey || !rowVersion || !statusUrl) return;
        if (manual) announce("Checking the private photo status.");
        const form = new FormData();
        form.append("expected_row_version", rowVersion);
        try {
            const payload = await postForm(endpoint("reconcile"), form);
            updateSource(payload);
            renderStatus(payload.state);
        } catch (error) {
            if (error.code === "changed") {
                try {
                    const payload = await getCurrentStatus();
                    renderStatus(payload.state);
                    return;
                } catch (_refreshError) {
                    // Fall through to the stable, owner-safe changed message.
                }
            }
            const failedState = ["unsupported", "dimensions", "invalid-image", "integrity-failed"].includes(error.code)
                ? "failed"
                : sourceState;
            renderStatus(failedState, error.code);
        }
    };

    function schedulePoll() {
        clearPoll();
        if (pollCount >= maxPolls) {
            statusLine.textContent = "The security check is taking longer than expected. Use Check status when you are ready.";
            announce(statusLine.textContent);
            return;
        }
        pollCount += 1;
        pollTimer = window.setTimeout(() => reconcile(false), 2500);
    }

    const handleSelection = (file) => {
        if (!file) return;
        if (!allowedTypes.has(file.type)) {
            announce(ERROR_COPY.unsupported, true);
            inputs.forEach((input) => { input.value = ""; });
            return;
        }
        if (file.size > maxBytes) {
            announce(ERROR_COPY["too-large"], true);
            inputs.forEach((input) => { input.value = ""; });
            return;
        }
        clearLocal();
        selectedFile = file;
        localObjectUrl = URL.createObjectURL(file);
        localPreview.src = localObjectUrl;
        showView("local");
        announce("Photo selected locally. It has not been uploaded or saved.");
    };

    const uploadSelection = () => {
        if (!selectedFile || activeUpload) {
            if (!selectedFile) announce(ERROR_COPY.required, true);
            return;
        }
        showView("uploading");
        progress.value = 0;
        progress.textContent = "0%";
        progressLabel.textContent = "Preparing upload\u2026";
        announce("Uploading the private photo. It is not a Capture yet.");

        const form = new FormData();
        form.append("photo", selectedFile);
        const request = new XMLHttpRequest();
        activeUpload = request;
        request.open("POST", uploadUrl);
        request.setRequestHeader("X-Requested-With", "fetch");
        request.upload.addEventListener("progress", (event) => {
            if (!event.lengthComputable) return;
            const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
            progress.value = percent;
            progress.textContent = `${percent}%`;
            progressLabel.textContent = `${percent}% uploaded`;
        });
        request.addEventListener("load", () => {
            activeUpload = null;
            let payload = {};
            try { payload = JSON.parse(request.responseText || "{}"); } catch (_error) { payload = {}; }
            if (payload.source_key) {
                updateSource(payload);
                clearLocal();
            }
            if (request.status < 200 || request.status >= 300) {
                const code = payload.error || "upload-failed";
                if (sourceKey) {
                    renderStatus("failed", code);
                    getCurrentStatus()
                        .then((current) => renderStatus(current.state, code))
                        .catch(() => announce(ERROR_COPY[code] || ERROR_COPY["upload-failed"], true));
                } else {
                    showView("local");
                    announce(ERROR_COPY[code] || ERROR_COPY["upload-failed"], true);
                }
                return;
            }
            pollCount = 0;
            renderStatus(payload.state || "scanning");
        });
        request.addEventListener("error", () => {
            activeUpload = null;
            showView("local");
            announce(ERROR_COPY["upload-failed"], true);
        });
        request.addEventListener("abort", () => {
            activeUpload = null;
            showView("local");
            announce("Upload cancelled in this browser. PeerSlate is not claiming that a server draft was deleted.");
        });
        request.send(form);
    };

    const confirmCapture = async (event) => {
        event.preventDefault();
        if (!confirmForm.reportValidity() || !sourceKey || !rowVersion) return;
        const submit = confirmForm.querySelector("[type='submit']");
        submit.disabled = true;
        announce("Saving one private Capture. Nothing is being shared or published.");
        const form = new FormData();
        form.append("approved_body", note.value.trim());
        form.append("confirm_photo", "save-private-capture");
        form.append("expected_row_version", rowVersion);
        try {
            await postForm(endpoint("confirm"), form);
            const target = new URL(captureUrl, window.location.href);
            target.searchParams.set("photo", sourceKey);
            target.searchParams.set("changed", "photo-saved");
            window.location.assign(target.toString());
        } catch (error) {
            submit.disabled = false;
            if (error.code === "changed") {
                await reconcile(true);
                return;
            }
            announce(ERROR_COPY[error.code] || ERROR_COPY.unavailable, true);
        }
    };

    const deleteDraft = async (button) => {
        const view = button.closest("[data-photo-view]");
        const confirmation = view?.querySelector("[data-photo-delete-confirm]");
        if (!confirmation?.checked) {
            confirmation?.focus();
            announce(ERROR_COPY["confirm-delete"], true);
            return;
        }
        if (!sourceKey || !rowVersion) return;
        button.disabled = true;
        announce("Deleting the private original and any safe preview.");
        const form = new FormData();
        form.append("confirm_delete", "delete");
        form.append("expected_row_version", rowVersion);
        try {
            await postForm(endpoint("delete"), form);
            const target = new URL(captureUrl, window.location.href);
            target.searchParams.set("changed", "photo-deleted");
            window.location.assign(target.toString());
        } catch (error) {
            button.disabled = false;
            if (error.code === "changed") {
                await reconcile(true);
                return;
            }
            announce(ERROR_COPY[error.code] || ERROR_COPY.unavailable, true);
        }
    };

    const switchTo = (mode) => {
        closePhoto();
        const target = modeButtons.find((button) => button.dataset.captureMode === mode);
        target?.click();
    };

    modeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            if (button.dataset.captureMode === "photo") {
                modeButtons.forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
                openPhoto();
            } else if (portalPosition) {
                closePhoto();
            }
        });
    });

    inputs.forEach((input) => input.addEventListener("change", () => handleSelection(input.files?.[0])));
    panel.querySelectorAll("[data-photo-action]").forEach((button) => {
        button.addEventListener("click", () => {
            const action = button.dataset.photoAction;
            if (action === "close") switchTo("text");
            else if (action === "upload") uploadSelection();
            else if (action === "replace") inputs[0]?.click();
            else if (action === "clear-local") {
                clearLocal();
                showView("entry");
                announce("Local selection cleared. Nothing was uploaded.");
            } else if (action === "cancel-upload") activeUpload?.abort();
            else if (action === "check-status") {
                pollCount = 0;
                reconcile(true);
            } else if (action === "use-text") switchTo("text");
            else if (action === "use-voice") switchTo("voice");
            else if (action === "delete-draft") deleteDraft(button);
        });
    });
    confirmForm?.addEventListener("submit", confirmCapture);
    note?.addEventListener("input", () => {
        const description = note.value.trim();
        const alt = description ? description.slice(0, 240) : "Private photo awaiting your description";
        panel.querySelector("[data-photo-server-preview]")?.setAttribute("alt", alt);
    });

    window.addEventListener("beforeunload", () => {
        clearPoll();
        if (localObjectUrl) URL.revokeObjectURL(localObjectUrl);
    });

    if (sourceKey) {
        modeButtons.forEach((button) => button.setAttribute("aria-pressed", String(button === photoButton)));
        setMediaLinks();
        renderStatus(sourceState, panel.dataset.safeErrorCode || "", false);
        openPhoto();
    } else {
        showView("entry", false);
    }
})();
