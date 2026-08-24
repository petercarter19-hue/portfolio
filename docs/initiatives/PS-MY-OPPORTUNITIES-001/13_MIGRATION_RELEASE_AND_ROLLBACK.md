# 13 — Migration, release, and rollback

Nothing here is an action. It is the strategy every child must implement
under the repository's existing controls: additive gated migrations
(`SQL FIles/Migrations/registry.json` + `scripts/govern_sql_migrations.py`;
applied-ness only from `docs/governance/PRODUCTION_SCHEMA_STATE.md`), CI-only
merges, manual exact-SHA production deployment with Pete's authorization
reference, serialized schema operations.

## 1. Fixture isolation

- `data_class ∈ {fixture, production}` on every shared-side row (doc 02 §1);
  service-layer refusal of cross-class reads; fixture rows only via fixture
  loaders in test/demo contexts; UI labels fixture data wherever rendered.
- Fixture fixtures (Astraeus, LumenWorks, Northwind, Canopy) live in
  versioned fixture files, not migrations, so production schema never carries
  demo content.
- Contract tests assert no production query path can return fixture rows and
  vice versa — the confusion is structurally impossible, not policed by
  convention.

## 2. Feature flags

- REC-04 (decision-pending): all My Opportunities routes register
  unconditionally and gate inside the blueprint (`before_request` → neutral
  404 when off), the `ask_pete_direct` style `app.py:810-816` documents —
  flippable without redeploy, per-test exercisable, identical refusal for
  cross-site and same-origin callers. The Slate registration conditional's
  per-test limitation (sign-in report) is the counter-example not to repeat.
- Flag granularity: one master surface flag — the proposed exact key
  `PEERSLATE_MY_OPPORTUNITIES_ENABLED` (an architecture proposal, not
  deployed truth; C8 implements it and binds the same key into the
  `safe_return` destination registration and both browser allowlists,
  doc 01 §2) — plus independent capability flags for ingestion scheduling,
  the index retrieval path, and member-URL fetching (the proposed exact key
  `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED`, effective only alongside
  the parent flag; C13, if ever approved) — so C9 can stage Level 2 dark
  operation without member exposure.
  Enablement of any member-facing flag is an owner release decision, never
  a side effect of merge or deployment.

## 3. Additive schema strategy and backfill

- **REC-02 gate first:** no physical schema, migration, projection, or
  provider-dependent design exists anywhere in this program before Pete
  records the REC-02 topology decision (doc 14 §1). The `PS-MYOPP-001`–`008`
  migration reservations are proposals under the recommended topology and
  re-derive at activation if Pete selects otherwise. Ownership per object
  family is doc 02 §6.
- Every child's schema change: additive forward + verified rollback pair in
  `proposed/` until gated; no destructive change; takeover/alteration of
  existing objects only with the guarded-stamp discipline the OPPSLATE
  lineage established.
- Backfills are bounded jobs (doc 09 §3), idempotent, resumable, verified by
  row-count/invariant checks, and separated from the schema apply run
  (schema and web deployments never share a run — standing rule).
- Member-side and shared-side tables never share a migration when either
  carries a privacy-relevant constraint change, keeping review scope honest.

## 4. Reversible projections and index rollback

If the index topology is accepted (REC-02): the index is a rebuildable
projection — create/rebuild/drop are operational actions with zero canonical
or member data risk; the retrieval flag falls back to the bounded canonical
path (doc 04 §9). Rollback of the index is: flag off → drop. Nothing
member-owned or canonical lives in it (REC-05).

## 5. Deployment, cutover, and release levels

- Merges are repository truth only; production web deployment is the separate
  manual exact-SHA operation; schema is separately gated and serialized.
  Each child's completion record states merge / deployment / schema /
  enablement / live verification separately (workflow rule).
- **Level 1 — fixture-backed foundation**: canonical models + contracts +
  protected multi-member tests + responsive UI against fixtures; no provider
  or live-inventory claim.
- **Level 2 — provider-neutral dark system**: ingestion/index/lifecycle
  processing on synthetic or specifically permitted evidence, dark flags,
  operational telemetry; no member-facing widening.
- **Level 3 — licensed limited pilot**: requires Pete's owner-approved
  licensed commercial feed + exact rights (standing entry condition);
  bounded inventory; live freshness/dedupe/link/strict-gate proof.
- **Level 4 — broader production**: broader coverage, cost evidence, outage/
  termination handling, live responsive/visual acceptance, accepted rollback.
- No level inflation: a fixture-backed build is never called a live
  job-search engine; deployment is never called enablement; enablement is
  never called live-accepted.

## 6. Rollback and cleanup ladder

| Scope | Rollback |
|---|---|
| Member-facing surface | Surface flag off (no redeploy under REC-04) |
| Retrieval path | Retrieval flag → canonical path; index drop/rebuild at leisure |
| Ingestion | Scheduling flag off; listings age truthfully (could-not-reverify semantics degrade honestly, by design) |
| Schema | Verified rollback scripts per migration, governed and serialized |
| Provider exit | Doc 05 §7 termination row: listings leave current results; content handled per termination rights; member history stays explainable (§8 doc 05) |
| Full retreat | All flags off leaves the site exactly as today: `/opportunity-slate` behavior untouched, no My Opportunities route reachable |

Cleanup obligations (TTL sweeps, policy purges, index teardown) ship with
their feature, with exact-target manifests where infrastructure is involved
(Search 3F cleanup-manifest discipline) — never left as "later".

## 7. What P0 changes

Nothing runtime. This phase adds documentation only; the release ladder above
starts at C1+.
