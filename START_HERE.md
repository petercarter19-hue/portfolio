# PeerSlate — START HERE

This is the mandatory first file for every Cowork, Claude Code, Codex, human developer, and reviewer session. Do not write code, change documents, run a migration, or make a product decision until this checklist is complete.

## 1. Synchronize the authority

```bash
git status --short --branch
git branch --show-current
git remote get-url origin
git remote get-url github
git fetch origin --prune
git switch main
git pull --ff-only origin main
git status --short
```

Inspect before switching. If the checkout is dirty, contains an untracked file,
or is already on another task branch, identify and preserve that work before any
branch change. Use a clean task worktree when that is safer. Stop if `main` does
not fast-forward or `origin` is not the authoritative Azure DevOps remote. Do
not copy a repository folder between computers as a synchronization method.

## 2. Read in this order

1. `docs/AI_WORKFLOW.md`
2. `docs/governance/CURRENT_BASELINE.yaml`
3. `docs/governance/CURRENT_STATE.md`
4. `docs/governance/ACTIVE_INITIATIVES.md`
5. The current Bible and Roadmap paths listed in `CURRENT_BASELINE.yaml`
6. `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`
7. `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`
8. For ChatGPT Work manager or cross-lane sessions,
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

Stop and report when authority, ownership, identity boundary, migration ownership, or current document version is unclear. Never guess.

## 4. Mandatory closeout

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`. Every report must preserve full technical detail and include a separate plain-English translation, product functionality, architectural connection, evidence, limitations, and the clear next step.
