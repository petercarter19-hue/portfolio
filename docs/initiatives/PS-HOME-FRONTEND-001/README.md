# PS-HOME-FRONTEND-001 - Exact-Authority Owner Home Frontend

## Assignment

- Package: `PS-HOME-FRONTEND-001`
- Roadmap position: Phase 4 - Owner Home and viewer modes, first finite owner
  Home frontend only
- Designated session manager: current ChatGPT Work/Codex manager session
- Sole implementation writer: the separately assigned Codex frontend task
- Manager activation branch:
  `work/2026-07-20-home-frontend-manager`
- Activation base: Azure DevOps `origin/main` at
  `b7b674415f1f7c9ac2844fa0482091b62a7ec979`
- Required implementation branch:
  `work/2026-07-20-home-frontend-001`
- Entry gate: create the implementation branch from exact post-activation
  `origin/main` only after this governance release and its Azure pipeline pass
- Current production state: Owner Home backend deployed default-off;
  `PEERSLATE_OWNER_HOME_ENABLED=false`; `/app` remains the existing owner
  workspace; no new Owner Home interface is live

This package activates implementation of the already accepted Owner Home
frontend. It is not a new visual direction, backend expansion, viewer-mode
release, or production enablement.

## Controlling authority

The writer must read the complete
`PS-OWNER-HOME-VIEWER-GATE-001` and `PS-HOME-BACKEND-001` packages before
product edits. The controlling implementation sources are:

- `docs/governance/approved_owner_visual_baseline/01_owner_home_interface_mockup.png`
- `artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`
- `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/SONNET_FRONTEND_IMPLEMENTATION_BRIEF.md`
- `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/05_FABLE_FRONTEND_IMPLEMENTATION_ARCHITECTURE.md`
- `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/06_FABLE_VISUAL_PARITY_DEVIATION_REGISTER.md`
- `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/07_FABLE_FILE_RESERVATIONS_INTERSECTIONS.md`
- `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/10_FABLE_REVIEW_CHARTER_EVIDENCE_MATRIX.md`
- `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/FINITE_HOME_CONTRACT.md`
- `docs/initiatives/PS-HOME-BACKEND-001/README.md`
- `docs/initiatives/PS-HOME-BACKEND-001/COMPLETION_REPORT.md`
- `01_MANAGER_ACTIVATION_AND_EVIDENCE_DISPOSITION.md` in this package

The binding visual direction is the dark cinematic navy-and-gold shell, exact
accepted alpine atmosphere, luminous ivory working stage, unequal editorial
hierarchy, and one dominant Capture action. The accepted alpine source asset is
copied without regeneration, recropping, recoloring, or substitution. Only
deviations D1-D6 are pre-approved.

## Released backend contract

The first frontend consumes the released `owner-home.v1` view model. It does
not add fields, endpoints, SQL, services, client-side aggregation, or a second
Home truth.

The finite top-level contract remains:

- `schema_version`
- `owner`
- `generated_at`
- `state_version`
- `capture_action`
- `review_items`
- `recent_moment`
- `resurfaced_moment`
- `noticed_item`
- `connection_item`
- `next_step`
- `availability`

The server supplies at most three review items and nine finite Home objects.
Unavailable resurfacing, noticed, connection, Journal, Slate, and broader
viewer capabilities remain content-free, genuinely disabled `Coming later`
presentation. The frontend may not fabricate a person, record, count,
recommendation, insight, relationship, or member-like result.

## Exact writable reservation

The implementation writer may change only:

- `templates/owner_home.html`
- the exact `templates/partials/owner_home/_*.html` inventory defined by the
  accepted frontend architecture
- `static/css/owner-home.css`
- optional progressive enhancement in `static/js/owner-home.js`
- `static/img/owner-home/**`
- `auth_routes.py`, limited to flag-on Owner Home template/bootstrap selection
  and private no-store/error handling
- `templates/base.html`, limited to the accepted server-owned U1/U3 standalone
  Owner Home conditional
- `tests/test_owner_home.py`
- `tests/test_owner_home_accessibility.py`
- `docs/initiatives/PS-HOME-FRONTEND-001/**`
- `artifacts/ps-home-frontend-001/**`

`templates/owner_workspace.html` is read-only and remains the exact flag-off
fallback.

The writer must not edit `owner_routes.py`, `services/**`, SQL, migrations,
`identity.py`, `app.py`, shared CSS/JavaScript, homepage/Interview files,
Voice, Capture, Photo, Moment, Placement, Story, Resume, Slate Board, Feed,
Community, Journal, shared governance, credentials, local launch files, or
production settings. Any newly required file is a manager stop, not inferred
permission.

## Truthful first-release evidence boundary

The accepted review charter contains aspirational states beyond the released
backend contract. This activation resolves that mismatch without inventing
frontend behavior.

Required real runtime evidence for this first release is:

- exact flag-off `/app` fallback;
- successful empty Home;
- successful populated Home at the three-review/nine-object ceiling;
- complete content-free unavailable/failure handling;
- an actual retry or fresh-navigation recovery after the complete failure;
- truthful `coming_later` availability;
- long and bidirectional content within the released fields;
- missing optional presentation media without broken layout;
- desktop, 390px, 320px, narrow-height, 200% zoom/reflow, keyboard/focus,
  forced-colors, reduced-motion, and no-JavaScript behavior; and
- two-owner/privacy canaries, no-store behavior, unchanged non-Owner routes,
  and no fabricated DOM/network/storage state.

Partial category failure, stale/`409 state_changed`, and restricted runtime
states are not representable by `owner-home.v1`. They remain future
design authority only. They are not first-release implementation or screenshot
requirements and may not be simulated in production code, query parameters,
fixtures on the member path, or client-only state. A later package must first
extend and verify the server contract before those states become runtime gates.

A loading treatment is evidence only when tied to a real navigation or retry.
It may not make a server-rendered no-JavaScript result depend on JavaScript.

## Parallel coordination

- `PS-HOME-INTERVIEW-PARITY-001` owns only its bounded homepage Interview
  partial, CSS/JavaScript, include/cache references, tests, and evidence.
- Owner Home owns no homepage file. Its `base.html` conditional must be inert
  on `/` and every non-Owner-Home route.
- Capture Photo architecture owns no Owner Home file. Future Photo runtime work
  may use `owner_routes.py`; this Owner Home frontend is expressly forbidden
  from that file.
- If another lane merges first, the writer synchronizes from current
  `origin/main`, resolves only in-scope changes, and reruns affected focused,
  homepage, site-rule, governance, and full-suite evidence.
- The implementation branch may not edit shared governance.

## Acceptance and release boundary

The writer self-manages implementation, complete-diff review, corrections,
tests, visual evidence, and `Pass`, `Conditional`, or `Fail` reporting. It must
return the exact pushed branch SHA and real desktop/mobile evidence for Pete
and designated-manager visual-product acceptance before opening the Azure
implementation PR.

The implementation deploys with `PEERSLATE_OWNER_HOME_ENABLED=false`. It may
not enable Owner Home, change production settings, claim the interface live,
or begin broader viewer modes. Controlled founding-alpha enablement requires a
separate explicit owner/manager decision after flag-off production
verification.

The logged-out homepage does not project Owner Home today, so homepage impact
is currently `Not Applicable`. The writer must recheck that fact at release.

## Single next action

After this manager activation squash-merges and its Azure pipeline succeeds,
the assigned Codex frontend writer creates
`work/2026-07-20-home-frontend-001` from that exact `origin/main` and performs
the mandatory entry/read-only confirmation before any product edit.
