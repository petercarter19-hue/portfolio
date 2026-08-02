/*
 * PS-SIGNIN-EXPERIENCE-001 item 2.2 — bounded automatic re-check for the two
 * "your workspace is waking up" surfaces (templates/identity_storage_unavailable.html
 * and the Owner Home waking stage).
 *
 * Azure SQL serverless auto-pauses, so the first signed-in request after an
 * idle period fails while the database resumes. That resume normally finishes
 * in well under a minute, and until this script existed a member had to keep
 * pressing "Try again" through the whole window.
 *
 * Everything here is progressive enhancement. Both pages are complete and
 * usable with JavaScript disabled: the manual link is server-rendered and the
 * stop control below stays hidden unless this script is running.
 *
 * Deliberate constraints:
 *   - Bounded. Automatic checking stops after the server-supplied budget
 *     (about 90 seconds), then the page stays put and says so.
 *   - Interruptible (WCAG 2.2 SC 2.2.1). "Stop checking automatically" is a
 *     real control, revealed only when there is something to stop.
 *   - Quiet. The live region is polite and is updated only when the state
 *     actually changes, never on a per-second tick.
 *   - Honest. It never claims the workspace is back, and it changes nothing
 *     but the current page request.
 */
(function () {
    'use strict';

    var root = document.querySelector('[data-ps-waking]');
    if (!root) {
        return;
    }

    var statusElement = root.querySelector('[data-ps-waking-status]');
    var stopButton = root.querySelector('[data-ps-waking-stop]');

    var retryUrl = root.getAttribute('data-ps-waking-retry-url');
    if (!retryUrl || retryUrl.charAt(0) !== '/' || retryUrl.charAt(1) === '/') {
        // Only ever re-request a same-origin path this application rendered.
        retryUrl = window.location.pathname;
    }

    var budgetSeconds = parseInt(root.getAttribute('data-ps-waking-budget-seconds'), 10);
    if (!isFinite(budgetSeconds) || budgetSeconds < 5 || budgetSeconds > 600) {
        budgetSeconds = 90;
    }

    /* Bounded backoff. The last value repeats if the budget allows it. */
    var DELAYS_SECONDS = [4, 6, 9, 13, 18, 25];

    /* A gap longer than this means the member left and came back, so the
       previous wake-up episode is over and the budget starts again. */
    var EPISODE_GAP_MS = 120000;

    var STORAGE_KEY = 'ps-waking:' + window.location.pathname;

    function readEpisode() {
        try {
            var raw = window.sessionStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return null;
            }
            var parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') {
                return null;
            }
            if (typeof parsed.startedAt !== 'number' || typeof parsed.updatedAt !== 'number') {
                return null;
            }
            return parsed;
        } catch (error) {
            return null;
        }
    }

    function writeEpisode(episode) {
        try {
            window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(episode));
        } catch (error) {
            /* Private mode or a full quota: automatic checking still works for
               this page view, it just cannot carry the budget across reloads. */
        }
    }

    function announce(message) {
        if (statusElement && statusElement.textContent !== message) {
            statusElement.textContent = message;
        }
    }

    function stopAutomaticChecking(episode, message) {
        episode.stopped = true;
        episode.updatedAt = Date.now();
        writeEpisode(episode);
        root.removeAttribute('data-ps-waking-active');
        if (stopButton) {
            stopButton.hidden = true;
        }
        announce(message);
    }

    var now = Date.now();
    var episode = readEpisode();
    if (!episode || now - episode.updatedAt > EPISODE_GAP_MS || now < episode.startedAt) {
        episode = { startedAt: now, attempt: 0, stopped: false };
    }

    if (episode.stopped) {
        announce('Automatic checking is off. Use Check now when you are ready.');
        return;
    }

    var timer = null;

    function remainingMs() {
        return budgetSeconds * 1000 - (Date.now() - episode.startedAt);
    }

    function schedule(announceNext) {
        var left = remainingMs();
        if (left <= 1000) {
            stopAutomaticChecking(
                episode,
                'Your workspace is taking longer than usual. Automatic checking '
                    + 'has stopped. Use Check now when you are ready.'
            );
            return;
        }

        var index = Math.min(episode.attempt, DELAYS_SECONDS.length - 1);
        var delayMs = Math.min(DELAYS_SECONDS[index] * 1000, left);
        timer = window.setTimeout(check, delayMs);
        if (announceNext) {
            announce(
                'Still starting. PeerSlate will check again in about '
                    + Math.round(delayMs / 1000)
                    + ' seconds.'
            );
        }
    }

    function check() {
        /* Never move the page out from under someone who is using these
           controls: a member reaching for "Safe return" by keyboard must not
           have the document replaced mid-reach. Wait and try again instead —
           the overall budget keeps running either way. */
        if (document.activeElement && root.contains(document.activeElement)) {
            schedule(false);
            return;
        }
        episode.attempt += 1;
        episode.updatedAt = Date.now();
        writeEpisode(episode);
        /* replace() so a member who waited through several checks does not
           have to walk back through them to leave the page. */
        window.location.replace(retryUrl);
    }

    root.setAttribute('data-ps-waking-active', 'true');
    schedule(true);

    if (stopButton && root.getAttribute('data-ps-waking-active') === 'true') {
        stopButton.hidden = false;
        stopButton.addEventListener('click', function () {
            window.clearTimeout(timer);
            stopAutomaticChecking(
                episode,
                'Automatic checking is off. Use Check now when you are ready.'
            );
        });
    }
}());
