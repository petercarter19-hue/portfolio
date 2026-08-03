# PS-AZURE-RELEASE-RELIABILITY-001 - completion record

## Core record

- Task/package and delivery path: `PS-AZURE-RELEASE-RELIABILITY-001`, Protected
  shared-infrastructure release.
- Outcome and member/site effect: Released and verified live. Deploy-and-verify
  is now one atomic operation per selected cumulative `main` release, with
  manual production deployment explicit and false by default.
- Branch, base SHA, final SHA, and changed paths: branch
  `work/2026-08-03-azure-release-reliability-001`; base
  `f0a802b6bdd9b388facb07b786d76b1809759ae9`; reviewed source
  `c743e0fca164e7da5ea73ccfd98636e39d47d4f8`; squash-merged Azure `main`
  `7161d5d495e362b236594a9ddf69138bd8ca8ca2`. The bounded paths are the Azure
  pipeline, its regression, the lean workflow clarification, the existing
  PS-OPS release authority, and this package.
- Verification performed and result: focused operational/governance suite
  passed 44 tests; Azure PR `258` iteration 1 validation run `416` passed the
  implementation merge ref with 1,762 tests and 20 environment-specific skips;
  `git diff --check` passed. Final PR validation run `418` passed on the exact
  reviewed source, and independent complete-diff review returned PASS.
  Automatic batched-CI run `419` passed Build and the locked ProductionRelease
  stage for exact main `7161d5d495e362b236594a9ddf69138bd8ca8ca2` without a
  manual duplicate. Live `/healthz` returned 200 and exact release
  `896d8ac3ce01a2052b29eb6d`; homepage, Interview Studio, signed-out auth,
  hosted sign-in, and canonical Azure-host redirect checks passed. HTTP/2,
  Always On, gzip, and immutable content-hash caching remain enabled. Five warm
  homepage samples were 0.24-0.40 seconds; Interview Studio was 0.31-0.62
  seconds; ten canonical resume samples had a 0.71-second median and a
  1.48-second maximum.
- Release state: reviewed, PR-validated, squash-merged, automatically deployed,
  and independently verified live.
- Known limits, deferred work, or owner decision needed: deployment-slot
  architecture, stale Candidate provisioning, active Community SQL proof, and
  branch/worktree cleanup remain separate as recorded in `README.md`.
- Next action: no runtime recovery action remains. Keep the active Community SQL
  proof, stale Candidate provisioning, and branch/worktree ownership cleanup in
  their separate lanes; do not treat their red or deferred state as a production
  deployment failure.

## Protected additions

- Shared infrastructure: exact incident chronology, release-identity behavior,
  negative manual-run path, batching, atomic lock, rollback, and live evidence
  are recorded in this package.
- Data, identity, privacy, authorization, deletion, publication, and AI: no
  application contract or production setting is changed.
- Actual handoff: runtime ownership is released after verified closeout. Deferred
  Community, Candidate, and cleanup work remains with its existing owner or a
  separately activated package.

## Plain-English translation

PeerSlate's code deployments were succeeding, but extra manual runs were
restarting the same site and changing the live build before the first run could
prove what it had installed. This change makes deployment and proof one locked
operation and makes an extra manual production deployment a deliberate choice.
