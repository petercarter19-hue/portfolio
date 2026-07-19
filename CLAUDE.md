@AGENTS.md
@docs/AI_WORKFLOW.md

> **MANDATORY PRE-WORK GATE**
> Before any analysis that may lead to a write, code change, migration, deployment, or product decision, open and follow [`START_HERE.md`](START_HERE.md). Synchronize from authoritative `origin/main`, then read `docs/governance/CURRENT_BASELINE.yaml`, `docs/governance/CURRENT_STATE.md`, `docs/governance/ACTIVE_INITIATIVES.md`, the current Bible/Roadmap named there, and your assigned initiative package. Stop rather than guess when any pointer or ownership record is unclear. Every material closeout must use [`docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).
>
> **Authoritative versions are always the ones named in `docs/governance/CURRENT_BASELINE.yaml` (currently Bible v2.4 + Roadmap v2.3).** This supersedes any version-specific note below.

# Claude / Claude Code instructions

The live authority is `docs/governance/CURRENT_BASELINE.yaml` and its referenced
Bible v2.4 / Roadmap v2.3 documents. Consult `docs/governance/DOCUMENT_CONTROL.md` when
an older specification conflicts. Do not treat v1.1-v1.4 or Iris/Direction C
language as current merely because it remains in repository history.

ChatGPT Work is the owner-designated PeerSlate manager. Claude Code owns only
the public-experience package explicitly assigned in
`docs/governance/ACTIVE_INITIATIVES.md`. Before editing, read that initiative's
README, confirm its reserved branch and files, and verify the exact `origin/main`
base. Do not begin Interview Studio work while the résumé package is active
unless the manager assigns a separate writer, branch, and non-overlapping files.

The guardrail suites `tests/test_site_rules.py` and
`tests/test_governance_pointers.py` must stay green.

For every user-facing task, read
`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`. Name the exact approved
visual authority before implementation. A selected mockup or demonstration is a
binding minimum: the real experience must match or exceed it, and material work
requires comparison screenshots plus Pete and ChatGPT Work visual acceptance.
Do not treat functional completion as permission to ship a visual downgrade.

- Treat `AGENTS.md` as the shared PeerSlate product and quality rules.
- Treat `docs/PEERSLATE_SITE_RULES.md` as binding where it does not conflict
  with the current baseline, Bible, Roadmap, or Document Control record.
- Treat `docs/AI_WORKFLOW.md` as the canonical Git, branch, handoff, pull-request, deployment, and cleanup workflow. Read it in full before repository work.
- Read the current baseline, document-control record, and assigned initiative
  package before planning changes.
- Start in plan mode and inspect the repository before editing.
- At the start of every session, inspect `git status`, the current branch, both remotes, and the latest commit before editing.
- `origin` is Azure DevOps and the only source of truth. `github` is a backup mirror. There is no active remote named `azure`.
- Never commit or push directly to `main`. Start each new task from current `origin/main` on a short-lived `work/YYYY-MM-DD-task-name` branch.
- Only one writer may own a branch. Do not overwrite Codex changes, merge branches, switch worktrees, or continue another agent's branch without an explicit handoff containing the branch and exact full SHA.
- Before handing work to Codex or another computer, commit it, push it to `origin`, provide the required handoff, and state that active-writer ownership is relinquished.
- When reviewing Codex work, identify regressions, missing requirements, accessibility issues, and places where fixture UI is being mistaken for production functionality.
- Keep project memory concise. Durable product decisions belong in the repository documents, not only in chat memory.
- Push task branches to `origin`, merge them through an Azure pull request using squash merge, and delete the source branch after merge.
- GitHub Actions deployment is intentionally disabled. Do not enable, configure, suggest, or rely on it for publishing. Use `azure-pipelines.yml` and `docs/AZURE_DEVOPS_DEPLOYMENT_RUNBOOK.md`.
- Never claim a change is live until the Azure pipeline succeeds and the public production URL is verified.
- Never stage or commit the machine-local `.claude/launch.json`, `.env`, credentials, tokens, publish profiles, or other secrets.
