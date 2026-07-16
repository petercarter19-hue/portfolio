@AGENTS.md
@docs/AI_WORKFLOW.md

# Claude / Claude Code instructions

## v1.3 governance — read BEFORE any product work (2026-07-16)

1. `PeerSlate_Company_and_Product_Bible_v1.3.docx` (repo root) — the
   authoritative product direction and implementation baseline. Version 1.2
   remains in the repository as the prior decision record.
2. `docs/PEERSLATE_SITE_RULES.md` — 85 locked rules for copy, IA, data,
   AI, design, and delivery. They bind humans and AI agents alike.
3. `docs/PEERSLATE_V12_IMPLEMENTATION_INSTRUCTIONS.md` — the approved
   corrective package program (PS-PLAN-002 → PS-CONSTELLATION-001) and
   delivery method. Version 1.3 adds PS-PROFILE-001, PS-PHOTOS-001,
   PS-CONNECT-001, and PS-LINKS-001; where the instructions conflict with
   the v1.3 Bible, the Bible controls. One package, one branch, one
   reviewable outcome.
4. `docs/INITIATIVE_CHECKLIST.md` — answer it in every package handoff.
5. Status (2026-07-16): PS-PLAN-002 ✔, PS-RULES-001 ✔,
   PS-BRAND-NAV-001 / PS-INTERVIEW-002 / PS-FEED-002 delivered as
   public-safe slices; **PS-JOURNAL-002 is owner-held** ("hold off on
   the journal"); PS-QUALIFY-001, PS-RESUME-001, PS-CONSTELLATION-001
   are auth-gated for the private phase.

The Bible governs product direction; the repository governs current
implementation. When they conflict, report the conflict before coding.
The guardrail suite `tests/test_site_rules.py` must stay green.

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
