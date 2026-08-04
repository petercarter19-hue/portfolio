# Claude continuation handoff — Community public pilot

Paste this entire document into the existing Claude Community task. It is an
exact state transfer, not a claim that Community is live or release-ready.

## Transfer instruction

Pete is transferring `PS-COMMUNITY-PUBLIC-PILOT-001` from the current Codex
task to Claude. After accepting this handoff, Claude is the sole active writer
for the Community package. The Codex worktree must remain frozen as transfer
evidence. Do not combine this lane with the frozen PC lane or any historical
Community worktree.

Before changing anything, follow `AGENTS.md` and `START_HERE.md`, fetch
authoritative Azure DevOps `origin/main`, read `CURRENT_BASELINE.yaml`, verify
ownership and status, and compare any newer mainline change by path. Preserve
all existing Community evidence. Stop for a real ownership, privacy,
authorization, migration, retention, or material-visual conflict.

## Exact repository state at transfer

- Mac worktree:
  `/Users/petercarter/.codex/worktrees/6be8/portfolio`
- Branch:
  `codex/2026-08-01-community-primary-feed-sol-ultra`
- Reviewed proof source SHA:
  `2234597b2024ee1f1eb5e706cf8b94aff345003f`
- Authoritative `origin/main` at the last proof:
  `33342495227b55ed0077388899b3f5de44f69de3`
- The branch already merged that exact `origin/main` in local merge commit
  `09396ff`; `app.py` preserves both current Workshop registration/config and
  the Community routes/config. `CURRENT_BASELINE.yaml` preserves Community as
  active and keeps the retired Interview package retired.
- No Community PR, merge to `main`, production migration, deployment, or
  feature activation has occurred.
- Production pipeline ID `1` was not edited or queued by this proof work.
- Dedicated proof definition ID `2` is triggerless and must remain undeleted.

The final remote branch HEAD will include one later documentation-only commit
containing run `344` evidence and this handoff; verify it with `git rev-parse
HEAD` and `git log -3` before acting. Do not reset, clean, stash, or overwrite
the transfer evidence.

## Product and visual truth

Pete approved the primary `/the-slate` Feed locally and later approved the
Community Voice implementation and propagation checkpoints. Do not originate a
new visual direction or roll back to the earlier oversized Respond dialog.

Preserve the implemented direction:

- Threadline Signal Feed with one horizontal, non-wrapping `Replies & updates`
  Motion-card shelf and a persistent `View all Replies & Updates` path to the
  traditional vertical conversation.
- Wider, layered center Feed; professional left/right activity rails; subtle
  cool blue-gray Motion cards; pale tinted rail surfaces; restrained depth,
  borders, and shadows; large media; compact actions.
- Compact five-emoji Respond rail on hover/activation, with actual emoji,
  immediate private selection/removal, no large modal and no extra Done,
  Remove, Open-post, or Save step on the primary card.
- One compact auto-growing comment row immediately below reactions/comments
  and above the Motion shelf, with Voice and Send beside the field.
- The top Feed composer uses the same typed/Voice model. Community activity is
  single-line and compact.
- Full conversation and selected-contribution states are implemented locally,
  including the focused overlay and nested-reply depth guard.
- Community Voice is transient and private: explicit recording, permission,
  stop, transcription, editable review, explicit transcript insertion, then a
  separate user publish/reply action. Voice never publishes automatically.
- Server-derived identity/authorization, private local drafts, explicit Public
  selection plus confirmation, reusable multi-user architecture, and truthful
  Pete-only fixtures remain mandatory.

Primary fixture preview processes were left running at transfer:

- primary Feed: `http://127.0.0.1:5055/the-slate`
- secondary conversation fixture: `http://127.0.0.1:5056/the-slate`
- Community Voice fixture: `http://127.0.0.1:5065/the-slate`

These are local fixtures, not live multi-user or provider evidence. Restart
them from the repository scripts if stale; do not treat process presence as
acceptance evidence.

Read these controlling records first:

- `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/README.md`
- `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/PRIMARY_FEED_MAC_CONTINUATION_CHECKPOINT_2026-08-01.md`
- `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/SECONDARY_STATE_TRANCHE_1_CHECKPOINT_2026-08-02.md`
- `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/COMMUNITY_VOICE_PRIMARY_COMMENT_CHECKPOINT_2026-08-02.md`
- `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/COMMUNITY_VOICE_PROPAGATION_CHECKPOINT_2026-08-02.md`
- `docs/initiatives/PS-COMMUNITY-FEED-VISUAL-001/visual-authority/2026-08-01-pete-voice-first-lock/MANIFEST.md`

Use `git diff --name-status origin/main...HEAD` for the complete authoritative
Community overlay. Key runtime paths include `community_api.py`,
`community_routes.py`, `services/community_*.py`, `templates/community_feed.html`,
`static/css/community-v1.css`, `static/js/community-v1.js`, the three proposed
Community SQL/verifier files, and the Community test suite.

## Collision truth

The earlier PC worktree at `C:\Users\peter\Documents\pscf`, branch
`codex/2026-08-01-community-primary-feed-sol-ultra`, HEAD `3210e403...`, is
frozen historical evidence and is not an active writer. The PC-to-Mac overlay
was reconciled in `PC_TO_MAC_COLLISION_MATRIX_2026-08-01.md`. No separate live
Community product or feature gate was found. Do not revive or merge the PC
lane. This Mac branch is the sole continuation source until Claude accepts the
transfer.

## Disposable SQL proof truth

The Community flag remains default `false`. No production SQL or provider was
used. The dedicated pipeline is
`azure-pipelines-community-sql-proof.yml`; it has no deployment stage, service
connection, provider credential, host port, or repository/database volume.

Definition `2` has exactly two manual runs and is now out of retry authority:

1. Run `339`, SHA `14f8ebe85ff8a4c6f8ab56fe221fced7fc01da1c`, failed with
   `external_command_failed`. Its checksummed evidence is preserved under
   `evidence/2026-08-02-disposable-sql-proof/run-339/`.
2. Run `344`, SHA `2234597b2024ee1f1eb5e706cf8b94aff345003f`, failed with
   `inside_preflight_unexpected`. Its checksummed evidence is preserved under
   `evidence/2026-08-02-disposable-sql-proof/run-344/`.

Run `344` proves the exact source/branch/agent guard, feature-off boundary,
strict inside-client failure parsing, no member data, no production action,
and successful job-owned Docker cleanup. It records no successful database or
migration step. Do not claim SQL readiness, database cleanup, forward
migration, idempotency, verifier, or rollback evidence.

Run `344` evidence hashes:

- proof JSON:
  `ddf1b031c68e80b127b0b9be9b56034bc185c740450f78413f47523441373b30`
- run envelope:
  `5883b395f0f3edd3a3427b1f0bb8e07ee910d30d1db5fffce41e91335aacea07`

Read:

- `DISPOSABLE_X64_SQL_CI_PROOF_ARCHITECTURE_AMENDMENT_2026-08-02.md`
- `DISPOSABLE_X64_SQL_CI_DIAGNOSTIC_ARCHITECTURE_AMENDMENT_2026-08-02.md`
- both `RUN_RESULT.md` files and adjacent evidence.

The remaining failure is inside the client's preflight stage. Diagnose it
without altering either run's evidence and without immediately queueing a
third run. Likely inspection surfaces are the container's bounded environment,
`mssql-python` import/connection behavior, internal DNS/address binding, SQL
machine/build/edition query, and exception-to-code mapping. Do not infer which
one failed from timing alone. Any new diagnostic must remain content-free and
must never record argv, stdout, stderr, environment values, credentials,
connection strings, SQL results, or synthetic/member content.

No third disposable run is authorized by this Codex task. Present the exact
root cause or minimum reviewed correction and obtain Pete's next gate before
queueing again.

## Verification already completed

- 32 focused diagnostic tests: PASS.
- Diagnostic harness plus Community runtime/verifier suite: 127 tests PASS.
- Mainline operational-readiness checks after merge: 21 tests PASS.
- Community Voice, secondary-state, browser, responsive, focus, attachment,
  and XLSX results are recorded in their package checkpoints and evidence.
- Python compilation, JavaScript syntax where affected, inert plan, YAML
  structure, diff whitespace, and both run-339/run-344 evidence checksums pass.
- Independent Sol very-high review of the second-run source passed with no open
  P0/P1/P2 findings.

Rerun only tests relevant to new work. Do not repeat visual creation or the
entire historical review stack without a changed-risk reason.

## Remaining release gates

The Feed is not live. Before any public claim, Claude must truthfully resolve
or explicitly gate:

1. supported disposable SQL forward/idempotency/verifier/rollback evidence;
2. the proposed retention/deletion decision, which remains unapproved and
   unimplemented despite immediate public revocation and unattached cleanup;
3. production attachment/Blob/Defender and Voice/Speech configuration and
   cleanup truth, or an explicit bounded pilot disposition;
4. the current Candidate exact-SHA admission finding in
   `CURRENT_BASELINE.yaml`, if Candidate is used;
5. production migration sequencing and rollback/disable plan;
6. reviewed Azure DevOps PR/merge, deployment, default-off flag activation,
   and exact-source live smoke; and
7. honest owner-pilot labeling—never represent Pete-only fixture data as live
   multi-user behavior.

The package records Pete's earlier “Build and deploy it” direction, but Claude
must still verify the current authority, exact source, protected prerequisites,
and production targets before any destructive or externally visible action.
Do not push to `main`, bypass PR review, migrate production, alter retention,
enable the flag, or deploy merely because this handoff exists.

## Required Claude checkpoint

First return a concise continuation checkpoint containing:

- actual worktree, branch, HEAD, `origin/main`, and status;
- confirmation that Claude is sole Community writer and this Codex task is
  frozen;
- run-344 evidence verification and root-cause assessment;
- exact files proposed for the minimum correction;
- tests/review required, with redundant work removed;
- whether another disposable run is actually necessary;
- the remaining release sequence and explicit Pete gate; and
- confirmation that no PR, merge, production migration, deployment, retention
  change, or flag activation has happened.

After that checkpoint, continue only within Pete's explicit authority. Do not
delete definition `2`, either run, the branch, the worktree, or any evidence.
