# Delivery contracts and safe custody

Package: `PS-DELIVERY-CONTRACTS-SAFE-CUSTODY-001`

Path: Protected
Production authority: withheld

## Outcome

Keep repository and local delivery guidance consistent across supported
runtimes, persist an OpenCode worker identity before uncertain dispatch, and
deliver gated tooling for monotonic scope release and guarded main
reconciliation. Candidate A introduced it compatibly and dormant; the later
qualified Candidate B cutover enabled its index capabilities.

Candidate A's compatible delivery and routing code was reviewed and accepted in
PR 1046 at `1485b3d2bc98547654a8f2d08b527c84e4ae86ba`. Its six separately
reviewed local OpenCode helper files were installed after acceptance with
original-byte checks and a fake-process/no-provider test; the installation
manifest is retained outside the repository.

Candidate B's qualified, atomic migration of the existing machine registry to
schema 2 has completed with its deterministic backup. The separately reviewed
schema-4 `CURRENT_LANES.json` cutover was accepted in PR 1073 at
`7fd5c19c3877f48865b832ecd80283c4af09e373`. The index now declares the
`safe_custody_v1` capabilities; each use still requires its exact live claim,
caller, accepted-tool, worktree, and journal gates. A narrow claim-path safety
repair was accepted in PR 1078 at
`17926f436d60f203db8ad5b7b5e31c12867686cc`. The original package then
resumed and completed its journaled, non-rewriting reconciliation from preserved
checkpoint `8345307b00eeab5370df6b183c1c17e8098556dc` to pinned main
`10bcfeb345040c9de727b5ea180f9fedd73af4b8`. Its resulting merge commit
`01df08ddc47c00c9e24d077e70f1d394cde867b4` has the same tree as that
accepted main. At this report's pre-merge snapshot, the package claim was
active and not yet closed; the authoritative claim and review evidence record
subsequent status.

## Candidate A acceptance

- Current claims remain compatible and old delivery/lifecycle behavior remains
  green.
- A strict optional claim `scope_release` proof permits only exact path removal
  and/or a strict semantic reduction of hierarchical domain coverage; domain
  permutations and redundant descendants are no-ops, and fixed controls cannot
  be released.
- A machine-local freeze spans the asynchronous control PR and atomically
  becomes `scope_sync_required` only after exact prepared-main ancestry, old
  claim digest, and accepted claim-transition lineage proofs.
- Reconciliation pins C/M, limits conflicts and final delta to retained owned
  paths, prevents resolution edits to every non-conflicted index path, journals
  every side-effect boundary, preserves exact committed R, and
  ends moved-main recovery as `refresh_required` without reset or force push.
- Migration binds the actual caller, runs only from accepted delivery-tool
  bytes, self-digests schema-2 state, and proves its exact backup again on
  already-migrated recovery.
- Old accepted clients refuse schema-2/4 state before side effects.
- Reviewed OpenCode helper staging and its post-acceptance installation prove
  create-new invocation evidence, early structured primary-session capture,
  separate streams, ambiguity refusal, and no automatic replay with a fake
  process and no provider call.
- Independent reviewers assessed the exact Candidate A and schema-cutover
  candidates before their respective implementation PRs.

## Exclusions

The accepted Candidate A registration changed only this package's
`PACKAGE_REGISTRY.json` accounting. No product package, Media, Corporate,
MyData, Interview, unrelated Azure CI/pipeline surface, paid provider,
production flag, database schema, or deployment is part of this package.
Existing sealed-QA exceptions and owner-reassignment recovery controls remain
intact.
