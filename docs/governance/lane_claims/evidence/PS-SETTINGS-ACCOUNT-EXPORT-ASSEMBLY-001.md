# PS-SETTINGS-ACCOUNT-EXPORT-ASSEMBLY-001 review evidence

Runtime-inert review-tail record for the Protected C2 Settings
account-export assembly package. The paired receipt is
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-ASSEMBLY-001.json`.

- **Package and authority boundary:** Protected,
  `review_requirement: independent`, `repository_authority: through_merge`,
  `production_authority: withheld`. This record binds review evidence only.
  It grants no storage or SQL permission (both grant layers remain pending:
  the container-scoped role assignment awaits the owner because the
  manager's harness declines permission-granting actions; the SQL contained
  user/EXECUTE grants require the AAD-admin path), no schedule, no C3/C4 or
  B1/D–F activation, no deployment or enablement. Account-wide export
  remains unavailable today; nothing member-facing exists.
- **Reviewed candidate:** `366d34834991536b5ddd4e20d6655810e225baf2` on
  `work/2026-08-28-settings-account-export-assembly-001`, activation base
  `7eb29a3d71f8bbdc0b8a5be351f3e2822884caf8`. Custody: three writer commits
  (`agent:claude-code/settings-c2-writer`, Sonnet, incl. the gate-round
  verification-script fix), one manager commit (`19a8833b`: registry gate
  block + provisioning record), one writer correction-round-2 commit. All
  changes inside the claim's frozen surfaces; the sealed C1 migration files
  and (post-gate) the verification script were never edited after sealing.
- **Gate pairing (transferred C1 obligation — fulfilled):** the manager's
  paired gate run on disposable `ps-migration-path-20260828-c2` executed
  the owner-isolation verification against a real engine; the registry
  gate block records `verification: PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql
  returned verified = 1`, digest `767e8509fcd7b8933157cfa331e85b3395a6043a2d4506ed0912166904b84917`
  unchanged. A first gate attempt failed inside the original verification
  script (INSERT-EXEC vs ROLLBACK) and was corrected by the writer; the
  script is sealed as of the gate that proved it (THROW 57724 intentionally
  skipped; recorded, not renumbered).
- **Provisioning state at review time (manager actions under the owner's
  recorded program authorization):** private container
  `peerslate-private-account-export` exists on `peerslatecapturemedia`
  (private at container and account level); workload identity
  `peerslate-account-export-worker` exists (clientId `b84a0485-…`,
  principalId `e6a73ef9-…`). No grant of any kind has been made.
- **Independent review:** a fresh Opus reviewer (read-only, distinct task
  from writer and manager) reviewed `19a8833b` → CONDITIONAL (2 MODERATE
  code/doc, 1 MODERATE doc-contradiction, 5 lower; zero privacy/identity/
  authorization defects; manager's commit judged substantially clean), then
  confirmed all eight fixes on `366d3483` by re-running its own
  reproductions → **PASS, zero findings open**. Suites reproduced: 91
  passed / 121 subtests, plus 246/166 across governance suites at the first
  round. Determinism hash byte-identical across both candidates. Zero
  mutations across all rounds.
- **Round 3 (secret-scanner) and final confirmation:** after the PASS on
  `366d3483`, the PR validation build failed the repository-history secret
  scan on the synthetic example-UUID fixture in the two C2 test files. The
  fixture was replaced with an entropy-dead case-sensitive value and the
  branch was squashed to a single delivery commit on base `7eb29a3d` so no
  reachable commit carries the old string. The reviewer's confirmation round
  verified this by git plumbing (`git log --all -S` empty; branch shape one
  commit; sealed set byte-unchanged), reproduced the suites at exit 0,
  found two record defects (a receipt naming the superseded candidate and a
  round-3 note recording the rejected first-attempt fixture as shipped),
  and pre-approved the exact corrections as merge-ready. The delivered tree
  is `cdaaa1a538040d40bb887b344fa224e0f2be2d00` (the squash plus those
  record corrections); this receipt was reissued fresh for it rather than
  retargeted with a stale timestamp, per the reviewer's instruction. The
  reviewer noted, correctly, that receipt/evidence records are authored on
  the writer/manager side for a review the reviewer performed; the
  reviewer's own verdict text lives in this session's transcript and its
  outcome facts are restated here without alteration.
- **Provisioning update 2026-08-29:** on the owner's explicit chat
  direction (ref `pete-chat-2026-08-29/settings-c2-worker-rbac-grant`),
  the manager granted `peerslate-account-export-worker` the
  `Storage Blob Data Contributor` role scoped to the single container
  `peerslate-private-account-export` and verified the assignment by
  listing it. The SQL-side contained user and least-privilege `EXECUTE`
  grants remain pending via the AAD-admin authority path (C4).
- **Transferred notes for C3/C4 (recorded, non-blocking):** post-promotion
  failure (now corruption-class only) can orphan a committed final object
  with no `cleanup_final` caller — cleanup orchestration is deferred by
  C0's expiry/cleanup design and belongs to C3/C4; C3 must add the three
  owner procedures to `services/database_service.py` ALLOWED_PROCEDURES
  (unclaimed in C2) and handle the owner procedures' no-result-set early
  return; C4 owes the two grant layers, any schedule decision, and live
  proofs (nothing live was proven here — all storage/DB behavior in this
  package is mock/fixture-proven except the gate-executed SQL verification).
