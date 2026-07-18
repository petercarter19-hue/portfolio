# PeerSlate — START HERE

This is the mandatory first file for every Cowork, Claude Code, Codex, human developer, and reviewer session. Do not write code, change documents, run a migration, or make a product decision until this checklist is complete.

## 1. Synchronize the authority

```bash
git fetch origin --prune
git switch main
git pull --ff-only origin main
git status --short
```

Stop if `main` does not fast-forward, the worktree is dirty, or `origin` is not the authoritative Azure DevOps remote. Do not copy a repository folder between computers as a synchronization method.

## 2. Read in this order

1. `docs/AI_WORKFLOW.md`
2. `docs/governance/CURRENT_BASELINE.yaml`
3. `docs/governance/CURRENT_STATE.md`
4. `docs/governance/ACTIVE_INITIATIVES.md`
5. The current Bible and Roadmap paths listed in `CURRENT_BASELINE.yaml`
6. The assigned initiative `README.md`
7. Relevant architecture decisions and evidence linked by that initiative

## 3. Confirm before writing

Confirm the package ID, branch owner, files/domains reserved, migration owner, entry gate, current production commit, and next required evidence. Create a work branch from current `origin/main`.

Stop and report when authority, ownership, identity boundary, migration ownership, or current document version is unclear. Never guess.

## 4. Mandatory closeout

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`. Every report must preserve full technical detail and include a separate plain-English translation, product functionality, architectural connection, evidence, limitations, and the clear next step.
