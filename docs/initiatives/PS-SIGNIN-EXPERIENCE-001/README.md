# PS-SIGNIN-EXPERIENCE-001 — Sign-in smoothness corrections (items 2 + 5)

Owner decision, 2026-08-02: Pete reviewed the sign-in experience assessment
(evidence in `artifacts/2026-08-02-signin-experience-assessment/`) and approved
three of its five findings for immediate work: (1) Entra External ID branding,
(2) graceful database-wake experience, (5) the signed-in mobile header overlap
bug. Items 3 (chrome unification) and 4 ("coming later" density) are explicitly
deferred pending a later owner discussion. Item 1 is Azure tenant configuration
and is executed outside this repository package; this package covers items 2
and 5 only.

## Classification and roles

- Delivery path: **Bounded** (item 2) + **Routine** (item 5), per
  `docs/AI_WORKFLOW.md`. Item 2 renders new truthful transient states on
  protected routes but changes no identity derivation, authorization decision,
  session handling, schema, or data lifecycle. No Protected trigger is touched;
  if implementation discovers it must alter identity or authorization logic,
  stop and reclassify.
- Sole writer: Claude **Opus 5** (owner exception 2026-08-02, superseding the
  routing table's Sonnet 5 implementer row for this package only; recorded per
  AI_WORKFLOW exception rule).
- No independent reviewer is triggered; the writer performs the complete-diff
  self-review and the coordinating session re-reviews before PR.
- Visual authority: no new visual direction is created. Item 2 reuses the
  existing released waking/failure panel patterns
  (`identity_storage_unavailable.html`, `owner-app.css`, `oh__failure` stage
  card) with truthful state wiring and copy — a documented non-material
  adaptation. Item 5 restores the already-locked header layout at mobile
  widths (bug fix). Any change to composition, hierarchy, typography family,
  color language, or the responsive interaction model is out of scope and
  returns to the ChatGPT visual lane.

## Item 2 — graceful database wake ("workspace waking", not "HOME DATA FAILED")

Problem evidence (2026-08-02, against `origin/main`
`388f47307a65bec6e70731a1b7794acad2dd1884`): Azure SQL serverless auto-pauses.
On the first signed-in request after idle:

- `get_current_identity()` raises `DatabaseServiceError` →
  `identity_storage_unavailable.html` (503, `Retry-After: 5`): honest copy but
  **manual retry only**; members must click "Try again" repeatedly for the
  30–60 s resume window.
- When identity resolves but home data does not, `/app` collapses
  `DatabaseServiceError` and `OwnerHomeContractError` into one
  `home_failed=True` "HOME DATA FAILED / Owner Home data could not load" card
  (`templates/partials/owner_home/_stage.html`,
  `auth_routes.py` owner_workspace). A paused database therefore presents as a
  product failure at the exact moment of first sign-in.

Required behavior:

1. **Distinguish transient storage unavailability from contract failure** on
   `/app` (flag-on path): `DatabaseServiceError` → a waking state;
   `OwnerHomeContractError` → the existing honest failure card, unchanged.
2. **Auto-retry with honest copy** on both waking surfaces
   (`identity_storage_unavailable.html` and the new `/app` waking state):
   automatic periodic re-request (JS with backoff; no-JS fallback via
   `<meta http-equiv="refresh">` or the existing manual link), a visible
   truthful line (e.g. "Your private workspace is starting. This usually takes
   under a minute."), a bounded attempt window (~90 s) after which automatic
   retry stops and the manual guidance remains, and preservation of the
   503 + `Retry-After` + `Cache-Control: private, no-store` response policy.
   Copy must not claim data was lost, published, or changed.
3. **Pre-warm on sign-in intent**: when `/auth/sign-in` runs (immediately
   before the Easy Auth redirect), fire one non-blocking, fully
   error-swallowed, short-timeout background attempt to open a database
   connection so the serverless resume starts while the member is on the
   Microsoft page. It must never delay or fail the redirect, never run when
   auth is disabled, and never log secrets. Keep it dead simple (daemon thread
   + try/except); if this cannot be done safely within those bounds, deliver
   items 2.1/2.2 and report the pre-warm as deferred with the reason.
4. Reduced motion: any spinner/pulse respects `prefers-reduced-motion`.
5. Accessibility: the waking state announces politely (`role="status"` /
   `aria-live="polite"`), not as a repeated interrupting alert.

## Item 5 — signed-in mobile header overlap

Problem evidence: `artifacts/2026-08-02-signin-experience-assessment/20-mobile-home.png`
— at 390 px signed-in, the theme toggle renders on top of the PeerSlate
wordmark in the public header (`templates/base.html` nav; signed-in adds the
"My Slate" and "Sign out" controls, and the row no longer fits). Fix the
layout so no control overlaps any other element at mobile widths, signed in
and signed out, light and dark, at 320 / 360 / 390 / 414 px. Preserve every
existing control and the locked visual design; adjust flex sizing, wrapping,
spacing, or ordering only. Do not remove the toggle, restructure the nav, or
change desktop rendering (byte-identical desktop DOM/CSS behavior above the
mobile breakpoints; visual no-change verified by screenshot comparison).

## Reserved files

`auth_routes.py` (workspace/sign-in routes only), `owner_routes.py` only if a
shared waking helper requires it, `templates/identity_storage_unavailable.html`,
`templates/owner_home.html` + `templates/partials/owner_home/*` (waking/failure
state only), `templates/base.html` (header only), the CSS files that style
those surfaces, one optional small static JS file for the retry behavior,
focused tests (`tests/test_auth.py`, `tests/test_owner_home.py`, new focused
files), and this package folder. Nothing else — no Settings/Capture chrome
work (deferred item 3), no "coming later" changes (deferred item 4), no
Interview Studio, Community, Journal, Studio, or homepage content changes.

## Evidence required

- Focused tests for: the two distinguished `/app` failure states, response
  policy headers, auto-retry markup presence, pre-warm never blocking or
  failing the sign-in redirect, and header layout (as testable).
- Guardrail suites green: `tests/test_site_rules.py`,
  `tests/test_governance_pointers.py`; plus the full suite result.
- Headless Playwright screenshots (the interactive browser pane cannot
  composite in this environment): waking states desktop + 390 px, header at
  320/360/390/414 signed-in/signed-out light/dark, desktop header unchanged.
  Local signed-in rendering recipe: run the app from this worktree with
  `PEERSLATE_ALLOW_DEV_IDENTITY=true`, `PEERSLATE_DEV_USER_KEY=test-user-1`,
  `PEERSLATE_OWNER_HOME_ENABLED=true`; force storage-unavailable states with
  an intentionally unreachable `AZURE_SQL_CONNECTIONSTRING`; never print or
  commit secret values; use a free local port other than 5000 if 5000 is busy.
- Complete-diff self-review and a compact completion record in this folder.

## Release boundary

This package stops at a pushed branch, PR readiness, and evidence. The Azure
PR may be created but not completed before Pete's acceptance of the visual
evidence. Deployment claims require the pipeline and live verification per
`docs/AI_WORKFLOW.md`.
