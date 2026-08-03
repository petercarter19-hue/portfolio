# PS-AZURE-RELEASE-RELIABILITY-001 - completion record

## Core record

- Task/package and delivery path: `PS-AZURE-RELEASE-RELIABILITY-001`, Protected
  shared-infrastructure release.
- Outcome and member/site effect: Local implementation complete; exact PR,
  merge, pipeline, and post-release live evidence remain pending. The change
  makes deploy-and-verify one atomic operation per selected cumulative `main`
  release, with manual production deployment explicit and false by default.
- Branch, base SHA, final SHA, and changed paths: branch
  `work/2026-08-03-azure-release-reliability-001`; base
  `f0a802b6bdd9b388facb07b786d76b1809759ae9`; final SHA pending. The bounded
  paths are the Azure pipeline, its regression, the lean workflow clarification,
  the existing PS-OPS release authority, and this package.
- Verification performed and result: focused operational/governance suite
  passed 44 tests; Azure PR `258` iteration 1 validation run `416` passed the
  implementation merge ref with 1,762 tests and 20 environment-specific skips;
  `git diff --check` passed. The final source update remains subject to fresh
  blocking validation before merge. Current live latency,
  gzip, immutable caching, auth issuer, route, and exact build-411 identity
  checks passed. Exact independent review and final Azure PR validation are
  pending.
- Release state: local implementation complete; not merged or deployed.
- Known limits, deferred work, or owner decision needed: deployment-slot
  architecture, stale Candidate provisioning, active Community SQL proof, and
  branch/worktree cleanup remain separate as recorded in `README.md`.
- Next action: complete exact-SHA independent review and final validation on
  open Azure PR `258`, then squash-merge and verify the automatic production
  release.

## Protected additions

- Shared infrastructure: exact incident chronology, release-identity behavior,
  negative manual-run path, batching, atomic lock, rollback, and live evidence
  are recorded in this package.
- Data, identity, privacy, authorization, deletion, publication, and AI: no
  application contract or production setting is changed.
- Actual handoff: none; the same self-managed writer retains ownership through
  release and closeout.

## Plain-English translation

PeerSlate's code deployments were succeeding, but extra manual runs were
restarting the same site and changing the live build before the first run could
prove what it had installed. This change makes deployment and proof one locked
operation and makes an extra manual production deployment a deliberate choice.
