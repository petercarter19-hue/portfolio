# PS-MYOPP-QUALIFICATION-001 — technical completion record

## Core record

- **Task/package and delivery path:** `PS-MYOPP-QUALIFICATION-001`, Protected.
- **Outcome and member/site effect:** Owner-scoped evidence grants fixed to
  the `qualification_verification` purpose, the four canonical assessment
  states (`verified`, `not_established`, `appears_unmet`,
  `review_unavailable`) under Pete's approved evidence policy, one current
  assessment per member x requirement item x requirement version with
  append-only revision history and recompute on correction/revocation/expiry,
  the deterministic `Fully verified` gate over required items only, a
  canary-proven proposal-only AI seam, and honest failure semantics
  (`Review unavailable` / `AssessmentPersistenceError`) are implemented at
  P-1/P-2. There is no route or current member-visible site effect.
- **Package manager:** Codex session
  `01a02f42-15ac-7d92-a2a9-60b7e800c388`; repository/schema/backend truth
  makes Codex the routed manager. ChatGPT Work is not needed for this
  non-visual service slice.
- **Writer:** `session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/myopp-qualification-writer`.
- **Branch and base:** `work/2026-08-31-myopp-qualification-001` from
  `origin/main` at claim activation
  `5408a76e3ae329a4dd0f09d40efa36af35e5d674`.
- **Candidate SHA:** implementation committed and pushed as
  `0b776424fe0fab837fa9d7a895b469cb1863e067` (services, tests, SQL trio,
  registry entry pre-gate, initiative docs) and
  `924394d0dd9427bc3a958831e4cbf47513c19559` (the recorded disposable gate
  proof), then the package-registry line and this record's completion. The
  frozen candidate is the tip of `work/2026-08-31-myopp-qualification-001`
  at review routing; its exact 40-character SHA is recorded in the review
  receipt and, at close, in the claim's `merged_sha` lineage.
- **Changed paths:** the two C5 services (phase 1, already green); focused C5
  tests (phase 1 groups A–J, L; phase 2 group K); `PS-MYOPP-003` forward,
  rollback, and verifier; the migration registry entry; this package README
  and completion record; and, at close, the runtime-inert claim evidence
  file.
- **Verification performed and result (as of this self-review fix pass):**
  an independent Opus self-review scan found 3 blocker-severity and 6
  important-severity behavioral defects plus 8 minor issues (see below); all
  were fixed in the same worktree/branch, each with a dedicated, descriptively
  named regression test (`test_blocker1_...` through `test_minorc_...`, 18
  new tests total). The full focused C5 suite
  (`tests.test_my_opportunities_qualification`) now runs 79 tests: 77 pass; 2
  fail honestly and as designed —
  `QualificationMigrationTests.test_c5_migration_registry_and_verifier_are_bounded_and_gate_proven`
  fails with `TypeError: 'NoneType' object is not subscriptable` at
  `gate["executable_sha256"]` (the registry entry's `"gate": null` has not
  been proven yet, so nothing downstream of that line in the test ran), and
  `QualificationMigrationTests.test_package_registry_contains_c5_once_and_counts_reconcile`
  fails with `AssertionError: 0 != 1` (the package registry does not yet
  carry `PS-MYOPP-QUALIFICATION-001`). The repository's own
  `tests.test_package_registry` also now fails for the same reason (the
  initiative directory exists; the registry entry does not yet). The C2/C3
  regression suite (`test_my_opportunities_criteria`,
  `test_my_opportunities_canonical`) is fully green (48/48). After the gate
  proof was recorded (below), the suite stands at 79 tests / 78 pass, the
  single remaining failure being the package-registry entry
  (`test_package_registry_contains_c5_once_and_counts_reconcile`,
  `AssertionError: 0 != 1`), plus the repository's own
  `tests.test_package_registry` for the same one reason. Both migration
  SQL files were checked for internal consistency: every table created in the
  forward migration is dropped in the rollback (in dependency order:
  commands, links, revisions, assessments, observations, grants) and named
  in the verifier; THROW numbers 55660–55674/55680–55682/55690–55714 do not
  collide with any other tracked migration; the verifier ends with the exact
  `SELECT CAST(1 AS bit) AS verified` row naming "content-free" and
  "reference". Final tallies at freeze: with the gate proof recorded and the
  package-registry line added, `tests.test_my_opportunities_qualification`
  plus `tests.test_package_registry` run 81/81 green, and the C2/C3
  regression suites run 48/48 green. `tests.test_operational_readiness`
  cannot import in this worktree (no local flask — a known environment gap,
  exercised authoritatively in CI); this package's diff does not touch its
  subject matter.
- **Self-review fix pass (this session):** blockers fixed — (1)
  `RequirementConstraints` fields (duration, recency window, credential
  names) are now validated at spec-assessment time, with a defense-in-depth
  guard in `_satisfies` so a zero/negative duration can never verify off
  zero contributing evidence; (2) `revoke_grant` and
  `recompute_for_expired_grants` now build their recompute candidate set
  from assessments linked to ANY of the owner's grants (deduped by item x
  version), not just the grant being acted on, so revoking the last live
  grant always recomputes even when a link's `admitting_grant_key` has gone
  stale; (3) `_recompute_after_authorization_loss` now collapses
  `appears_unmet` to `not_established/evidence_revoked` when its
  contradicting evidence itself loses authorization, instead of silently
  standing with dead/zero links. Important-severity fixes — (4)
  `recompute_for_expired_grants`'s `spec_by_version` is no longer a
  membership gate (advisory/unused, kept for signature compatibility); (5)
  `_derive_gate` reports a required item with no assessment as
  `review_unavailable/assessment_error` instead of silently dropping it, and
  `_gate_label` can no longer render a dangling separator; (6) the K1 gate
  test now also asserts `gate_database`/`gate_server`/`operator` are
  populated and `gate_database` is never a real database name; (7) an
  evidence record with an unrecognized `strength` is now refused both at
  `InMemoryEvidencePort` construction and by `_validate_proposal`; (8) a
  flagged reading now short-circuits to `classification_ambiguous` before
  any grant/port/provider step, in both the initial-assessment and recompute
  paths (previously only `evaluate_item`'s internal check caught it, after
  the port/AI had already been called); (9) a persistence failure inside
  `revoke_grant`'s recompute loop now records a replayable partial receipt
  before re-raising, so a retry with the same idempotency key replays
  instead of refusing `grant_terminal`. Minor fixes — the service no longer
  requires a repository to expose a private `_lock`; `list_grants` no longer
  discards its documented `now` parameter; `opportunity_key`/
  `observation_key` are now bounded; dead `excluded_by_window` plumbing in
  `_satisfies` was deleted; `evidence_version` was added to
  `UQ_myopp_assessment_evidence_links_claim`'s key columns; the verifier's
  `UQ_myopp_assessments_identity` check now asserts the exact three key
  columns and two presence-only THROW messages were reworded away from
  "exactly N"; the K1 test now asserts all seven forbidden-scoring LIKE
  patterns and the no-scoring-fields walk now also covers
  `evidence_port`'s dataclasses; a vacuous loop and a vacuous
  practical-fit audit assertion were deleted (practical fit emits no audit
  events by design, noted in a comment). Status remains **Conditional**: no
  behavioral defect blocks freeze, but the disposable gate proof,
  package-registry activation, and independent exact-SHA review are still
  outstanding.
- **Release state:** repository-only — no PR completion, deployment, schema
  apply, enablement, or live verification has happened. The independent
  review outcome, PR, and merge SHA post-date this frozen candidate by
  design and are recorded in the review receipt and the runtime-inert claim
  evidence file (the only permitted post-review additions), and in the
  closed claim.
- **Known limits / owner decision needed:** No owner decision is outstanding
  (blueprint `C5_ARCHITECTURE.md` §9: the evidence-policy questions are
  closed by Pete's approved policy, and the two derived determinism rules in
  §0.3 are consequences of that policy, flagged in this package's README for
  Pete's post-live review, not held for pre-approval). Three procedural items
  remain: the disposable migration-gate proof, the package-registry
  activation entry (owned by another active claim, not edited by this
  writer), and the required fresh independent review.
- **Next action:** when `docs/governance/PACKAGE_REGISTRY.json` is released
  by the claim currently holding it, run the governed `extend-surfaces`
  control transition to add that one path to this claim, add the
  `PS-MYOPP-QUALIFICATION-001` line (category `future_finish`) with count
  updates, confirm 79/79 plus a green `tests.test_package_registry`, complete
  this record's final SHA, freeze and push the proof-bearing candidate, then
  route that exact SHA for independent review. Do not open/complete a PR
  before the review pass.

## Protected additions

- **Privacy and authorization:** Every service method is owner-scoped;
  direct cross-member keys return the same `not_found` shape as an absent
  key (test group I). Evidence is only ever admitted through a live
  `qualification_verification` grant; a class with no live grant is never
  read (no pre-fetch), and evidence outside a grant's `record_keys`
  allowlist is excluded before it reaches the AI prompt or any persisted
  link (test groups B, H).
- **Consequential AI:** The AI proposal seam
  (`FencedAssessmentPrompt`/`AssessmentProposalProvider`) can only propose
  bounded evidence claims over the admitted evidence set and the requirement
  clauses; deterministic code alone validates every proposal
  (`_validate_proposal`), evaluates every item, writes every row, and derives
  the gate. A malformed, unavailable, or timed-out proposal never becomes a
  fabricated assessment state — it becomes a durable, honest
  `review_unavailable` row (test group G). Canary tests prove another
  member's evidence, and this member's unadmitted evidence, never reach the
  prompt (test group H).
- **Migration and rollback:** `PS-MYOPP-003` is additive, depends on
  `PS-MYOPP-001` and `PS-MYOPP-002`, and has a data/later-ledger-refusing
  rollback (drops in dependency order: commands, links, revisions,
  assessments, observations, grants) and an exact verifier (owner fencing,
  closed four-state vocabulary, fifteen-code reason pairing, reference-only
  evidence links, content-free command receipts, gate-separated practical
  fit, and a forbidden-scoring-column scan). THROW numbers 55660–55674
  (forward), 55680–55682 (rollback), and 55690–55714 (verify — extended from
  55712 by the self-review fix pass's two additional identity-uniqueness
  checks) were confirmed unused against every other tracked migration before
  use.
  The disposable-database gate proof is DONE and recorded in
  `SQL FIles/Migrations/registry.json` (commit `924394d0`): owner-authorized
  envelope (chat approval 2026-08-31), attempt a1 only, throwaway database
  `ps-myopp-c5-gate-20260831-a1` (Basic tier, `peerslate` server), forward
  apply, idempotent guard, verifier `verified = 1`, rollback rehearsal, full
  object inventory captured, executable SHA-256 recorded; the database was
  deleted afterward with `ResourceNotFound` confirmed, the temporary
  firewall rule was removed, and attempts a2/a3 were never created. No
  production or staging database was contacted.
- **Status:** **Conditional** — P-1 and P-2 implementation and tests are
  complete; the disposable gate proof, package-registry activation, and
  independent exact-SHA review are all still required before repository
  merge.
