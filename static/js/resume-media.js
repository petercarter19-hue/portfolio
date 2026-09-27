/* MVP1 D: scoped private Resume media chooser.

   The chooser keeps My photos, the curated PeerSlate library, per-slot
   assignments, the member caption, the placement preview and the explicit Add
   together. Selecting, previewing, swapping and cropping are owner-scoped
   pending state on the server; only "Add photos to résumé" writes the reviewed
   placements to the private draft. Nothing here publishes, and nothing here
   invents a caption, alt text or story sentence. */
(function () {
    "use strict";

    const root = document.getElementById("resume-media");
    if (!root) {
        return;
    }

    const SLOTS = ["story_banner", "experience_support"];
    const SLOT_ASPECT = { story_banner: 3.0, experience_support: 1.5 };
    const SLOT_LABEL = { story_banner: "My Story banner", experience_support: "Experience photo" };
    const PLACEMENT_PREVIEW_LABEL = "Placement preview \u00b7 Not added yet";
    const SAVED_LABEL = "Saved in your private draft";

    const urls = {
        workspace: root.getAttribute("data-media-workspace-url"),
        upload: root.getAttribute("data-media-upload-url"),
        refreshTemplate: root.getAttribute("data-media-refresh-url-template"),
        photoTemplate: root.getAttribute("data-media-photo-url-template"),
        library: root.getAttribute("data-media-library-url"),
        libraryThumbnailTemplate: root.getAttribute("data-media-library-thumbnail-url-template"),
        placement: root.getAttribute("data-media-placement-url"),
        placementPreviewTemplate: root.getAttribute("data-media-placement-preview-url-template"),
        placementMediaTemplate: root.getAttribute("data-media-placement-media-url-template"),
        draftMediaTemplate: root.getAttribute("data-media-draft-media-url-template"),
        swap: root.getAttribute("data-media-placement-swap-url"),
        commands: root.getAttribute("data-media-commands-url"),
    };

    const elements = {
        header: root.querySelector(".resume-media__header"),
        guide: document.getElementById("resume-media-guide"),
        previewPanel: document.getElementById("resume-media-preview"),
        status: document.getElementById("resume-media-status"),
        tabPhotos: document.getElementById("resume-media-tab-photos"),
        tabLibrary: document.getElementById("resume-media-tab-library"),
        panelPhotos: document.getElementById("resume-media-panel-photos"),
        panelLibrary: document.getElementById("resume-media-panel-library"),
        photos: document.getElementById("resume-media-photos"),
        photosEmpty: document.getElementById("resume-media-photos-empty"),
        upload: document.getElementById("resume-media-upload"),
        librarySearch: document.getElementById("resume-media-library-search"),
        libraryResults: document.getElementById("resume-media-library-results"),
        libraryEmpty: document.getElementById("resume-media-library-empty"),
        libraryError: document.getElementById("resume-media-library-error"),
        libraryMore: document.getElementById("resume-media-library-more"),
        caption: document.getElementById("resume-media-caption"),
        selectedCount: document.getElementById("resume-media-selected-count"),
        previewCount: document.getElementById("resume-media-preview-count"),
        previewProvenance: document.getElementById("resume-media-preview-provenance"),
        hide: document.getElementById("resume-media-hide"),
        previewHide: document.getElementById("resume-media-preview-hide"),
        reopen: document.getElementById("resume-media-reopen"),
        previewPlacement: document.getElementById("resume-media-preview-placement"),
        previewBack: document.getElementById("resume-media-preview-back"),
        changePhotos: document.getElementById("resume-media-change-photos"),
        keepWords: document.getElementById("resume-media-keep-words"),
        add: document.getElementById("resume-media-add"),
        swap: document.getElementById("resume-media-swap"),
        retryRow: document.getElementById("resume-media-retry-row"),
        retry: document.getElementById("resume-media-retry"),
    };

    let workspace = null;
    let staged = {};
    let saved = {};
    let libraryCursor = null;
    let renderEpoch = 0;
    let workspaceEpoch = 0;
    let libraryEpoch = 0;
    let libraryInFlight = null;
    // One unresolved private command: the exact UUID and canonical payload are
    // retained until the server authoritatively resolves it, so a retry after a
    // lost response reuses the same request instead of issuing a new one.
    let pendingCommand = null;
    // Bumped by every local intent change (stage, crop, swap, clear, command).
    // A workspace refresh that started before a newer local change is
    // discarded, so an older snapshot can never overwrite newer intent.
    let intentVersion = 0;

    function setStatus(message, kind) {
        elements.status.textContent = message || "";
        elements.status.setAttribute("data-kind", kind || "ok");
    }

    // The caption is an explicit member input. Its current value — including
    // deliberately empty — is what binds to a placement at review and Add, so
    // clearing it clears it instead of silently reviving an older caption.
    function currentCaption() {
        const value = elements.caption ? elements.caption.value.trim() : "";
        return value ? value : null;
    }

    function setPendingCommand(command) {
        pendingCommand = command;
        updateCommandGate();
        if (!elements.retryRow || !elements.retry) {
            return;
        }
        if (command) {
            elements.retry.textContent = command.retryLabel;
            elements.retryRow.hidden = false;
        } else {
            elements.retryRow.hidden = true;
            elements.retry.textContent = "";
        }
    }

    // While one private command's outcome is unknown, every other committing
    // action is refused: only the exact retry may dispatch, so a second
    // request can never be issued over an unresolved one.
    function updateCommandGate() {
        const blocked = !!pendingCommand;
        [elements.add, elements.keepWords].forEach(function (button) {
            if (!button) {
                return;
            }
            button.disabled = blocked;
            button.setAttribute("aria-disabled", blocked ? "true" : "false");
        });
        SLOTS.forEach(function (slot) {
            const remove = document.getElementById("resume-media-slot-" + slot + "-remove");
            if (remove) {
                remove.disabled = blocked;
            }
        });
    }

    function refuseWhilePending(actionLabel, allowedKind) {
        if (!pendingCommand) {
            return false;
        }
        if (allowedKind && pendingCommand.kind === allowedKind) {
            // The exact retry of the unresolved command is always allowed.
            return false;
        }
        setStatus(
            "An earlier change (" + pendingCommand.retryLabel + ") is still unresolved. " +
                "Resolve it with Retry before " + actionLabel + ".",
            "pending"
        );
        return true;
    }

    function requestId() {
        if (window.crypto && window.crypto.randomUUID) {
            return window.crypto.randomUUID();
        }
        return "00000000-0000-4000-8000-000000000000".replace(/0/g, function () {
            return Math.floor(Math.random() * 10);
        });
    }

    async function sendJson(url, body, method) {
        const response = await fetch(url, {
            method: method || "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-PeerSlate-Request": "same-origin",
            },
            body: body === undefined ? undefined : JSON.stringify(body),
        });
        const payload = await response.json().catch(function () {
            return {};
        });
        return { response: response, payload: payload };
    }

    function failedMessage(payload, fallback) {
        return (payload && payload.message) || fallback;
    }

    // The slot's shape is a server contract; the browser only pre-composes a
    // centred crop so the preview matches, and the server revalidates it.
    function defaultCrop(width, height, aspect) {
        const safeWidth = Number(width) > 0 ? Number(width) : 1;
        const safeHeight = Number(height) > 0 ? Number(height) : 1;
        const sourceAspect = safeWidth / safeHeight;
        let cropWidth = 1;
        let cropHeight = 1;
        if (sourceAspect >= aspect) {
            cropWidth = Math.min((aspect * safeHeight) / safeWidth, 1);
        } else {
            cropHeight = Math.min(safeWidth / (aspect * safeHeight), 1);
        }
        return {
            x: Number(((1 - cropWidth) / 2).toFixed(6)),
            y: Number(((1 - cropHeight) / 2).toFixed(6)),
            width: Number(cropWidth.toFixed(6)),
            height: Number(cropHeight.toFixed(6)),
        };
    }

    function mediaUrl(template, replacements) {
        let value = template || "";
        Object.keys(replacements || {}).forEach(function (key) {
            value = value.split(key).join(encodeURIComponent(String(replacements[key])));
        });
        return value + "?v=" + String(++renderEpoch);
    }

    // One crop calculation for preview and stored placement: the normalized
    // rectangle is mapped onto the slot-shaped frame, so the member reviews
    // exactly the region that was validated and saved.
    function applyCropGeometry(image, crop) {
        if (!image) {
            return;
        }
        const rect = crop || {};
        const width = Number(rect.width);
        const height = Number(rect.height);
        if (!(width > 0) || !(height > 0)) {
            image.style.width = "";
            image.style.height = "";
            image.style.left = "";
            image.style.top = "";
            return;
        }
        const x = Number(rect.x) || 0;
        const y = Number(rect.y) || 0;
        image.style.width = (100 / width).toFixed(4) + "%";
        image.style.height = (100 / height).toFixed(4) + "%";
        image.style.left = ((-100 * x) / width).toFixed(4) + "%";
        image.style.top = ((-100 * y) / height).toFixed(4) + "%";
    }

    function placementMediaUrl(slot) {
        // A pending choice reads the staged preview; a placement already saved
        // to the private draft reads the persisted draft placement, so the
        // image still resolves after Add and after a reload.
        const template = staged[slot]
            ? urls.placementMediaTemplate
            : (urls.draftMediaTemplate || urls.placementMediaTemplate);
        return mediaUrl(template, { __SLOT__: slot });
    }

    function photoPreviewUrl(sourceId) {
        return mediaUrl(urls.photoTemplate, { __SOURCE__: sourceId });
    }

    function libraryThumbnailUrl(assetId, assetVersion) {
        let value = urls.libraryThumbnailTemplate || "";
        value = value.split("__ASSET__").join(encodeURIComponent(String(assetId)));
        value = value.replace(/\/0\/thumbnail/, "/" + String(assetVersion) + "/thumbnail");
        return value + "?v=" + String(++renderEpoch);
    }

    function selectedEntry(slot) {
        return staged[slot] || saved[slot] || null;
    }

    // A small selected-state marker mirrors the approved chooser, where a
    // chosen thumbnail carries a checkmark instead of only a text row.
    function markSelections() {
        const chosen = {};
        SLOTS.forEach(function (slot) {
            const entry = selectedEntry(slot);
            if (entry) {
                chosen[String(entry.asset_id)] = SLOT_LABEL[slot];
            }
        });
        Array.prototype.forEach.call(
            document.querySelectorAll("[data-source-id], [data-asset-id]"),
            function (card) {
                if (card.tagName !== "LI") {
                    return;
                }
                const key = String(card.getAttribute("data-source-id") || card.getAttribute("data-asset-id") || "");
                const slotLabel = chosen[key];
                if (slotLabel) {
                    card.setAttribute("data-selected", "true");
                    card.setAttribute("aria-label", "Selected for " + slotLabel);
                } else {
                    card.removeAttribute("data-selected");
                    card.removeAttribute("aria-label");
                }
            }
        );
    }

    function entryLabel(entry) {
        if (!entry) {
            return null;
        }
        if (entry.source_kind === "generated_illustration") {
            return entry.asset_label || entry.label || ("Library illustration " + String(entry.asset_id));
        }
        return "Your photo";
    }

    function updateCounts() {
        const pending = SLOTS.filter(function (slot) { return !!staged[slot]; }).length;
        const savedCount = SLOTS.filter(function (slot) { return !!saved[slot]; }).length;
        const count = pending || savedCount;
        const suffix = pending ? "Not added yet" : (savedCount ? SAVED_LABEL : "Not added yet");
        elements.selectedCount.textContent = count + " selected \u00b7 " + suffix;
        elements.previewCount.textContent = count + " photos \u00b7 " + suffix;
        const kinds = SLOTS.map(function (slot) { return selectedEntry(slot); })
            .filter(Boolean)
            .map(function (entry) { return entry.source_kind; });
        if (kinds.indexOf("generated_illustration") !== -1) {
            elements.previewProvenance.textContent =
                "PeerSlate library \u00b7 AI generated illustrations.";
        } else if (kinds.length) {
            elements.previewProvenance.textContent =
                "Your own private photo \u00b7 Member photo.";
        } else {
            elements.previewProvenance.textContent =
                "PeerSlate library \u00b7 AI generated illustrations.";
        }
    }

    function renderAssignments() {
        SLOTS.forEach(function (slot) {
            const value = document.getElementById("resume-media-slot-" + slot + "-value");
            const remove = document.getElementById("resume-media-slot-" + slot + "-remove");
            const entry = selectedEntry(slot);
            if (staged[slot]) {
                value.textContent = SLOT_LABEL[slot] + ": " + (entryLabel(entry) || "Selected");
            } else if (saved[slot]) {
                value.textContent = SLOT_LABEL[slot] + ": " + (entryLabel(entry) || "Saved") + " (saved privately)";
            } else {
                value.textContent = "Nothing selected yet.";
            }
            remove.hidden = !entry;
        });
        updateCounts();
        markSelections();
    }

    function renderPlacement() {
        SLOTS.forEach(function (slot) {
            const image = document.getElementById("resume-media-placement-image-" + slot);
            const badge = document.getElementById("resume-media-placement-badge-" + slot);
            const attribution = document.getElementById("resume-media-placement-attribution-" + slot);
            const empty = document.getElementById("resume-media-placement-empty-" + slot);
            const entry = selectedEntry(slot);
            if (!entry) {
                image.hidden = true;
                image.removeAttribute("src");
                badge.hidden = true;
                attribution.hidden = true;
                empty.hidden = false;
                return;
            }
            image.src = placementMediaUrl(slot);
            applyCropGeometry(image, entry.crop);
            image.hidden = false;
            empty.hidden = true;
            badge.hidden = false;
            badge.textContent = staged[slot] ? PLACEMENT_PREVIEW_LABEL : SAVED_LABEL;
            attribution.hidden = false;
            attribution.textContent = entry.source_kind === "generated_illustration"
                ? "Library illustration \u00b7 " + (entry.provenance_label || "Generated illustration")
                : "Member photo";
        });
    }

    function renderPreviewPanel() {
        SLOTS.forEach(function (slot) {
            const entry = selectedEntry(slot);
            const image = document.getElementById("resume-media-preview-image-" + slot);
            const label = document.getElementById("resume-media-preview-label-" + slot);
            const cropFields = document.getElementById("resume-media-crop-fields-" + slot);
            if (!entry) {
                image.hidden = true;
                image.removeAttribute("src");
                label.textContent = "Nothing selected for this slot.";
                return;
            }
            image.src = placementMediaUrl(slot);
            applyCropGeometry(image, entry.crop);
            image.hidden = false;
            label.textContent = (entryLabel(entry) || "Selected") +
                (staged[slot] ? "" : " (saved privately)");
            if (cropFields && !cropFields.hidden) {
                fillCropInputs(slot, entry.crop || {});
            }
        });
        updateCounts();
    }

    function photoCard(photo) {
        const card = document.createElement("li");
        card.className = "resume-media__card";
        card.setAttribute("data-source-id", photo.source_id);
        if (photo.preview_available) {
            const image = document.createElement("img");
            image.className = "resume-media__thumb";
            image.src = photoPreviewUrl(photo.source_id);
            image.alt = "";
            card.appendChild(image);
        } else {
            const placeholder = document.createElement("span");
            placeholder.className = "resume-media__thumb resume-media__thumb--empty";
            placeholder.setAttribute("aria-hidden", "true");
            placeholder.textContent = photo.state === "ready" ? "\u2713" : "\u2026";
            card.appendChild(placeholder);
        }
        const state = document.createElement("p");
        state.className = "resume-media__card-state";
        state.setAttribute("data-state", photo.state);
        state.textContent = photoLabel(photo);
        card.appendChild(state);
        if (photo.selectable) {
            SLOTS.forEach(function (slot) {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "resume-media__quiet";
                button.setAttribute("data-action", "select");
                button.setAttribute("data-slot", slot);
                button.setAttribute("data-source-id", photo.source_id);
                button.textContent = "Use for " + SLOT_LABEL[slot];
                button.addEventListener("click", function () {
                    choosePhoto(photo, slot, button);
                });
                card.appendChild(button);
            });
        } else if (photo.retryable) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "resume-media__quiet";
            button.setAttribute("data-action", "refresh");
            button.setAttribute("data-source-id", photo.source_id);
            button.textContent = "Check scan";
            button.addEventListener("click", function () {
                refreshPhoto(photo.source_id, button);
            });
            card.appendChild(button);
        }
        return card;
    }

    function photoLabel(photo) {
        const state = photo.state;
        if (state === "uploading") { return "Uploading privately."; }
        if (state === "scanning") { return "Scanning before it can be used."; }
        if (state === "processing") { return "Processing privately."; }
        if (state === "ready") { return "Ready to use."; }
        if (state === "failed") { return "Processing failed. You can try again."; }
        if (state === "rejected") { return "Rejected by the scan. This photo cannot be used."; }
        if (state === "quarantined") { return "Quarantined by the scan. This photo cannot be used."; }
        return "Private photo.";
    }

    function renderPhotos() {
        const photos = (workspace && workspace.photos) || [];
        elements.photos.replaceChildren();
        photos.forEach(function (photo) {
            elements.photos.appendChild(photoCard(photo));
        });
        elements.photosEmpty.hidden = photos.length !== 0;
    }

    function libraryCard(item) {
        const card = document.createElement("li");
        card.className = "resume-media__card";
        card.setAttribute("data-asset-id", item.asset_id);
        const image = document.createElement("img");
        image.className = "resume-media__thumb";
        image.alt = "";
        image.src = libraryThumbnailUrl(item.asset_id, item.asset_version);
        card.appendChild(image);
        const label = document.createElement("span");
        label.className = "resume-media__card-label";
        label.textContent = item.label;
        card.appendChild(label);
        SLOTS.forEach(function (slot) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "resume-media__quiet";
            button.setAttribute("data-action", "select-library");
            button.setAttribute("data-asset-id", item.asset_id);
            button.setAttribute("data-asset-version", String(item.asset_version));
            button.setAttribute("data-slot", slot);
            button.textContent = "Use for " + SLOT_LABEL[slot];
            button.addEventListener("click", function () {
                chooseLibraryItem(item, slot, button);
            });
            card.appendChild(button);
        });
        const meta = document.createElement("p");
        meta.className = "resume-media__card-state";
        meta.textContent = "AI generated illustration. Not your photo.";
        card.appendChild(meta);
        return card;
    }

    function renderLibraryPage(payload, append) {
        if (!append) {
            elements.libraryResults.replaceChildren();
        }
        const items = (payload && payload.items) || [];
        items.forEach(function (item) {
            elements.libraryResults.appendChild(libraryCard(item));
        });
        libraryCursor = payload ? payload.next_cursor : null;
        elements.libraryMore.hidden = !libraryCursor;
        if (!append) {
            elements.libraryEmpty.hidden = items.length !== 0;
        }
    }

    async function loadLibrary(append) {
        const params = new URLSearchParams();
        const query = elements.librarySearch.value.trim();
        if (query) {
            params.set("query", query);
        }
        if (append && libraryCursor) {
            params.set("cursor", libraryCursor);
        }
        // One intent per search: a slower earlier response may not repaint the
        // results for a newer query.
        const epoch = ++libraryEpoch;
        if (libraryInFlight) {
            libraryInFlight.abort();
        }
        libraryInFlight = window.AbortController ? new AbortController() : null;
        elements.libraryError.hidden = true;
        elements.libraryError.textContent = "";
        let result;
        try {
            const options = { credentials: "same-origin" };
            if (libraryInFlight) {
                options.signal = libraryInFlight.signal;
            }
            const response = await fetch(urls.library + "?" + params.toString(), options);
            const payload = await response.json().catch(function () { return {}; });
            result = { response: response, payload: payload };
        } catch (error) {
            if (epoch !== libraryEpoch) {
                return;
            }
            elements.libraryError.textContent =
                "The PeerSlate library could not be reached. Your own photos are unaffected.";
            elements.libraryError.hidden = false;
            return;
        }
        if (epoch !== libraryEpoch) {
            return;
        }
        libraryInFlight = null;
        if (!result.response.ok) {
            elements.libraryError.textContent = result.response.status === 503
                ? "The PeerSlate library is unavailable right now. Try again."
                : failedMessage(result.payload, "That library search could not run.");
            elements.libraryError.hidden = false;
            if (!append) {
                elements.libraryResults.replaceChildren();
                elements.libraryEmpty.hidden = true;
                elements.libraryMore.hidden = true;
            }
            return;
        }
        renderLibraryPage(result.payload, append);
    }

    function sourceRefForEntry(entry) {
        if (entry.source_kind === "generated_illustration") {
            return {
                kind: "generated_illustration",
                asset_id: entry.asset_id,
                asset_version: entry.asset_version,
            };
        }
        // Bind the exact source version the member reviewed, so a source that
        // was replaced while they worked conflicts instead of saving silently.
        return {
            kind: "owner_photo",
            source_id: entry.asset_id,
            expected_version: entry.asset_version,
        };
    }

    async function stageSource(slot, source, crop, options) {
        const altText = (options && options.altText) || "";
        const body = {
            slot: slot,
            source: source,
            crop: crop,
            alt_text: altText,
            decorative: !altText,
            caption: currentCaption(),
        };
        noteLocalIntent();
        const result = await sendJson(urls.placement, body);
        if (!result.response.ok) {
            setStatus(
                failedMessage(result.payload, "That photo could not be prepared for this slot."),
                "error"
            );
            return null;
        }
        staged[slot] = result.payload.preview;
        renderAssignments();
        renderPlacement();
        renderPreviewPanel();
        setStatus(
            SLOT_LABEL[slot] + " is a placement preview \u00b7 Not added yet.",
            "ok"
        );
        return result.payload.preview;
    }

    async function choosePhoto(photo, slot, button) {
        button.disabled = true;
        try {
            const crop = defaultCrop(photo.width, photo.height, SLOT_ASPECT[slot]);
            await stageSource(
                slot,
                { kind: "owner_photo", source_id: photo.source_id },
                crop
            );
        } finally {
            button.disabled = false;
        }
    }

    async function chooseLibraryItem(item, slot, button) {
        button.disabled = true;
        try {
            const crop = defaultCrop(item.width, item.height, SLOT_ASPECT[slot]);
            const preview = await stageSource(
                slot,
                {
                    kind: "generated_illustration",
                    asset_id: item.asset_id,
                    asset_version: item.asset_version,
                },
                crop
            );
            if (preview) {
                preview.asset_label = item.label;
                staged[slot] = preview;
                renderAssignments();
            }
        } finally {
            button.disabled = false;
        }
    }

    async function refreshPhoto(sourceId, button) {
        button.disabled = true;
        try {
            const result = await sendJson(
                urls.refreshTemplate.split("__SOURCE__").join(encodeURIComponent(sourceId)),
                {}
            );
            if (!result.response.ok) {
                setStatus(
                    failedMessage(result.payload, "That photo could not be checked again."),
                    "error"
                );
                return;
            }
            setStatus(
                result.payload.state === "ready"
                    ? "That photo is scanned and ready to use."
                    : "That photo is still " + String(result.payload.state) + ".",
                result.payload.state === "ready" ? "ok" : "pending"
            );
            await loadWorkspace();
        } finally {
            button.disabled = false;
        }
    }

    function fillCropInputs(slot, crop) {
        ["x", "y", "width", "height"].forEach(function (key) {
            const field = document.querySelector(
                "#resume-media-crop-" + slot + "-" + key
            );
            if (field && crop && crop[key] !== undefined) {
                field.value = String(crop[key]);
            }
        });
    }

    function readCropInputs(slot) {
        const values = {};
        ["x", "y", "width", "height"].forEach(function (key) {
            const field = document.querySelector(
                "#resume-media-crop-" + slot + "-" + key
            );
            values[key] = field ? Number(field.value) : NaN;
        });
        return values;
    }

    async function applyCrop(slot) {
        const entry = staged[slot];
        if (!entry) {
            setStatus("Choose a photo for this slot before adjusting its crop.", "error");
            return;
        }
        const crop = readCropInputs(slot);
        noteLocalIntent();
        const result = await sendJson(urls.placement, {
            slot: slot,
            source: sourceRefForEntry(entry),
            crop: crop,
            alt_text: entry.alt_text || "",
            decorative: !!entry.decorative,
            caption: currentCaption(),
        });
        if (!result.response.ok) {
            setStatus(
                failedMessage(result.payload, "That crop cannot be used for this placement."),
                "error"
            );
            return;
        }
        staged[slot] = result.payload.preview;
        fillCropInputs(slot, staged[slot].crop);
        renderAssignments();
        renderPlacement();
        renderPreviewPanel();
        setStatus("Crop updated. This is still a placement preview \u00b7 Not added yet.", "ok");
    }

    async function swapPlacements() {
        noteLocalIntent();
        const result = await sendJson(urls.swap, {});
        if (!result.response.ok) {
            setStatus(
                failedMessage(result.payload, "Both slots need a photo before swapping."),
                "error"
            );
            return;
        }
        staged = result.payload.slots || {};
        renderAssignments();
        renderPlacement();
        renderPreviewPanel();
        setStatus("Swapped. Each slot now has a crop shaped for that slot \u00b7 Not added yet.", "ok");
    }

    async function removeSlot(slot) {
        if (staged[slot]) {
            noteLocalIntent();
            const result = await sendJson(
                urls.placementPreviewTemplate.split("__SLOT__").join(slot),
                {},
                "DELETE"
            );
            if (!result.response.ok) {
                setStatus(
                    failedMessage(result.payload, "That pending choice could not be cleared."),
                    "error"
                );
                return;
            }
            delete staged[slot];
            renderAssignments();
            renderPlacement();
            renderPreviewPanel();
            setStatus(SLOT_LABEL[slot] + " pending choice cleared. Your other slot is unchanged.", "ok");
            return;
        }
        // Removal retries use retryPendingCommand with the retained command.
        // A fresh slot click must never replace an unresolved removal, even
        // though both operations share the remove_slot UI kind.
        if (refuseWhilePending("removing a saved photo")) {
            return;
        }
        // Removing one saved slot is one private draft command. The other slot,
        // the text draft and the publication are untouched.
        const payload = await runCommand({
            kind: "remove_slot",
            slot: slot,
            requestId: requestId(),
            payload: {
                type: "add_media",
                request_id: null,
                expected_draft_version: currentVersion(),
                choices: [{ slot: slot, source: null }],
            },
            retryLabel: "Retry remove " + SLOT_LABEL[slot],
            fallback: "That photo could not be removed from your r\u00e9sum\u00e9.",
            successMessage:
                SLOT_LABEL[slot] +
                " removed from your private r\u00e9sum\u00e9. The other slot is unchanged.",
        });
        if (!payload) {
            return;
        }
        setStatus(
            SLOT_LABEL[slot] +
                " removed from your private r\u00e9sum\u00e9. The other slot is unchanged.",
            "ok"
        );
        await loadWorkspace();
    }

    function currentVersion() {
        return workspace ? workspace.draft_version : 0;
    }

    function noteLocalIntent() {
        intentVersion += 1;
    }

    // One private command with a retained identity. The payload is canonical
    // per attempt: the request UUID lives in the payload itself and is never
    // regenerated for a retry.
    async function runCommand(command) {
        if (command.payload) {
            command.payload.request_id = command.requestId;
        }
        // The outcome becomes unknown when the request is dispatched, not only
        // after a transport error is observed. Gate every other committing
        // action for the complete in-flight window and retain this exact
        // command if the response is lost.
        noteLocalIntent();
        setPendingCommand(command);
        let result;
        try {
            result = await sendJson(urls.commands, command.payload);
        } catch (error) {
            // Transport failure after send: the outcome is unknown. Keep the
            // exact request and invite an idempotent retry.
            setStatus(
                "PeerSlate did not confirm that command. Its outcome is unknown, so retry the same request before anything else.",
                "pending"
            );
            return null;
        }
        if (!result.response.ok) {
            if (result.response.status === 409 || result.response.status === 400) {
                // The server authoritatively refused the command.
                setPendingCommand(null);
            } else {
                // The request reached the server but did not produce an
                // authoritative success/refusal response. Keep the exact
                // request available for idempotent retry.
                setPendingCommand(command);
            }
            setStatus(failedMessage(result.payload, command.fallback), "error");
            return null;
        }
        setPendingCommand(null);
        return result.payload;
    }

    function buildChoices() {
        const choices = [];
        SLOTS.forEach(function (slot) {
            const entry = staged[slot];
            if (!entry) {
                return;
            }
            choices.push({
                slot: slot,
                source: sourceRefForEntry(entry),
                crop: entry.crop,
                alt_text: entry.alt_text || "",
                decorative: !!entry.decorative,
                caption: currentCaption(),
            });
        });
        return choices;
    }

    async function addPhotos() {
        if (refuseWhilePending("adding another photo", "add_media")) {
            return;
        }
        let command = pendingCommand && pendingCommand.kind === "add_media"
            ? pendingCommand
            : null;
        if (!command) {
            const choices = buildChoices();
            if (!choices.length) {
                setStatus("Choose at least one photo before adding it to your r\u00e9sum\u00e9.", "error");
                return;
            }
            command = {
                kind: "add_media",
                choices: choices,
                requestId: requestId(),
                payload: {
                    type: "add_media",
                    request_id: null,
                    expected_draft_version: currentVersion(),
                    choices: choices,
                },
                retryLabel: "Retry Add photos to r\u00e9sum\u00e9",
                fallback: "Your private r\u00e9sum\u00e9 was not changed.",
            };
        }
        elements.add.disabled = true;
        try {
            const payload = await runCommand(command);
            if (!payload) {
                return;
            }
            const count = (command.payload.choices || []).length;
            setStatus(
                "Added " + count + " photo" + (count === 1 ? "" : "s") +
                    " to your private r\u00e9sum\u00e9. Nothing was published.",
                "ok"
            );
            staged = {};
            await loadWorkspace();
        } finally {
            // Re-apply the gate: a command whose outcome is still unknown must
            // keep every other committing control disabled.
            updateCommandGate();
        }
    }

    async function keepWordsOnly() {
        if (refuseWhilePending("choosing Keep it words only", "keep_words_only")) {
            return;
        }
        let command = pendingCommand && pendingCommand.kind === "keep_words_only"
            ? pendingCommand
            : null;
        if (!command) {
            command = {
                kind: "keep_words_only",
                requestId: requestId(),
                payload: {
                    type: "keep_words_only",
                    request_id: null,
                    expected_draft_version: currentVersion(),
                },
                retryLabel: "Retry Keep it words only",
                fallback: "Your pending photo choices were not changed.",
            };
        }
        const payload = await runCommand(command);
        if (!payload) {
            return;
        }
        staged = {};
        setStatus(
            "Kept your words. Pending photo choices were discarded; photos already on your r\u00e9sum\u00e9 were not changed.",
            "ok"
        );
        await loadWorkspace();
    }

    async function retryPendingCommand() {
        const command = pendingCommand;
        if (!command) {
            return;
        }
        if (command.kind === "add_media") {
            await addPhotos();
        } else if (command.kind === "keep_words_only") {
            await keepWordsOnly();
        } else if (command.kind === "remove_slot") {
            const payload = await runCommand(command);
            if (payload) {
                setStatus(command.successMessage, "ok");
                await loadWorkspace();
            }
        }
    }

    function showGuide() {
        root.hidden = false;
        if (elements.header) {
            elements.header.hidden = false;
        }
        elements.guide.hidden = false;
        elements.previewPanel.hidden = true;
        elements.reopen.hidden = true;
    }

    // The private composer and this chooser are separate guides over the same
    // room. Whichever guide is already open stays the active one; the other
    // waits as its reopen affordance instead of stacking two sheets.
    function intakeGuideOpen() {
        const intake = document.getElementById("resume-intake");
        if (!intake || intake.hidden) {
            return false;
        }
        const intakeGuide = document.getElementById("resume-intake-guide");
        return !(intakeGuide && intakeGuide.hidden);
    }

    function syncWithComposer() {
        const narrow = window.matchMedia
            ? window.matchMedia("(max-width: 63.99rem)").matches
            : true;
        if (narrow && intakeGuideOpen()) {
            hideGuide(false);
        } else {
            showGuide();
        }
    }

    function hideGuide(focusReopen) {
        root.hidden = true;
        elements.guide.hidden = true;
        elements.previewPanel.hidden = true;
        elements.reopen.hidden = false;
        if (focusReopen !== false) {
            elements.reopen.focus();
        }
    }

    function showPreviewPanel() {
        if (elements.header) {
            // The preview panel carries its own Back and Hide guide controls.
            elements.header.hidden = true;
        }
        elements.guide.hidden = true;
        elements.previewPanel.hidden = false;
        const entry = selectedEntry(SLOTS[0]) || selectedEntry(SLOTS[1]);
        if (!entry) {
            setStatus("Choose at least one photo before previewing a placement.", "error");
        }
        elements.previewBack.focus();
    }

    function selectTab(name) {
        const photos = name === "photos";
        elements.panelPhotos.hidden = !photos;
        elements.panelLibrary.hidden = photos;
        elements.tabPhotos.setAttribute("aria-selected", photos ? "true" : "false");
        elements.tabLibrary.setAttribute("aria-selected", photos ? "false" : "true");
        elements.tabPhotos.tabIndex = photos ? 0 : -1;
        elements.tabLibrary.tabIndex = photos ? -1 : 0;
        if (!photos && !elements.libraryResults.childElementCount) {
            loadLibrary(false);
        }
    }

    async function loadWorkspace() {
        const epoch = ++workspaceEpoch;
        const intentAtStart = intentVersion;
        let result;
        try {
            const response = await fetch(urls.workspace, { credentials: "same-origin" });
            const payload = await response.json().catch(function () { return {}; });
            result = { response: response, payload: payload };
        } catch (error) {
            if (epoch !== workspaceEpoch || intentAtStart !== intentVersion) {
                return;
            }
            setStatus("Resume media is unavailable right now.", "error");
            return;
        }
        if (epoch !== workspaceEpoch || intentAtStart !== intentVersion) {
            // Either a newer refresh already answered, or the member chose
            // something new while this snapshot was in flight: the older data
            // must not overwrite newer intent.
            return;
        }
        if (!result.response.ok) {
            setStatus(
                failedMessage(result.payload, "Resume media is unavailable right now."),
                "error"
            );
            return;
        }
        workspace = result.payload;
        staged = workspace.staged || {};
        saved = {};
        SLOTS.forEach(function (slot) {
            const entry = workspace.slots ? workspace.slots[slot] : null;
            if (entry) {
                saved[slot] = entry;
            }
        });
        renderPhotos();
        renderAssignments();
        renderPlacement();
        renderPreviewPanel();
    }

    if (elements.upload) {
        const retryUpload = document.createElement("button");
        retryUpload.type = "button";
        retryUpload.className = "resume-media__quiet";
        retryUpload.textContent = "Try upload again";
        retryUpload.hidden = true;
        elements.upload.insertAdjacentElement("afterend", retryUpload);
        async function uploadSelectedPhoto() {
            const file = elements.upload.files && elements.upload.files[0];
            retryUpload.hidden = true;
            if (!file) {
                return;
            }
            const form = new FormData();
            form.append("photo", file, file.name);
            let response;
            try {
                response = await fetch(urls.upload, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "X-PeerSlate-Request": "same-origin" },
                    body: form,
                });
            } catch (error) {
                retryUpload.hidden = false;
                setStatus("The upload response did not arrive. Check My photos before trying this upload again. Your file is still selected.", "error");
                return;
            }
            const payload = await response.json().catch(function () { return {}; });
            if (!response.ok) {
                retryUpload.hidden = false;
                setStatus(
                    failedMessage(payload, "That photo could not be accepted."),
                    "error"
                );
                return;
            }
            setStatus(
                "Uploaded privately. It is not on your r\u00e9sum\u00e9 yet; check the scan before using it.",
                "pending"
            );
            elements.upload.value = "";
            await loadWorkspace();
        }
        elements.upload.addEventListener("change", uploadSelectedPhoto);
        retryUpload.addEventListener("click", uploadSelectedPhoto);
    }

    elements.tabPhotos.addEventListener("click", function () { selectTab("photos"); });
    elements.tabLibrary.addEventListener("click", function () { selectTab("library"); });
    elements.tabPhotos.addEventListener("keydown", function (event) {
        if (event.key === "ArrowRight") { selectTab("library"); elements.tabLibrary.focus(); }
    });
    elements.tabLibrary.addEventListener("keydown", function (event) {
        if (event.key === "ArrowLeft") { selectTab("photos"); elements.tabPhotos.focus(); }
    });
    elements.librarySearch.addEventListener("input", function () {
        window.clearTimeout(elements.librarySearch._timer);
        elements.librarySearch._timer = window.setTimeout(function () {
            loadLibrary(false);
        }, 250);
    });
    elements.libraryMore.addEventListener("click", function () { loadLibrary(true); });
    elements.hide.addEventListener("click", hideGuide);
    elements.previewHide.addEventListener("click", hideGuide);
    elements.reopen.addEventListener("click", showGuide);
    elements.previewPlacement.addEventListener("click", showPreviewPanel);
    elements.previewBack.addEventListener("click", showGuide);
    elements.changePhotos.addEventListener("click", showGuide);
    elements.keepWords.addEventListener("click", keepWordsOnly);
    elements.add.addEventListener("click", addPhotos);
    elements.swap.addEventListener("click", swapPlacements);
    if (elements.retry) {
        elements.retry.addEventListener("click", retryPendingCommand);
    }
    SLOTS.forEach(function (slot) {
        document.getElementById("resume-media-slot-" + slot + "-remove")
            .addEventListener("click", function () { removeSlot(slot); });
        document.getElementById("resume-media-crop-" + slot)
            .addEventListener("click", function () {
                const fields = document.getElementById("resume-media-crop-fields-" + slot);
                fields.hidden = !fields.hidden;
                if (!fields.hidden) {
                    const entry = selectedEntry(slot);
                    fillCropInputs(slot, (entry && entry.crop) || {});
                }
            });
        document.getElementById("resume-media-crop-apply-" + slot)
            .addEventListener("click", function () { applyCrop(slot); });
        document.getElementById("resume-media-placement-change-" + slot)
            .addEventListener("click", showGuide);
    });

    // One active guide per narrow viewport: the composer's own sheet wins when
    // it is already open, and handing the room back re-opens this chooser.
    const composerHide = document.getElementById("resume-intake-hide");
    const composerReopen = document.getElementById("resume-intake-reopen");
    if (composerHide) {
        composerHide.addEventListener("click", function () {
            window.setTimeout(syncWithComposer, 0);
        });
    }
    if (composerReopen) {
        composerReopen.addEventListener("click", function () {
            window.setTimeout(syncWithComposer, 0);
        });
    }

    loadWorkspace();
    selectTab("photos");
    syncWithComposer();
})();
