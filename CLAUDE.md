@AGENTS.md
@docs/AI_WORKFLOW.md

# Claude / Claude Code instructions

- Treat `AGENTS.md` as the shared PeerSlate product and quality rules.
- Treat `docs/AI_WORKFLOW.md` as the canonical Git, branch, handoff, pull-request, deployment, and cleanup workflow. Read it in full before repository work.
- Read the four source-of-truth documents listed there before planning changes.
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
