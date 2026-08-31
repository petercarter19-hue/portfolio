# PS-MYOPP-QUALIFICATION-001 — candidate evidence

## Scope and authority

Pete assigned C5 to this writer via the Codex program-management handoff
(`session:01a02f42-15ac-7d92-a2a9-60b7e800c388/owner-direction:2026-08-30/claude-finish-c5`)
and authorized the bounded disposable proof envelope in chat on 2026-08-31,
including one temporary server firewall rule for the proof, removed
immediately after. Repository authority remains `through_merge`; production
authority remains withheld. This evidence grants no staging or production
schema action, deployment, enablement, provider contact, search execution,
UI work, C4, or any other package.

## P-1 repository evidence

The owner-scoped evidence port and qualification service prove: reads
restricted to the member's confirmed, unarchived, version-pinned Workshop
knowledge records through the governed, already-applied
`usp_ListOpportunityEvidenceForOwner` procedure; explicit, inspectable,
revocable, expiring grants fixed to the `qualification_verification`
purpose with class/record scope enforcement; the four canonical assessment
states under Pete's approved evidence policy with doc 07 §4's exact reason
vocabulary; one current assessment per member x requirement item x
requirement version with idempotent evaluation, append-only revisions, and
correction/retry/revocation/expiry recompute; the deterministic
`Fully verified` gate over required items only, with preferred criteria,
practical-fit observations, and AI proposals structurally excluded; a
fenced, canary-proven proposal-only AI seam that never persists, decides,
or sees unadmitted or cross-member content; and honest failure semantics —
computation failure lands a durable `review_unavailable` row, persistence
failure raises a distinct error and fabricates nothing.

A writer self-review pass (independent Opus scan, execution-confirmed)
found and fixed 3 blocker and 6 important defects pre-freeze, each locked
by a dedicated regression test; details in the package
OWNER_TECHNICAL_COMPLETION_REPORT.md.

At the frozen candidate the focused suites run green:
`tests.test_my_opportunities_qualification` + `tests.test_package_registry`
81/81; C2/C3 regression (`test_my_opportunities_criteria`,
`test_my_opportunities_canonical`) 48/48.

## P-2 disposable Azure SQL proof

- Authorized attempt: 1 of 3, `ps-myopp-c5-gate-20260831-a1`.
- Attempts a2 and a3 were never created.
- Pre-create exact-name lookup: `ResourceNotFound`.
- Azure scope: resource group `peerslate`; server `peerslate`
  (`peerslate.database.windows.net`); `centralus`; `Basic`;
  `SQL_Latin1_General_CP1_CI_AS`.
- Gate time: `2026-08-31T08:33:13Z`.
- Executable SHA-256:
  `305647f2db93fa3d5d6386c2f130a30196caa1f421a2bf08ff47958906314ab9`.
- Prerequisites applied: `PS-PLAT-000`, `PS-MYOPP-001`, `PS-MYOPP-002`.
- Forward apply: 84 objects created.
- Idempotent reapply: object inventory and ledger unchanged.
- Verifier: `PS-MYOPP-003_qualification_verify.sql returned verified = 1`.
- Rollback rehearsal: objects reversed and the target ledger row removed;
  forward reapplied cleanly after rollback.
- Post-delete exact-name lookup: `ResourceNotFound`; the temporary firewall
  rule was removed and the server's rule set restored to its prior two
  entries. No production or staging database was contacted.

## Review

Independent read-only exact-SHA review: candidate
`b819b6cfa960dc91563372d396f515d9a792b438` returned REVISE on one
documentation-only finding (the README described the pre-proof state); the
writer corrected the README and recorded findings F2–F6 as named forward
obligations, and the re-frozen candidate
`9adff9cb90db1fb1c05aee58a178691f8c46a0c3` (doc-only diff, reviewer-confirmed)
returned PASS. The reviewer ran ~60 adversarial probes of its own against
owner scoping, the gate, grants, the AI fence, and failure paths, and
independently recomputed the gate proof's executable SHA-256. Verdict and
answers are summarized in the receipt
(`docs/governance/lane_claims/receipts/PS-MYOPP-QUALIFICATION-001.json`).
The reviewer was a fresh Claude Opus session with no writer context,
dispatched by the writer with a fixed pre-written handoff; provenance
disclosed here for the record.

## Coordination record

`docs/governance/PACKAGE_REGISTRY.json` entered the claim via the governed
extend-surfaces transition (PR 792) after PS-AZURE-STARTUP-QUALIFICATION-001
paused at Pete's direction ("Let c5 finish", 2026-08-31, writer session
chat); that package resumes after this claim closes.
