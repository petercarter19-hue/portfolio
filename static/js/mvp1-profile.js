(function () {
    "use strict";
    const form = document.getElementById("mvp1-profile-form");
    if (!form) return;
    let state = JSON.parse(document.getElementById("profile-state").textContent);
    let review = null;
    let pending = null;
    let busy = false;
    let dirty = false;
    const status = document.getElementById("profile-status");
    const panel = document.getElementById("profile-review-panel");
    const reviewButton = document.getElementById("profile-review");
    const publishButton = document.getElementById("profile-publish");
    const withdrawButton = document.getElementById("profile-withdraw");
    const publicLink = document.getElementById("profile-public-link");
    const field = (name) => form.elements.namedItem(name);

    function controls() {
        Array.from(form.elements).forEach((element) => { element.disabled = busy || !!pending; });
        publishButton.disabled = busy;
        withdrawButton.disabled = busy || (!!pending && pending.type !== "withdraw");
    }
    function update(result) {
        state = result;
        field("slug").readOnly = !!state.profile_slug;
        publicLink.hidden = !state.public_profile_url;
        publicLink.setAttribute("href", state.public_profile_url || "#");
        withdrawButton.hidden = !state.public_profile_url;
    }
    async function send(command) {
        const response = await fetch(form.dataset.commandUrl, {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-PeerSlate-Request": "same-origin" },
            body: JSON.stringify(command),
        });
        const result = await response.json();
        if (!response.ok || result.success !== true) {
            const error = new Error(result.message || "This could not finish. Keep your input and try again.");
            error.status = response.status;
            throw error;
        }
        return result;
    }
    form.addEventListener("input", () => { dirty = true; review = null; panel.hidden = true; });
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (busy || pending || !form.reportValidity()) return;
        const command = { type: "save", slug: field("slug").value,
            expected_draft_version: state.draft_version,
            identity: { display_name: field("display_name").value, headline: field("headline").value,
                location: field("location").value || null, summary: field("summary").value } };
        busy = true; controls();
        status.textContent = "Saving privately…";
        try {
            update(await send(command)); dirty = false; review = null; panel.hidden = true;
            status.textContent = "Saved privately. Review when you want to publish your introduction.";
        } catch (error) { status.textContent = error.message; }
        finally { busy = false; controls(); }
    });
    reviewButton.addEventListener("click", async () => {
        if (busy || pending) return;
        if (dirty || !state.draft_version) { status.textContent = "Save your introduction privately before reviewing it."; return; }
        busy = true; controls(); review = null; panel.hidden = true;
        try {
            const result = await send({ type: "review", expected_draft_version: state.draft_version,
                expected_public_revision: state.public_revision });
            review = result.review;
            document.getElementById("profile-reviewed-name").textContent = result.identity.display_name;
            document.getElementById("profile-reviewed-headline").textContent = result.identity.headline;
            document.getElementById("profile-reviewed-location").textContent = result.identity.location || "";
            document.getElementById("profile-reviewed-summary").textContent = result.identity.summary;
            panel.hidden = false;
            status.textContent = "Review the introduction below. Nothing has been published.";
            publishButton.focus();
        } catch (error) { status.textContent = error.message; }
        finally { busy = false; controls(); }
    });
    async function publishOrWithdraw(type) {
        if (busy || (pending && pending.type !== type)) return;
        if (!pending) {
            if (type === "publish" && (!review || dirty)) return;
            pending = { type, request_id: crypto.randomUUID(), confirmed: true,
                expected_public_revision: state.public_revision };
            if (type === "publish") Object.assign(pending, {
                expected_draft_version: review.draft_version, candidate_digest: review.candidate_digest,
            });
        }
        busy = true; controls();
        try {
            const result = await send(pending);
            pending = null; update(result); panel.hidden = true; review = null;
            status.textContent = type === "publish"
                ? "Your introduction is public. Review Resume again to select it there."
                : "Your introduction was withdrawn. Resume will no longer show this selected name.";
        } catch (error) {
            if (error.status >= 400 && error.status < 500 && error.status !== 408 && error.status !== 429) {
                pending = null; panel.hidden = true; review = null;
                status.textContent = error.message;
            } else {
                status.textContent = "The response was interrupted. Use the same button to retry this exact request.";
            }
        } finally { busy = false; controls(); }
    }
    publishButton.addEventListener("click", () => publishOrWithdraw("publish"));
    withdrawButton.addEventListener("click", () => publishOrWithdraw("withdraw"));
})();
