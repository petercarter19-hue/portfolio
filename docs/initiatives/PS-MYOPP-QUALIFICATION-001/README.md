# PS-MYOPP-QUALIFICATION-001 — C5 owner-scoped qualification foundation

This Protected child implements the accepted My Opportunities qualification
and evidence-assessment foundation. A bounded, canary-proven AI seam may
propose evidence claims from the member's own admitted evidence; deterministic
service code alone validates those claims, evaluates every requirement item,
persists one current assessment per member x item x requirement version with
append-only history, and derives the `Fully verified` gate over required items
only. AI never persists, decides, scores, or ranks.

## Outcome

- An evidence port (`services/my_opportunities/evidence_port.py`) that reads
  only the member's own confirmed, unarchived, version-pinned Workshop
  knowledge records through the already-governed, already-allowlisted
  `usp_ListOpportunityEvidenceForOwner` procedure. The port owns no grant
  knowledge and is never called for a class no live grant admits
  (authorization-before-retrieval).
- Explicit, revocable, expiring evidence grants
  (`services/my_opportunities/qualification_service.py`) fixed to the single
  `qualification_verification` purpose, with class and record-key scope
  enforcement. Expiry and revocation are both terminal and one-way.
- The four canonical assessment states —
  `verified`, `not_established`, `appears_unmet`, `review_unavailable` — under
  Pete's approved evidence policy (§ below): firm, confirmed, source-linked
  evidence only ever verifies; dated records aggregate for duration; named
  credentials only; recency applies only when the posting states a window;
  absence of evidence is never a negative signal; an unmet result requires
  affirmative contradicting evidence.
- One current assessment per member x requirement item x requirement version,
  idempotent evaluation, append-only revision history, and recompute on
  member correction, a flagged reading, grant revocation, and grant expiry.
- The deterministic `Fully verified` gate, computed over required items only —
  preferred items, practical-fit observations, and AI never affect it.
- A canary-proven AI proposal seam (`FencedAssessmentPrompt`,
  `AssessmentProposalProvider`) that can only propose bounded evidence claims;
  it never persists, decides, or sees anything outside the admitted evidence
  set and the requirement clauses.
- Honest `Review unavailable` and distinct `AssessmentPersistenceError`
  behavior: an AI outage, an evidence-source outage, a malformed provider
  proposal, and a repository write failure are never converted into a
  fabricated assessment state.
- The additive, governed `PS-MYOPP-003` migration (grants, assessments,
  append-only revisions, reference-only evidence links, practical-fit
  observations structurally separate from the gate, and content-free
  idempotency receipts), its rollback, its verifier, and the repository
  registry entry.

## Scope exclusions (hard)

No route or UI, no C4 candidate assembly or search execution/retrieval, no
provider integration (no Anthropic client, no network), no change to any C2
(`canonical_service.py`) or C3 (`criteria_service.py`,
`interpretation_service.py`) file, no Workshop schema or behavior change, no
new stored procedure, no durable audit/telemetry table (C9 owns that), no UI
alias table (C8 owns that), no grant-expiry background job (the named
recompute method exists and is tested; wiring a job is later), no
deployment/enablement, and no production or staging schema action. A
disposable migration-gate database needs its own bounded owner authorization
and is not this file's authority.

## Authorities

- Doc 07 — [`07_QUALIFICATION_AND_EVIDENCE_POLICY.md`](../PS-MY-OPPORTUNITIES-001/07_QUALIFICATION_AND_EVIDENCE_POLICY.md)
- Doc 08 §§2, 2a, 7 — [`08_PRIVACY_AND_AUTHORIZATION.md`](../PS-MY-OPPORTUNITIES-001/08_PRIVACY_AND_AUTHORIZATION.md)
  (grants, authorization-before-AI, the owner-bound assessment writer, negative
  multi-member proofs)
- Doc 02 §§1, 6 — [`02_DOMAIN_AND_PROVENANCE_MODEL.md`](../PS-MY-OPPORTUNITIES-001/02_DOMAIN_AND_PROVENANCE_MODEL.md)
  (record shapes, persistence ownership)
- Doc 03 §§5–6 — [`03_STATE_MACHINES.md`](../PS-MY-OPPORTUNITIES-001/03_STATE_MACHINES.md)
  (grant and correction state machines)
- Doc 14 — [`14_FINAL_CHILD_GRAPH.md`](../PS-MY-OPPORTUNITIES-001/14_FINAL_CHILD_GRAPH.md)
  ### C5 (outcome, reservations, stop controls)
- Doc 16 — [`16_TRACEABILITY_MATRIX.md`](../PS-MY-OPPORTUNITIES-001/16_TRACEABILITY_MATRIX.md)
  (traceability rows, including the "Revoked evidence" recompute row)
- Precedent mirrored throughout: C3 (`criteria_service.py`,
  `interpretation_service.py`, `tests/test_my_opportunities_criteria.py`, the
  `PS-MYOPP-002` SQL trio) and C2 (`canonical_service.py`, `PS-MYOPP-001`).

### Pete's approved evidence policy (binding, restated — not re-litigated)

1. `Verified` requires confirmed, owner-scoped, source-linked evidence pinned
   to a version.
2. Inferred, partial, ambiguous, or unconfirmed evidence never verifies.
3. No blanket two-record rule; one explicit firm record may suffice.
4. Dated records may be aggregated to establish duration.
5. Credentials must be explicitly named.
6. Recency applies only when the posting explicitly establishes a time
   window; otherwise evaluation is any-time.
7. The initial evidence port reads only the member's confirmed, unarchived
   Workshop knowledge records (doc 07 §6 binding decision — resolved).
8. Absence of evidence ⇒ `Not established`; never infer a negative.
9. `Appears unmet` requires affirmative contradictory evidence.

### Two derived determinism rules — flagged for Pete's post-live review

These are direct, mechanical consequences of the policy above, not new
policy decisions, but they are recorded here explicitly so Pete can review
the consequence, not just the premise:

- **Mixed signals rule.** If an item has both firm confirming evidence that
  would satisfy it AND firm affirmative contradiction, the result is
  `Not established(ambiguous_evidence)` — never `Verified` and never
  `Appears unmet`. `Appears unmet` requires contradiction with no firm
  satisfying support; candidate-strength contradiction never produces
  `Appears unmet`.
- **Flagged-reading rule.** If the atomized reading of an item is flagged
  ambiguous/disputed (`reading_flagged`, doc 03 §6 `flagged`), the item
  cannot be `Verified`; it assesses `Not established(classification_ambiguous)`
  until reassessed under a corrected reading. This can only withhold `Fully
  verified`, never overclaim it.

Distinct from the above: `classification_basis ==
"ambiguous_default_required"` (required-vs-preferred placement ambiguity)
does not block verification; it only forces the item into the required set
for gate purposes.

## Delivered files

| File | Content |
|---|---|
| `services/my_opportunities/evidence_port.py` | Typed, immutable, reference-only evidence reads; the Workshop adapter and an in-memory reference port |
| `services/my_opportunities/qualification_service.py` | Grants, the fenced AI proposal seam, deterministic per-item evaluation, the assessment writer, recompute paths, gate derivation, and practical-fit observations |
| `tests/test_my_opportunities_qualification.py` | Groups A–L: grants, authorization boundary, deterministic evaluation, gate derivation, identity/idempotency/history, revocation/expiry recompute, failure semantics, the AI prompt fence and canaries, negative multi-member isolation, practical fit, migration/registry/verifier, and focused C2/C3 regression |
| `SQL FIles/Migrations/PS-MYOPP-003_qualification.sql` | Additive forward migration: `myopp_evidence_grants`, `myopp_assessments`, `myopp_assessment_revisions`, `myopp_assessment_evidence_links`, `myopp_practical_fit_observations`, `myopp_qualification_commands`, and their triggers/indexes |
| `SQL FIles/Migrations/PS-MYOPP-003_qualification_rollback.sql` | Fail-closed rollback: refuses on a later ledger row or any C5 member data; drops in dependency order |
| `SQL FIles/Verification/PS-MYOPP-003_qualification_verify.sql` | Real catalog assertions: owner fencing, closed state/reason vocabulary, reference-only evidence links, content-free command receipts, gate-separation of practical fit, and the forbidden-scoring-column scan |
| `SQL FIles/Migrations/registry.json` | One appended `PS-MYOPP-003` entry carrying the recorded disposable gate proof (throwaway database `ps-myopp-c5-gate-20260831-a1`, verifier `verified = 1`) |

`PS-MYOPP-003` adds only owner-scoped evidence grants, four-state assessments
with append-only revisions, reference-only evidence links, practical-fit
observations, and content-free idempotency receipts. Its forward migration,
rollback, verifier, and registry entry are repository candidate artifacts
only; merge will not apply schema, deploy, enable, contact a provider, or
change production.

## How to run the tests

```bash
python3 -m unittest tests.test_my_opportunities_qualification -v
python3 -m unittest tests.test_my_opportunities_criteria tests.test_my_opportunities_canonical -v
```

All suites are green at the frozen candidate: the disposable gate proof is
recorded in the registry entry, and `PS-MYOPP-QUALIFICATION-001` is
registered in `docs/governance/PACKAGE_REGISTRY.json` (that surface entered
the claim via the governed extend-surfaces transition after the claim
previously holding it paused). The qualification suite plus
`tests.test_package_registry` run 81/81; the C2/C3 regression suites run
48/48.

## Current state

Phase 2 (SQL trio, registry entry, group K tests, and these initiative docs)
is complete on `work/2026-08-31-myopp-qualification-001`, following phase 1
(the two service modules and test groups A–J, L, all green). An independent
Opus self-review pass then found and the writer fixed 3 blocker- and 6
important-severity behavioral defects plus 8 minor issues (constraint
validation gaps, stale-admitting-grant-key recompute misses, a surviving
`appears_unmet` after evidence loss, an unknown evidence strength silently
dropping out of evaluation, the flagged-reading short-circuit running after
the port/AI call instead of before, and smaller issues) — see the
OWNER_TECHNICAL_COMPLETION_REPORT.md for the full list and its 18 new
regression tests. The disposable migration-gate proof is recorded, the
package-registry entry is present, and all focused suites are green at the
frozen candidate; the independent exact-SHA review is the remaining gate
before merge. The package is not merged, schema-applied, deployed, enabled,
or live.

## Known limitations and forward obligations (from independent review)

Recorded truthfully; none blocks this repository merge, and none may be
silently forgotten:

1. **Member-data erasure path (before real member data exists).** All five
   member-side C5 tables are delete-blocked by triggers with no erasure
   carve-out, while doc 08 §5 requires member-side deletion on account
   deletion. A future additive migration must provide the governed erasure
   path before these tables hold real member data (enablement-gated; C4/C9
   era).
2. **`evidence_key` is reference-validated in code, not fenced in schema.**
   Links pin evidence by key/class/version with service-layer validation
   (`_validate_proposal`), but no cross-store SQL constraint exists (Workshop
   fences on a different owner key). Settle structurally before any write
   path beyond this service lands.
3. **The verifier attests schema shape, not behavior**, and its owner-fencing
   check ranges over a named FK list. `verified = 1` in the gate proof means
   catalog-shape conformance; behavioral proof lives in the P-1 suite.
4. **Revocation is deliberately pessimistic.** An assessment links the first
   sufficient supporting claim; revoking the grant behind it collapses
   `verified → not_established (evidence_revoked)` even when other
   still-authorized evidence could verify independently. Conservative (never
   overclaims) and recoverable via member correction; surfaced as a UX
   consequence for C8 copy.
5. **Assessment head duplicates the current revision's state/reason** for
   query convenience; the head guard enforces counter contiguity but not
   byte-equality with the newest revision row. A future hardening trigger may
   assert equality.
