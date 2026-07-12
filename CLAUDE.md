@AGENTS.md

# Claude Fable / Claude Code notes

- Treat `AGENTS.md` as the shared PeerSlate source of working rules.
- Read the four source-of-truth documents listed there before planning changes.
- Start in plan mode and inspect the repository before editing.
- Do not overwrite Codex changes, merge branches, or switch worktrees without checking `git status`, current branch, and recent commits.
- When reviewing Codex work, identify regressions, missing requirements, accessibility issues, and places where fixture UI is being mistaken for production functionality.
- Keep project memory concise. Durable product decisions belong in the repository documents, not only in chat memory.
- **Deployment until GitHub Actions is restored:** GitHub Actions are disabled for this project. Do not suggest, configure, or rely on GitHub Actions for publishing. Use the Azure DevOps deployment path in `docs/AZURE_DEVOPS_DEPLOYMENT_RUNBOOK.md`. Before claiming a change is live, verify both the Azure pipeline result and the public production URL.
