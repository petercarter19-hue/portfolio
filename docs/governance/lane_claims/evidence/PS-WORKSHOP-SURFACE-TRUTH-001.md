# PS-WORKSHOP-SURFACE-TRUTH-001 — delivery evidence

Runtime-inert record. Bounded path; independent review required and obtained.

## Outcome

The member-facing Workshop surface tells the truth, delivered as two
coordinated scopes with separate acceptance evidence (owner decisions of
2026-08-23).

**Scope B — public-demo and fixture truth.** An anonymous `GET
/app/workshop/work` generated a Spark on page load: real billable provider
spend, drawn from a daily ceiling shared with signed-in members, with no
click. Generation is un-automated rather than removed — the "Give me a spark"
door on that screen posts to the same authorized endpoint, keeping its
same-origin guard, per-minute limit, and spend guard. Proven at the SDK call
site: zero `messages.create` and zero spend reservations across four
anonymous GETs; exactly one of each on an explicit ask. The resulting screen
is the already-locked R05/R06 "no Spark yet" composition, so no new visual
authority was required. The preview now names Jordan Ellis as the example
member, explains in plain language what Workshop is, and states that the
public preview is temporary and its apparent saves are never member records.
Signed-in wording is untouched and pinned by test.

**Scope C — retire the dead status filters.** Suggested and Unfinished
offered choices that can never match: every member-authored save has
confirmed at save time since 2026-08-06, and no production path writes
`suggested`. Only the controls were retired. Stored values, SQL CHECK
constraints, status code maps, and chip labels keep all four states.
Stored values, enums, and member data were not rewritten by this package, and
legacy information remains visible -- but the product does not promise that an
old visible label remains unchanged: the owner-ordered signed-in
reconciliation runs before the list read and may render a legacy Unfinished
row's current status as Confirmed. A stale `?status=` link falls back
safely and now says so. "All statuses" became "All current" because archived
rows were always excluded from it.

## Review

Independent external review (Grok, via the Codex Workshop manager), three
rounds against exact frozen SHAs:

1. `1701c12f` — two findings: a false label-preservation promise in the
   retired-filter notice (contradicted by the owner-ordered backlog sweep
   that runs before the list read), and two malformed-Spark tests made
   vacuous by scope B's trigger change.
2. `a565fa02` — both findings verified resolved and PASS; one closeout item:
   the focus-anchor test now skipped deterministically.
3. **`86a53df367b5b547420d7e7f7a71fad1d8390d03` — ACCEPT, zero findings.**

Each finding and its resolution is recorded individually in
`lane_claims/receipts/PS-WORKSHOP-SURFACE-TRUTH-001.json`.

## Verification

- Independent Spark rerun at the accepted candidate: **79 passed, 0 skipped.**
- Writer full 15-module suite: **788 passed, 1 skipped** (the deliberately
  unset PS-WORKSHOP-001 SQL gate).
- All runs hermetic: `AZURE_SQL_CONNECTIONSTRING` and `PS_WORKSHOP_SQL_GATE`
  unset, placeholder provider key. **No real provider or database call.**

## Honest limitations

- **Merged is not deployed.** This record claims repository truth only.
  Production still serves release `f21b9745e9e67d2ac958e586` (Package A's
  deployment); until a separately authorized deployment, the live anonymous
  Work opening still generates a Spark on page load.
- No live/browser proof and no signed-in live proof; evidence is source and
  hermetic tests.
- Package A's authenticated provenance behaviour remains live but not
  attended-proven; that proof is owed separately (preserved queue item K).
- No schema, migration, configuration, dependency, or production change.

## Deployment and live proof (2026-08-24, owner-authorized)

- Deployed current-main SHA: `44c3e8fe3b3f4d90d8f2d099e2c3fc118a590800`
  (carries the B+C merge `7372f79dd4a865881cb494184212245807511c93` with the
  reviewed bytes verified intact, plus unrelated ordinary main drift).
- Manual Azure run **1582**, reason Manual, `forceProductionDeploy=true`,
  `schemaAction=none`: Build and Deploy succeeded; the schema read/apply,
  candidate, and independently gated maintenance stages all skipped; the run
  carries zero Checkpoint.Approval records.
- Release identity proven, not observed: live `/healthz` returned
  `status: ok`, `service: peerslate`, `release: c493f5c6c2a3e544dee6ef61`,
  which equals `release_id_for_build(44c3e8fe..., "1582")` exactly.
- Public live checks after the release was proven: one controlled anonymous
  GET of `/app/workshop/work` loaded with Jordan Ellis named, the plain
  explanation, the temporary/non-durable wording, no auto-rendered Spark
  card, the ask-first note, and the explicit Spark door present but never
  pressed. The library shows no Suggested/Unfinished controls, `All current`
  wording, the `in this library` footer, and legacy chips still visible in
  the default view. Stale `?status=suggested` / `?status=unfinished` links
  fell back with the truthful removal notice and no label-preservation
  promise. A malformed status value produced no invented notice and no raw
  markup; its only appearance is URL-encoded inside the pre-existing
  site-wide sign-in `return_to` parameter, behaviour already present in the
  prior deployed source.
- The explicit Spark action was not invoked: provider operation and spend
  were outside this authorization. Live provider-call/spend telemetry was
  **not** instrumented; the zero-provider-call contract for anonymous GET
  rests on the exact-SHA test and SDK-seam proof accepted at review.
- No schema, migration, database, configuration, dependency, provider, or
  destructive operation was performed. No authenticated or two-member proof
  was performed; Package A's attended signed-in provenance proof remains
  owed under preserved queue item K.

## Rollback

Single squash commit; `git revert` restores prior behaviour exactly. Nothing
to unwind in schema, data, configuration, or flags. Last known-good
production reference before this release: source `5436e423...`, run 1512,
release `f21b9745e9e67d2ac958e586`.
