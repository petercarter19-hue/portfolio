/* PeerSlate Control Room — read-only progressive enhancement.
 *
 * This script only READS. It filters already-rendered rows and re-fetches the
 * owner-gated JSON projection to update the "refreshed" timestamp. It performs
 * no writes, submits no forms, and calls no mutation endpoint. The page is fully
 * functional (server-rendered) without it.
 */
(function () {
    'use strict';

    // --- Client-side table filtering (pure display; never mutates data) -----
    function wireFilter(input) {
        var tableId = input.getAttribute('data-filter-target');
        var table = document.getElementById(tableId);
        if (!table) { return; }
        var countEl = document.querySelector('[data-filter-count="' + tableId + '"]');
        var rows = Array.prototype.slice.call(table.tBodies[0] ? table.tBodies[0].rows : []);

        function apply() {
            var q = input.value.trim().toLowerCase();
            var shown = 0;
            rows.forEach(function (row) {
                var match = q === '' || row.textContent.toLowerCase().indexOf(q) !== -1;
                row.hidden = !match;
                if (match) { shown += 1; }
            });
            if (countEl) {
                countEl.textContent = q === ''
                    ? ''
                    : shown + ' of ' + rows.length + ' shown';
            }
        }
        input.addEventListener('input', apply);
    }

    document.querySelectorAll('[data-filter-target]').forEach(wireFilter);

    // --- Refresh: re-fetch the read-only JSON projection --------------------
    var refreshBtn = document.getElementById('cr-refresh');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function () {
            var endpoint = refreshBtn.getAttribute('data-endpoint');
            if (!endpoint) { window.location.reload(); return; }
            refreshBtn.setAttribute('aria-busy', 'true');
            fetch(endpoint, {
                method: 'GET',
                credentials: 'same-origin',
                headers: { 'Accept': 'application/json' }
            })
                .then(function (res) {
                    if (!res.ok) { throw new Error('refresh failed'); }
                    return res.json();
                })
                .then(function (data) {
                    var stamp = document.getElementById('cr-generated');
                    if (stamp && data && data.generated_at) {
                        stamp.textContent = data.generated_at;
                        stamp.classList.remove('cr-flash');
                        // reflow so the flash animation can replay
                        void stamp.offsetWidth;
                        stamp.classList.add('cr-flash');
                    }
                    // A full reload gives the authoritative server-rendered view;
                    // do it so every section reflects the fresh projection.
                    window.location.reload();
                })
                .catch(function () {
                    // On any failure fall back to a plain reload.
                    window.location.reload();
                })
                .then(function () {
                    refreshBtn.removeAttribute('aria-busy');
                });
        });
    }

    // --- Small HTML builders for partial re-rendering (read-only) -----------
    // Mirrors the Jinja macros in templates/control_room.html closely enough
    // that a polled update looks identical to a fresh server render.
    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function freshnessChipHtml(status, fetchedAt) {
        var dot = '<span class="cr-freshness__dot" aria-hidden="true"></span>';
        if (status === 'ok') {
            return '<span class="cr-freshness">' + dot + 'Live' +
                (fetchedAt ? ' · fetched ' + escapeHtml(fetchedAt) : '') + '</span>';
        }
        if (status === 'stale') {
            return '<span class="cr-freshness cr-freshness--stale">' + dot + 'Stale' +
                (fetchedAt ? ' · last success ' + escapeHtml(fetchedAt) : '') + '</span>';
        }
        if (status === 'not_configured') {
            return '<span class="cr-freshness cr-freshness--unknown">' + dot + 'Not configured</span>';
        }
        return '<span class="cr-freshness cr-freshness--unknown">' + dot + 'Unavailable</span>';
    }

    var PILL_MAP = {
        ok: ['cr-pill--ok', 'OK', '●'],
        active: ['cr-pill--ok', 'Active', '●'],
        unknown: ['cr-pill--unknown', 'Unknown', '○'],
        unavailable: ['cr-pill--unavailable', 'Unavailable', '—'],
        partial: ['cr-pill--partial', 'Partial', '◐'],
        stale: ['cr-pill--stale', 'Stale', '◑'],
        failed: ['cr-pill--failed', 'Failed', '✕']
    };

    function pillHtml(status, label) {
        var entry = PILL_MAP[(status || '').toLowerCase()] || ['cr-pill--unknown', status, '○'];
        return '<span class="cr-pill ' + entry[0] + '"><span class="cr-pill__glyph" aria-hidden="true">' +
            entry[2] + '</span>' + escapeHtml(label || entry[1]) + '</span>';
    }

    // --- "Since you last looked" — client-side only, no server state --------
    var LAST_VISIT_KEY = 'cr-last-visit';

    function applyNewPillHighlighting(root) {
        var lastVisit = null;
        try {
            lastVisit = window.localStorage.getItem(LAST_VISIT_KEY);
        } catch (e) { /* localStorage unavailable (private mode, etc.) */ }
        if (!lastVisit) { return; }
        (root || document).querySelectorAll('[data-ts]').forEach(function (el) {
            var ts = el.getAttribute('data-ts');
            if (!ts || ts <= lastVisit) { return; }
            var pill = el.querySelector('.cr-new-pill');
            if (pill) { pill.hidden = false; }
        });
    }

    function recordVisitTimestamp() {
        try {
            window.localStorage.setItem(LAST_VISIT_KEY, new Date().toISOString().slice(0, 10));
        } catch (e) { /* private mode: skip remembering this visit */ }
    }

    // Highlight anything newer than the last recorded visit, then advance the
    // stored timestamp to today so the same items don't stay marked "New".
    applyNewPillHighlighting(document);
    recordVisitTimestamp();

    // --- Auto-refresh: poll the read-only JSON projection --------------------
    // Re-renders only the status band and Repository activity section — the
    // two things that can change between deploys. Everything else (Initiatives,
    // Documents, Decisions, Traceability) only changes on redeploy, so a poll
    // updating them would be wasted work and could disturb filter/scroll state.
    var AUTO_REFRESH_INTERVAL_MS = 90 * 1000;
    var autoRefreshTimer = null;
    var autoRefreshInFlight = false;

    function renderStatusBand(data) {
        var build = data.build_identity || {};
        var activity = data.repository_activity || {};
        var drift = activity.drift || {};

        var productionEl = document.getElementById('cr-status-production');
        if (productionEl) {
            if (build.status === 'ok') {
                var devTag = build.environment === 'local_development'
                    ? ' <span class="cr-tag">Local dev</span>' : '';
                var buildLine = build.build_id
                    ? '<p class="cr-muted">Build ' + escapeHtml(build.build_id) + '</p>' : '';
                productionEl.innerHTML =
                    '<span class="cr-mono cr-statuscard__commit">' + escapeHtml(build.commit) + '</span>' + devTag +
                    '<p class="cr-statuscard__detail">' +
                    escapeHtml(build.subject || 'No commit subject recorded.') + '</p>' + buildLine;
            } else {
                productionEl.innerHTML =
                    '<p class="cr-muted">Unknown — no deployment snapshot or local git found.</p>';
            }
        }

        var repoFreshnessEl = document.getElementById('cr-status-repository-freshness');
        if (repoFreshnessEl) {
            repoFreshnessEl.innerHTML = freshnessChipHtml(activity.status, activity.fetched_at);
        }

        var repoEl = document.getElementById('cr-status-repository');
        if (repoEl) {
            if (activity.status === 'ok' || activity.status === 'stale') {
                var branches = (activity.branches && activity.branches.items) || [];
                var mainBranch = branches.filter(function (b) { return b.name === 'main'; })[0];
                var activeCount = ((activity.prs_active && activity.prs_active.items) || []).length;
                var commits = (activity.commits_main && activity.commits_main.items) || [];
                var latestLine = commits.length
                    ? '<p class="cr-muted">Latest commit ' + escapeHtml(commits[0].date) + '</p>' : '';
                repoEl.innerHTML =
                    (mainBranch
                        ? '<span class="cr-mono cr-statuscard__commit">' + escapeHtml(mainBranch.commit) + '</span>'
                        : '') +
                    '<p class="cr-statuscard__detail">' + activeCount + ' active PR' +
                    (activeCount !== 1 ? 's' : '') + '</p>' + latestLine;
            } else if (activity.status === 'not_configured') {
                repoEl.innerHTML = '<p class="cr-muted">Not configured. ' +
                    '<a href="https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site' +
                    '?path=/docs/control-room/V2_LIVE_SYNC_SPEC.md" target="_blank" ' +
                    'rel="noopener noreferrer" class="cr-source">Setup guide</a></p>';
            } else {
                repoEl.innerHTML = '<p class="cr-muted">' + escapeHtml(activity.note || 'Unavailable.') + '</p>';
            }
        }

        var driftEl = document.getElementById('cr-status-drift');
        if (driftEl) {
            if (drift.state === 'up_to_date') {
                driftEl.innerHTML = pillHtml('ok', 'Up to date');
            } else if (drift.state === 'behind') {
                var pending = (drift.pending_commits || []).slice(0, 3).map(function (c) {
                    return '<li>' + escapeHtml(c.subject || c.commit) + '</li>';
                }).join('');
                driftEl.innerHTML = pillHtml('partial', 'Behind') +
                    '<p class="cr-statuscard__detail">' + escapeHtml(drift.detail) + '</p>' +
                    (pending ? '<ul class="cr-bullets cr-muted" style="margin-top:6px;">' + pending + '</ul>' : '');
            } else {
                driftEl.innerHTML = pillHtml('unknown', 'Unknown') +
                    '<p class="cr-muted">Needs both a deployment snapshot and live repository data.</p>';
            }
        }
    }

    function renderRepositoryActivitySection(data) {
        var activity = data.repository_activity || {};
        var chipEl = document.getElementById('cr-repo-activity-chip');
        if (chipEl) { chipEl.innerHTML = freshnessChipHtml(activity.status, activity.fetched_at); }

        var bodyEl = document.getElementById('cr-repo-activity-body');
        if (!bodyEl) { return; }

        if (activity.status === 'not_configured') {
            bodyEl.innerHTML = '<div class="cr-banner cr-banner--info">' +
                pillHtml('unavailable', 'Not configured') + ' ' + escapeHtml(activity.note) + '</div>';
            return;
        }
        if (activity.status === 'unavailable') {
            bodyEl.innerHTML = '<div class="cr-banner cr-banner--warn">' +
                pillHtml('unavailable') + ' ' + escapeHtml(activity.note) + '</div>';
            return;
        }

        var staleBanner = activity.status === 'stale'
            ? '<div class="cr-banner cr-banner--warn">' + pillHtml('stale') + ' ' +
              escapeHtml(activity.note) + '</div>'
            : '';

        function prItem(pr, dateField) {
            var detail = dateField === 'created'
                ? escapeHtml(pr.source_branch) + ' → ' + escapeHtml(pr.target_branch) +
                  ' · ' + escapeHtml(pr.author) + ' · ' + escapeHtml(pr.created)
                : escapeHtml(pr.status) + ' · ' + escapeHtml(pr.closed || pr.created);
            return '<li data-ts="' + escapeHtml(pr[dateField] || '') + '">' +
                '<a href="' + escapeHtml(pr.link) + '" target="_blank" rel="noopener noreferrer">#' +
                escapeHtml(pr.id) + ' ' + escapeHtml(pr.title) + '</a>' +
                '<span class="cr-new-pill" hidden>New</span>' +
                '<span class="cr-muted">' + detail + '</span></li>';
        }

        var activeItems = (activity.prs_active && activity.prs_active.items) || [];
        var completedItems = (activity.prs_completed && activity.prs_completed.items) || [];
        var branchItems = (activity.branches && activity.branches.items) || [];
        var buildItems = (activity.pipeline_runs && activity.pipeline_runs.items) || [];

        var activeHtml = activeItems.length
            ? '<ul class="cr-activity-list">' +
              activeItems.map(function (pr) { return prItem(pr, 'created'); }).join('') + '</ul>'
            : '<p class="cr-muted">No active pull requests.</p>';
        var completedHtml = completedItems.length
            ? '<ul class="cr-activity-list">' +
              completedItems.map(function (pr) { return prItem(pr, 'closed'); }).join('') + '</ul>'
            : '<p class="cr-muted">No recently completed pull requests.</p>';
        var branchesHtml = branchItems.length
            ? '<ul class="cr-activity-list">' + branchItems.map(function (b) {
                return '<li><span class="cr-tag">' + escapeHtml(b.name) + '</span> <span class="cr-mono">' +
                    escapeHtml(b.commit) + '</span></li>';
            }).join('') + '</ul>'
            : '<p class="cr-muted">No branch data.</p>';
        var buildsHtml = buildItems.length
            ? '<ul class="cr-activity-list">' + buildItems.map(function (run) {
                var link = run.link
                    ? '<a href="' + escapeHtml(run.link) + '" target="_blank" rel="noopener noreferrer">Build ' +
                      escapeHtml(run.build_number || run.id) + '</a>'
                    : 'Build ' + escapeHtml(run.build_number || run.id);
                var resultStatus = run.result === 'succeeded' ? 'ok' : (run.result === 'failed' ? 'failed' : 'unknown');
                return '<li>' + link + ' ' + pillHtml(resultStatus, run.result || run.status) +
                    ' <span class="cr-muted cr-mono">' + escapeHtml(run.commit) + '</span>' +
                    ' <span class="cr-muted">' + escapeHtml(run.finished) + '</span></li>';
            }).join('') + '</ul>'
            : '<p class="cr-muted">No pipeline run data.</p>';

        bodyEl.innerHTML =
            staleBanner +
            '<div class="cr-grid cr-grid--2">' +
                '<div class="cr-card"><h3 class="cr-h3">Active pull requests <span class="cr-count">' +
                    activeItems.length + '</span></h3>' + activeHtml + '</div>' +
                '<div class="cr-card"><h3 class="cr-h3">Recently completed</h3>' + completedHtml + '</div>' +
            '</div>' +
            '<div class="cr-grid cr-grid--2" style="margin-top:14px;">' +
                '<div class="cr-card"><h3 class="cr-h3">Branches</h3>' + branchesHtml + '</div>' +
                '<div class="cr-card"><h3 class="cr-h3">Recent pipeline runs</h3>' + buildsHtml + '</div>' +
            '</div>';

        applyNewPillHighlighting(bodyEl);
    }

    function pollForUpdates() {
        if (autoRefreshInFlight) { return; }
        var refreshBtn = document.getElementById('cr-refresh');
        var endpoint = refreshBtn && refreshBtn.getAttribute('data-endpoint');
        if (!endpoint) { return; }
        autoRefreshInFlight = true;
        fetch(endpoint, {
            method: 'GET',
            credentials: 'same-origin',
            headers: { Accept: 'application/json' }
        })
            .then(function (res) {
                if (!res.ok) { throw new Error('poll failed'); }
                return res.json();
            })
            .then(function (data) {
                renderStatusBand(data);
                renderRepositoryActivitySection(data);
            })
            .catch(function () {
                // Quiet failure: keep showing the last good render. The
                // status band and Repository activity chips already reflect
                // their own stale/unavailable states from the last update.
            })
            .then(function () {
                autoRefreshInFlight = false;
            });
    }

    function startAutoRefresh() {
        stopAutoRefresh();
        autoRefreshTimer = window.setInterval(pollForUpdates, AUTO_REFRESH_INTERVAL_MS);
    }

    function stopAutoRefresh() {
        if (autoRefreshTimer) {
            window.clearInterval(autoRefreshTimer);
            autoRefreshTimer = null;
        }
    }

    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            pollForUpdates();
            startAutoRefresh();
        }
    });

    if (!document.hidden) {
        startAutoRefresh();
    }

    // --- Detail pop-out modal (read-only) -----------------------------------
    // Reveals an initiative's plain-language detail, already rendered
    // server-side into a hidden store. Fully accessible: focus moves into the
    // dialog, Tab is trapped, Escape / backdrop / close all dismiss, and focus
    // returns to the row button that opened it.
    var modal = document.getElementById('cr-modal');
    var modalBody = document.getElementById('cr-modal-body');
    var modalTitle = document.getElementById('cr-modal-title');
    var modalReturnFocus = null;

    function modalFocusables() {
        if (!modal) { return []; }
        return Array.prototype.filter.call(
            modal.querySelectorAll('a[href], button:not([disabled])'),
            function (el) { return el.offsetParent !== null; }
        );
    }

    function onModalKeydown(e) {
        if (e.key === 'Escape') { e.preventDefault(); closeDetail(); return; }
        if (e.key !== 'Tab') { return; }
        var focusable = modalFocusables();
        if (!focusable.length) { return; }
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault(); last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault(); first.focus();
        }
    }

    function openDetail(sourceId, trigger) {
        var source = document.getElementById(sourceId);
        if (!source || !modal || !modalBody) { return; }
        modalReturnFocus = trigger || document.activeElement;
        modalTitle.textContent = source.getAttribute('data-title') || 'Initiative detail';
        // The source content is server-rendered and Jinja-autoescaped; copying
        // its innerHTML re-parses the same safe markup.
        modalBody.innerHTML = source.innerHTML;
        modalBody.scrollTop = 0;
        modal.hidden = false;
        document.body.classList.add('cr-modal-open');
        document.addEventListener('keydown', onModalKeydown, true);
        var closeBtn = modal.querySelector('.cr-modal__close');
        (closeBtn || modalBody).focus();
    }

    function closeDetail() {
        if (!modal || modal.hidden) { return; }
        modal.hidden = true;
        document.body.classList.remove('cr-modal-open');
        document.removeEventListener('keydown', onModalKeydown, true);
        modalBody.innerHTML = '';
        if (modalReturnFocus && modalReturnFocus.focus) { modalReturnFocus.focus(); }
        modalReturnFocus = null;
    }

    document.querySelectorAll('[data-detail]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            openDetail(btn.getAttribute('data-detail'), btn);
        });
    });
    if (modal) {
        modal.querySelectorAll('[data-modal-close]').forEach(function (el) {
            el.addEventListener('click', closeDetail);
        });
    }
}());
