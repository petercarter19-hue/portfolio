/* Descriptive-field dictation stays in the owner editor. It never submits a
 * form or creates source/canonical facts. Each session owns one exact field;
 * canceled, detached, revised or repeated results cannot reach another field. */
(function () {
    let active = null;
    let generation = 0;
    function stop() {
        generation += 1;
        const session = active; active = null;
        if (!session) return;
        clearTimeout(session.timer);
        if (session.recognition) { try { session.recognition.abort(); } catch (_) {} }
        session.button.textContent = 'Dictate'; session.button.setAttribute('aria-pressed', 'false');
        session.cancel.hidden = true; session.message.textContent = '';
    }
    function bind(field, label, announce) {
        if (field.dataset.resumeVoiceBound) return;
        field.dataset.resumeVoiceBound = 'true';
        const controls = document.createElement('div'); controls.className = 'resume-field-voice';
        const button = document.createElement('button'); button.type = 'button'; button.textContent = 'Dictate';
        button.className = 'resume-intake__quiet resume-editor__button resume-editor__button--quiet';
        button.setAttribute('aria-label', 'Dictate ' + label); button.setAttribute('aria-pressed', 'false');
        const cancel = document.createElement('button'); cancel.type = 'button'; cancel.textContent = 'Cancel dictation'; cancel.hidden = true;
        cancel.className = button.className;
        const message = document.createElement('span'); message.setAttribute('role', 'status');
        const supported = Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
        button.disabled = !supported;
        if (!supported) message.textContent = 'Dictation is unavailable in this browser. You can type here.';
        controls.append(button, cancel, message); field.after(controls);
        function eligible(session) {
            const modal = document.querySelector('dialog[open]');
            return active === session && session.generation === generation && field.isConnected &&
                !field.disabled && !field.readOnly && field.getClientRects().length > 0 && (!modal || modal.contains(field));
        }
        function arm(session) { clearTimeout(session.timer); session.timer = setTimeout(stop, 10000); }
        button.addEventListener('click', async function () {
            if (active && active.field === field) { stop(); return; }
            stop();
            if (!supported || field.disabled || field.readOnly || !field.getClientRects().length) return;
            const session = {field, button, cancel, message, generation: generation, finalIndexes: new Set(), inserting: false};
            active = session; cancel.hidden = false; message.textContent = 'Requesting microphone access…';
            arm(session);
            try {
                if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                    const stream = await navigator.mediaDevices.getUserMedia({audio:true, video:false});
                    stream.getTracks().forEach(track => track.stop());
                }
                if (!eligible(session)) return;
                const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                const recognition = session.recognition = new Recognition();
                recognition.lang = document.documentElement.lang || 'en-US';
                recognition.continuous = true; recognition.interimResults = true;
                recognition.onresult = function (event) {
                    if (!eligible(session)) { if (active === session) stop(); return; }
                    let interim = '';
                    for (let index = event.resultIndex; index < event.results.length; index += 1) {
                        const result = event.results[index]; const words = (result[0] || {}).transcript || '';
                        if (result.isFinal && !session.finalIndexes.has(index)) {
                            session.finalIndexes.add(index); session.inserting = true;
                            try { window.PeerSlateDictation.appendTranscript(field, words); } finally { session.inserting = false; }
                        } else if (!result.isFinal) interim += words;
                    }
                    message.textContent = interim || 'Listening. Stop or cancel when finished; stops after 10 seconds of silence.';
                    arm(session);
                };
                recognition.onerror = function (event) {
                    if (!eligible(session)) return;
                    const text = window.PeerSlateDictation.friendlySpeechError(event.error);
                    stop(); message.textContent = text; if (announce) announce(text, 'error');
                };
                recognition.onend = function () { if (active === session) stop(); };
                button.textContent = 'Stop dictation'; button.setAttribute('aria-pressed', 'true');
                message.textContent = 'Listening. Review your words before saving.'; arm(session); recognition.start();
            } catch (_) {
                if (active !== session) return;
                stop(); message.textContent = 'Microphone access is unavailable. You can keep typing.';
            }
        });
        cancel.addEventListener('click', stop);
        field.addEventListener('input', function () { if (active && active.field === field && !active.inserting) stop(); });
    }
    document.addEventListener('focusin', function (event) {
        if (active && event.target.matches('input,textarea,select') && event.target !== active.field) stop();
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') stop(); });
    document.addEventListener('submit', stop, true);
    document.addEventListener('toggle', function () {
        if (active && (!active.field.isConnected || !active.field.getClientRects().length)) stop();
    }, true);
    window.addEventListener('pagehide', stop);
    window.PeerSlateResumeFieldVoice = {bind, stop};
})();
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
        credential: ["name", "issuer", "completion_status", "identifier", "issue_date", "issue_date_precision", "expiration_date", "expiration_date_precision"],
        skill: ["name", "summary"],
        accomplishment: ["wording", "metric_value", "metric_label"],
        knowledge: ["title", "wording"],
    };
    const sectionTitles = {
        role: "Experience",
        education: "Education",
        credential: "Credentials",
        skill: "Skills",
        accomplishment: "Impact",
        knowledge: "Private entries",
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
        if (url === commandsUrl && response.ok && payload.success === true &&
            ['save_item', 'discard_item', 'create_private_item', 'bind_story', 'clear_story'].includes(body.type)) {
            document.dispatchEvent(new Event('resume-private-draft-changed'));
        }
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
        if (recordType === 'credential') {
            ['issue_date', 'expiration_date'].forEach(function (name) {
                const raw = String(merged[name] || '').trim();
                if (!raw) { merged[name] = null; delete merged[name + '_precision']; return; }
                const precision = merged[name + '_precision'] || ({4: 'year', 7: 'month', 10: 'day'})[raw.length];
                const pattern = {year: /^\d{4}$/, month: /^\d{4}-\d{2}$/, day: /^\d{4}-\d{2}-\d{2}$/}[precision];
                if (!pattern || !pattern.test(raw)) throw new Error('Use YYYY, YYYY-MM or YYYY-MM-DD to match the credential date detail.');
                merged[name] = raw + (precision === 'year' ? '-01-01' : precision === 'month' ? '-01' : '');
                if (precision === 'day') delete merged[name + '_precision'];
                else merged[name + '_precision'] = precision;
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
        } else if (['issue_date', 'expiration_date'].includes(field.name)) field.value = dateText(value, source[field.name + '_precision'] || 'day');
        else field.value = value == null ? "" : value;
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
        if (item.record_type === 'credential') {
            const dates = document.createElement('p'); dates.className = 'resume-editor__entry-detail';
            dates.textContent = ['issue_date', 'expiration_date'].filter(function (name) { return values[name]; }).map(function (name) {
                return (name === 'issue_date' ? 'Issued ' : 'Expires ') + dateText(values[name], values[name + '_precision'] || 'day');
            }).join(' · ');
            if (dates.textContent) card.appendChild(dates);
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
            if (name === 'issue_date_precision' || name === 'expiration_date_precision') {
                field = document.createElement('select');
                [['', 'From supplied date'], ['year', 'Year'], ['month', 'Month'], ['day', 'Exact day']].forEach(function (option) { field.add(new Option(option[1], option[0])); });
            } else if (name === "date_precision") {
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
            if (field.tagName === 'TEXTAREA') window.PeerSlateResumeFieldVoice.bind(field, label.textContent, setStatus);
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
        window.PeerSlateResumeFieldVoice.stop();
        workspace = payload;
        refreshAssistanceTargets();
        // Retain the live media nodes and handlers across workspace reloads.
        const experienceMedia = document.getElementById("resume-editor-experience-media");
        if (experienceMedia) root.before(experienceMedia);
        root.replaceChildren();
        const items = payload.items || [];
        const storyChoice = document.getElementById("resume-story-choice");
        if (storyChoice) {
            storyChoice.replaceChildren(new Option("No Story selected", ""));
            items.filter(item => item.record_type === "knowledge" && !item.orphaned &&
                Object.assign({}, item.values || {}, item.proposed_values || {}).classification === 'personal').forEach(item => {
                const values = Object.assign({}, item.values || {}, item.proposed_values || {});
                storyChoice.add(new Option(values.title || "Personal entry", item.record_key));
            });
            storyChoice.value = payload.story_entry_key || "";
        }
        const story = items.find(item => item.record_key === payload.story_entry_key && !item.orphaned &&
            Object.assign({}, item.values || {}, item.proposed_values || {}).classification === 'personal');
        const storyPreview = document.getElementById("resume-editor-story-preview");
        if (storyPreview) {
            const values = story ? Object.assign({}, story.values || {}, story.proposed_values || {}) : {};
            storyPreview.textContent = values.wording ? ((values.title || 'My Story') + '\n' + values.wording) :
                "No Story selected. Choose a saved personal entry to preview your introduction.";
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

    let displayedFormState = '';
    function editorFormState() {
        return JSON.stringify(Array.from(root.querySelectorAll('input, textarea, select'))
            .concat(Array.from(document.querySelectorAll('#resume-story-choice')))
            .map(function (field) { return [field.id, field.type === 'checkbox' ? field.checked : field.value]; }));
    }
    function hasUnresolvedEditorChanges() {
        return pendingEdit || editInFlight || pendingStory || editorFormState() !== displayedFormState;
    }
    async function loadWorkspace(preserveEdits) {
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
        if (preserveEdits && hasUnresolvedEditorChanges()) {
            setStatus("Fact saved privately. Your unsaved edits are kept; reload after saving them to see the new entry.", "ok");
            return;
        }
        renderWorkspace(payload);
        displayedFormState = editorFormState();
    }

    document.addEventListener('resume-intake-fact-saved', function () {
        if (hasUnresolvedEditorChanges()) {
            setStatus("Fact saved privately. Your unsaved edits are kept; reload after saving them to see the new entry.", "ok");
            return;
        }
        loadWorkspace(true);
    });
    document.addEventListener('resume-private-draft-changed', function (event) {
        const receipt = event.detail;
        // A confirmed media-only mutation leaves text/source bindings intact.
        // Advance only our exact matching baseline from its actual receipt;
        // never realign an older/different workspace or an unresolved command.
        if (workspace && receipt && receipt.source === 'media' &&
            Number.isInteger(receipt.draftVersion) && Number.isInteger(receipt.previousDraftVersion) &&
            receipt.draftVersion === receipt.previousDraftVersion + 1 &&
            workspace.draft_version === receipt.previousDraftVersion) {
            workspace.draft_version = receipt.draftVersion;
        }
    });
    document.getElementById("resume-editor-reload").addEventListener("click", function () {
        loadWorkspace();
    });
    document.getElementById("resume-editor-review").addEventListener("click", async function () {
        if (pendingEdit) {
            setStatus("Confirm the unresolved save before reviewing your Resume.", "error");
            return;
        }
        if (this.dataset.pageUrl) {
            window.location.assign(this.dataset.pageUrl + '?preview=private');
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
    const storyWords = document.getElementById('resume-story-wording');
    if (storyWords) window.PeerSlateResumeFieldVoice.bind(storyWords, 'My Story words', setStatus);
    const storySelect = document.getElementById("resume-story-select");
    async function commitStory(command, message) {
        window.PeerSlateResumeFieldVoice.stop();
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

    const assistance = document.getElementById("resume-private-assistance");
    const synthesisForm = document.getElementById("resume-synthesis-form");
    const synthesisTarget = document.getElementById("resume-synthesis-target");
    const confirmWording = document.getElementById("resume-synthesis-confirm");
    const assistanceStatus = document.getElementById("resume-private-assistance-status");
    let synthesisProposal = null;
    let assistanceBusy = false;

    function refreshAssistanceTargets() {
        if (!synthesisTarget) return;
        const selected = synthesisTarget.value;
        synthesisTarget.replaceChildren(new Option("Preview only", ""));
        const prose = {role: "summary", education: "summary", skill: "summary", accomplishment: "wording", knowledge: "wording"};
        (workspace.items || []).forEach(function (item) {
            const field = prose[item.record_type];
            if (!field || item.orphaned || item.draft_is_stale || (!item.editable && item.save_mode !== "draft_overlay")) return;
            const values = item.proposed_values || item.values || {};
            const title = values.role_title || values.title || values.name || values.wording || item.record_type;
            synthesisTarget.add(new Option(String(title).slice(0, 90) + " · " + field, JSON.stringify({record_key: item.record_key, field: field})));
        });
        synthesisTarget.value = selected;
        synthesisProposal = null;
        if (confirmWording) confirmWording.disabled = true;
    }

    async function assistanceRequest(url, body) {
        if (assistanceBusy) return null;
        assistanceBusy = true;
        assistance.querySelectorAll("button, input, textarea, select").forEach(control => { control.disabled = true; });
        assistanceStatus.textContent = "Preparing a private proposal…";
        try {
            const result = await send(url, body);
            if (!result.response.ok) {
                assistanceStatus.textContent = result.payload.message || "Private assistance is unavailable. Your words and manual editor remain available.";
                return null;
            }
            assistanceStatus.textContent = "Private proposal only. Review it before saving anything.";
            return result.payload;
        } catch (_) {
            // Never automatically retry an uncertain paid dispatch.
            assistanceStatus.textContent = "The response could not be confirmed. Your words are preserved; use the manual editor.";
            return null;
        } finally {
            assistanceBusy = false;
            assistance.querySelectorAll("button, input, textarea, select").forEach(control => { control.disabled = false; });
            if (confirmWording) confirmWording.disabled = !synthesisProposal || !synthesisProposal.target;
        }
    }

    if (synthesisForm) {
        synthesisTarget.addEventListener("change", function () {
            synthesisProposal = null;
            confirmWording.disabled = true;
        });
        synthesisForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            if (!workspace || pendingEdit || editInFlight || pendingStory) return;
            const target = synthesisTarget.value ? JSON.parse(synthesisTarget.value) : null;
            synthesisProposal = null;
            const payload = await assistanceRequest(assistance.dataset.synthesisUrl, {
                request_id: requestId(), expected_draft_version: workspace.draft_version,
                task: document.getElementById("resume-synthesis-task").value,
                selected_targets: target ? [target] : [],
            });
            if (!payload) return;
            synthesisProposal = {proof: payload.proof, target: target};
            document.getElementById("resume-synthesis-text").textContent = payload.proposal.resume_text;
            document.getElementById("resume-synthesis-uncertainties").textContent = payload.proposal.uncertainties.join(" · ");
            document.getElementById("resume-synthesis-wording").value = "";
            document.getElementById("resume-synthesis-preview").hidden = false;
            confirmWording.disabled = !target;
        });
        confirmWording.addEventListener("click", async function () {
            if (!synthesisProposal || !synthesisProposal.target || pendingEdit || editInFlight || pendingStory) return;
            const payload = await assistanceRequest(assistance.dataset.confirmUrl, {
                proof: synthesisProposal.proof, record_key: synthesisProposal.target.record_key,
                field: synthesisProposal.target.field, confirm: true,
                confirmed_text: document.getElementById("resume-synthesis-wording").value,
            });
            if (!payload) return;
            synthesisProposal = null;
            document.dispatchEvent(new Event('resume-private-draft-changed'));
            await loadWorkspace();
            assistanceStatus.textContent = "Selected wording saved privately. It has not been published.";
        });
    }
    const careerForm = document.getElementById("resume-career-interview-form");
    if (careerForm) careerForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (!workspace) return;
        const payload = await assistanceRequest(assistance.dataset.interviewUrl, {
            request_id: requestId(), expected_draft_version: workspace.draft_version,
            statement: document.getElementById("resume-career-interview-statement").value,
            selected_target: null, source_keys: [],
        });
        if (!payload) return;
        document.getElementById("resume-career-interview-response").textContent = payload.response;
        document.getElementById("resume-career-interview-question").textContent = payload.next_question;
        const candidates = document.getElementById("resume-career-interview-candidates");
        candidates.replaceChildren();
        (payload.proposals || payload.candidates || []).forEach(function (candidate) {
            const row = document.createElement("li");
            row.textContent = candidate.record_type + ": " + candidate.quote;
            candidates.appendChild(row);
        });
        document.getElementById("resume-career-interview-preview").hidden = false;
    });

    loadWorkspace();
})();
