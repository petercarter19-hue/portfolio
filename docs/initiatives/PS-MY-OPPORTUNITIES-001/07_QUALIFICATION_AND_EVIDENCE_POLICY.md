# 07 — Qualification and evidence policy (candidate)

The strict gate in one sentence: **`Fully verified` means every stated
required/basic qualification has firm, authorized, source-linked confirming
evidence — and nothing weaker ever passes.** Missing, ambiguous, inferred,
partial, contradictory, unavailable, or unauthorized evidence does not pass,
and never proves the member lacks the experience.

This is the policy *candidate* the trial contract requires; the exact
evidence-strength and corroboration thresholds remain an owner decision
before qualification implementation/release (doc 15 §3).

## 1. Requirement atomization

- Input: the governing `source_version`'s requirement text. Output: one
  immutable `requirement_version` of ordered `requirement_item`s, each bound
  to its exact clause span (provenance walk, doc 02 §2).
- Atomization splits conjunctions into independently assessable items
  ("7+ years product management **and** 3+ years payments" → two items) and
  keeps genuine alternatives as one item with alternative satisfaction paths
  ("degree **or** equivalent experience").
- AI may propose the atomization; deterministic code stores it; the member
  sees requirement text verbatim beside the atomized reading and can flag a
  wrong reading (doc 03 §6 `flagged`).

## 2. Required/preferred classification authority

- The **stated posting** governs: items under required/basic/minimum headings
  are `required`; items under preferred/nice-to-have are `preferred`.
- **Ambiguous placement defaults to `required` for gate purposes** (REC-06,
  decision-pending): the conservative direction — it can only *withhold*
  `Fully verified`, never overclaim it. The item carries
  `classification_basis: ambiguous_default_required` and is flagged
  member-visible.
- Preferred qualifications never rescue a failed required gate and never
  penalize: they order otherwise comparable qualifying roles only
  (doc 04 §4). Practical fit is a separate truth and never enters either.

## 3. Evidence model

- Evidence is **referenced, never copied**: an assessment's evidence links
  point into the member's authorized evidence source(s) (§6) with record
  identity + version.
- **Strength tiers**: `firm` (explicit, member-confirmed, source-linked
  records) vs `candidate` (member-supplied but unconfirmed, inferred, or
  partial). Only `firm` evidence can support `Verified`. Tier definitions per
  evidence class — and whether corroboration (≥2 independent records) is
  required for specific requirement kinds — are the owner evidence-policy
  decision C5 presents.
- **Temporal relevance**: evidence carries its own time span; a requirement
  with an explicit recency term ("in the last 5 years") is satisfied only by
  evidence overlapping that window; the policy default for un-windowed
  requirements (any-time vs recency-weighted) is part of the same owner
  decision.
- **Contradiction**: authorized evidence that affirmatively indicates
  non-satisfaction (stated 4 years against required 7+) supports
  `Appears unmet` — contradiction is an affirmative signal, never a default.
- **No hidden evidence search**: assessment reads only within live
  `evidence_grant` scope. Unauthorized evidence is simply invisible — it is
  neither read, hinted at, counted, nor logged.

## 4. The four canonical assessment states

| State | Meaning | Reason codes |
|---|---|---|
| `Verified` | Firm, authorized, source-linked confirming evidence for this item | `direct_evidence`, `corroborated`, `alternative_path_met` |
| `Not established` | Authorized evidence does not firmly confirm it — **not** a negative verdict | `no_evidence_in_scope`, `ambiguous_evidence`, `partial_evidence`, `temporal_mismatch`, `evidence_revoked`, `classification_ambiguous`, `candidate_evidence_only` |
| `Appears unmet` | Authorized evidence affirmatively indicates non-satisfaction | `affirmative_contradiction` |
| `Review unavailable` | The check itself could not run — always a durable, stored assessment row with its reason (a computation failure persists as this state; a failed *persistence* of the row itself is never reported as any state — the entry is excluded instead, doc 08 §2a) | `ai_unavailable`, `evidence_source_unavailable`, `timeout`, `assessment_error` |

- These four are canonical and closed: **an outage label is not a fifth
  state.** UI aliases map onto them exactly — `check unavailable` and
  source-outage wording are display aliases of `Review unavailable`;
  `1 not established` renders `Not established`. The alias map is a C8
  contract table (doc 16 rows bind it); inventing a new state is a contract
  violation.
- Gate derivation is deterministic: `Fully verified` ⟺ every `required` item
  of the governing `requirement_version` is `Verified`. Anything else —
  including a single `Review unavailable` — is `Not fully verified`, labeled
  truthfully (e.g. `5 of 6 required verified · 1 not established`).
- Explanation obligation: every non-`Verified` item renders its reason in
  member language, with the no-negative-inference sentence on
  `Not established` and `Review unavailable` (approved evidence-authorization
  boundary state: "this does not mean you lack the experience").

## 5. Transitions (with doc 03 §§5–6)

- New governing `requirement_version` ⇒ new assessment rows; old rows are
  history bound to their version.
- Grant revocation/expiry ⇒ recompute without dead evidence; typical
  `Verified → Not established (evidence_revoked)`. Loss of prior verification
  is visible and explained; historical snapshots keep their historical labels
  and are never rewritten.
- Member correction (add/fix evidence, fix atomization reading) ⇒ reassess;
  append-only history preserves what was believed before and why it changed.
- `Review unavailable` is always retryable; retry succeeds into a real state
  and never inherits the failure.

## 6. Evidence-source port (deliberately unbound here)

Assessment consumes evidence through a port interface — `list authorized
records (grant scope) → typed evidence records with identity, version, time
span, class` — with the binding chosen at C5 under a then-current claim.
Reason: at the base SHA, future Profile direction is not verified live
member-evidence truth, and Journal is dormant by owner decision. Candidate
bindings C5 must evaluate: the legacy Slate's evidence structures, the
Profile/evidence foundations *if by then cut over and verified*, and
member-entered evidence records created inside the qualification flow.
Binding is an architecture-acceptance-level decision if it lands before C5
activation; a blocker only if C5 arrives with no truthful live source — in
which case member-entered evidence (created within the flow, private,
correctable) is the safe minimal path.

## 7. Anti-goals (enforced by contract tests)

No overall score, percentage, probability, ranking, employer prediction, or
paid influence anywhere in assessment data, APIs, or UI. No silent weakening
of the gate by AI (AI proposes; the deterministic gate decides). No renaming
of ambiguous evidence as verified. No treating fixture evidence as member
truth. No negative inference from absence, ever.
