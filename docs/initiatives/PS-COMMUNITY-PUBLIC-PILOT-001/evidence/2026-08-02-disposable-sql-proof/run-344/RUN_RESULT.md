# Disposable Community SQL proof — run 344 result

## Outcome

Azure DevOps run `344` is a valid, checksum-verified **failed proof**. It is
not Community migration runtime evidence and does not authorize a third run,
production migration, feature activation, PR, merge, deployment, or a live
claim.

The reviewed diagnostic harness reported `inside_preflight_unexpected`. This
proves that the outer isolated client execution returned a strictly validated,
content-free failure record. It does not identify or prove the exact SQL
connection, name-resolution, driver, query, or server-identity outcome inside
that stage. No migration proof step was recorded.

## Bound source and run

- Worktree: `/Users/petercarter/.codex/worktrees/6be8/portfolio`
- Branch: `codex/2026-08-01-community-primary-feed-sol-ultra`
- Source SHA: `2234597b2024ee1f1eb5e706cf8b94aff345003f`
- `origin/main` at execution: `33342495227b55ed0077388899b3f5de44f69de3`
- Pipeline definition: `2`, `community-sql-proof-20260802-14f8ebe`
- Run/build: `344`, `20260802.2`
- Reason: manual
- Start: `2026-08-02T22:38:29.313477Z`
- Finish: `2026-08-02T22:40:08.910009Z`
- Hosted image: `ubuntu22`, version `20260720.234.2`
- Azure result: failed
- Azure run: <https://dev.azure.com/peerslate19/portfolio-site/_build/results?buildId=344>

The source, branch, manual-reason, agent, and feature-default-off guards passed.
Definition `2` remains triggerless and now has exactly two manual runs: the
preserved run `339` and this final authorized run. It was not deleted because
deletion could remove the associated run and artifact record.

## Verified evidence

The always-published `CommunitySqlProofEvidence` artifact was downloaded and
both files pass the adjacent `SHA256SUMS` file:

- `community-sql-proof-evidence.json`:
  `ddf1b031c68e80b127b0b9be9b56034bc185c740450f78413f47523441373b30`
- `run-envelope.json`:
  `5883b395f0f3edd3a3427b1f0bb8e07ee910d30d1db5fffce41e91335aacea07`

The sealed record proves only:

- exact source, branch, definition, build, and hosted-image binding;
- Community remained feature-default-off;
- no member data was used and no production action occurred;
- an allowlisted inside-client failure record was returned;
- the job-owned Docker cleanup step passed and `cleanup_confirmed` is true;
- evidence sealing, hashing, and artifact upload succeeded.

It does **not** prove SQL identity/readiness, database creation or cleanup, any
forward migration, idempotency, the two-owner verifier, empty rollback, or
populated rollback refusal. Missing proof steps mean not assessed.

## Preparation verification

- 32 focused diagnostic tests: PASS.
- Harness plus Community runtime and verifier suite: 127 tests PASS.
- Operational-readiness merge checks: 21 tests PASS.
- Python compilation, inert plan, YAML structure, and diff whitespace: PASS.
- Independent Sol very-high Protected review: PASS with no open P0/P1/P2.
- Run `339` evidence remained byte-for-byte valid throughout.

## Handoff gate

Pete directed this Codex task to stop after this proof and hand the remaining
Community work to Claude. No third run is authorized in this task. Claude must
first diagnose the bounded `inside_preflight_unexpected` failure without
rewriting either run's evidence, then obtain or verify the next protected gate
before another disposable run or any release action.
