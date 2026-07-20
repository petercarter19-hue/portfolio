# PS-OWNER-HOME-VIEWER-GATE-001 — Fable Frontend Implementation Architecture

Recorded 2026-07-19 against `origin/main`
`6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`. This maps the accepted authority
candidate and the Codex gate contracts onto this repository's real frontend
conventions for the future `PS-HOME-FRONTEND-001` package. Architecture only —
no template, CSS, JavaScript, route, or test is implemented by this branch.

## 1. File mapping

| Concern | Exact proposed file | Notes |
|---|---|---|
| Page template | `templates/owner_home.html` | Extends `templates/base.html`; sets `page_title` and `{% block title %}{{ page_title }} \| PeerSlate{% endblock %}` like `owner_capture.html:3`; **must not** repeat the nested `<main id="main-content">` defect present in `owner_workspace.html:10` and `owner_settings.html:10` — `base.html:267` already provides the single `<main>` |
| Page partials | `templates/partials/owner_home/_owner_shell_header.html`, `_owner_hero.html`, `_capture_action.html`, `_audience_rail.html`, `_stage.html`, `_review_list.html`, `_recent_moment.html`, `_resurfaced_moment.html`, `_noticed.html`, `_connections.html`, `_next_step.html`, `_home_status.html`, `_mobile_bottom_nav.html` | Follows the underscore-partials convention of `templates/partials/homepage/` |
| Route-scoped CSS | `static/css/owner-home.css` | Loaded from the page's `extra_head` block with a `?v=` cache-bust, like `owner_capture.html:6`; defines route-local `--oh-*` tokens from the authority palette (see parity register D6); does not edit `style.css`, `owner-app.css`, or shared tokens |
| Route-scoped JS | `static/js/owner-home.js` | Optional progressive enhancement only (category retry, focus/announcement management); deferred IIFE in `extra_scripts`, matching `owner-capture-voice.js` conventions; the page is fully functional without it |
| Atmosphere asset | `static/img/owner-home/atmosphere.png` | Exact accepted candidate asset `assets/owner-home-alpine-atmosphere.png`; no regeneration, recrop, recolor, or substitution in the first release |
| Decorative section material (R3) | `static/img/owner-home/` (abstract brand material per section) | No people, records, counts, or member-like photography |
| Tests | `tests/test_owner_home.py` (extend backend package's file), `tests/test_owner_home_accessibility.py` (new) | Sequential ownership with `PS-HOME-BACKEND-001` — see intersection register |
| Evidence artifacts | `artifacts/ps-home-frontend-001/**` named screenshots | Named per the review charter |

## 2. Server-rendered versus progressively enhanced

The page is **server-rendered first**. `GET /app` (behind `PEERSLATE_OWNER_HOME_ENABLED`)
renders `owner_home.html` from the bounded `OwnerHomeViewModel` produced by
`services/owner_home_service.py` — the same view model serialized by
`GET /api/v1/owner/home`. This matches the repository's existing owner pattern
(server-rendered lists/forms in `owner_capture.html`, client fetch only for the
voice upload).

- **No-JS behavior:** everything renders and every action works. Category
  Retry falls back to a plain link/refresh of `/app` (a safe idempotent GET).
  Capture, review items, Moments, and next step are ordinary links to their
  authoritative routes. Disabled Coming-later previews are static disabled
  markup — they need no JS to be honest.
- **JS enhancement (`owner-home.js`):** category-level Retry that calls
  `GET /api/v1/owner/home` with
  `fetch(url, {credentials:"same-origin", headers:{"X-Requested-With":"fetch"}})`
  and re-renders only the failed category; one polite completion announcement;
  focus kept on the invoking Retry control (or moved to the updated section
  heading with `tabindex="-1"` if the control disappears); bounded backoff; no
  polling; no localStorage/sessionStorage/IndexedDB persistence of any payload
  (`private, no-store` contract).
- **Never:** a broad client fetch followed by hiding, a legacy
  `/api/dashboard` call, or any request from a Coming-later control.

## 3. Semantic DOM / component inventory

One `<h1>` ("Owner Home" / welcome heading per accepted composition). Reading
order matches the authority's structured order (candidate doc
`03_ACCESSIBILITY_RESPONSIVE_EVIDENCE.md`):

1. Owner shell header band (page-scoped; disabled future destinations are
   text + visible **Coming later**, not links)
2. `<h1>` + private-workspace context line (answers whose space / what context
   / what is not happening)
3. Capture action — one real `<a>` styled as the dominant card; accessible
   name names the action and destination
4. Audience rail — Owner View current-context text-state plus four disabled
   capability previews; wording pattern `"[Mode] — coming later. Not yet
   available."`
5. `<section aria-labelledby=…>` Needs Review — `<ol>` of at most 3 items;
   bounded-remainder shell row; honest empty text
6. `<section>` Recent Moment — one card, `<time datetime=…>` with absolute text
7. `<section>` From your history (Resurfaced) — dormant Coming-later preview in
   the first slice
8. `<section>` What PeerSlate noticed — dormant preview
9. `<section>` Connections — dormant preview
10. `<section>` Your next useful step — one real action
11. Status/footer truth line
12. Mobile bottom nav (page-scoped) on small viewports

Statuses (Private draft, Stale, Coming later…) are text plus treatment, never
color/icon alone. Dates include absolute accessible text. Icons decorative
when adjacent text names the action.

**Disabled Coming-later semantics (zero routes, zero requests):** native
`disabled` on `<button>`-shaped previews plus `aria-disabled="true"` where
applicable; excluded from any form; no `href`; no pointer/keyboard handlers;
visible **Coming later** text inside the element (not tooltip/icon/opacity
only); explanatory copy remains in normal reading order because native
disabled controls leave the tab order. This reuses the accepted Voice pattern
already in the codebase (`.owner-app__voice-soon` pill, disabled +
`aria-disabled` chips in `owner_capture.html:257–313`), restyled to the Owner
Home authority. A separately labeled "Learn what is coming" disclosure may be
focusable if it only explains the future capability. No browser flag, DOM
edit, or query parameter can activate a preview — activation requires the real
backend, registry change, tests, deployment, and acceptance.

## 4. State architecture

All states are server-decidable and render without JS; `owner-home.js` only
improves the retry/announcement ergonomics. State copy and composition follow
authority exports 12–18 and 22.

| State | Server input | Rendering |
|---|---|---|
| Loading | JS-initiated category refresh only (initial load is a normal full render) | Stable heading/structure; `aria-hidden` skeletons with no fake text/counts; one polite status announcement |
| Empty | `review_items=[]`, `recent_moment=null` | Honest empty text per category; Capture remains dominant; no generated tasks |
| Partial failure | Per-category failure flags from the service's failure-independent adapters | Only the failed category renders its named unavailable card + Retry; independent categories intact; never scope-broadening |
| Complete failure | Core aggregation failed (`503 temporarily_unavailable`) | Heading + explanation + Retry + independently verified safe Capture destination; no raw error IDs; no cached-private fallback |
| Stale | `409 state_changed` on an action, or version mismatch flag | Explicit `Stale` label, affected action disabled, visible Refresh; never silent overwrite |
| Restricted | An owner-owned reference became ineligible | Bounded neutral unavailable item; no source leak; non-enumerating |
| Retry (succeeds/fails) | Idempotent GET re-issue | One completion announcement; focus per §2; repeated failures do not append duplicate errors |
| Session expired | `401` from the JSON endpoint mid-session | Clear protected content, offer the validated local sign-in return path (`/auth/sign-in?return_to=/app`); no private payload in the URL or title |
| Recovery | Post-retry success | Updated section, single announcement, predictable focus |

## 5. Responsive, zoom, and assistive behavior

- **Breakpoints:** the authority requires standalone 390px and 320px
  compositions and an 844px landscape reflow. No 390/320 breakpoints exist
  anywhere in `static/css` today (narrowest is 460px; `owner-app.css` uses a
  single 540px), so `owner-home.css` defines its own set (proposed: ≤844,
  ≤540, ≤390, ≤320) with a fluid single-column stack below the stage grid.
  R1 is implemented here: at 320px, Noticed controls (Inspect support /
  Correct / Dismiss when live; none while dormant) stack with full-width touch
  targets and the Next-step decorative material moves behind/below the text
  instead of clipping it.
- **200% zoom / reflow:** fluid `clamp()`/`min()` sizing per existing owner
  CSS conventions; no fixed-height clipping; verified against export 07.
- **Keyboard:** logical order matching §3; visible 3px marigold focus +
  separation edge (`:focus-visible`), meeting WCAG 2.2 focus appearance on
  both the dark shell and ivory stage; skip link already targets
  `#main-content` (`base.html:136`); no keyboard traps; Retry/Refresh/sign-in
  reachable in every failure state.
- **NVDA:** landmark/section labels per §3; live regions
  `role="status" aria-live="polite"` for retry results and
  `role="alert"` for failures, matching the repository's existing pattern
  (`owner_capture.html:26–38`, `141–143`); Coming-later text read once in
  document order, never as an alert.
- **Forced colors:** `@media (forced-colors: active)` block is **required** in
  `owner-home.css` (the existing `owner-app.css` has none — a known gap);
  meaning survives via system colors and borders; the atmosphere may drop.
- **Reduced motion:** `prefers-reduced-motion: reduce` removes non-essential
  animation; the atmosphere is static; state changes remain immediate.
- **Visually-hidden helper:** Owner Home ships its own route-scoped class
  (e.g. `.oh-visually-hidden`) — there is no shared one in the codebase.
- **Touch:** 44px minimum target heights per existing owner convention
  (`owner-app.css:62`); no hover-only controls; orientation unlocked, 844px
  landscape composition per export 23.

## 6. Shell integration constraints (route-scoped only)

`base.html` currently wraps every non-`/` page in more than a header: a legacy
touch-tablet forced-desktop viewport script, site sky,
global header/profile tabs, public footer, Ask Pete AI, public search data,
theme bootstrap, and the global mobile tabbar/scripts also surround owner
pages. The accepted Owner Home provides its own shell.

Manager decisions U1/U3 require `auth.owner_workspace` to pass a server-owned
boolean such as `standalone_owner_shell=True` only for the flag-on Home render.
`base.html` uses it to bypass the tablet override; suppress that complete public
chrome and its `chatbot.js`, `site-search.js`, `mobile-nav.js`, and
`theme-toggle.js` scripts; omit `portfolio-shell`/`platform-shell`,
`slate-light`, and `ps-editorial-surface`; and add only the route-scoped Owner
Home body class.
The skip link and the one base `<main id="main-content">` remain. The page
renders one page-scoped mobile bottom nav; the global `mobile-tabbar` and
`mobile-nav.js` are absent. Shared fonts/base styles remain. No flag-off or
non-Owner-Home render may change, which must be proved by full-suite tests and
representative DOM/screenshots.

## 7. What the frontend package must not do

- No fake client-side records, no fixture data in production paths, no
  Pete-hardcoded content in reusable components.
- No calls to `/api/dashboard`; no second Capture/Moment/profile data model.
- No viewer modes, My Slate preview behavior, Connections, Journal, insights,
  sharing, publication, or matching activation.
- No working routes or handlers behind Coming-later controls.
- No edits to `base.html` beyond the manager-approved server-owned conditional;
  no edits to `style.css`, `owner-app.css`, `mobile-nav.js`, or
  `theme-toggle.js`; no global navigation/theme behavior change.
- No offline persistence of any Home payload.
