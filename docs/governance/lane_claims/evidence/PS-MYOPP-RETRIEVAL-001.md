# PS-MYOPP-RETRIEVAL-001 — candidate evidence

## Scope and authority

Pete's package-selection and full-sequence direction is recorded at
`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-08-31/start-c4-go-all-the-way`
(claim `owner_outcome_ref`). The disposable-proof envelope is authorized by
Pete's direct in-session answer, reference
`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-08-31/disposable-proof-envelope-c4-through-c9-yes-i-do`.
Repository authority `through_merge`; production authority withheld. This
evidence grants no deployment, enablement, index provisioning, provider
contact, or production/staging schema action.

## P-1 repository evidence

The doc 08 s2a owner-bound search worker (execution-record binding with no
owner parameter; start, per-write-via-C5, and pre-persistence rechecks;
authorization_changed writing nothing beyond the bounded failed status),
deterministic doc 04 s4 ordering with byte-stable pagination, honest
partial/degraded/ceiling behavior, REC-05 projections structurally unable to
carry member data, the doc 04 s10 fence (finite-relevance validation,
duplicate dedup, canonical-only display), registration-time refusal of
unsupported criterion kinds (criterion_unsupported), and the additive
PS-MYOPP-004 trio are implemented and locked by 104 package tests plus
127 C2/C3/C5 regression tests, all green at the frozen candidate.

A writer self-review scan fixed 3 blockers, 7 importants, and 11 minors
pre-freeze; the independent review then found and the writer fixed a real
cancel/persist race (results could be served for a cancelled search in the
reference repository) with the guard placed inside the repository's own
lock, mirroring the SQL backstop THROW 55731.

## P-2 disposable Azure SQL proof

- Gate time 2026-08-31T14:06:54Z; database `ps-myopp-c4-gate-20260831-a1` (Basic,
  `peerslate` server), attempt 1 of 3; attempts a2/a3 never created.
- Executable SHA-256 `a2d77e1fcfd16cc15cc45c1b42b8b74addc9b8e5160c27d09db4144f312230ca`
  (independently recomputed by the reviewer at both frozen SHAs).
- Prerequisites ['PS-PLAT-000', 'PS-MYOPP-001', 'PS-MYOPP-002', 'PS-MYOPP-003']; verifier returned verified = 1;
  rollback rehearsed; full object inventory recorded.
- Database deleted with ResourceNotFound confirmed; the temporary firewall
  rule was removed; no production or staging database was contacted.

## Review

Independent read-only exact-SHA review: candidate `2270a5b1` REVISE
(one blocking race plus four important findings, all execution-proven);
fixed candidate `aa00c0e1da924cfe10113ca0d5543ee9e7e594b9` PASS after the
reviewer reran its own two-thread reproductions and complete probe battery
with no regressions. Reviewer: a fresh Claude Opus session dispatched by the
writer with a fixed pre-written handoff (provenance disclosed);
reference `agent:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/myopp-retrieval-independent-reviewer-a1`.

## Residual recorded per the reviewer (obligation 16)

A microseconds-wide window remains between the snapshot persist committing
and the terminal write: a member cancel landing exactly there yields a
cancelled execution whose complete, fully-backed snapshot remains readable
through results(). This interleaving is inherent to the mandated
snapshot-last ordering (production SQL permits the identical schedule), is
handled gracefully (truthful cancelled record, no raise, nothing partial or
fabricated), and its full closure is a contract decision - narrowing the
doc 04 s3 cancellable flag once an execution reaches ordering - which
belongs to the package owner, not a fix round. Recorded here so C8's
member-facing copy and any future cancellable-flag decision inherit it.

## Coordination record

docs/governance/PACKAGE_REGISTRY.json entered the claim via extend-surfaces
(PR 802) after the prior holder closed. The C4 test suite's fixture idiom
triggered repo-wide secret-scan false positives mid-delivery; the CI
allowlist package (independent third entry, separately owner-referenced)
resolved it, and this package's README records the non-key-shaped-fixture
guidance for future suites.
