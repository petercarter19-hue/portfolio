/* PS-JOURNAL-001 Slice J1 - the owner Journal page: context rail local
   filtering, "Load more moments" (keyset cursor), the in-context Capture a
   Moment composer (Type/Speak -> Save Moment), and the saved state.

   Consumes the already-released POST/GET /api/journal/moments (peerslate_api.py)
   and the released Voice upload endpoint (/app/capture/voice) exactly as
   built - this file adds no new server behavior of its own, only calls the
   routes owner_routes.py already exposes (including the two small new ones,
   the Journal page/detail routes and the additive voice-draft JSON route
   described in the completion report). */
(() => {
    "use strict";

    const CONFIG = window.__PS_JOURNAL__;
    if (!CONFIG) return;

    const DRAFT_STORAGE_KEY = "ps-journal-draft-narrative";

    const liveRegion = document.getElementById("journal-live-region");
    const announce = (message) => {
        if (liveRegion) liveRegion.textContent = message;
    };

    /* ================= Context rail: local filter only (never leaves
       the room - Context Rail Standard law 1). Filters the Moments already
       rendered/loaded on this page; a chapter therefore only shows what has
       been loaded so far via "Load more moments". ================= */

    const railEntries = Array.from(document.querySelectorAll("[data-rail-entry]"));
    const chapterEmptyMessages = Array.from(document.querySelectorAll("[data-chapter-empty]"));

    const timelineRows = () => Array.from(document.querySelectorAll("[data-journal-row]"));

    const setActiveChapter = (chapterKey) => {
        railEntries.forEach((entry) => {
            entry.setAttribute("aria-current", String(entry.dataset.chapter === chapterKey));
        });
        let visibleCount = 0;
        timelineRows().forEach((row) => {
            const matches = chapterKey === "timeline" || row.dataset.chapter === chapterKey;
            row.hidden = !matches;
            if (matches) visibleCount += 1;
        });
        chapterEmptyMessages.forEach((message) => {
            const isThisChapter = message.dataset.chapterEmpty === chapterKey;
            message.hidden = !(isThisChapter && visibleCount === 0 && chapterKey !== "timeline");
        });
        const chapterLabelEl = railEntries.find((entry) => entry.dataset.chapter === chapterKey);
        const label = chapterLabelEl
            ? chapterLabelEl.querySelector(".ps-rail__name")?.textContent || chapterKey
            : chapterKey;
        announce(`Showing ${label}.`);
    };

    railEntries.forEach((entry) => {
        entry.addEventListener("click", () => {
            // Two rail twins (desktop + mobile chip row) share chapter keys;
            // keep both in sync so switching on one updates the other.
            setActiveChapter(entry.dataset.chapter);
        });
    });

    /* ================= Manage view: client-side kind + archived filters
       of currently loaded/rendered rows (explicitly sanctioned by the
       brief for Manage), plus the Slice J1.1 server search wired to the
       now-merged GET /api/journal/moments?q= (same flag/identity gates as
       the plain list - this file adds no new endpoint, only calls the one
       peerslate_api.py already exposes). ================= */

    const kindFilterButtons = Array.from(document.querySelectorAll("[data-kind-filter]"));
    const archivedFilterButton = document.querySelector("[data-archived-filter]");

    const applyManageFilters = () => {
        const activeKindButton = kindFilterButtons.find((btn) => btn.getAttribute("aria-pressed") === "true");
        const kind = activeKindButton ? activeKindButton.dataset.kindFilter : "all";
        const archivedOnly = Boolean(archivedFilterButton && archivedFilterButton.getAttribute("aria-pressed") === "true");
        let visibleCount = 0;
        document.querySelectorAll("[data-manage-row]").forEach((row) => {
            const matchesKind = kind === "all" || row.dataset.momentKind === kind;
            const matchesArchived = !archivedOnly || row.dataset.lifecycleState === "archived";
            const visible = matchesKind && matchesArchived;
            row.hidden = !visible;
            if (visible) visibleCount += 1;
        });
        return visibleCount;
    };

    kindFilterButtons.forEach((button) => {
        button.addEventListener("click", () => {
            kindFilterButtons.forEach((other) => other.setAttribute("aria-pressed", "false"));
            button.setAttribute("aria-pressed", "true");
            const count = applyManageFilters();
            announce(
                button.dataset.kindFilter === "all"
                    ? `Showing all Moments (${count}).`
                    : `Filtered to ${button.dataset.kindFilter} (${count}).`
            );
        });
    });

    if (archivedFilterButton) {
        archivedFilterButton.addEventListener("click", () => {
            const nowPressed = archivedFilterButton.getAttribute("aria-pressed") !== "true";
            archivedFilterButton.setAttribute("aria-pressed", String(nowPressed));
            const count = applyManageFilters();
            announce(nowPressed ? `Showing archived Moments only (${count}).` : `Showing all Moments (${count}).`);
        });
    }

    /* ---- Manage: dense row builder shared by the search re-render below.
       Mirrors the server-rendered row markup in templates/journal.html's
       Manage branch exactly, so search results and the initial page look
       and filter identically. ---- */

    const manageSearchInput = document.querySelector("[data-manage-search]");
    const manageList = document.querySelector("[data-manage-list]");
    const manageCountEl = document.querySelector("[data-manage-count]");

    const formatOccurredIso = (occurredOn) => {
        if (!occurredOn) return null;
        const parsed = new Date(occurredOn);
        if (Number.isNaN(parsed.getTime())) return null;
        const year = parsed.getUTCFullYear();
        const month = String(parsed.getUTCMonth() + 1).padStart(2, "0");
        const day = String(parsed.getUTCDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    };

    const buildManageRowElement = (item) => {
        const row = document.createElement("div");
        row.className = "ps-journal__manage-row";
        row.setAttribute("data-manage-row", "");
        row.dataset.momentKind = item.moment_kind || "";
        row.dataset.lifecycleState = item.lifecycle_state || "active";
        const title = item.title || "Untitled Moment";
        const kindLabel = item.moment_kind
            ? item.moment_kind.charAt(0).toUpperCase() + item.moment_kind.slice(1)
            : "Moment";
        const kindIcon =
            item.moment_kind === "achievement"
                ? '<svg class="ps-journal__kind-star" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 2l2.6 5.6 6.1.7-4.5 4.2 1.2 6-5.4-3-5.4 3 1.2-6-4.5-4.2 6.1-.7z"/></svg>'
                : '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5"/></svg>';
        const archivedBadge =
            item.lifecycle_state === "archived"
                ? '<span class="ps-journal__manage-archived-badge">Archived</span>'
                : "";
        const occurredIso = formatOccurredIso(item.occurred_on);
        row.innerHTML = `
            <span>${occurredIso || "Date not set"}</span>
            <span class="ps-journal__manage-kind">${kindIcon}${escapeHtml(kindLabel)}</span>
            <span class="ps-journal__manage-title"><a href="${momentDetailUrl(item.moment_key)}">${escapeHtml(title)}</a></span>
            <span class="ps-journal__manage-status"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg> Private ${archivedBadge}</span>
            <button type="button" class="ps-journal__manage-menu" disabled aria-disabled="true" aria-label="More options for this Moment - coming later"><svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg></button>`;
        return row;
    };

    let lastSearchQuery = "";

    const renderManageRows = (items) => {
        if (!manageList) return;
        manageList.innerHTML = "";
        if (!items.length) {
            const empty = document.createElement("p");
            empty.className = "ps-journal__manage-empty";
            empty.setAttribute("data-manage-empty", "");
            empty.textContent = lastSearchQuery
                ? `No matches for "${lastSearchQuery}".`
                : "No Moments yet. Capture your first one from the Journal.";
            manageList.appendChild(empty);
        } else {
            const head = document.createElement("div");
            head.className = "ps-journal__manage-head";
            head.setAttribute("aria-hidden", "true");
            head.innerHTML = "<span>Date</span><span>Kind</span><span>Moment</span><span>Status</span><span></span>";
            manageList.appendChild(head);
            items.forEach((item) => manageList.appendChild(buildManageRowElement(item)));
        }
        if (manageCountEl) {
            manageCountEl.textContent = `${items.length} ${items.length === 1 ? "Moment" : "Moments"}`;
        }
        applyManageFilters();
    };

    /* ---- Manage: search, debounced, wired to ?q= on the shared
       GET /api/journal/moments endpoint. An empty query returns to the
       plain (unsearched) archived-inclusive list - never a stale search
       result left on screen. A request token guards against an earlier,
       slower response overwriting a newer one. ---- */

    let manageSearchDebounceId = null;
    let manageSearchToken = 0;

    const loadManageRows = async (query) => {
        if (!manageList) return;
        const token = (manageSearchToken += 1);
        lastSearchQuery = query;
        announce(query ? `Searching for "${query}"…` : "Loading your Moments…");
        try {
            const url = new URL(CONFIG.apiUrl, window.location.origin);
            url.searchParams.set("include_archived", "1");
            url.searchParams.set("limit", "50");
            if (query) url.searchParams.set("q", query);
            const response = await fetch(url.toString(), { credentials: "same-origin" });
            const result = await response.json().catch(() => ({}));
            if (token !== manageSearchToken) return;
            if (response.ok && result.success) {
                const items = result.items || [];
                renderManageRows(items);
                announce(
                    query
                        ? `Found ${items.length} result${items.length === 1 ? "" : "s"} for "${query}".`
                        : `Showing ${items.length} Moments.`
                );
            } else {
                announce("Could not search right now. Try again.");
            }
        } catch (error) {
            if (token !== manageSearchToken) return;
            announce("Could not search right now. Check your connection and try again.");
        }
    };

    if (manageSearchInput) {
        manageSearchInput.addEventListener("input", () => {
            const value = manageSearchInput.value.trim();
            window.clearTimeout(manageSearchDebounceId);
            manageSearchDebounceId = window.setTimeout(() => {
                loadManageRows(value);
            }, 300);
        });
    }

    /* ================= Timeline row rendering (used both for the
       initial "Load more" append and for the post-save refresh). ================= */

    const chapterKeyForItem = (item) => {
        if (item.source_type === "voice") return "voice";
        if (item.source_type === "photo") return "photos";
        if (item.source_type === "video") return "videos";
        if (item.moment_kind === "achievement") return "milestones";
        if (item.moment_kind === "lesson") return "reflections";
        return "";
    };

    const momentDetailUrl = (momentKey) =>
        CONFIG.momentUrlTemplate.replace("__MOMENT_KEY__", encodeURIComponent(momentKey));

    // S4: tracks whether the sparse "Proud of this one" flourish has
    // already been shown on the page, across both server-rendered and
    // client-appended rows - initialized from whatever the server already
    // rendered so "Load more" never adds a second one, and explicitly reset
    // in refreshTimelineFirstPage when a save fully rebuilds the list.
    let firstAchievementAnnotated = Boolean(document.querySelector(".ps-journal__annotation"));

    const formatOccurred = (occurredOn) => {
        if (!occurredOn) return { day: null, month: null };
        // Flask's jsonify serializes a Python date as an RFC 822/1123
        // string with an explicit "GMT" suffix (e.g. "Mon, 20 Jul 2026
        // 00:00:00 GMT"), not plain ISO "YYYY-MM-DD" - confirmed against
        // this app's actual /api/journal/moments response. Both that format
        // and a bare ISO date string parse as UTC per the Date spec, so
        // passing the value straight through (no truncation) and reading it
        // back with getUTCDate()/timeZone:"UTC" is correct in every local
        // browser timezone. An earlier version of this function sliced the
        // string to 10 characters assuming ISO input, which silently broke
        // "Load more" and the post-save refresh (RFC 822 truncated at 10
        // chars is not a parseable date) - both now covered by
        // tests/test_journal_frontend.py's rendered-content assertions
        // stayed green because that suite only exercises server-rendered
        // HTML, not this client fetch path; caught instead by evidence
        // screenshots, see the completion report.
        const parsed = new Date(occurredOn);
        if (Number.isNaN(parsed.getTime())) return { day: null, month: null };
        return {
            day: String(parsed.getUTCDate()).padStart(2, "0"),
            month: parsed.toLocaleString("en-US", { month: "short", timeZone: "UTC" }).toUpperCase(),
        };
    };

    const buildRowElement = (item) => {
        const li = document.createElement("li");
        const chapterKey = chapterKeyForItem(item);
        const sourceType = item.source_type || "text";
        li.className = `ps-journal__row ps-journal__row--${sourceType}`;
        li.setAttribute("data-journal-row", "");
        li.dataset.sourceType = sourceType;
        li.dataset.momentKind = item.moment_kind || "";
        li.dataset.chapter = chapterKey;
        li.id = `journal-moment-${item.moment_key}`;

        const { day, month } = formatOccurred(item.occurred_on);
        const title = item.title || "Untitled Moment";
        const kindLabel = item.moment_kind
            ? item.moment_kind.charAt(0).toUpperCase() + item.moment_kind.slice(1)
            : "Moment";
        // S4 (Opus review): the source-type label ("Text Note"/"Voice Note")
        // next to kind, from the real source_type field - mirrors the
        // server-rendered row and the Moment detail page exactly.
        const sourceLabel = { voice: "Voice Note", photo: "Photo", video: "Video" }[sourceType] || "Text Note";
        const star =
            item.moment_kind === "achievement"
                ? '<svg class="ps-journal__kind-star" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 2l2.6 5.6 6.1.7-4.5 4.2 1.2 6-5.4-3-5.4 3 1.2-6-4.5-4.2 6.1-.7z"/></svg>'
                : "";
        // S4: a sparse, designed flourish on the first achievement row only
        // per page-build (see firstAchievementAnnotated, reset in
        // refreshTimelineFirstPage on a full rebuild, left alone across
        // "Load more" appends so it never repeats further down the list).
        const annotationMarkup =
            item.moment_kind === "achievement" && !firstAchievementAnnotated
                ? (() => {
                      firstAchievementAnnotated = true;
                      return '<p class="ps-journal__annotation">Proud of this one <svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor" width="14" height="14"><path d="M12 2l2.6 5.6 6.1.7-4.5 4.2 1.2 6-5.4-3-5.4 3 1.2-6-4.5-4.2 6.1-.7z"/></svg></p>';
                  })()
                : "";
        // The title (row heading below) is the only content the read API
        // returns - no separate narrative field - so a voice row adds the
        // disabled playback control, and a text row adds nothing further
        // rather than repeating the same title as a fake second line.
        const mediaMarkup =
            sourceType === "voice"
                ? '<div class="ps-journal__voice-row"><button type="button" class="ps-journal__voice-play" disabled aria-disabled="true" aria-label="Playback for this voice Moment is coming later">' +
                  '<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></button>' +
                  '<span class="ps-journal__voice-wave" aria-hidden="true"></span><span class="ps-journal__voice-duration">Coming later</span></div>'
                : "";

        li.innerHTML = `
            <div class="ps-journal__date">
                ${
                    day
                        ? `<span class="ps-journal__date-day">${day}</span><span class="ps-journal__date-month">${month}</span>`
                        : '<span class="ps-journal__date-day">&mdash;</span><span class="ps-journal__date-month">Date not set</span>'
                }
            </div>
            <div class="ps-journal__content">
                <p class="ps-journal__meta">
                    ${star}
                    <span>${escapeHtml(kindLabel)}</span>
                    <span aria-hidden="true">&middot;</span>
                    <span>${escapeHtml(sourceLabel)}</span>
                    <span aria-hidden="true">&middot;</span>
                    <span class="ps-journal__meta-privacy"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg> Private</span>
                </p>
                <h3 class="ps-journal__row-title"><a href="${momentDetailUrl(item.moment_key)}">${escapeHtml(title)}</a></h3>
                ${annotationMarkup}
                ${mediaMarkup}
            </div>`;
        return li;
    };

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value == null ? "" : String(value);
        return div.innerHTML;
    }

    /* ================= Load more moments (API keyset cursor) ================= */

    const timelineList = document.querySelector("[data-timeline]");
    const loadMoreButton = document.getElementById("journal-load-more");

    const appendItems = (items) => {
        if (!timelineList) return;
        items.forEach((item) => timelineList.appendChild(buildRowElement(item)));
        // A freshly appended row must respect whichever chapter is currently
        // active, not always "timeline".
        const activeEntry = railEntries.find((entry) => entry.getAttribute("aria-current") === "true");
        setActiveChapter(activeEntry ? activeEntry.dataset.chapter : "timeline");
    };

    if (loadMoreButton) {
        loadMoreButton.addEventListener("click", async () => {
            const cursor = loadMoreButton.dataset.cursor;
            if (!cursor) return;
            loadMoreButton.disabled = true;
            const originalText = loadMoreButton.textContent;
            loadMoreButton.textContent = "Loading…";
            try {
                const url = new URL(CONFIG.apiUrl, window.location.origin);
                url.searchParams.set("cursor", cursor);
                url.searchParams.set("limit", "20");
                const response = await fetch(url.toString(), { credentials: "same-origin" });
                const result = await response.json().catch(() => ({}));
                if (response.ok && result.success) {
                    appendItems(result.items || []);
                    announce(`Loaded ${((result.items) || []).length} more moments.`);
                    if (result.next_cursor) {
                        loadMoreButton.dataset.cursor = result.next_cursor;
                        loadMoreButton.disabled = false;
                        loadMoreButton.textContent = originalText;
                    } else {
                        loadMoreButton.remove();
                    }
                } else {
                    loadMoreButton.disabled = false;
                    loadMoreButton.textContent = originalText;
                    announce("Could not load more moments. Try again.");
                }
            } catch (error) {
                loadMoreButton.disabled = false;
                loadMoreButton.textContent = originalText;
                announce("Could not load more moments. Check your connection and try again.");
            }
        });
    }

    /* ================= Composer ================= */

    const scrim = document.querySelector("[data-composer-scrim]");
    const composer = document.querySelector("[data-composer]");
    if (!scrim || !composer) return;

    const composeView = composer.querySelector('[data-composer-view="compose"]');
    const savedView = composer.querySelector('[data-composer-view="saved"]');
    const tabs = Array.from(composer.querySelectorAll("[data-composer-tab]"));
    const panels = Array.from(composer.querySelectorAll("[data-composer-panel]"));
    const narrativeField = composer.querySelector("[data-composer-narrative]");
    const statusEl = composer.querySelector("[data-composer-status]");
    const saveButton = composer.querySelector("[data-composer-save]");
    const cancelButton = composer.querySelector("[data-composer-cancel]");
    const closeButton = composer.querySelector("[data-composer-close]");
    const doneButton = composer.querySelector("[data-composer-done]");
    const backButton = composer.querySelector("[data-composer-back]");
    const kindSelect = composer.querySelector("[data-composer-kind]");
    const precisionSelect = composer.querySelector("[data-composer-precision]");
    const occurredInput = composer.querySelector("[data-composer-occurred-on]");
    const voiceRecorder = composer.querySelector("[data-voice-recorder]");
    const voiceReview = composer.querySelector("[data-voice-review]");
    const voiceTranscriptField = composer.querySelector("[data-voice-transcript]");
    const voiceAudio = composer.querySelector("[data-voice-audio]");
    const voiceStateTitle = composer.querySelector("[data-voice-state-title]");
    const voiceStateHelp = composer.querySelector("[data-voice-state-help]");
    const voiceTimer = composer.querySelector("[data-voice-timer]");
    const voiceStart = composer.querySelector('[data-voice-action="start"]');
    const voiceStop = composer.querySelector('[data-voice-action="stop"]');
    const voiceCancel = composer.querySelector('[data-voice-action="cancel"]');

    const ERROR_MESSAGES = {
        required: "Add a Moment before saving - the title comes from its first line.",
        "too-long": "Shorten your Moment - it is over the length limit.",
        date: "Choose a valid date, or set When to “Date not set.”",
        changed: "That did not save. Please try again.",
    };

    let idempotencyKey = null;
    let openInvoker = null;
    let saving = false;
    let recorder = null;
    let mediaStream = null;
    let chunks = [];
    let recordingStartedAt = 0;
    let recordingTimerId = null;
    let recordingCancelled = false;

    const genIdempotencyKey = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        return `k-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    };

    const setStatus = (message, isError) => {
        statusEl.textContent = message || "";
        if (isError) statusEl.setAttribute("data-tone", "error");
        else statusEl.removeAttribute("data-tone");
    };

    // Save Moment always requires a Title; the accepted composer screens
    // show a single content field with no separate Title input, so the
    // title is deterministically derived from the member's own first line -
    // never AI-paraphrased. Disclosed in the completion report.
    const deriveTitle = (narrative) => {
        const firstLine = narrative.split(/\r?\n/)[0].trim() || narrative.trim();
        const limit = CONFIG.maxTitleLength || 160;
        return firstLine.length > limit ? `${firstLine.slice(0, limit - 1)}…` : firstLine;
    };

    const activeNarrativeField = () =>
        voiceReview && !voiceReview.hidden ? voiceTranscriptField : narrativeField;

    const switchTab = (name) => {
        tabs.forEach((tab) => {
            const selected = tab.dataset.composerTab === name;
            tab.setAttribute("aria-selected", String(selected));
            tab.tabIndex = selected ? 0 : -1;
        });
        panels.forEach((panel) => {
            panel.hidden = panel.dataset.composerPanel !== name;
        });
        if (name === "type") narrativeField.focus();
    };
    tabs.forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.composerTab)));

    const focusableIn = (container) =>
        Array.from(
            container.querySelectorAll(
                "button, [href], input, textarea, select, summary, audio[controls], [tabindex]:not([tabindex='-1'])"
            )
        ).filter((el) => !el.disabled && el.offsetParent !== null);

    const trapFocus = (event) => {
        if (event.key !== "Tab") return;
        const visible = composeView.hidden ? savedView : composeView;
        const items = focusableIn(visible);
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

    const onKeydown = (event) => {
        if (event.key === "Escape") {
            event.preventDefault();
            if (!composeView.hidden) handleCancel();
            else handleDone();
            return;
        }
        trapFocus(event);
    };

    const teardownRecording = () => {
        window.clearInterval(recordingTimerId);
        recordingTimerId = null;
        if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
        recorder = null;
        chunks = [];
        if (voiceStop) voiceStop.hidden = true;
        if (voiceCancel) voiceCancel.hidden = true;
        if (voiceStart) voiceStart.hidden = false;
        if (voiceTimer) voiceTimer.hidden = true;
    };

    const restoreDraftIfAny = () => {
        let draft = "";
        try {
            draft = window.localStorage.getItem(DRAFT_STORAGE_KEY) || "";
        } catch (error) {
            draft = "";
        }
        if (draft) {
            narrativeField.value = draft;
            setStatus("Draft restored from your last attempt - nothing was lost.", false);
        }
    };

    const resetComposer = () => {
        idempotencyKey = genIdempotencyKey();
        narrativeField.value = "";
        if (voiceTranscriptField) voiceTranscriptField.value = "";
        if (voiceReview) voiceReview.hidden = true;
        if (voiceRecorder) voiceRecorder.hidden = false;
        teardownRecording();
        if (voiceStateTitle) voiceStateTitle.textContent = "Ready when you are";
        if (voiceStateHelp) {
            voiceStateHelp.textContent =
                "Your browser asks for microphone permission when you start. You can review and edit the transcript before anything saves.";
        }
        setStatus("", false);
        const today = new Date();
        const isoToday = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(
            today.getDate()
        ).padStart(2, "0")}`;
        if (occurredInput) occurredInput.value = isoToday;
        if (precisionSelect) precisionSelect.value = "exact";
        if (kindSelect) kindSelect.value = "update";
        switchTab("type");
    };

    const openComposer = (invoker) => {
        openInvoker = invoker || document.activeElement;
        scrim.hidden = false;
        composeView.hidden = false;
        savedView.hidden = true;
        resetComposer();
        restoreDraftIfAny();
        document.body.style.overflow = "hidden";
        document.addEventListener("keydown", onKeydown, true);
        narrativeField.focus();
    };

    const closeComposer = () => {
        scrim.hidden = true;
        document.body.style.overflow = "";
        document.removeEventListener("keydown", onKeydown, true);
        teardownRecording();
        if (openInvoker && document.contains(openInvoker)) openInvoker.focus();
        openInvoker = null;
    };

    const handleCancel = () => {
        try {
            window.localStorage.removeItem(DRAFT_STORAGE_KEY);
        } catch (error) {
            /* private mode or unavailable storage - nothing to clean up */
        }
        closeComposer();
    };

    let needsFullReloadOnClose = false;

    const handleDone = () => {
        if (needsFullReloadOnClose) {
            // No [data-timeline] list exists to update in place - this was
            // either the true empty first-visit state or the Manage view.
            // A full navigation back to the Journal is simple, honest, and
            // guarantees the just-saved Moment "must appear in the timeline
            // immediately" (doc 11) rather than leaving stale empty-state
            // markup on screen.
            window.location.href = CONFIG.listUrl;
            return;
        }
        closeComposer();
    };

    document.querySelectorAll("[data-open-composer]").forEach((trigger) => {
        trigger.addEventListener("click", () => openComposer(trigger));
    });
    cancelButton.addEventListener("click", handleCancel);
    closeButton.addEventListener("click", handleCancel);
    doneButton.addEventListener("click", handleDone);
    backButton.addEventListener("click", handleDone);

    const refreshTimelineFirstPage = async () => {
        if (!timelineList) return;
        try {
            const url = new URL(CONFIG.apiUrl, window.location.origin);
            url.searchParams.set("limit", "20");
            const response = await fetch(url.toString(), { credentials: "same-origin" });
            const result = await response.json().catch(() => ({}));
            if (response.ok && result.success) {
                timelineList.innerHTML = "";
                firstAchievementAnnotated = false;
                appendItems(result.items || []);
                if (loadMoreButton) {
                    if (result.next_cursor) loadMoreButton.dataset.cursor = result.next_cursor;
                    else loadMoreButton.remove();
                }
            }
        } catch (error) {
            /* the Moment is already safely saved server-side; a stale visible
               timeline is a display-refresh issue, not a save failure. */
        }
    };

    const incrementHeroTotal = () => {
        const valueEl = document.querySelector(".ps-journal__hero-stat-value");
        if (!valueEl) return;
        const current = Number.parseInt(valueEl.textContent, 10);
        if (!Number.isNaN(current)) valueEl.textContent = String(current + 1);
    };

    const onSaved = async () => {
        composeView.hidden = true;
        savedView.hidden = false;
        const savedTitle = savedView.querySelector("#journal-saved-title");
        if (savedTitle) savedTitle.focus?.();
        announce("Moment saved privately. It is now in your Journal.");
        incrementHeroTotal();
        if (timelineList) {
            needsFullReloadOnClose = false;
            await refreshTimelineFirstPage();
        } else {
            // The Manage view and the empty-first-visit state have no
            // [data-timeline] element to update in place; Done/Back to page
            // does a full navigation back to the Journal instead (see
            // handleDone) so the saved Moment reliably appears.
            needsFullReloadOnClose = true;
        }
        doneButton.focus();
    };

    const handleSave = async () => {
        if (saving) return;
        const field = activeNarrativeField();
        const narrative = field.value.trim();
        if (!narrative) {
            setStatus(ERROR_MESSAGES.required, true);
            field.focus();
            return;
        }
        const precision = precisionSelect ? precisionSelect.value : "exact";
        const occurredOn = precision === "unknown" ? "" : occurredInput.value;
        if (precision !== "unknown" && !occurredOn) {
            setStatus(ERROR_MESSAGES.date, true);
            occurredInput.focus();
            return;
        }

        saving = true;
        saveButton.disabled = true;
        cancelButton.disabled = true;
        setStatus("Saving…", false);
        try {
            window.localStorage.setItem(DRAFT_STORAGE_KEY, narrative);
        } catch (error) {
            /* best-effort only */
        }

        const body = {
            idempotency_key: idempotencyKey,
            moment_kind: kindSelect ? kindSelect.value : "update",
            title: deriveTitle(narrative),
            narrative,
            occurred_precision: precision,
        };
        if (occurredOn) body.occurred_on = occurredOn;

        try {
            const response = await fetch(CONFIG.apiUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-PeerSlate-Request": "same-origin",
                    "X-Requested-With": "fetch",
                },
                body: JSON.stringify(body),
            });
            const result = await response.json().catch(() => ({}));
            if (response.ok && result.success) {
                try {
                    window.localStorage.removeItem(DRAFT_STORAGE_KEY);
                } catch (error) {
                    /* best-effort only */
                }
                await onSaved();
            } else if (response.status === 409) {
                setStatus(
                    "That could not be confirmed as saved - your draft is kept. Try Save Moment again.",
                    true
                );
            } else {
                const key = result && result.error;
                setStatus((key && ERROR_MESSAGES[key]) || "That did not save. Your draft is kept.", true);
            }
        } catch (networkError) {
            setStatus(
                "The save did not finish. Your draft is kept - try again when you are back online.",
                true
            );
        } finally {
            saving = false;
            saveButton.disabled = false;
            cancelButton.disabled = false;
        }
    };
    saveButton.addEventListener("click", handleSave);

    /* ================= Speak: reuses the released Voice lifecycle
       (record -> upload -> transcribe -> review), then hands the accepted
       transcript to the same Save Moment action above. See the completion
       report for the disclosed voice-source linkage gap: the resulting
       Moment always saves as source_type "text", the same as Type. ================= */

    const supportedMimeTypes = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"];
    const chooseMimeType = () => {
        if (!window.MediaRecorder || typeof window.MediaRecorder.isTypeSupported !== "function") return "";
        return supportedMimeTypes.find((type) => window.MediaRecorder.isTypeSupported(type)) || "";
    };

    const formatSeconds = (seconds) => {
        const bounded = Math.max(0, Math.min(CONFIG.maxVoiceDurationSeconds || 180, Math.floor(seconds)));
        return `${Math.floor(bounded / 60)}:${String(bounded % 60).padStart(2, "0")}`;
    };

    const showVoiceReview = (draft) => {
        if (voiceRecorder) voiceRecorder.hidden = true;
        if (voiceReview) voiceReview.hidden = false;
        if (voiceTranscriptField) voiceTranscriptField.value = draft.transcript || "";
        if (voiceAudio && draft.audio_url) voiceAudio.src = draft.audio_url;
        setStatus("Transcript ready for your review. Nothing is saved until Save Moment.", false);
        if (voiceTranscriptField) voiceTranscriptField.focus();
    };

    const uploadVoiceRecording = async (blob, durationSeconds) => {
        if (blob.size > (CONFIG.maxVoiceBytes || 20971520)) {
            if (voiceStateHelp) {
                voiceStateHelp.textContent =
                    "The recording exceeded the size limit and was not uploaded. Use Type instead, or record a shorter Moment.";
            }
            teardownRecording();
            return;
        }
        if (voiceStateTitle) voiceStateTitle.textContent = "Preparing your private draft…";
        if (voiceStateHelp) voiceStateHelp.textContent = "Uploading the private recording, then transcribing it. Keep this open.";
        const formData = new FormData();
        formData.append("audio", blob, "recording");
        formData.append("duration_seconds", String(Math.min(durationSeconds, CONFIG.maxVoiceDurationSeconds || 180)));
        try {
            const response = await fetch(CONFIG.voiceUploadUrl, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: { "X-Requested-With": "fetch" },
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok || !result.review_url) {
                if (voiceStateTitle) voiceStateTitle.textContent = "Something needs your attention";
                if (voiceStateHelp) {
                    voiceStateHelp.textContent =
                        result.error === "transcription-failed"
                            ? "The recording stayed private, but transcription failed. Use Type instead, or record again."
                            : "The private recording could not be completed. Use Type instead, or try again.";
                }
                teardownRecording();
                return;
            }
            let sourceKey = "";
            try {
                sourceKey = new URL(result.review_url, window.location.origin).searchParams.get("voice") || "";
            } catch (error) {
                sourceKey = "";
            }
            if (!sourceKey) {
                teardownRecording();
                return;
            }
            const draftUrl = CONFIG.voiceDraftUrlTemplate.replace("__SOURCE_KEY__", encodeURIComponent(sourceKey));
            const draftResponse = await fetch(draftUrl, { credentials: "same-origin" });
            const draft = await draftResponse.json().catch(() => ({}));
            teardownRecording();
            if (draftResponse.ok && draft.success && draft.state === "needs_review") {
                showVoiceReview(draft);
            } else if (draftResponse.ok && draft.success && draft.state === "failed") {
                if (voiceStateTitle) voiceStateTitle.textContent = "Transcription needs attention";
                if (voiceStateHelp) voiceStateHelp.textContent = "Use Type instead, or record again.";
            } else {
                if (voiceStateTitle) voiceStateTitle.textContent = "Something needs your attention";
                if (voiceStateHelp) voiceStateHelp.textContent = "Use Type instead, or record again.";
            }
        } catch (error) {
            if (voiceStateTitle) voiceStateTitle.textContent = "The upload did not finish";
            if (voiceStateHelp) voiceStateHelp.textContent = "Nothing was saved. Use Type instead, or try again.";
            teardownRecording();
        }
    };

    const startRecording = async () => {
        if (recorder && recorder.state === "recording") return;
        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            if (voiceStateTitle) voiceStateTitle.textContent = "Speak is not supported in this browser";
            if (voiceStateHelp) voiceStateHelp.textContent = "Type remains fully available.";
            return;
        }
        const mimeType = chooseMimeType();
        if (!mimeType) {
            if (voiceStateTitle) voiceStateTitle.textContent = "Speak is not supported in this browser";
            if (voiceStateHelp) voiceStateHelp.textContent = "Type remains fully available.";
            return;
        }
        if (voiceStateTitle) voiceStateTitle.textContent = "Requesting microphone access";
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            chunks = [];
            recordingCancelled = false;
            recorder = new MediaRecorder(mediaStream, { mimeType });
            recorder.addEventListener("dataavailable", (event) => {
                if (event.data?.size) chunks.push(event.data);
            });
            recorder.addEventListener(
                "stop",
                () => {
                    window.clearInterval(recordingTimerId);
                    recordingTimerId = null;
                    if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
                    mediaStream = null;
                    const duration = Math.min(
                        (Date.now() - recordingStartedAt) / 1000,
                        CONFIG.maxVoiceDurationSeconds || 180
                    );
                    if (recordingCancelled) {
                        chunks = [];
                        teardownRecording();
                        return;
                    }
                    const blob = new Blob(chunks, { type: recorder.mimeType });
                    chunks = [];
                    uploadVoiceRecording(blob, duration);
                },
                { once: true }
            );
            recorder.start(1000);
            recordingStartedAt = Date.now();
            if (voiceTimer) {
                voiceTimer.hidden = false;
                voiceTimer.textContent = `0:00 / ${formatSeconds(CONFIG.maxVoiceDurationSeconds || 180)}`;
            }
            recordingTimerId = window.setInterval(() => {
                const elapsed = (Date.now() - recordingStartedAt) / 1000;
                if (voiceTimer) {
                    voiceTimer.textContent = `${formatSeconds(elapsed)} / ${formatSeconds(CONFIG.maxVoiceDurationSeconds || 180)}`;
                }
                if (elapsed >= (CONFIG.maxVoiceDurationSeconds || 180) && recorder?.state === "recording") {
                    recorder.stop();
                }
            }, 250);
            if (voiceStart) voiceStart.hidden = true;
            if (voiceStop) voiceStop.hidden = false;
            if (voiceCancel) voiceCancel.hidden = false;
            if (voiceStateTitle) voiceStateTitle.textContent = "Listening…";
            if (voiceStateHelp) voiceStateHelp.textContent = "Speak naturally. You can edit everything before anything is saved.";
            if (voiceStop) voiceStop.focus();
        } catch (error) {
            teardownRecording();
            if (voiceStateTitle) voiceStateTitle.textContent = "Microphone access was denied or unavailable";
            if (voiceStateHelp) voiceStateHelp.textContent = "Type remains fully available.";
        }
    };

    if (voiceStart) voiceStart.addEventListener("click", startRecording);
    if (voiceStop) {
        voiceStop.addEventListener("click", () => {
            if (recorder?.state === "recording") recorder.stop();
        });
    }
    if (voiceCancel) {
        voiceCancel.addEventListener("click", () => {
            recordingCancelled = true;
            if (recorder?.state === "recording") recorder.stop();
            else teardownRecording();
        });
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !chooseMimeType()) {
        if (voiceStart) voiceStart.disabled = true;
    }
})();
