/*
 * Workshop capped-field behaviour — audit fix F1 (2026-08-04).
 *
 * Two small jobs, both progressive enhancement over markup that is already
 * correct and usable without this file:
 *
 *   1. Keep each field's server-rendered character counter in step as the
 *      member types. The counter's initial value is rendered by
 *      templates/partials/workshop/_field_counter.html, so with JavaScript
 *      off the page still states the limit and the current usage honestly —
 *      it simply stops updating.
 *
 *   2. Warn, rather than silently swallow, when a paste would exceed the
 *      cap. A browser's ``maxlength`` truncates a paste with no feedback at
 *      all, so a member pasting 1200 characters into a 1000-character field
 *      saw 1000 of them appear and had no way to know the rest were gone.
 *      This says so, once, next to the field. It never edits, restores, or
 *      rewrites the member's text — the truncation is the browser's, and
 *      this only makes it visible.
 *
 * Focus management for a REJECTED submission is deliberately not here: the
 * server already renders ``aria-invalid`` and ``autofocus`` on the offending
 * field (workshop_routes._offending_field), so it works on the very first
 * paint and without JavaScript.
 */
(function () {
    "use strict";

    function countOf(value) {
        // Unicode code points, matching the len() bound the preview save
        // actually enforces server-side — not UTF-16 units, which would
        // over-count an emoji and show a number the server disagrees with.
        return Array.from(value || "").length;
    }

    function wire(counter) {
        var fieldId = counter.getAttribute("data-wk-count-for");
        var limit = parseInt(counter.getAttribute("data-wk-count-limit"), 10);
        var field = fieldId ? document.getElementById(fieldId) : null;
        var used = counter.querySelector(".wk-field__count-used");
        if (!field || !used || !limit) {
            return;
        }

        function render() {
            var count = countOf(field.value);
            used.textContent = String(count);
            counter.classList.toggle("wk-field__count--at-limit", count >= limit);
        }

        field.addEventListener("input", render);

        field.addEventListener("paste", function (event) {
            var clipboard = event.clipboardData || window.clipboardData;
            if (!clipboard) {
                return;
            }
            var pasted = countOf(clipboard.getData("text"));
            var selected = countOf(
                String(field.value).slice(field.selectionStart, field.selectionEnd)
            );
            var resulting = countOf(field.value) - selected + pasted;
            if (resulting > limit) {
                notifyTruncated(counter, resulting - limit);
            }
        });

        render();
    }

    function notifyTruncated(counter, dropped) {
        var notice = counter.parentNode.querySelector(".wk-field__paste-notice");
        if (!notice) {
            notice = document.createElement("p");
            notice.className = "wk-field__paste-notice";
            notice.setAttribute("role", "status");
            counter.parentNode.insertBefore(notice, counter.nextSibling);
        }
        notice.textContent =
            "That paste was longer than this field allows, so the last " +
            dropped +
            (dropped === 1 ? " character was" : " characters were") +
            " not kept. Shorten it, or sign in to save at full length.";
    }

    function init() {
        var counters = document.querySelectorAll("[data-wk-count-for]");
        for (var i = 0; i < counters.length; i += 1) {
            wire(counters[i]);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
