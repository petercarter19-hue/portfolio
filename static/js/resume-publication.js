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
                reviewedDigest +
                " display " +
                String(result.payload.display_count || 0) +
                " visitor-AI " +
                String(result.payload.visitor_ai_count || 0);
            publishButton.disabled = false;
            setStatus(
                "Reviewed current facts with independent display and visitor-AI choices. Publishing is a separate step and uses this digest.",
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
            setStatus("Choose a public slug that is not the labeled Pete example.", "error");
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
