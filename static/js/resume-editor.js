(function () {
    const root = document.getElementById("resume-editor-lists");
    const status = document.getElementById("resume-editor-status");
    if (!root) {
        return;
    }

    const workspaceUrl = root.getAttribute("data-workspace-url");
    const commandsUrl = root.getAttribute("data-commands-url");
    const reviewUrl = root.getAttribute("data-review-url");
    let pendingEdit = null;
    let editInFlight = false;
    const fieldOrder = {
        role: ["role_title", "employer_name", "summary", "location_text", "date_precision", "start_date", "end_date", "current_role"],
        education: ["title", "institution_name", "field_of_study", "education_status", "summary", "date_precision", "start_date", "end_date"],
        credential: ["name", "issuer", "completion_status", "identifier"],
        skill: ["name", "summary"],
        accomplishment: ["wording", "metric_value", "metric_label"],
        knowledge: ["title", "wording"],
    };
    const sectionTitles = {
        role: "Experience",
        education: "Education",
        credential: "Credentials",
        skill: "Strengths",
        accomplishment: "Impact",
        knowledge: "Personal entries",
    };
    let workspace = null;
    let pendingStory = null;

    function setStatus(message, kind) {
        status.textContent = message;
        status.setAttribute("data-kind", kind || "ok");
    }

    function requestId() {
        if (window.crypto && window.crypto.randomUUID) {
            return window.crypto.randomUUID();
        }
        return "00000000-0000-4000-8000-000000000000".replace(/0/g, function () {
            return Math.floor(Math.random() * 10);
        });
    }

    async function send(url, body) {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-PeerSlate-Request": "same-origin",
            },
            body: JSON.stringify(body),
        });
        const payload = await response.json().catch(function () {
            return {};
        });
        return { response: response, payload: payload };
    }

    function valuesFromForm(form, item) {
        const recordType = item.record_type;
        const merged = Object.assign({}, item.values || {}, item.proposed_values || {});
        const fields = fieldOrder[recordType] || Object.keys(merged);
        fields.forEach(function (name) {
            const field = form.elements.namedItem(name);
            if (field) {
                merged[name] = field.type === "checkbox" ? field.checked : field.value;
            }
        });
        if (["role", "education"].includes(recordType)) {
            ["start_date", "end_date"].forEach(function (name) {
                const raw = merged[name].trim();
                const precision = merged.date_precision;
                if (!raw) { merged[name] = null; return; }
                const pattern = {year: /^\d{4}$/, month: /^\d{4}-\d{2}$/, day: /^\d{4}-\d{2}-\d{2}$/,
                    approximate: /^\d{4}-\d{2}-\d{2}$/, unknown: /^\d{4}-\d{2}-\d{2}$/}[precision];
                if (!pattern || !pattern.test(raw)) throw new Error("Use YYYY, YYYY-MM or YYYY-MM-DD to match date detail. Leave unknown dates empty.");
                merged[name] = raw + (precision === "year" ? "-01-01" : precision === "month" ? "-01" : "");
            });
        }
        return merged;
    }

    function dateText(value, precision) {
        if (!value || precision === "unknown" || !precision) return "";
        return String(value).slice(0, precision === "year" ? 4 : precision === "month" ? 7 : 10);
    }

    function setField(field, value, source) {
        if (field.type === "checkbox") field.checked = value === true;
        else if (["start_date", "end_date"].includes(field.name)) {
            // Preserve pre-existing unqualified date values in the edit form;
            // an unknown precision never presents them as established dates.
            field.value = dateText(value, source.date_precision) || (value || "");
        } else field.value = value == null ? "" : value;
    }

    function fillForm(form, item) {
        const source = Object.assign({}, item.values || {}, item.proposed_values || {});
        Object.keys(source).forEach(function (name) {
            const field = form.elements.namedItem(name);
            if (field) setField(field, source[name], source);
        });
    }

    function preserveFromError(form, payload) {
        const proposed = payload.proposed_values;
        if (!proposed) {
            return;
        }
        Object.keys(proposed).forEach(function (name) {
            const field = form.elements.namedItem(name);
            if (field) setField(field, proposed[name], proposed);
        });
    }

    async function saveItem(form, item) {
        if (editInFlight) return;
        if (pendingEdit && pendingEdit.record_key !== item.record_key) {
            setStatus("Retry the unresolved save before saving another entry.", "error");
            return;
        }
        let proposed;
        try { proposed = valuesFromForm(form, item); }
        catch (error) { setStatus(error.message, "error"); return; }
        if (!pendingEdit) pendingEdit = {
            request_id: requestId(),
            type: "save_item",
            record_key: item.record_key,
            record_type: item.record_type,
            expected_draft_version: workspace.draft_version,
            expected_content_token: item.content_token,
            expected_access_revision: item.access_revision,
            values: proposed,
        };
        const save = form.querySelector('[type="submit"]');
        function lock(locked) {
            form.querySelectorAll("input, select, textarea, button").forEach(function (field) {
                field.disabled = locked && field !== save;
            });
        }
        lock(true);
        editInFlight = true;
        save.disabled = true;
        let result;
        try {
            result = await send(commandsUrl, pendingEdit);
        } catch (error) {
            setStatus("The save response did not arrive. Your wording is kept. Retry this same save to confirm it.", "error");
            save.textContent = "Retry same save";
            return;
        } finally {
            editInFlight = false;
            save.disabled = false;
        }
        if (result.response.status >= 500) {
            setStatus("The save could not be confirmed. Your wording is kept. Retry this same save.", "error");
            save.textContent = "Retry same save";
            return;
        }
        pendingEdit = null;
        lock(false);
        save.textContent = "Save draft";
        if (result.response.status === 409) {
            preserveFromError(form, result.payload);
            setStatus(result.payload.message || "That save could not be applied. Your wording is still here.", "error");
            return;
        }
        if (!result.response.ok) {
            setStatus(result.payload.message || "That save could not be applied.", "error");
            return;
        }
        await loadWorkspace();
        setStatus("Draft saved. Sharing did not change.", "ok");
    }

    function renderItem(item) {
        const card = document.createElement("article");
        card.className = "resume-editor__card";
        const values = Object.assign({}, item.values || {}, item.proposed_values || {});
        const heading = document.createElement("h3");
        heading.textContent = values.role_title || values.title || values.name || values.wording || "Untitled entry";
        card.appendChild(heading);
        const detail = document.createElement("p");
        detail.className = "resume-editor__entry-detail";
        detail.textContent = [values.employer_name || values.institution_name || values.issuer,
            values.location_text].filter(Boolean).join(" · ");
        if (detail.textContent) card.appendChild(detail);
        if (["role", "education"].includes(item.record_type)) {
            const dates = document.createElement("p");
            dates.className = "resume-editor__entry-detail";
            const start = dateText(values.start_date, values.date_precision);
            const end = dateText(values.end_date, values.date_precision);
            dates.textContent = [start, values.current_role === true ? "Present" : end].filter(Boolean).join(" – ");
            if (!start && !end) dates.textContent = (values.current_role === true ? "Current role · " : "") + "Dates not supplied";
            card.appendChild(dates);
        }
        const wording = document.createElement("p");
        wording.className = "resume-editor__entry-wording";
        wording.textContent = values.summary || (heading.textContent !== values.wording ? values.wording : "") || "";
        if (wording.textContent) card.appendChild(wording);
        const editor = document.createElement("details");
        editor.className = "resume-editor__edit";
        const toggle = document.createElement("summary");
        toggle.textContent = "Edit";
        toggle.setAttribute("aria-label", "Edit " + heading.textContent);
        editor.appendChild(toggle);
        const form = document.createElement("form");
        const meta = document.createElement("p");
        meta.className = "resume-editor__meta";
        const mode = "Changes stay private until you review and publish";
        const draftLabel = item.has_draft ? "Unpublished changes saved." : "";
        meta.textContent = mode + ". " + draftLabel;
        if (item.draft_is_stale) {
            const stale = document.createElement("span");
            stale.className = "resume-editor__stale";
            stale.textContent = " This draft is stale and will not overwrite newer corrections.";
            meta.appendChild(stale);
        }
        form.appendChild(meta);

        const fields = fieldOrder[item.record_type] || Object.keys(item.values || {});
        fields.forEach(function (name) {
            const label = document.createElement("label");
            const fieldId = item.record_key + "-" + name;
            label.setAttribute("for", fieldId);
            label.textContent = name === "date_precision" ? "Date detail" : name === "current_role" ? "Current role" : name.replace(/_/g, " ");
            let field;
            if (name === "date_precision") {
                field = document.createElement("select");
                [["unknown", "Not supplied"], ["year", "Year"], ["month", "Month"], ["day", "Exact day"]]
                    .concat(item.record_type === "education" ? [["approximate", "Approximate"]] : [])
                    .forEach(function (option) { field.add(new Option(option[1], option[0])); });
            } else if (name === "summary" || name === "wording") {
                field = document.createElement("textarea");
            } else {
                field = document.createElement("input");
                field.type = name === "current_role" ? "checkbox" : "text";
                if (name === "current_role") field.style.width = "auto";
                if (["start_date", "end_date"].includes(name)) {
                    field.placeholder = "YYYY, YYYY-MM or YYYY-MM-DD";
                    field.maxLength = 10;
                }
            }
            field.id = fieldId;
            field.name = name;
            form.appendChild(label);
            form.appendChild(field);
        });
        fillForm(form, item);
        if (["role", "education"].includes(item.record_type)) {
            const hint = document.createElement("p");
            hint.textContent = "Use only the date detail you know. Leave unknown dates empty. A current role has no end date.";
            form.appendChild(hint);
            form.elements.namedItem("date_precision").addEventListener("change", function () {
                const precision = this.value;
                ["start_date", "end_date"].forEach(function (name) {
                    const field = form.elements.namedItem(name);
                    if (field.value && precision !== "unknown") field.value = dateText(field.value, precision);
                });
            });
        }

        const actions = document.createElement("p");
        actions.className = "resume-editor__toolbar";
        const save = document.createElement("button");
        save.type = "submit";
        save.className = "resume-editor__button";
        save.textContent = "Save draft";
        const discard = document.createElement("button");
        discard.type = "button";
        discard.className = "resume-editor__button resume-editor__button--quiet";
        discard.textContent = "Discard draft";
        discard.addEventListener("click", async function () {
            const result = await send(commandsUrl, {
                request_id: requestId(),
                type: "discard_item",
                record_key: item.record_key,
                record_type: item.record_type,
            });
            if (!result.response.ok) {
                setStatus(result.payload.message || "That draft could not be discarded.", "error");
                return;
            }
            await loadWorkspace();
            setStatus("Draft discarded. Canonical wording is unchanged.", "ok");
        });
        actions.appendChild(save);
        actions.appendChild(discard);
        form.appendChild(actions);
        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            await saveItem(form, item);
        });
        editor.appendChild(form);
        card.appendChild(editor);
        return card;
    }

    function renderWorkspace(payload) {
        workspace = payload;
        // Retain the live media nodes and handlers across workspace reloads.
        const experienceMedia = document.getElementById("resume-editor-experience-media");
        if (experienceMedia) root.before(experienceMedia);
        root.replaceChildren();
        const items = payload.items || [];
        const storyChoice = document.getElementById("resume-story-choice");
        if (storyChoice) {
            storyChoice.replaceChildren(new Option("No Story selected", ""));
            items.filter(item => item.record_type === "knowledge" && !item.orphaned).forEach(item => {
                storyChoice.add(new Option((item.values || {}).title || "Personal entry", item.record_key));
            });
            storyChoice.value = payload.story_entry_key || "";
        }
        const story = items.find(item => item.record_key === payload.story_entry_key && !item.orphaned);
        const storyPreview = document.getElementById("resume-editor-story-preview");
        if (storyPreview) {
            const values = story ? Object.assign({}, story.values || {}, story.proposed_values || {}) : {};
            storyPreview.textContent = values.wording || "No Story selected. Choose a saved personal entry to preview your introduction.";
        }
        const grouped = {};
        items.forEach(function (item) {
            const type = item.record_type || "role";
            grouped[type] = grouped[type] || [];
            grouped[type].push(item);
        });
        Object.keys(sectionTitles).forEach(function (type) {
            const section = document.createElement("section");
            section.className = "resume-editor__section";
            section.setAttribute("aria-labelledby", "resume-section-" + type);
            const heading = document.createElement("h2");
            heading.id = "resume-section-" + type;
            heading.textContent = sectionTitles[type];
            section.appendChild(heading);
            const records = document.createElement("div");
            records.className = "resume-editor__records";
            const rows = grouped[type] || [];
            if (!rows.length && !["role", "education", "skill"].includes(type)) return;
            if (!rows.length) {
                const empty = document.createElement("p");
                empty.className = "resume-editor__empty";
                empty.textContent = "Add your " + sectionTitles[type].toLowerCase() + " when you are ready.";
                records.appendChild(empty);
            } else {
                rows.forEach(function (item) {
                    records.appendChild(renderItem(item));
                });
            }
            section.appendChild(records);
            if (type === "role" && experienceMedia) {
                section.classList.add("resume-editor__experience-composition");
                experienceMedia.hidden = false;
                section.appendChild(experienceMedia);
            }
            root.appendChild(section);
        });
        const persistence = payload.capabilities && payload.capabilities.persistence;
        if (payload.capabilities && payload.capabilities.canonical_read === "unavailable") {
            setStatus("Canonical Resume records are unavailable. Drafts were not overwritten.", "error");
        } else if (persistence === "in_memory_not_live_db") {
            setStatus("Loaded a private workspace. This test store is not a live database.", "ok");
        } else {
            setStatus("Loaded your private Resume workspace. Nothing here is published.", "ok");
        }
    }

    async function loadWorkspace() {
        const response = await fetch(workspaceUrl, { credentials: "same-origin" });
        const payload = await response.json().catch(function () {
            return {};
        });
        if (response.status === 503) {
            setStatus(payload.message || "Resume drafts are unavailable. Your wording was not saved as published.", "error");
            return;
        }
        if (!response.ok) {
            setStatus(payload.message || "The Resume editor could not be opened.", "error");
            return;
        }
        renderWorkspace(payload);
    }

    document.getElementById("resume-editor-reload").addEventListener("click", function () {
        loadWorkspace();
    });
    document.getElementById("resume-editor-review").addEventListener("click", async function () {
        if (pendingEdit) {
            setStatus("Confirm the unresolved save before reviewing your Resume.", "error");
            return;
        }
        if (this.dataset.pageUrl) {
            window.location.assign(this.dataset.pageUrl);
            return;
        }
        const result = await send(reviewUrl, {
            request_id: requestId(),
            type: "review_candidate",
        });
        if (!result.response.ok) {
            setStatus(result.payload.message || "Review is unavailable.", "error");
            return;
        }
        setStatus("Review digest ready. Nothing was published.", "ok");
    });

    const addForm = document.getElementById("resume-editor-add-education");
    addForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const title = document.getElementById("new-education-title");
        const institution = document.getElementById("new-education-institution");
        const educationStatus = document.getElementById("new-education-status");
        const values = {
            title: title.value,
            institution_name: institution.value,
            degree_name: null,
            field_of_study: null,
            education_status: educationStatus.value,
            grade_text: null,
            location_text: null,
            summary: null,
            start_date: null,
            end_date: null,
            date_precision: "unknown",
        };
        const result = await send(commandsUrl, {
            request_id: requestId(),
            type: "create_private_item",
            record_key: requestId(),
            record_type: "education",
            values: values,
        });
        if (result.response.status === 503 || result.response.status === 409) {
            title.value = values.title;
            institution.value = values.institution_name;
            setStatus(result.payload.message || "That private record could not be saved. Your wording is still here.", "error");
            return;
        }
        if (!result.response.ok) {
            setStatus(result.payload.message || "That private record could not be saved.", "error");
            return;
        }
        addForm.reset();
        setStatus("Private education record saved. It is not shown to visitors.", "ok");
        await loadWorkspace();
    });

    const storyStatus = document.getElementById("resume-story-status");
    const storyCreate = document.getElementById("resume-story-create");
    const storySelect = document.getElementById("resume-story-select");
    async function commitStory(command, message) {
        pendingStory = pendingStory || command;
        const wording = document.getElementById("resume-story-wording");
        const choice = document.getElementById("resume-story-choice");
        wording.readOnly = true;
        choice.disabled = true;
        storySelect.disabled = true;
        storyCreate.querySelector("button").disabled = true;
        try {
            const result = await send(commandsUrl, pendingStory);
            if (result.response.status >= 500) throw new Error("uncertain");
            const created = pendingStory.type === "create_private_item";
            pendingStory = null;
            if (!result.response.ok) {
                storyStatus.textContent = result.payload.message || "The entry changed. Reload and review it again.";
                return;
            }
            if (created) wording.value = "";
            await loadWorkspace();
            storyStatus.textContent = message;
        } catch (_) {
            storyStatus.textContent = "The save could not be confirmed. Your words are preserved. Retry the same action.";
        } finally {
            wording.readOnly = Boolean(pendingStory);
            choice.disabled = Boolean(pendingStory);
            storySelect.disabled = Boolean(pendingStory && pendingStory.type === "create_private_item");
            storyCreate.querySelector("button").disabled = Boolean(pendingStory && pendingStory.type !== "create_private_item");
        }
    }
    if (storyCreate && storySelect) {
        storyCreate.addEventListener("submit", async function (event) {
            event.preventDefault();
            await commitStory({type: "create_private_item", request_id: requestId(), record_key: requestId(),
                record_type: "knowledge", values: {title: "My Story", wording: document.getElementById("resume-story-wording").value, classification: "personal"}},
                "Saved privately. Choose the entry above to use it for My Story.");
        });
        storySelect.addEventListener("click", async function () {
            if (!workspace) return;
            const key = document.getElementById("resume-story-choice").value;
            const item = workspace.items.find(row => row.record_key === key);
            if (key && !item) return;
            await commitStory({type: key ? "bind_story" : "clear_story", request_id: requestId(), record_key: key || null,
                expected_draft_version: workspace.draft_version, expected_content_token: item ? item.content_token : null,
                expected_access_revision: item ? item.access_revision : null},
                key ? "Selected for your private Resume draft. Review display and visitor AI before publishing." : "Removed from your private Resume draft. The saved entry is kept.");
        });
    }

    loadWorkspace();
})();
