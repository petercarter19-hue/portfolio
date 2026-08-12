# PeerSlate - START HERE

Use this first for work that may change files, behavior, data, or a release.
It prevents unsafe work without turning every task into governance.

## 1. Establish a safe starting point

Before editing, inspect the checkout, fetch the authority, and preserve work
that is not yours:

```bash
git status --short --branch
git remote -v
git branch --show-current
git log -1 --format='%H %s'
git fetch origin --prune
git status --short --branch
```

- Confirm what `origin` means. Azure DevOps `origin/main` is authoritative;
  GitHub is a backup mirror.
- Do not switch, reset, clean, or edit a dirty checkout that belongs to another
  task. Use a clean worktree when needed.
- Start a task branch from current `origin/main`. Do not push directly to
  `main`.

## 2. Read only what the task needs

Read `docs/governance/CURRENT_BASELINE.yaml`, then classify the work before
reading more:

Also read `docs/governance/CURRENT_LANES.json` and run the executable preflight:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent write --fetch --require-clean
```

Use `--intent read` for a read-only audit. If the ledger reports an
owner-directed reset, only its `writes_allowed_for` package may write. Do not
create a branch or worktree to work around a failed preflight.

In-place writer changes use the control-only `--intent transfer` flow in
`MANAGER_SESSION_HANDOFF.md`.

From `controlled_idle`, Pete must name one exact outcome before the small
ledger/baseline activation branch is created. During `active_delivery`, the
same path may add a writer only within the two-implementation-plus-one-direction
limit and with disjoint paths and exclusive domains. The direction slot may
write only initiative documentation/evidence, and only one active lane may be
production-capable. Run:

```bash
python scripts/delivery_preflight.py --package PS-DELIVERY-CONTROL-001 --intent activate --fetch --require-clean
```

Record the branch, writer, class, domains, surfaces, exclusions, and path. Merge
that control record before creating the implementation worktree. Product code,
a full class limit, or a path/domain collision is a stop.

Only writers consume capacity. To pause safely, commit and push the work
checkpoint, then create a dedicated
`work/YYYY-MM-DD-delivery-pause-<slug>` branch from current `origin/main`,
change only the ledger/baseline, record the fetched work SHA, and run:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent pause --fetch --require-clean
```

Merge only the control record. Paused work consumes no slot and resumes only
through fresh activation.

A completed non-production direction lane uses a clean grant branch:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent grant --fetch --require-clean
```

After grant reaches `origin/main`, keep the candidate frozen and run from a
clean current-main verifier:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent merge --fetch --require-clean --candidate-worktree <ABSOLUTE-FROZEN-WORKTREE>
```

The candidate must be a clean sibling sharing the Git directory and Azure
origin. Never alter it or use its old validator. Preserve its remote branch
through close; clean it up afterward. Close removes authority. This grants no
runtime or production rights.

| Path | Use for | Read next |
|---|---|---|
| Routine | Copy, isolated bug fix, test, or internal refactor with no trust, data, public-contract, or material-visual change | The relevant code and focused test. |
| Bounded | A feature or route change within an approved package and established architecture | The package README and the directly affected contract. |
| Protected | Identity, authorization, privacy, canonical data, migration, deletion/publication, consequential AI, shared infrastructure, or a materially revised visual direction | The package plus the named specialist standard and risk-specific evidence. |

Read the current Constitution and Roadmap only when their product rule or
sequence is relevant. Read a specialist standard only when its trigger applies.
`docs/governance/DOCUMENT_CONTROL.md` resolves a real conflict; it is not a
required reading assignment for ordinary work.

## 3. Confirm before writing

Know the task purpose, owner/writer, files or domain, current ledger state, and the one verification
that makes the result believable. Stop and ask when an ownership, identity,
privacy, migration, or visual-authority conflict is real. Do not stop merely
because an unrelated historical record is long or a global checkpoint is open.

## 4. Finish proportionately

Use the compact completion record in
`docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`. Record the branch/SHA,
what changed, verification, release state when applicable, and an honest next
step. Add protected-path evidence only when its risk trigger applied.
