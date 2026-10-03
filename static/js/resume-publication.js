(function () {
    const root = document.getElementById("resume-publication-review");
    if (!root) {
        return;
    }
    const status = document.getElementById("resume-publication-status");
    const digestNode = document.getElementById("resume-publication-digest");
    const slugInput = document.getElementById("resume-publication-slug");
    const reviewButton = document.getElementById("resume-publication-review-button");
    const publishButton = document.getElementById("resume-publication-publish-button");
    const sharingOffButton = document.getElementById("resume-publication-sharing-off-button");
    const previewButton = document.getElementById("resume-publication-preview-button");
    const previewRegion = document.getElementById("resume-private-preview");
    const previewContent = document.getElementById("resume-private-preview-content");
    const previewClose = document.getElementById("resume-private-preview-close");
    const reviewUrl = root.getAttribute("data-review-url");
    const commandsUrl = root.getAttribute("data-commands-url");
    const previewUrl = root.getAttribute("data-preview-url");
    const entriesNode = document.getElementById("resume-publication-entries");
    let reviewedDigest = null;
    let reviewedIdentity = null;
    let reviewedCandidate = null;
    let pendingPublish = null;
    let inFlight = false;
    const privateMode = new URLSearchParams(window.location.search).get('preview') === 'private';
    if (privateMode) {
        document.getElementById('resume-publication-title').textContent = 'Preview my Resume privately';
        document.getElementById('resume-publication-review-title').textContent = 'Your private draft';
        slugInput.closest('p').hidden = true;
        publishButton.hidden = true;
        sharingOffButton.hidden = true;
        const privateNotice = document.createElement('p');
        privateNotice.textContent = 'These selections are for this private preview. Your saved sharing choices stay unchanged.';
        root.prepend(privateNotice);
        const sharingLink = document.createElement('a');
        sharingLink.href = window.location.pathname;
        sharingLink.textContent = 'Review sharing choices';
        root.appendChild(sharingLink);
    }

    function hidePreview(returnFocus) {
        previewRegion.hidden = true;
        previewContent.replaceChildren();
        if (returnFocus) previewButton.focus();
    }
    previewClose.addEventListener("click", function () { hidePreview(true); });
    previewRegion.addEventListener("keydown", function (event) {
        if (event.key === "Escape") { event.preventDefault(); hidePreview(true); }
    });

    function choices() {
        return Array.from(entriesNode.querySelectorAll("[data-entry-key]")).map(function (row) {
            return { entry_key: row.dataset.entryKey,
                resume_display: row.querySelector('[data-permission="resume_display"]').checked,
                visitor_ai: row.querySelector('[data-permission="visitor_ai"]').checked };
        });
    }

    function textElement(tag, value, parent) {
        const node = document.createElement(tag);
        node.textContent = value == null ? "Not set" : String(value);
        parent.appendChild(node);
        return node;
    }

    function reviewValue(field, value, values) {
        if (["start_date", "end_date"].includes(field)) {
            const precision = values.date_precision;
            if (!value || !precision || precision === "unknown") return null;
            return String(value).slice(0, precision === "year" ? 4 : precision === "month" ? 7 : 10);
        }
        if (["issue_date", "expiration_date"].includes(field) && value) {
            const precision = values[field + '_precision'] || 'day';
            return String(value).slice(0, precision === 'year' ? 4 : precision === 'month' ? 7 : 10);
        }
        if (field === "date_precision") return {unknown:"Not supplied",year:"Year",month:"Month",day:"Exact day",approximate:"Approximate"}[value] || value;
        if (field === "current_role" && typeof value === "boolean") return value ? "Current role" : "Past role";
        return value;
    }

    function renderEntries(entries) {
        entriesNode.replaceChildren();
        entries.forEach(function (entry) {
            const section = document.createElement("section");
            section.className = "resume-publication__review-entry";
            section.dataset.entryKey = entry.entry_key;
            textElement("h3", entry.title, section);
            const wording = entry.after || {};
            Object.keys(wording).forEach(function (field) {
                const value = reviewValue(field, wording[field], wording);
                if (value !== null && value !== "") {
                    const line = document.createElement("p");
                    textElement("strong", (field === "date_precision" ? "date detail" : field.replaceAll("_", " ")) + ": ", line);
                    textElement("span", value, line);
                    section.appendChild(line);
                }
            });
            if (entry.changes && entry.changes.length) {
                const changes = document.createElement("details");
                textElement("summary", privateMode ? "Draft wording in this preview" : "Wording changes to save when you publish", changes);
                entry.changes.forEach(function (change) {
                    const line = document.createElement("p");
                    textElement("strong", change.field.replaceAll("_", " ") + ": ", line);
                    textElement("del", reviewValue(change.field, change.before, entry.before || {}), line);
                    textElement("span", " → ", line);
                    textElement("ins", reviewValue(change.field, change.after, wording), line);
                    changes.appendChild(line);
                });
                section.appendChild(changes);
            }
            const fieldset = document.createElement("fieldset");
            textElement("legend", privateMode ? "Include in this private preview" : "Choose each use independently", fieldset);
            [["resume_display", "Show on my Resume"], ["visitor_ai", "Allow visitor AI to use this"]].forEach(function (item) {
                const label = document.createElement("label");
                const input = document.createElement("input");
                input.type = "checkbox";
                input.dataset.permission = item[0];
                input.checked = entry[item[0]] === true;
                if (privateMode && item[0] === 'visitor_ai') { input.checked = false; label.hidden = true; }
                input.addEventListener("change", function () {
                    reviewedDigest = null;
                    reviewedCandidate = null;
                    publishButton.disabled = true;
                    previewButton.disabled = false;
                    hidePreview(false);
                    digestNode.hidden = true;
                    setStatus(privateMode ? "Preview again to see your updated selection. Your saved choices stay unchanged." : "Review your updated sharing choices before publishing.");
                });
                label.appendChild(input);
                label.appendChild(document.createTextNode(" " + (privateMode && item[0] === 'resume_display' ? 'Include in this preview' : item[1])));
                fieldset.appendChild(label);
            });
            section.appendChild(fieldset);
            entriesNode.appendChild(section);
        });
        if (!entries.length) textElement("p", "No saved entries yet. Add information in your Resume or My Data.", entriesNode);
    }

    function lockChoices(locked) {
        entriesNode.querySelectorAll("input").forEach(function (input) { input.disabled = locked; });
    }

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
        return { ok: response.ok, status: response.status, payload: payload };
    }

    async function reviewCurrent(previewAfterReview) {
        if (inFlight || pendingPublish) {
            return;
        }
        inFlight = true;
        publishButton.disabled = true;
        previewButton.disabled = true;
        hidePreview(false);
        lockChoices(true);
        setStatus("Reviewing current facts. This does not publish.", "ok");
        try {
            const selected = choices();
            let result = await send(reviewUrl, selected.length ? {entries: selected} : {});
            if (privateMode && !selected.length && result.ok && Array.isArray(result.payload.entries)) {
                renderEntries(result.payload.entries.map(function (entry) {
                    return Object.assign({}, entry, {resume_display: true, visitor_ai: false});
                }));
                result = await send(reviewUrl, {entries: choices()});
            }
            if (!result.ok || !result.payload.digest) {
                reviewedDigest = null;
                digestNode.hidden = true;
                setStatus(result.payload.message || "Review could not finish.", "error");
                return;
            }
            reviewedDigest = result.payload.digest;
            reviewedIdentity = result.payload.profile_identity || null;
            reviewedCandidate = result.payload.candidate;
            renderEntries(result.payload.entries || []);
            digestNode.hidden = false;
            digestNode.textContent =
                (result.payload.identity_display_name ? "Name: " + result.payload.identity_display_name + ". " : "No public name selected. ") +
                (privateMode ? String(result.payload.display_count || 0) + " entries in this private preview. Nothing is published." :
                String(result.payload.display_count || 0) + " entries shown on your Resume. " +
                String(result.payload.visitor_ai_count || 0) + " entries available to visitor AI.");
            publishButton.disabled = false;
            previewButton.disabled = false;
            setStatus(
                privateMode ? 'Your private preview choices are ready.' : "Your information and sharing choices are ready to review. Publish when you are ready to share them.",
                "ok"
            );
        } catch (error) {
            reviewedDigest = null;
            setStatus("Review could not finish. Your saved information is unchanged; try again.", "error");
        } finally {
            inFlight = false;
            lockChoices(false);
            previewButton.disabled = false;
        }
        if (previewAfterReview === true && reviewedDigest) await previewCurrent();
    }
    reviewButton.addEventListener('click', function () { reviewCurrent(false); });

    async function previewCurrent() {
        if (inFlight || pendingPublish) return;
        if (!reviewedDigest || !reviewedCandidate) { await reviewCurrent(true); return; }
        inFlight = true;
        previewButton.disabled = true;
        publishButton.disabled = true;
        lockChoices(true);
        hidePreview(false);
        setStatus("Checking the current private draft for your preview. Nothing is published.");
        try {
            const result = await send(previewUrl, {
                candidate: reviewedCandidate, reviewed_digest: reviewedDigest,
                profile_identity: reviewedIdentity,
            });
            if (!result.ok || !result.payload.html || result.payload.digest !== reviewedDigest) {
                reviewedDigest = null;
                reviewedCandidate = null;
                digestNode.hidden = true;
                setStatus(result.payload.message || "Your draft changed. Review it again before previewing.", "error");
                return;
            }
            // Escaped server rendering reuses the approved composition. Import
            // only its content section; navigation/scripts are never executed.
            const documentPreview = new DOMParser().parseFromString(result.payload.html, "text/html");
            const composition = documentPreview.querySelector(".resume-publication--public");
            if (!composition) throw new Error("Preview composition unavailable");
            if (privateMode) {
                composition.querySelectorAll('#visitor-ai-panel, #visitor-ai-open').forEach(function (element) { element.remove(); });
                composition.classList.remove('resume-publication--with-ai');
            }
            previewContent.replaceChildren(document.importNode(composition, true));
            previewRegion.hidden = false;
            const heading = previewContent.querySelector("#resume-preview-title");
            if (heading) heading.focus();
            setStatus("Private draft preview ready. Nothing was published; saved sharing choices are unchanged.");
        } catch (error) {
            hidePreview(false);
            setStatus("The private preview could not finish. Your saved information is unchanged. Try again.", "error");
        } finally {
            inFlight = false;
            lockChoices(false);
            previewButton.disabled = false;
            publishButton.disabled = !reviewedDigest;
        }
    }
    previewButton.addEventListener('click', previewCurrent);
    if (privateMode) previewCurrent();

    publishButton.addEventListener("click", async function () {
        if (inFlight || !reviewedDigest) {
            return;
        }
        const slug = pendingPublish ? pendingPublish.slug : (slugInput.value || "").trim();
        if (!slug || slug.toLowerCase() === "petec") {
            setStatus("Choose an available public address for your Resume.", "error");
            return;
        }
        inFlight = true;
        try {
            if (!pendingPublish) pendingPublish = {
                type: "publish",
                request_id: requestId(),
                reviewed_digest: reviewedDigest,
                profile_identity: reviewedIdentity,
                candidate: reviewedCandidate,
                slug: slug,
            };
            slugInput.disabled = true;
            reviewButton.disabled = true;
            lockChoices(true);
            const result = await send(commandsUrl, pendingPublish);
            if (!result.ok) {
                if (result.status >= 400 && result.status < 500 && result.status !== 408 && result.status !== 429) {
                    pendingPublish = null;
                    reviewedDigest = null;
                    publishButton.disabled = true;
                    slugInput.disabled = false;
                    reviewButton.disabled = false;
                    lockChoices(false);
                }
                setStatus(result.payload.message || "Publish could not finish.", "error");
                return;
            }
            pendingPublish = null;
            publishButton.disabled = true;
            slugInput.disabled = false;
            reviewButton.disabled = false;
            lockChoices(false);
            const availability = result.payload.availability || {};
            setStatus(availability.state !== "current"
                ? "Publish recorded. The current sharing status could not be checked; refresh to check it."
                : availability.sharing_enabled
                    ? "Published. Your Resume is currently shared."
                    : "Publish recorded. Sharing is currently off.", "ok");
        } catch (error) {
            setStatus("The publish response was interrupted. Retry Publish to check the same request safely.", "error");
        } finally {
            inFlight = false;
        }
    });

    sharingOffButton.addEventListener("click", async function () {
        if (inFlight) {
            return;
        }
        inFlight = true;
        try {
            const result = await send(commandsUrl, {
                type: "sharing_off",
                request_id: requestId(),
            });
            if (!result.ok) {
                setStatus(result.payload.message || "Sharing could not be turned off.", "error");
                return;
            }
            setStatus("Sharing is off. The public page is unavailable.", "ok");
        } finally {
            inFlight = false;
        }
    });
})();

(function () {
    const panel = document.getElementById("visitor-ai-panel");
    if (new URLSearchParams(window.location.search).get('preview') === 'private') {
        if (panel) panel.hidden = true;
        const visitorOpener = document.getElementById('visitor-ai-open');
        if (visitorOpener) visitorOpener.hidden = true;
        return;
    }
    if (!panel) return;
    const opener = document.getElementById("visitor-ai-open");
    const closer = document.getElementById("visitor-ai-close");
    const form = document.getElementById("visitor-ai-form");
    const question = document.getElementById("visitor-ai-question");
    const ask = document.getElementById("visitor-ai-ask");
    const status = document.getElementById("visitor-ai-status");
    const answer = document.getElementById("visitor-ai-answer");
    const choices = document.getElementById("visitor-ai-choices");
    const mobile = window.matchMedia("(max-width: 900px)");
    let draftRevision = null;
    let busy = false;
    let generation = 0;
    panel.classList.add("visitor-ai--enhanced");

    function layout() {
        panel.close();
        if (!mobile.matches) panel.show();
    }
    layout();
    mobile.addEventListener("change", layout);
    opener.addEventListener("click", function () {
        if (!panel.open) {
            if (mobile.matches) panel.showModal();
            else panel.show();
        }
        question.focus();
    });
    closer.addEventListener("click", function () { panel.close(); opener.focus(); });
    panel.addEventListener("close", function () { if (!panel.open) opener.focus(); });

    function message(text, failed) {
        status.textContent = text;
        status.dataset.kind = failed ? "error" : "ok";
    }
    function clearAnswer() { answer.replaceChildren(); generation += 1; }
    function textNode(tag, text) {
        const node = document.createElement(tag);
        node.textContent = text;
        return node;
    }

    async function refreshChoices() {
        clearAnswer();
        draftRevision = null;
        ask.disabled = true;
        const oldLegend = choices.querySelector("legend");
        choices.replaceChildren(oldLegend);
        message("Loading your saved information…", false);
        try {
            const response = await fetch(panel.dataset.choicesUrl, { credentials: "same-origin", cache: "no-store" });
            const body = await response.json();
            if (!response.ok || !Number.isInteger(body.draft_revision) || !Array.isArray(body.choices)) throw new Error();
            draftRevision = body.draft_revision;
            body.choices.forEach(function (item) {
                const label = document.createElement("label");
                const input = document.createElement("input");
                input.type = "checkbox";
                input.value = item.entry_key;
                input.checked = item.selected === true;
                label.append(input, document.createTextNode(item.label));
                choices.append(label);
            });
            ask.disabled = busy;
            message("Choose saved information, then try a question. Nothing is published.", false);
        } catch (_) {
            message("Your preview choices are unavailable. Refresh choices to try again. Your question is still here.", true);
        }
    }

    if (choices) {
        document.getElementById("visitor-ai-refresh").addEventListener("click", refreshChoices);
        choices.addEventListener("change", function () {
            clearAnswer();
            message("Preview choices changed. Ask again to use these choices.", false);
        });
        refreshChoices();
    } else {
        ask.disabled = false;
    }

    function renderResult(body) {
        if (body.state !== "supported") {
            message(body.text || "Answers are temporarily unavailable. Your question is still here.", true);
            return;
        }
        const entry = document.createElement("details");
        entry.open = true;
        entry.append(textNode("summary", body.question), textNode("p", body.text));
        (body.citations || []).forEach(function (citation) {
            const url = new URL(citation.url, window.location.origin);
            if (url.origin !== window.location.origin || !url.pathname.startsWith("/api/")) return;
            const link = textNode("a", "View source excerpt");
            link.href = url.href;
            link.className = "visitor-ai__citation";
            const excerpt = document.createElement("blockquote");
            excerpt.hidden = true;
            excerpt.setAttribute("aria-live", "polite");
            link.addEventListener("click", async function (event) {
                event.preventDefault();
                excerpt.hidden = false;
                excerpt.textContent = "Checking this source…";
                try {
                    const response = await fetch(url.href, { credentials: "same-origin", cache: "no-store" });
                    const source = await response.json();
                    excerpt.textContent = response.ok ? source.excerpt : "This source excerpt is unavailable.";
                } catch (_) {
                    excerpt.textContent = "This source excerpt is unavailable. Try again when your connection returns.";
                }
            });
            entry.append(link, excerpt);
        });
        answer.append(entry);
        message("Answer complete.", false);
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (busy || !question.value.trim() || (choices && draftRevision === null)) return;
        clearAnswer();
        const submittedGeneration = generation;
        const body = { question: question.value };
        if (choices) {
            body.draft_revision = draftRevision;
            body.choices = Array.from(choices.querySelectorAll("input")).map(function (input) {
                return { entry_key: input.value, selected: input.checked };
            });
        }
        busy = true;
        ask.disabled = true;
        form.setAttribute("aria-busy", "true");
        message("Checking the permitted information…", false);
        try {
            const response = await fetch(panel.dataset.questionUrl, {
                method: "POST", credentials: "same-origin", cache: "no-store",
                headers: { "Content-Type": "application/json", "X-PeerSlate-Request": "same-origin" },
                body: JSON.stringify(body),
            });
            const result = await response.json();
            if (generation !== submittedGeneration) return;
            if (response.ok) renderResult(result);
            else message(result.text || "Answers are unavailable. Your question is still here; please try again.", true);
        } catch (_) {
            if (generation === submittedGeneration) message("The answer could not be completed. Your question is still here; please try again.", true);
        } finally {
            busy = false;
            ask.disabled = choices && draftRevision === null;
            form.removeAttribute("aria-busy");
        }
    });
})();
