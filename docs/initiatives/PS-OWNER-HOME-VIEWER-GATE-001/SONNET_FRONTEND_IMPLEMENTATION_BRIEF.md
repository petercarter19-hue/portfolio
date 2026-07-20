# SONNET_FRONTEND_IMPLEMENTATION_BRIEF — PS-HOME-FRONTEND-001

Prepared 2026-07-19 by the Claude/Fable architecture writer for the future
Sonnet frontend implementation lane. **Do not start until:** (1) ChatGPT
Work/Codex accepts this architecture package, (2) `PS-HOME-BACKEND-001` is
squash-merged to `origin/main` with its pipeline green and
`PEERSLATE_OWNER_HOME_ENABLED` defaulting off. Decisions U1–U4 are resolved in
`11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`; they are binding, not a new design gate.

## 0. Non-negotiables

- Start a fresh `work/YYYY-MM-DD-home-frontend-001` branch from the
  post-backend `origin/main`. Follow `START_HERE.md` and `docs/AI_WORKFLOW.md`.
- **Consume the real bounded owner view model** rendered by the backend
  package (`owner-home.v1` via `services/owner_home_service.py` /
  `GET /api/v1/owner/home`). **Never create fake client-side records**, fixture
  data in production paths, or a second data model.
- The accepted visual authority is binding (see
  `01_FABLE_AUTHORITY_MANIFEST.md`): baseline
  `docs/governance/approved_owner_visual_baseline/01_owner_home_interface_mockup.png`
  plus authority candidate `31864e4` preserved at
  `artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`.
  **Owner decision 2026-07-19: implement the dark cinematic shell, alpine
  atmosphere, and backgrounds exactly as those images show.** Match or exceed;
  no alternate visual direction; only deviations D1–D6 are pre-approved.
- Nine-object maximum, three-review maximum, honest states, and content-free
  disabled **Coming later** previews are product law
  (`FINITE_HOME_CONTRACT.md`).

## 1. Files you own (exact reservation)

- `templates/owner_home.html` (new)
- `templates/partials/owner_home/_*.html` (new partials, inventory in
  `05_FABLE_FRONTEND_IMPLEMENTATION_ARCHITECTURE.md` §1/§3)
- `static/css/owner-home.css` (new)
- `static/js/owner-home.js` (new, optional enhancement only)
- `static/img/owner-home/**` (atmosphere + abstract section material)
- `auth_routes.py` — **only** the minimal flag-on `owner_home.html`
  selection/bootstrap integration; the backend package deliberately leaves
  this file and `/app` unchanged
- `templates/owner_workspace.html` — read-only exact flag-off fallback through
  founding-alpha stabilization (decision U4)
- `templates/base.html` — only the server-owned standalone-shell conditional
  defined by U1/U3
- `tests/test_owner_home.py` (extend), `tests/test_owner_home_accessibility.py`
  (new)
- `docs/initiatives/PS-HOME-FRONTEND-001/**`,
  `artifacts/ps-home-frontend-001/**`

**Do not touch:** `base.html` beyond the manager-approved U1/U3 conditional,
`owner_routes.py`, `style.css`, `owner-app.css`, `mobile-nav.js`,
`theme-toggle.js`, Voice/Capture/Moment/Interview/Story/homepage files,
`services/**`, SQL, `identity.py`, shared governance records.

## 2. Build order

1. **Tokens and shell.** Route-local `--oh-*` tokens from the authority
   palette (Deep Navy `#071421`, Elevated Navy `#0D2133`, Cloud White
   `#FFFDF8`, Warm Ivory `#F5F0E7`, Paper `#FBF8F2`, Marigold `#D9AA2B`,
   text-safe gold `#8A5A00`, Focus `#FFD75E`, Success `#1E725F`, Error
   `#A43737`). Typography: Newsreader display serif + Inter UI (already loaded
   by `base.html`) replacing the candidate's Georgia/Arial stand-ins (D5).
   Implement the U1/U3 server-owned conditional: bypass the legacy tablet
   forced-desktop viewport code and suppress complete public chrome plus all
   four public-chrome scripts only on the flag-on Home render; shared fonts/base
   styles, skip link, and single base main retained; flag-off `/app` and all
   other routes inert.
2. **Server-rendered composition.** Template + partials in the exact reading
   order of §3 of the frontend architecture; one `<h1>`; no nested
   `<main id="main-content">`.
3. **States.** All server-decidable states (empty, populated, partial failure,
   complete failure, stale, restricted, session-expired) render without JS.
4. **Coming-later previews.** Voice-pattern semantics: visible label text,
   native `disabled` + `aria-disabled="true"` where applicable, no `href`, no
   handlers, excluded from forms, zero requests; wording
   `"[Feature] — coming later. Not yet available."`
5. **Enhancement.** `owner-home.js` category retry + announcements + focus
   management only; no payload persistence.
6. **Refinements.** Implement D1 (320px Noticed/Next-step reflow), D2
   (truthful labels once, no fixture pills), D3 (distinct per-section abstract
   material — no people, records, counts, or member-like photography).
7. **Evidence.** Full matrix in
   `10_FABLE_REVIEW_CHARTER_EVIDENCE_MATRIX.md` §2/§4/§5: focused tests,
   accessibility tests, guardrail + full suite, named screenshots at
   1440/844/390/320 across all states, parity matrix against authority
   exports, NVDA/keyboard/forced-colors/reduced-motion/200%-zoom evidence,
   two-owner DOM canaries, homepage-impact reassessment.
8. **Report.** Standard completion report; self-certify `Pass`/`Conditional`/
   `Fail`; request Pete + designated-manager visual acceptance. Release
   actions only after acceptance.

## 3. Truth rules you must render, not reinterpret

- Capture links to the real protected Capture experience; it is the only
  dominant action.
- Review rows come from `review_items[]` (max 3), with opaque keys and
  protected destinations; the bounded remainder is shell context, never a
  fourth record.
- `recent_moment` / `resurfaced_moment` / `noticed_item` / `connection_item`
  may be `null`; `availability.state = coming_later` renders the dormant
  preview in the same single slot. In the first slice, Resurfaced, Noticed,
  and Connections are expected to be dormant.
- `next_step` names a real action and destination; if it repeats Capture it
  must not visually compete with the primary Capture card.
- Never call `/api/dashboard`; never fetch broadly and hide; never persist a
  payload offline; never add a route or request to a Coming-later control.

## 4. Acceptance

Your package passes only when: focused + guardrail + full suites are green;
the parity matrix shows match/exceed or an approved deviation ID on all 20
areas; accessibility evidence is complete; two-owner canaries pass at the DOM
layer; the homepage-impact check is recorded; and Pete plus the designated
session manager accept the real rendered product. Then complete the Azure PR,
pipeline, live verification (flag-off default preserved), and closeout per
`docs/AI_WORKFLOW.md`.
