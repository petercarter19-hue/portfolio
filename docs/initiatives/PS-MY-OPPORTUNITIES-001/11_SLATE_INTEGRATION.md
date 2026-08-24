# 11 — Opportunity Slate integration

P0's obligation: map both implementations and the current conditional route,
legacy rollback, remaining v2 stages, persistence/history/source-intake/
private-authorization boundaries, and continuation/current-use breakage; then
**recommend** the C7 capability target/dependency with evidence — and select
nothing. The recommendation below is `decision_pending` for Pete at
architecture acceptance (REC-01, doc 15).

## 1. Current state map (base SHA `958727c5…`)

| Fact | Evidence |
|---|---|
| One canonical route `/opportunity-slate`; exactly one blueprint registered at startup: v2 when `PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED` is true, else legacy v1 | `app.py:806-809`; flag comment near lines 325–333 ("configuration-only rollback… process restart") |
| v2 recorded member-facing in production (flag true), proven live 2026-08-16 | `PS-SIGNIN-MEMBER-ARRIVAL-001/OWNER_TECHNICAL_COMPLETION_REPORT.md` — newest repository evidence; literal current App Service value unverified in this phase |
| Legacy v1 = complete original workbench: intake (paste/upload/import), source review/concerns, requirement interpretation/confirmation, alignment analysis, responses, save/saved/reanalyze, delete, public session | `opportunity_slate_routes.py` route set (decorators near lines 2728–4968); rate-limit census `app.py:947-984`; shipped live under `PS-OPPORTUNITY-SLATE-001` (2026-08-06) |
| v2 = R1 stages 1–2 only: intake + source identity/wording/confirm/delete; "No requirement interpretation, no alignment, no save" | `opportunity_slate_v2_routes.py` module docstring (near line 27) and route set; `PS-OPPORTUNITY-SLATE-002/README.md` "What R1 does not include" |
| v2 schema lineage `PS-OPPSLATE-001…004` all recorded applied in production (ledger rows 18–20, 27) | `docs/governance/PRODUCTION_SCHEMA_STATE.md`; the OS-002 README's "production re-apply remains pending" and "blueprint unregistered" sentences are older, superseded evidence |
| v2 persistence/authorization idioms: owner-scoped service (`user_key` required first), shared rowversion across identity/wording writes, idempotency, same-origin, no-store/noindex, truthful unknown-outcome handling | `services/opportunity_slate_v2_service.py`; `opportunity_slate_v2_routes.py` |
| Continuation boundary (Opportunity Home, autosave, history/archive, bounded workbench) is planned, not active — and holds the **unresolved owner-reported current-use breakage** (2026-08-14 import shows no extracted content; workbench "feels broken") | `PS-OPPORTUNITY-SLATE-CONTINUATION-001/README.md` |
| Signed-out `/opportunity-slate` redirected to sign-in at the R3 probe (302 → `/auth/sign-in?return_to=/opportunity-slate`) | External R3 `06_CURRENT_AUTHORITY_SNAPSHOT.md` production observation, 2026-08-23 — drift-prone, unverified since |

### Continuation/current-use breakage boundary

The breakage is real, owner-reported, undiagnosed, and **owned by the
continuation package**, which mandates a read-first, non-destructive
diagnosis of the source→extraction→interpretation chain. P0 and every My
Opportunities child stay out of it. Its consequence for this program is a
*dependency risk*, handled in §3.

## 2. What "integration" must mean (and not mean)

My Opportunities may deliberately create or continue a Slate through an
explicit contract. It must not duplicate the Slate database, source intake,
requirement workbench, evidence-selection flow, saved versions,
autosave/history plans, or private authorization model — reuse, don't
duplicate (preserved parent boundary). Save never creates a Slate; Slate
creation never applies, notifies, or monitors.

## 3. Recommendation — REC-01 (`decision_pending`)

**Target the v2 lineage (PS-OPPORTUNITY-SLATE-002 architecture) as the C7
capability target. Treat legacy v1 as configuration rollback only — never
build the create/continue contract against it.**

Evidence for: v2 owns the canonical route in the newest production evidence;
its schema lineage is applied; its service idioms are the repository's current
protected-data conventions; v1 is explicitly positioned as rollback by the
`app.py` flag contract; writing C7 against v1 would couple new work to the
surface the repository is actively replacing (incompatible-architecture risk
the R2 review named).

**Dependency (the honest part):** v2 today ends at source confirmation. A
create/continue handoff that lands a member in a workspace which cannot yet
interpret requirements or save is a truthful but weak product experience.
C7 therefore depends on **the required remaining Slate capability state**,
which is one of:

- (a) v2's remaining stages (requirement interpretation, alignment,
  save/history — its R2–R4) delivered under their own packages, and/or the
  continuation package resolving Opportunity Home/autosave/history and the
  2026-08-14 breakage; **or**
- (b) Pete explicitly accepting an interim C7 boundary: create/continue into
  v2's stage-2 state (source captured + confirmed), clearly labeled, with the
  workbench deepening as v2 stages land.

Which of (a)/(b) — and the v2-stage sequencing itself — is Pete's decision at
architecture acceptance; both keep C7's contract identical, which is why the
contract below is safe to fix now. If Pete instead selects v1 as the target,
C7's contract shape survives but its intake mapping and capability
assumptions must be re-derived — that is a scoping change, not a silent
re-target.

## 4. The create/continue/history contract (C7)

**Commands (member-initiated, explicitly confirmed, idempotent):**

- `create_slate_from_opportunity(user_key, opportunity_key,
  source_version_key, idempotency_key)` → `slate_link`
  - Pre-conditions: live opportunity reference; member confirmed the
    first-use private-workspace explanation (doc 03 §8); no existing active
    link for (member, opportunity).
  - Effect: creates one Slate workspace through the target Slate's own
    service-layer intake seam — **a new internal intake class**
    (`peerslate_opportunity` alongside paste/upload/import), not a bypass of
    its validation. The workspace's source record carries provenance
    (`opportunity_key`, `source_version_key`, source attribution per policy).
  - Content: the handoff passes the rights-permitted representation of the
    governing `source_version` — full stored description where
    `source_policy.full_description`+`storage` permit member-workspace use;
    otherwise permitted excerpt + attribution + original-posting link. The
    per-provider value of this is a C1 rights output; the contract requires
    the check, not a particular answer.
  - Failure: Slate-side failure creates nothing and links nothing (no orphan
    `slate_link`); truthful retryable failure per doc 09 §4.
- `continue_slate(user_key, link_key)` → open existing workspace; never a
  second create.
- `list_slate_history(user_key, opportunity_key)` → the member's links
  (active + unlinked-historical) for truthful "you already reviewed this"
  affordances (`Pick up a role review` is based only on actual Slate work —
  preserved rule).

**Invariants:** one active link per (member, opportunity); Slate-side
deletion → `unlinked` history label, never cascade-deleting saves; a source
update never rewrites the workspace (posting-changed flows through doc 03 §2
member review); identity is re-derived server-side on the Slate side — the
handoff asserts no identity.

**Change to the Slate itself:** exactly one bounded seam — the internal
intake class registration. C7 claims that seam explicitly in its future claim
(service + its tests); everything else in the Slate is out of C7's surfaces.

## 5. What P0 changes in the Slate

Nothing. This document is evidence and recommendation only.
