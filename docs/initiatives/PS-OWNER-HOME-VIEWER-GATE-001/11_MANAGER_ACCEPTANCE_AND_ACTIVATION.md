# PeerSlate Completion & Handoff Report — Owner Home Architecture Acceptance

## A. Status

- Package: `PS-OWNER-HOME-VIEWER-GATE-001` manager architecture review and
  activation.
- Status: **Accepted** on 2026-07-19. The architecture gate is closed; the
  first implementation slice remains sequential and default-off.
- Reviewed handoff: branch
  `work/2026-07-19-owner-home-fable-architecture` at
  `516177c7cf10caaf85dafce8b6fc3f713b831a94`.
- Synchronized authority: current Azure DevOps `origin/main` at
  `8da639fd47df5af7c1a146fb8ccb8992805bd7a5` (Bible v2.6 / Roadmap v2.5),
  merged cleanly into the review branch before this disposition.
- PR / pipeline / environment: recorded in the external handoff after this
  manager record is committed because a commit cannot contain its own SHA.
- Production state: architecture and activation records only. Owner Home is
  not implemented, deployed, enabled, or live; `/app` remains the released
  owner workspace.
- Visual authority and status: the dark cinematic authority candidate
  `31864e4` is accepted and binding; real-product visual acceptance is still a
  later frontend gate.
- Homepage product projection: **Not Applicable today** — `/` does not present
  Owner Home. `PS-HOME-FRONTEND-001` must reassess this at release.
- Pete / designated session manager visual acceptance: Pete accepted the
  production-intent direction and exact dark shell/atmosphere; final visual
  acceptance of implementation is pending.
- Designated session manager: ChatGPT Work/Codex manager session.
- Manager handoff status and next receiver: `PS-HOME-BACKEND-001` is activated
  and assigned to a ChatGPT Codex backend writer, queued behind the already
  allocated `PS-CAPTURE-PHOTO-BACKEND-001` shared-file lane. Its fresh branch
  starts from `origin/main` only after that lane merges or relinquishes its
  overlapping reservations.
- Lane owner and self-managed authority: the backend writer owns its fresh
  branch through implementation, complete-diff review, evidence, PR readiness,
  and accepted release/closeout.
- Self-certification: **Pass** for architecture acceptance and activation. No
  runtime implementation is certified by this report.
- Complete-diff review: passed after correcting the release-order boundary,
  shell scope, flag naming, and migration-path drift described below.
- Acceptance requested: manager/governance closeout only.

## B. What changed technically

The manager reviewed the full Fable package and accepted the finite owner-only
Home as the first slice. Decisions U1–U6 are resolved as follows:

| ID | Binding manager decision |
|---|---|
| U1 | `auth.owner_workspace` passes a server-owned boolean such as `standalone_owner_shell=True` only for the flag-on Owner Home render. `base.html` uses that boolean to bypass the legacy forced-desktop tablet viewport script and suppress the public site sky, global header and profile tabs, portfolio profile band, public footer, Ask Pete AI launcher/panel, public search data, global theme-preference bootstrap, global mobile tabbar, and the four public-chrome scripts (`chatbot.js`, `site-search.js`, `mobile-nav.js`, `theme-toggle.js`). It omits `portfolio-shell`/`platform-shell`, `slate-light`, and `ps-editorial-surface` and adds only the route-scoped Owner Home body class. The skip link, shared fonts/base styles, and single base `<main id="main-content">` remain. Tests prove every flag-off and non-Owner-Home render is byte/DOM-inert. |
| U2 | Ship the exact accepted `assets/owner-home-alpine-atmosphere.png` as the production atmosphere source for the first release. Do not regenerate, recrop, recolor, or substitute it. Any later optimization is a separately reviewed, visually indistinguishable derivative with the accepted PNG retained as authority and fallback. |
| U3 | Suppress the global `mobile-tabbar` and `mobile-nav.js` on the standalone Owner Home render. Render exactly one page-scoped Owner Home mobile bottom navigation: Home and Capture are real; Journal, Slate, and More are visibly disabled `Coming later` items with no routes or handlers. |
| U4 | Keep `GET /app` as the canonical Owner Home route. Retain `owner_workspace.html` as the exact flag-off fallback through backend, frontend, and founding-alpha stabilization. Retirement requires a separate cleanup decision after accepted Home is enabled and stable. |
| U5 | Close `PS-OWNER-HOME-VIEWER-GATE-001`, activate and assign `PS-HOME-BACKEND-001` behind the current Capture Photo backend shared-file lane, and record `PS-HOME-FRONTEND-001` as sequenced after the Home backend merge. Broader viewer/preview modes remain inactive. |
| U6 | First slice includes all three released workflows: `voice_draft_failed` (`voice_media_sources.state='failed'`), `moment_proposal_pending` (`moments.status='proposal'`), and `voice_draft_ready` (`voice_media_sources.state='needs_review'`). Urgency is failed Voice → pending Moment → ready Voice; within a kind, oldest actionable `updated_at_utc` first, then stable opaque key. Deleted/deletion-pending/confirmed records are excluded. Each row links only to its released protected review route. |

One manager correction is also binding: the backend package must be independently
deployable before the frontend exists. It therefore implements the default-off
flag, bounded service/read procedure, and flag-gated JSON endpoint, but it does
**not** modify `auth_routes.py` or select `owner_home.html`. With the flag off,
the JSON route returns neutral `404 {"error":"not_found"}` before retrieval.
With the flag on, anonymous JSON returns `401 authentication_required` and an
authenticated owner receives the bounded no-store payload. The later frontend
package owns the `/app` flag-on template switch and HTML no-store response.

Package drift was corrected to use `PEERSLATE_OWNER_HOME_ENABLED` consistently,
to reserve `app.py` only for default-off configuration in the backend slice,
and to place migrations under `SQL FIles/Migrations/proposed/` with verification
at `SQL FIles/Verification/PS-HOME-001_owner_isolation_verify.sql`.

## C. What this means in plain English

The approved design can now move into construction without asking the backend
writer to guess. The first build creates a private, small, predictable Home data
contract and leaves the visible website unchanged. The visual build starts only
after that backend has merged, then replaces `/app` behind the same off-by-default
switch while preserving an instant fallback to the current workspace.

## D. What the website or member can do now

Nothing new yet. No route, database object, template, stylesheet, JavaScript,
feature flag, or production behavior is changed by this manager review. Owner
Home, viewer modes, insights, connections, and resurfacing remain unavailable.

## E. How this connects to PeerSlate

This activates the Roadmap's finite Owner Home direction without turning Home
into a feed or duplicating canonical Capture/Moment truth. Authorization happens
before retrieval, every record remains owner-scoped and private, Capture remains
dominant, and future capabilities remain truthful disabled previews. The dark
cinematic shell follows Pete's explicit surface-specific decision and the Owner
Visual Integrity Standard.

## F. Verification and validation

- Read and followed `START_HERE.md` and `docs/AI_WORKFLOW.md`.
- Fetched Azure DevOps `origin`, preserved the unrelated primary-checkout work,
  and reviewed in the dedicated clean Fable worktree.
- Read the complete current Bible v2.6, Roadmap v2.5, baseline/state/initiative
  records, visual/story standards, manager handoff, full Fable package, both
  implementation briefs, and the completion-report template.
- Inspected the released `/app` route, `base.html` chrome, Moment schema and
  review route, Voice schema/states and review route, migration conventions,
  feature-flag convention, and governance guardrails.
- Visually compared the binding owner baseline and accepted desktop, 390px,
  320px, and future-state exports; the documented 320px collision remains D1
  implementation work.
- `python -m unittest tests.test_governance_pointers tests.test_site_rules -v`
  → **27 tests passed**.
- `python -m unittest discover -s tests` → **496 tests run, OK, 1 skipped**;
  the skip is the existing environment-conditional isolated SQL gate.
- `git diff --check` → clean. A distinct complete-diff review confirmed that
  the manager edits are limited to package/governance records and their
  guardrail; no runtime, template, CSS, JavaScript, SQL, infrastructure, or
  secret file changed.

## G. Known gaps, risks, and exclusions

- Performance, SQL apply/rollback, and two-owner payload evidence are backend
  implementation gates, not architecture-review evidence.
- The Windows design generator fix still needs runtime proof on a Node-capable
  machine; this does not block consuming the preserved accepted PNG.
- Viewer modes, selected-person/connection/member/public projections, My Slate
  preview, resurfacing policy, governed insights, and connections are excluded.
- Current `origin/main` assigns `PS-CAPTURE-PHOTO-BACKEND-001` first and that
  package reserves `owner_routes.py` and `services/database_service.py`.
  Owner Home is assigned but must not create its branch until those reservations
  merge or are explicitly relinquished; unmerged branch blending is forbidden.
- `PS-HOME-FRONTEND-001` is sequenced, not active; no frontend writer may start
  before the backend squash merge and green pipeline.
- Nothing in this acceptance claims Owner Home is deployed or live.

## H. Clear next step

Complete and merge (or explicitly relinquish) the already allocated
`PS-CAPTURE-PHOTO-BACKEND-001` shared-file lane. Then the assigned ChatGPT Codex
writer creates `work/YYYY-MM-DD-home-backend-001` from that current Azure
DevOps `origin/main`, using `CODEX_BACKEND_IMPLEMENTATION_BRIEF.md` as corrected
by this record. Merge and verify the default-off Home backend before starting
the frontend package.

## I. What Pete needs to do or decide

None for backend start. Pete's next required gate is visual acceptance of the
real frontend implementation against the preserved authority.
