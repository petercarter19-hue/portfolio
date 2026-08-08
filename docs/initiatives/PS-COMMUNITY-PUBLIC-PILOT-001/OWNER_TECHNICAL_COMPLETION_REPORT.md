# PeerSlate Completion Record

## 2026-08-07 protected recovery and public-demo release closeout

- **Task/package and delivery path:** `PS-COMMUNITY-PUBLIC-PILOT-001`,
  Protected.
- **Outcome and member/site effect:** **Conditional owner pilot live.** The
  owner-only canonical Community runtime, protected Voice workflow, media and
  conversation lifecycle, retention/restore procedures, and independent
  maintenance runner are deployed. When the successful canonical Feed read is
  empty, `/the-slate` presents the owner-approved, clearly labelled Pete-only
  public demo. Its text, local attachment preview, Respond, comment, Motion
  cards, conversation, and Voice controls are hands-on but have no publish or
  send action and create no Community record. A real public post replaces the
  demo automatically; demo and canonical rows never mix.
- **Branch, base, final SHA, and changed paths:** recovery branch
  `work/2026-08-07-community-revival-safety-v1`, activated from
  `819d348928f73ac3b526801f43dd370b1b6b06c1`; reviewed recovery merged through
  PR 326, deployment guard through PR 327, and public demo through PR 328 as
  exact main `1806d20c23736140fea787ea7cd8fb105c99e7f9`. Changed paths are the
  package-recorded Community runtime, maintenance, additive migration,
  pipeline, tests, demo projection, and Community-only UI/evidence surfaces.
- **Verification performed and result:** recovery validation passed 489
  relevant tests and 2,901 repository tests with 5 intentional skips; the
  public-demo follow-up passed 329 relevant tests, JavaScript/Python/dependency
  checks, desktop/narrow browser checks, and deterministic signed-out and
  signed-in Voice proofs. Independent Protected review reproduced 116 focused
  tests plus the Voice browser proof with no blocking finding. Azure PR policy
  passed without bypass. Production pipeline 610 succeeded for the exact
  merged SHA. Live `/healthz` is healthy, the Feed API returns
  `demo_mode=true` with one item and a truthful caught-up state, the browser
  shows 12 Motion cards with no console error, and unsigned post/Voice commands
  fail closed at the same-origin and authentication boundaries.
- **Schema, maintenance, and release state:** generated production state shows
  all 25 registered production migrations through additive
  `PS-COMMUNITY-REVIVAL-001`; no existing migration was rewritten. Community
  visibility is enabled on `peerslate-pete`. The independent hourly
  maintenance flag is enabled; scheduled runs 609, 611, and 612 succeeded
  under the narrow maintenance identity. Production reports opaque release
  `a00f609a6f82870292a3a0d5` for exact deployed source `1806d20c...`.
- **Protected boundaries:** identity remains server-derived; only the
  configured owner can mutate canonical Community state; drafts remain local
  and private; Public selection, confirmation, reviewed Voice transcript
  insertion, and publish/send remain separate actions. Signed-out and
  non-owner mutation is denied. Public demo Voice never uploads or transcribes;
  signed-in owner Voice uses the existing transient Speech boundary.
- **Known limits:** this is not broad Community launch. No broader member
  authorship, messaging, AI publication, public audio/video, alternate
  audience, or Journal projection is enabled. No canonical public post exists
  at closeout, so the live demo is intentionally visible. The final automated
  browser was signed out and therefore did not create a production post or
  exercise a real authenticated mutation; doing so would contradict Pete's
  requested no-submit review boundary. The real owner path is deployed and
  test-covered, but its first live publish remains a deliberate owner action.
- **Next action:** `None` for this release task. A later owner-authored post may
  be published through the separate signed-in composer when Pete chooses; any
  expansion beyond the narrow owner pilot requires a new activated package.

The earlier local-only records below remain historical evidence and are
superseded wherever they describe Community as unmerged, flag-off, or lacking
Voice/release work.

## 2026-08-01 primary Feed continuation addendum

The current bounded result is recorded in
`PRIMARY_FEED_MAC_CONTINUATION_CHECKPOINT_2026-08-01.md`. It reconciles the
checksum-verified PC continuation into the sole Mac writer lane and renders the
real local primary Feed with Pete's owner-corrected 748px card, compact Respond/comment
controls, one horizontal `Replies & updates` shelf, supporting desktop rails,
and owner-approved restrained color treatment. Focused Community checks pass
110 tests, adjacent boundary checks pass 59 tests, the focus harness passes 10
checks, and desktop/narrow browser evidence is captured.

This addendum is **primary-page review only**. It is not feature completion,
release readiness, Candidate approval, migration, deployment, flag activation,
or live Community evidence. Pete approved this exact primary page on
2026-08-02 and instructed the writer to continue. Full-conversation, nested
reply, and protected Community Voice work are therefore open as the next local
tranche; retention, infrastructure, Candidate, and release work remain closed
until their package gates are satisfied. The historical record below remains
evidence of the broader package state at its earlier checkpoint; where its
“next action” or visual-status wording conflicts, this dated addendum and the
continuation checkpoint control the current primary-Feed status.

## Core record

- **Task/package and delivery path:** `PS-COMMUNITY-PUBLIC-PILOT-001`,
  Protected.
- **Outcome and member/site effect:** **Conditional — local implementation and
  fixture-backed browser validation are substantially complete, but the pilot
  is not yet safe to merge, deploy, enable, or use on the public site.** The
  current code provides the owner-authored public Community Feed contract
  behind a default-off flag. It does not establish a live Azure SQL/Blob
  instance or production Community content.
- **Branch, base SHA, final SHA:**
  `codex/2026-07-31-community-public-pilot-runtime` /
  `2494aa73ed95bfbe97d8cf42f712b9929759e0b2` / no final SHA; the reviewed
  source is intentionally uncommitted while the release-blocking scope and
  owner decisions below remain open.
- **Changed paths and reasons:**
  - `.env.example`, `app.py`, `community_routes.py`, `community_api.py` —
    default-off configuration, route registration, owner/public HTTP boundary,
    and attachment delivery.
  - `services/database_service.py`, `services/community_*.py` — SQL access,
    contracts, keyset cursors, owner-authorized commands, finite Feed reads,
    and private media lifecycle/storage.
  - `templates/community_*.html`, `static/css/community-v1.css`,
    `static/js/community-v1.js` — exact-lock
    Community surface, responsive states, local-only composer drafts, search,
    conversations, interactions, uploads, and accessibility behavior.
  - `SQL FIles/Migrations/proposed/PS-COMMUNITY-PUBLIC-PILOT-001*`,
    `SQL FIles/Verification/PS-COMMUNITY-PUBLIC-PILOT-001*`, and
    `scripts/apply_sql_migrations.py` — idempotent Community schema/procedures,
    guarded rollback, owner/public verifier, and migration execution support.
  - `tests/test_community_public_pilot.py` and
    `tests/test_community_public_pilot_verifier.py`, plus
    `tests/test_community_xlsx_support.py` — authorization, privacy,
    publication, server-derived contribution kind, idempotency, cursor, media,
    strict OOXML/XLSX security, UI/static-contract, and verifier regression
    coverage.
  - `docs/governance/CURRENT_BASELINE.yaml` and this initiative package —
    bounded ownership, default-off release record, implementation contract, and
    evidence/status. The package includes an exact proposed retention decision
    for Pete; it is explicitly not approved or implemented.
  - `/Users/petercarter/portfolio/outputs/community-feed-gate-20260801/`
    contains the owner-review XLSX gate tracker and its generated inspection
    evidence. It is a review artifact, not a production Community row.
- **Verification performed and result:**
  - Combined Community runtime, verifier, and adversarial XLSX suite: **PASS**,
    104 tests.
  - Full repository suite with a non-secret test placeholder for the required
    Anthropic import variable: **PASS**, 1,182 tests; 2 intentional skips.
  - Independent-review migration regression suite: **PASS**, 45 tests and 1
    intentional skip.
  - JavaScript syntax, Python compile, dependency integrity, diff whitespace,
    changed-file secret-pattern scan, and all 25 dynamic SQL batch extraction
    checks: **PASS**.
  - Fixture-backed browser checks: **PASS** for desktop, narrow mobile,
    landscape, dark theme, signed-out read-only, composer publication gating,
    upload states, search/no-results, conversation/reply depth, save failure
    recovery, permission/error/empty/caught-up states, focus restoration, and
    320 CSS-pixel reflow. The 2026-08-01 owner-feedback recapture additionally
    proves a 462-by-202-pixel full-content-width Feed image, four shelf cards in
    a 748-pixel scroll extent within a 462-pixel viewport, compact visible
    `View all` with the full accessible name, two XLSX-capable file inputs, no
    contribution-kind control, working menu dismissal/copy action, and the
    fixture workbook card on the newest small-win conversation. This is not
    live SQL/Blob, real-device tablet, or true browser 200% zoom evidence.
  - The generated three-sheet workbook rendered successfully; re-import found
    no formula errors. Its 16,467 bytes pass the strict runtime validator with
    SHA-256 `dc9670da46574424761cc7cec00980e88e5071442834a6382b39383c1c1a0520`.
  - Complete-diff independent release/security review of the latest integrated
    pass is **complete with no open P0/P1/P2 code findings**. Review confirmed
    the strengthened XLSX package controls, exact migration-drift checks,
    rollback dependency refusal, ancestor-complete conversation paging,
    server-derived contribution types, and XLSX reserve-to-ready SQL
    verification. The product, visual, retention, infrastructure, and release
    blockers below still prevent acceptance or flag enablement.
- **Release state:** **local only**. No final commit, push, PR, merge, Candidate
  run, SQL migration, production pipeline, App Service configuration change,
  flag enablement, or live verification has occurred.
- **Known limits, deferred work, and owner decisions needed:**
  1. The reserved Community bundle now restores `width=device-width` after the
     shared shell's touch-tablet override. Independent re-audit accepts this as
     closing the known code/scope defect. Native tablet/reflow remains a
     release-evidence gate until the corrected build is captured on a
     qualifying touch tablet, in both orientations and zoom/reflow states.
  2. The locked boards place Community search and New Post in the visual
     header, while the bounded implementation preserves the existing global
     shell and supplies a Community toolbar below it. Pete must accept that
     adaptation or authorize the exact shared-shell integration.
  3. Pete's two 2026-08-01 review rounds materially revised the Community type
     scale, Respond/icon family, post and image activation, full-conversation
     composition, integrated send/file/photo/video/Voice composer, visible
     Save/Open-post disposition, and contribution action placement. ChatGPT
     created the final two-board set and Pete exactly locked it, with manifest
     corrections, at
     `PS-COMMUNITY-FEED-VISUAL-001/visual-authority/2026-08-01-pete-voice-first-lock/`.
     The current review build predates and does not implement that authority.
  4. The legacy fixture JSON endpoint now returns neutral 404 while the pilot
     flag is on. Break's client-side tab swap can still display the sample Feed
     while the browser URL is `/the-slate`. The package requires fixture
     retirement but does not reserve `templates/the_slate.html` or
     `static/js/community-tabs.js`. A narrow reservation is required to omit
     only the legacy Feed panel in flag-on Break and make its Feed control a
     normal `/the-slate` navigation; flag-off behavior and Break content stay
     unchanged.
  5. `CURRENT_BASELINE.yaml` blocks future Protected Candidate release until
     Candidate exact-SHA admission is corrected or explicitly bounded.
  6. Pete approved the schedule in
     `APPROVED_RETENTION_AND_DELETION_DECISION.md` on 2026-08-03, exactly as
     proposed and live for this release wave, with a commitment to readdress
     it when Community moves behind the sign-in experience. The corresponding
     expiry/deletion job required by `PS-LEGAL-020` and `PS-LEGAL-022` is
     **still not implemented**. Immediate public revocation and 24-hour
     unattached-upload cleanup are implemented; they are not a complete
     retention/deletion program, and production must not collect Community
     content until the jobs and their evidence pass.
  7. Production rate-limit counters and cleanup cadence are process-local. The
     owner pilot must either use a documented single-instance/single-worker
     topology or add shared coordination.
  8. Community Voice/dictation is now a **P0 release blocker for Pete's usable
     public pilot**, not deferred work. No Community Voice control or runtime
     exists yet. The protected capture/transcription/review/cleanup contract and
     the exact front-and-center visual states must be locked and implemented on
     the original-post and every reply/update composer before the pilot can be
     called usable. Public audio attachments remain a separate requested media
     capability requiring an explicit protected release disposition. Video,
     real messaging, broader member authoring, signed-out interaction, AI,
     Slate projections, Connections/member-only audiences, and broad launch
     remain deferred unless separately promoted.
- **Next action:** a new Sol Ultra session must reconcile the protected
  architecture against the 2026-08-01 Pete lock, then implement only the
  primary Feed page and stop for Pete's browser review before secondary states
  or complete Voice implementation. After that owner checkpoint, the manager
  must finish the Community Voice slice, reserve the narrow Break integration,
  decide the shared-header adaptation, obtain the retention decision, resolve
  Candidate admission, and complete corrected-build/real-device evidence before
  any Candidate/migration/PR/pipeline/live sequence.

## Protected additions

- **Data, identity, privacy, authorization, deletion, and publication:**
  server-derived identity and owner allowlisting fail closed; signed-out and
  non-owner writes are denied; audience is explicitly Public per publish;
  author-scoped idempotency, revision preconditions, deterministic response and
  save commands, neutral missing-object behavior, private media delivery, and
  immediate public revocation have focused passing evidence. Forward/rollback
  SQL and a body-free verifier have static regression evidence only; they have
  not run against Azure SQL. Retention/deletion remains a failing release gate.
- **Material visual:** Pete's exact authority is
  `PS-COMMUNITY-FEED-VISUAL-001/visual-authority/2026-07-31-pete-public-pilot-lock/`.
  The reserved Community surface has fixture-backed state and accessibility
  evidence, but shared header ownership, corrected-build browser recapture,
  true 200% zoom, and real-device tablet evidence remain unresolved. Visual
  acceptance is therefore **Conditional**, not final.
- **Shared infrastructure and release:** feature flag defaults off; production
  content can be preserved by disabling it. Flag-on startup requires a
  dedicated Community signing key and does not derive it from an AI-provider
  key. There is no Candidate, migration, deployment, rollback execution,
  monitoring handoff, or live evidence.
- **Capability classification:**
  - **Implemented locally:** public Feed/read routes, owner-only post and
    contribution lifecycle, Respond/save, search, finite pagination, private
    local drafts, guarded JPEG/PNG/PDF/XLSX attachment lifecycle, strict
    workbook validation/download delivery, and server-derived contribution
    kind with no browser kind claim.
  - **Fixture/browser evidence only:** rendered Community UI behavior and
    signed-out/owner interaction flows.
  - **Not backend-live:** Azure SQL procedures/data, Blob uploads/Defender scan,
    cleanup lease behavior, and production authorization/configuration.
  - **Flag-disabled:** the complete Community public-pilot route family in the
    current production baseline.
  - **Unimplemented release blocker:** Community Voice/dictation across the
    original-post and every reply/update composer.
  - **Deferred or awaiting separate disposition:** material 2026-08-01
    composer/Respond/action re-layout, public audio attachments, video, member
    authoring, messaging, AI, projections, alternate audiences, moderation
    console, and broad launch.
- **Actual handoff:** none. The current Codex task retains the uncommitted
  working tree; no pushed SHA exists and no release owner has received it.
