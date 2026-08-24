# 01 — Repository reuse and gap map

All citations are against base SHA `958727c54832d700f3fd1628381bc5e3b5ce7543`
(`origin/main` at writing time). Line numbers drift; headings and symbol names
are the durable reference.

## 1. The two Opportunity Slate implementations and the conditional route

`app.py:806-809` registers exactly one canonical Opportunity Slate blueprint at
startup:

```python
if app.config['PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED']:
    app.register_blueprint(opportunity_slate_v2)
else:
    app.register_blueprint(opportunity_slate)
```

- The flag block (`app.py`, `PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED` comment,
  near lines 325–333) states: "Startup registers exactly one Opportunity Slate
  blueprint. False therefore remains an immediate, configuration-only rollback
  to the legacy experience; an App Service setting change causes the required
  process restart." The comment attributes the launch to
  `PS-OPPORTUNITY-SLATE-R1-LAUNCH-001`; no `docs/initiatives/` record with that
  ID exists at this SHA — the comment and the completion evidence below are the
  repository record.
- `docs/initiatives/PS-SIGNIN-MEMBER-ARRIVAL-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`
  ("What was wrong") records: "`PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED` is
  `true` in production, so this was live and member-facing, not latent.
  **Proven live, 2026-08-16**, owner-assisted with a real authenticated
  session." That is the newest repository evidence of production flag state.
  The literal current App Service value is **unverified** in this phase (no
  production access); confirming it is a C7/C8-entry check.
- The same report's "Honest limitations" notes the flag "cannot be exercised
  per-test, because `app.py:806-809` chooses the blueprint at import time" —
  a real testability constraint the architecture addresses (REC-04 in doc 15).

### Legacy v1 — `opportunity_slate_routes.py`

Blueprint `opportunity_slate` (defined near line 136). It is the complete
original workbench: `GET /opportunity-slate` room plus POST routes for
`source` (paste), `source/upload`, `source/import` (public-link import),
`source/corrections`, `source/confirm`, `source/delete`, `source/review`,
`source/concerns`, `requirements`, `requirements/corrections`,
`requirements/confirm`, `analysis`, `responses`, `save`, `reanalyze`,
`GET saved`, `delete`, `public-session`, and `public-session/propose`
(route decorators near lines 2728–4968). Rate limits for these endpoints are
registered in `app.py` (near lines 947–984). Under
`PS-OPPORTUNITY-SLATE-001` this shipped live in 2026-08-06; it is now the
configuration rollback behind the registration conditional. Its own
`PEERSLATE_OPPORTUNITY_SLATE_ENABLED` flag (default false; `app.py` near line
321) gates its routes with a neutral 404 before identity resolution when the
legacy blueprint is the registered one.

### Replacement v2 — `opportunity_slate_v2_routes.py` + `services/opportunity_slate_v2_service.py`

Blueprint `opportunity_slate_v2` at the same canonical `/opportunity-slate`
route. Module docstring (near line 27): "source (image 05). No requirement
interpretation, no alignment, no save" — v2 at this SHA delivers R1 stages 1–2
only: intake (`set_source`, `upload_source`, `import_source`), source identity
(`save_identity`), wording correction (`correct_source`), confirmation
(`confirm_source`), and deletion (`delete_source`). The remaining v2 stages —
AI requirement interpretation, requirement review, qualification analysis,
save/history, cutover, legacy retirement — are recorded as not included in
`docs/initiatives/PS-OPPORTUNITY-SLATE-002/README.md` ("What R1 does not
include"). That README's route-state sentences ("blueprint remains
unregistered, `app.py` is untouched") are **older evidence superseded by the
current `app.py`**; do not cite them as current route state.

### Schema state

`SQL FIles/Migrations/registry.json` orders the lineage; the derived record
`docs/governance/PRODUCTION_SCHEMA_STATE.md` shows `PS-OPPSLATE-001` (row 18),
`-002` (row 19), `-003` (row 20), and `-004` (row 27, applied
2026-08-12T14:44:53Z) all applied. The v2 replacement schema exists in
production per that derived record (live database state itself: unverified in
this phase, by boundary).

### Continuation boundary and current-use breakage

`docs/initiatives/PS-OPPORTUNITY-SLATE-CONTINUATION-001/README.md` is
**planned, not active**. It owns Opportunity Home, autosave, history/archive,
bounded workbench, and the "Urgent owner-reported diagnostic intake -
2026-08-14": Pete reports the live Slate "substantially broken in current use"
— a 2026-08-14 imported link shows in the source list with no expected
extracted content or usable downstream result, and the sidebar/workbench feels
broken. These are owner observations, not reproduced causes. Its "Extraction
direction" (deterministic fetch/decode/extract tooling; an LLM is not the
extraction authority) is preserved direction this architecture reuses for
doc 06. P0 does not absorb, diagnose, or fix any of it.

## 2. Trusted identity and owner scoping (reuse as-is)

- `identity.py` — `get_current_identity()` (near line 303): server-derived
  principal → `PeerSlateIdentity`, request-cached on `g`, raising
  `AuthenticationRequired`; `get_optional_identity()` for public surfaces.
- `opportunity_slate_v2_routes.py` `_resolve_identity_or_gate()` (near line
  273): the reusable per-route pattern — flag gate, same-origin write check
  (`_is_same_origin_write`, near line 228), anonymous → sign-in redirect with a
  same-origin-only return target, identity-lookup failure → truthful 503, never
  silently "signed out".
- `safe_return.py` — the single shared return-path validator with
  `PROTECTED_DESTINATIONS` (a tuple of `ProtectedDestination(prefix, flag)`
  entries; a flag-gated destination is a valid return target only while its
  flag is on) from `PS-SIGNIN-MEMBER-ARRIVAL-001`. **Concrete My
  Opportunities contract:** the canonical route prefix is
  `/my-opportunities`, registered as
  `ProtectedDestination("/my-opportunities",
  "PEERSLATE_MY_OPPORTUNITIES_ENABLED")` (the proposed surface-flag key —
  an architecture proposal, not deployed truth) — never
  a parallel allowlist. The companion shared surfaces are
  `static/js/auth-state.js` (cross-tab/bfcache signed-state guard, whose
  private-namespace coverage must include the new prefix),
  `static/js/easy-auth-callback.js`, and
  `tests/test_signin_member_arrival.py` (the round-trip and structural
  parity proof — an unregistered destination fails a test, not a member's
  journey). All four are reserved by the UI/routing child C8 (doc 14), the
  program's highest collision-risk claim, with a sole-writer stop control.
- Response hardening pattern: `_apply_room_headers` (near line 260) —
  `Cache-Control: private, no-store` and `X-Robots-Tag: noindex, nofollow,
  noarchive` on every private-room response. Mandatory for every My
  Opportunities member surface (also enforces the no-public-indexing product
  rule at the HTTP layer).
- `services/opportunity_slate_v2_service.py` — every method takes the
  server-derived `user_key` (`_require_user_key`, near line 474); opaque keys
  (`_opaque_key`), version tokens (`_version_token`), bounded text validation
  (`utf16_length`, `_bounded_text`) are the canonical service-layer idioms to
  reuse.

## 3. Evidence, Resume, Profile, Capture, Project, and Ask boundaries

- **Private evidence**: the legacy Slate's evidence flows and
  `PS-PROFILE-CORE-FOUNDATION-001` / `PS-PROFILE-EXPERIENCE-001` records exist,
  but per the R3 boundary (and `06_CURRENT_AUTHORITY_SNAPSHOT.md` in the
  external candidate), future Profile direction and unregistered Profile
  candidates are **not current live member-evidence truth without verified
  cutover**. The architecture therefore defines an evidence-source *port*
  (doc 07 §6) rather than binding to a specific store; C5 binds it under a
  then-current claim.
- **Journal**: dormant by owner decision; not an evidence source, dependency,
  or navigation assumption anywhere in this package.
- **Capture/Moment/Placement**: reusable canonical-reference discipline
  (create once, use by reference) is the model this architecture follows; no
  runtime dependency is created.
- **Ask Slate AI / Ask Pete AI**: no dependency. My Opportunities' AI surfaces
  are contextual workflows, not a separate bot, per Site Rules §3.

## 4. Search patterns — `PS-SEARCH-DARK-PROOF-001`

`docs/initiatives/PS-SEARCH-DARK-PROOF-001/README.md` is a non-production,
synthetic-only Azure AI Search candidate. Committed, reusable patterns:
canonical truth outside the index; derived rebuildable projections; a local
fence validating every canonical field before output; serializer that never
copies the index candidate; request census retaining no query text or
identifiers; pre-dispatch ceilings persisted across invocations; exact-target
cleanup manifests. **Standing proof expiry: 2026-08-23 23:59 CDT** ("unless
Pete separately records another decision" — no newer owner record exists at
the base SHA; this package was written on the expiry date). After that
deadline, treat the package as committed pattern evidence only: assume **no
retained proof index, service principals, application registrations, or role
assignments**. Nothing in this architecture depends on retained Search 3F
infrastructure.

## 5. Shared shell, responsive, accessibility, test, observability, flags, release

- **Shell**: `templates/base.html` is the production shell; `PS-SHELL-001`
  reserves shared-shell direction. v2 explicitly follows the production shell,
  not a mockup shell (`PS-OPPORTUNITY-SLATE-002/README.md`, "What R1 does not
  include"). My Opportunities UI (C8) does the same unless a separately
  authorized shell package changes it. C8 additionally reserves
  `templates/base.html` and `tests/test_navigation.py` for exactly one
  bounded change: the flag-aware two-destination navigation entry making My
  Opportunities discoverable beside Opportunity Slate — any drift into
  shell direction or material visual change stops and returns to the
  separate shell/visual authority (doc 14 C8).
- **Responsive/accessibility**: Site Rules §4 (WCAG 2.2 AA, reflow, reduced
  motion, touch); v2's real-browser gauntlet (69 scenarios incl. 320px/390px,
  200%-equivalent reflow, focus order) is the proof convention to match.
- **Tests**: `unittest` discovery under `tests/`; per-package suites
  (`tests/test_opportunity_slate_v2.py` pattern); byte-baseline render tests
  exist elsewhere (sign-in report §"Changed expectations") — avoid brittle
  byte baselines for new surfaces.
- **Observability**: `PS-INTERVIEW-AI-EXTRACT-001` docs 10–11 are the current
  dark-telemetry convention — additive telemetry schema landed dark, purge
  script with closed reason enums, disposable SQL proof, content-free records.
  Doc 12 builds on it.
- **Feature flags**: `PEERSLATE_*` env-read config entries in `app.py`. Two
  styles exist: import-time registration choice (the Slate conditional — noted
  per-test limitation) and register-always + blueprint `before_request` gate
  (`ask_pete_direct`, `app.py:810-816`: "flag off means a 404 from a route
  that EXISTS... can be flipped without a redeploy"). REC-04 recommends the
  second style for all new My Opportunities routes.
- **Migrations**: additive forward + rollback pairs under
  `SQL FIles/Migrations/` (`proposed/` until gated); `registry.json` gate
  proofs via `scripts/govern_sql_migrations.py`; applied-ness only from
  `PRODUCTION_SCHEMA_STATE.md`. Schema apply is manual, separately gated,
  serialized (baseline `pipeline_schema_checkpoint_order` finding: resolved
  pattern).
- **Release**: CI-only PR/main runs; manual exact-SHA production deployment
  with Pete's authorization reference; `[skip ci]` documentation closeouts
  (`docs/AI_WORKFLOW.md`, "Documentation-only closeout").

## 6. Active claims and collision check (at the base SHA)

`docs/governance/lane_claims/` holds exactly four claims:
`PS-MY-OPPORTUNITIES-001` (**active**, this package),
`PS-DELIVERY-CONTROL-SIMPLIFICATION-001` (**paused** — reserves its branch and
delivery-control files; paused claims reserve branch only for collision
purposes), `PS-INTERVIEW-AI-EXTRACT-001` (**closed**),
`PS-SYNTHETIC-MULTI-MEMBER-QA-001` (**closed**). No path or hierarchical
domain collides with this package's surfaces
(`docs/governance/DECISIONS.md`, `docs/initiatives/PS-MY-OPPORTUNITIES-001`,
and its control records) or domains (`architecture:my-opportunities:p0`,
`governance:decisions:my-opportunities`). `delivery_preflight.py --intent
write` passed at the base SHA with zero errors/warnings.

## 7. Missing capabilities (the gap list the children close)

| Gap | Exists today? | Closing child |
|---|---|---|
| Provider-neutral connector contract, rights ledger, source policy | No (Slate imports one member-brought URL/doc; no feed ingestion anywhere) | C1 |
| Raw receipts, normalized listings, source versions, canonical opportunities, requirement versions, dedupe, freshness, closure/outage, Live Opportunity Gate | No | C2 |
| Natural-language criteria interpretation, visible draft, explicit Apply, clarification, direct-filter parity, AI-unavailable parity | No (legacy Slate has per-role requirement interpretation, not search criteria) | C3 |
| Discovery retrieval, ordering, pagination, degraded modes, index projection/fencing, plus search-execution/result-snapshot persistence | Pattern evidence only (Search 3F, synthetic/public) | C4 |
| Requirement atomization against authorized member evidence, four-state assessments, correction, revocation | Partially analogous in legacy Slate (`analysis`, `responses`) but single-role, not search-scale; v2 has none yet | C5 |
| Saves, changed/closed member-history overlays, removal/undo, saved-view search/filter | No | C6 |
| Explicit Slate create/continue/history contract from a canonical opportunity | No (both Slates intake member-brought sources only) | C7 |
| My Opportunities member UI (two-row search, dossier, rail, all approved states) | No `my-opportunities` or `my_opportunities` path exists at this SHA (also confirmed in the R3 snapshot findings) | C8 |
| Scheduling, monitoring, licensed-feed activation, cutover, rollback, cost | No | C9 |
| Private paste/upload member import (`member_import` storage, sanitization, provenance, export/delete, disabled fetch port) | Both Slates import member-brought sources into *their* workflows; no private My Opportunities import object exists | C10 (unconditional; URL fetching is the separate Pete-gated child C13) |
| Member URL fetch adapter (safe remote retrieval into `member_import` through C10's port and C2's `safe_outbound`) | No | C13 (Pete-gated; service-only late integration; skippable forever) |
| Selected licensed-feed provider adapter (`describe/acquire/normalize` against a real feed) | No | C11 (gated on Pete's provider/rights selection; before C9 Level 3) |
| Company-context runtime (claim ingestion, rights validation, persistence/API, removal) | No | C12 (gated on Pete's company provider/rights selection; the truthful absent state ships in C8 without it) |

## 8. Boundaries not to duplicate

- Either Opportunity Slate implementation, its workbench, source intake,
  autosave/history plans, or private authorization model (reuse via C7's
  contract only).
- `PS-OPPORTUNITY-SLATE-CONTINUATION-001` scope, including the 2026-08-14
  breakage diagnosis.
- `safe_return.py` (register destinations; do not fork rules).
- Journal, Profile cutover, general company intelligence, shared shell,
  delivery-control surfaces.
- Community placement of opportunities (Site Rules §3: no job posts or
  job-listing routes in Community).

Proposed child surfaces/domains are in doc 14 §3.
