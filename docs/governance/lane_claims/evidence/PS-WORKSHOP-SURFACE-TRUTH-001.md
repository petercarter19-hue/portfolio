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
constraints, status code maps, and chip labels keep all four states; legacy
rows keep their chips and stay visible. A stale `?status=` link falls back
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

## Rollback

Single squash commit; `git revert` restores prior behaviour exactly. Nothing
to unwind in schema, data, configuration, or flags.
