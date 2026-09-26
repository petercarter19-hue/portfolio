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
    const reviewUrl = root.getAttribute("data-review-url");
    const commandsUrl = root.getAttribute("data-commands-url");
    let reviewedDigest = null;
    let inFlight = false;

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

    reviewButton.addEventListener("click", async function () {
        if (inFlight) {
            return;
        }
        inFlight = true;
        publishButton.disabled = true;
        setStatus("Reviewing current facts. This does not publish.", "ok");
        try {
            const result = await send(reviewUrl, {});
            if (!result.ok || !result.payload.digest) {
                reviewedDigest = null;
                digestNode.hidden = true;
                setStatus(result.payload.message || "Review could not finish.", "error");
                return;
            }
            reviewedDigest = result.payload.digest;
            digestNode.hidden = false;
            digestNode.textContent =
                String(result.payload.display_count || 0) + " entries shown on your Resume. " +
                String(result.payload.visitor_ai_count || 0) + " entries available to visitor AI.";
            publishButton.disabled = false;
            setStatus(
                "Your information and sharing choices are ready to review. Publish when you are ready to share them.",
                "ok"
            );
        } finally {
            inFlight = false;
        }
    });

    publishButton.addEventListener("click", async function () {
        if (inFlight || !reviewedDigest) {
            return;
        }
        const slug = (slugInput.value || "").trim();
        if (!slug || slug.toLowerCase() === "petec") {
            setStatus("Choose an available public address for your Resume.", "error");
            return;
        }
        inFlight = true;
        try {
            const result = await send(commandsUrl, {
                type: "publish",
                request_id: requestId(),
                reviewed_digest: reviewedDigest,
                slug: slug,
            });
            if (!result.ok) {
                setStatus(result.payload.message || "Publish could not finish.", "error");
                return;
            }
            publishButton.disabled = true;
            setStatus("Published. Visitors now see the reviewed current facts.", "ok");
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
    panel.addEventListener("close", function () { opener.focus(); });

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
