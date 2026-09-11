(function () {
    const root = document.getElementById("resume-editor-lists");
    const status = document.getElementById("resume-editor-status");
    if (!root) {
        return;
    }

    const workspaceUrl = root.getAttribute("data-workspace-url");
    const commandsUrl = root.getAttribute("data-commands-url");
    const reviewUrl = root.getAttribute("data-review-url");
    const fieldOrder = {
        role: ["role_title", "employer_name", "summary", "location_text"],
        education: ["title", "institution_name", "field_of_study", "education_status", "summary"],
        credential: ["name", "issuer", "completion_status", "identifier"],
        skill: ["name", "summary"],
        accomplishment: ["wording", "metric_value", "metric_label"],
    };
    const sectionTitles = {
        role: "Experience",
        education: "Education",
        credential: "Credentials",
        skill: "Skills",
        accomplishment: "Impact",
    };

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
                merged[name] = field.value;
            }
        });
        return merged;
    }

    function fillForm(form, item) {
        const source = Object.assign({}, item.values || {}, item.proposed_values || {});
        Object.keys(source).forEach(function (name) {
            const field = form.elements.namedItem(name);
            if (field && source[name] != null) {
                field.value = source[name];
            }
        });
    }

    function preserveFromError(form, payload) {
        const proposed = payload.proposed_values;
        if (!proposed) {
            return;
        }
        Object.keys(proposed).forEach(function (name) {
            const field = form.elements.namedItem(name);
            if (field && proposed[name] != null) {
                field.value = proposed[name];
            }
        });
    }

    async function saveItem(form, item) {
        const proposed = valuesFromForm(form, item);
        const result = await send(commandsUrl, {
            request_id: requestId(),
            type: "save_item",
            record_key: item.record_key,
            record_type: item.record_type,
            expected_content_token: item.content_token,
            expected_access_revision: item.access_revision,
            values: proposed,
        });
        if (result.response.status === 409 || result.response.status === 503) {
            preserveFromError(form, result.payload);
            setStatus(result.payload.message || "That save could not be applied. Your wording is still here.", "error");
            return;
        }
        if (!result.response.ok) {
            setStatus(result.payload.message || "That save could not be applied.", "error");
            return;
        }
        setStatus("Draft saved. Sharing did not change.", "ok");
        await loadWorkspace();
    }

    function renderItem(item) {
        const card = document.createElement("article");
        card.className = "resume-editor__card";
        const form = document.createElement("form");
        const meta = document.createElement("p");
        meta.className = "resume-editor__meta";
        const mode = item.save_mode === "canonical" ? "Private record" : "Draft overlay for a shared or history-bearing record";
        const draftLabel = item.has_draft ? "Has unpublished draft wording." : "No draft overlay yet.";
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
            label.textContent = name.replace(/_/g, " ");
            let field;
            if (name === "summary" || name === "wording") {
                field = document.createElement("textarea");
            } else {
                field = document.createElement("input");
                field.type = "text";
            }
            field.id = fieldId;
            field.name = name;
            form.appendChild(label);
            form.appendChild(field);
        });
        fillForm(form, item);

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
            setStatus("Draft discarded. Canonical wording is unchanged.", "ok");
            await loadWorkspace();
        });
        actions.appendChild(save);
        actions.appendChild(discard);
        form.appendChild(actions);
        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            await saveItem(form, item);
        });
        card.appendChild(form);
        return card;
    }

    function renderWorkspace(payload) {
        root.replaceChildren();
        const items = payload.items || [];
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
            const rows = grouped[type] || [];
            if (!rows.length) {
                const empty = document.createElement("p");
                empty.className = "resume-editor__empty";
                empty.textContent = "No " + sectionTitles[type].toLowerCase() + " records yet.";
                section.appendChild(empty);
            } else {
                rows.forEach(function (item) {
                    section.appendChild(renderItem(item));
                });
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

    loadWorkspace();
})();
