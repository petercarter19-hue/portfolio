# PeerSlate - START HERE

This is the required first check for work that may change repository files,
product behavior, data, or a release. Its job is to prevent unsafe or wasted
work, not to turn every task into a governance exercise.

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

- Confirm what `origin` means in this checkout. Azure DevOps `origin/main` is
  authoritative where it is reachable; GitHub is a backup mirror.
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

When the ledger reports `controlled_idle`, ordinary writes are intentionally
blocked. After Pete names one exact next outcome, create only the small
delivery-activation branch described by `activation_policy`. The same bounded
activation path may reserve lane two during `active_delivery` only while the
recorded two-lane limit has capacity and the proposed mutable surfaces do not
conflict with an existing writer. Run:

```bash
python scripts/delivery_preflight.py --package PS-DELIVERY-CONTROL-001 --intent activate --fetch --require-clean
```

That branch may update only the ledger/baseline to reserve the selected
implementation branch, writer, surfaces, exclusions, and delivery path. Merge
the activation record before creating the implementation worktree. Do not put
product code in the activation PR. A full lane limit remains a stop; do not
pause, rewrite, or displace another lane to make room.

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
