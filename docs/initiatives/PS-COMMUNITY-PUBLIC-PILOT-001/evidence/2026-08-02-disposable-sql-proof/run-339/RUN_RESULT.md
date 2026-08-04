# Disposable Community SQL proof — run 339 result

## Outcome

Azure DevOps run `339` is a valid, integrity-checked **failed proof**. It is
not Community migration runtime evidence and does not authorize a retry,
production migration, retention implementation, Candidate, feature
activation, deployment, or a live/public claim.

The run stopped fail-closed with `external_command_failed`. The current
harness deliberately excludes command output, but it also collapses every
checked outer command failure to that single code. Therefore the exact failed
operation cannot be recovered truthfully from this run. No migration,
idempotency, verifier, or rollback result may be inferred.

## Bound source and run

- Worktree: `/Users/petercarter/.codex/worktrees/6be8/portfolio`
- Branch: `codex/2026-08-01-community-primary-feed-sol-ultra`
- Source SHA: `14f8ebe85ff8a4c6f8ab56fe221fced7fc01da1c`
- `origin/main` at execution: `dbd2226bd7bd3ea4793d4e47aa797c676857b83f`
- Pipeline definition: `2`, `community-sql-proof-20260802-14f8ebe`
- Run/build: `339`, `20260802.1`
- Reason: manual
- Start: `2026-08-02T21:35:19.658883Z`
- Finish: `2026-08-02T21:36:45.457173Z`
- Hosted image: `ubuntu22`, version `20260720.234.2`
- Azure result: failed
- Azure run: <https://dev.azure.com/peerslate19/portfolio-site/_build/results?buildId=339>

The source/branch guard passed before the proof began. Definition `2` was
created triggerless for this proof and has exactly one run. It was not deleted
because deletion can remove the associated run and artifact record.

## Verified evidence

The always-published `CommunitySqlProofEvidence` artifact was downloaded from
run `339`. Its allowlisted evidence and run envelope both pass the adjacent
`SHA256SUMS` file:

- `community-sql-proof-evidence.json`:
  `57f2d128c00760e3d11bb068c612680d706a44a4079c679037d2b9234276e3bc`
- `run-envelope.json`:
  `a5ae1df5df7a83b884d48a29d91e1a1b6646ae3f44225affeaad5b27781a8805`

The sealed record proves only:

- exact source, branch, definition, build, and hosted-image binding;
- Community remained feature-default-off;
- no member data was used;
- no production action occurred;
- the job-owned Docker cleanup step passed and `cleanup_confirmed` is true;
- evidence sealing, checksum generation, and artifact upload succeeded.

It does **not** prove SQL image/digest validation, client image construction,
network or SQL startup, database cleanup, any forward migration, idempotency,
the two-owner verifier, empty rollback, or populated rollback refusal. Missing
proof steps mean not assessed, not failed or passed.

## Local preparation verification

- 22 focused wrapper/harness tests: PASS.
- Wrapper plus Community runtime and verifier suite: 117 tests PASS.
- Python compilation: PASS.
- YAML structure and embedded Bash syntax: PASS.
- Diff whitespace check: PASS.
- Independent Sol very-high review: PASS with no open P0/P1/P2 before queue.

## Required next gate

Before any second run, the harness needs a reviewed, content-free diagnostic
amendment that assigns allowlisted failure codes to each external-operation
boundary and preserves a strictly validated `inside_<code>` when the client
container returns a safe JSON failure record. It must continue to exclude
argv, stdout, stderr, environment values, credentials, connection strings,
and synthetic content while keeping cleanup unconditional.

Pete's authorization covered one run only. A new implementation commit, push,
or second run requires separate explicit authorization. No retry was queued.
