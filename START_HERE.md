# PeerSlate — START HERE

This is the mandatory first file for every Cowork, Claude Code, Codex, human developer, and reviewer session. Do not write code, change documents, run a migration, or make a product decision until this checklist is complete.

## 1. Identify this checkout, then synchronize the authority

Run this first, in one block, before anything else. It answers "where am I, what
is `origin` here, am I current, and is anything unsaved" — the questions that
cause the most wasted work when they are assumed instead of checked.

```bash
git status --short --branch
pwd
git remote -v
git branch --show-current
git log -1 --format='%H %s'
git ls-files -v .claude/launch.json
git fetch origin --prune
git status --short --branch
```

Read the result before continuing:

- **`git remote -v`** — `origin` is not the same everywhere. In a local clone on
  Pete's computers `origin` is Azure DevOps and `github` is the mirror. In a
  hosted agent session the only remote is GitHub, named `origin`, and Azure is
  unreachable. Both are valid. Record which one you are in; never assume.
- **The second `git status --short --branch`** — after fetching, this reports
  `behind N` when your base is stale. **A cloud session branched from GitHub can
  be many commits behind Azure `main`.** Work built and tested on a stale base
  produces test results that do not describe the real code. Reconcile with
  current Azure `origin/main` and rerun the tests there before reporting
  evidence. See "Repository map" in `docs/AI_WORKFLOW.md`.
- **`git ls-files -v .claude/launch.json`** — `S` means skip-worktree is set and
  the machine-local file is protected. `H` means it is not, and a routine
  `git add -A` on this clone would commit another machine's local configuration.
  Index flags are per-clone and do not transfer, so this must be checked on each
  computer.

Then move to `main` and update:

```bash
git switch main
git pull --ff-only origin main
git status --short
```

Inspect before switching. If the checkout is dirty, contains an untracked file,
or is already on another task branch, identify and preserve that work before any
branch change. Uncommitted changes in a worktree are not captured by a branch
bundle, so preserve them explicitly. Use a clean task worktree when that is
safer. Stop if `main` does not fast-forward. Do not copy a repository folder
between computers as a synchronization method.

## 2. Read in this order

1. `docs/AI_WORKFLOW.md`
2. `docs/governance/CURRENT_BASELINE.yaml`
3. `docs/governance/CURRENT_STATE.md`
4. `docs/governance/ACTIVE_INITIATIVES.md`
5. The current Bible and Roadmap paths listed in `CURRENT_BASELINE.yaml`
6. `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`
7. `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`
8. For any designated session manager (ChatGPT Work/Codex or Claude Co-Work)
   or cross-lane session,
   `docs/governance/MANAGER_SESSION_HANDOFF.md`
9. The assigned initiative `README.md`
10. Relevant architecture decisions and evidence linked by that initiative

`docs/governance/DOCUMENT_CONTROL.md` records the authority order when an older
repository document conflicts with the current Bible or Roadmap.

## 3. Confirm before writing

Confirm the package ID, manager, branch owner, files/domains reserved, migration
owner, entry gate, current production baseline, named visual authority and
acceptance status when user-facing work is involved, and next required evidence.
Create a work branch from current `origin/main`.

Also confirm whether the package uses the self-managed delivery model, who owns
post-acceptance PR/deploy/closeout, whether shared governance files are reserved,
and which `Pass`, `Conditional`, or `Fail` evidence is required before final
acceptance.

Every package must name exactly one designated session manager. ChatGPT
Work/Codex and Claude Co-Work have the same manager authority when assigned;
Claude Code remains a separate implementation writer. Parallel managers may
coordinate different packages, but only one manager branch may reserve shared
governance files at a time.

Stop and report when authority, ownership, identity boundary, migration ownership, or current document version is unclear. Never guess.

## 4. Mandatory closeout

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`. Every report must preserve full technical detail and include a separate plain-English translation, product functionality, architectural connection, evidence, limitations, and the clear next step.
