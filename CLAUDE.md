@AGENTS.md
@docs/AI_WORKFLOW.md

> **MANDATORY PRE-WORK GATE**
> Before any analysis that may lead to a write, code change, migration, deployment, or product decision, open and follow [`START_HERE.md`](START_HERE.md). Synchronize from authoritative `origin/main`, then read `docs/governance/CURRENT_BASELINE.yaml`, `docs/governance/CURRENT_STATE.md`, `docs/governance/ACTIVE_INITIATIVES.md`, the current Bible/Roadmap named there, and your assigned initiative package. Stop rather than guess when any pointer or ownership record is unclear. Every material closeout must use [`docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).
>
> **Authoritative versions are always the ones named in `docs/governance/CURRENT_BASELINE.yaml` (currently Bible v2.6 + Roadmap v2.5).** This supersedes any version-specific note below.

# Claude / Claude Code instructions

The live authority is `docs/governance/CURRENT_BASELINE.yaml` and its referenced
Bible v2.6 / Roadmap v2.5 documents. Consult `docs/governance/DOCUMENT_CONTROL.md` when
an older specification conflicts. Do not treat v1.1-v1.4 or Iris/Direction C
language as current merely because it remains in repository history.

PeerSlate uses a package-designated session manager. ChatGPT Work/Codex manager
sessions and Claude Co-Work have the same manager authority when the active
initiative assigns them. Claude Co-Work management is not Claude Code writing:
the manager reviews and coordinates branches but does not silently take over a
Claude Code implementation branch. Claude Code owns any implementation package
explicitly assigned in `docs/governance/ACTIVE_INITIATIVES.md`, including a
protected owner surface when the package says so. Before editing, read that
initiative's README, confirm its designated manager, reserved branch and files,
and exact `origin/main` base. Do not begin another lane unless it has a separate
writer, branch, worktree, and non-overlapping files.

Owner decision, 2026-07-19: Claude self-manages its assigned branch. That means
implementing, reviewing the complete diff, finding and fixing its own issues,
running focused/full/responsive/accessibility/visual checks, producing the
completion report and exact evidence, synchronizing with `origin/main`, and
preparing the Azure PR. After Pete/designated-session-manager product and visual acceptance,
Claude may complete the PR, pipeline, production verification, and closeout.
The designated manager may rely on Claude's coherent `Pass` self-certification rather than
repeat the full technical audit. Report `Conditional` or `Fail` whenever an
issue, conflict, or evidence gap remains.

The guardrail suites `tests/test_site_rules.py` and
`tests/test_governance_pointers.py` must stay green.

For every user-facing task, read
`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`. Name the exact approved
visual authority before implementation. A selected mockup or demonstration is a
binding minimum: the real experience must match or exceed it, and material work
requires comparison screenshots plus Pete and the designated session manager's
visual acceptance.
Do not treat functional completion as permission to ship a visual downgrade.
For every such package, complete the homepage-impact check required by the
standard. If `/` presents or links that product, a material product or visual
change requires a truthful, showcase-quality homepage parity update in the
same release wave or an explicitly sequenced downstream package. The real
product remains upstream authority; a stale homepage walkthrough may not ship
as the current product story.

Before Story design or implementation, also read
`docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`. The future authenticated
Story Composer is member-directed: supported items can be moved and resized,
dragging has keyboard/structured equivalents, layout metadata stays separate
from canonical content, and AI suggestions never silently apply or publish.
`PS-STORY-COMPOSER-001` is future work until the manager explicitly activates it.

Before Project product, schema, workspace, projection, migration, or route work,
read `docs/initiatives/PS-PROJECTS-001/README.md`. Projects are private-first
connected containers: link exact canonical records rather than copying facts,
keep Project Workspace separate from Project Projection, preserve the Work and
Slate Board boundaries, and leave lifecycle/audience/publication under explicit
member-controlled deterministic actions. `PS-PROJECTS-001` is planned Phase 10
work, not active implementation, and it is not authorization to revive the
retired public fixture or build a task-management suite.

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
- During self-review, identify regressions, missing requirements, accessibility
  issues, visual deviations, unrelated changes, and places where fixture UI is
  being mistaken for production functionality. Correct them before returning a
  `Pass` self-certification.
- Do not relinquish a self-managed branch at PR readiness when Claude is also
  assigned post-acceptance release and closeout. A handoff is required only if
  another writer will continue the branch.
- Keep project memory concise. Durable product decisions belong in the repository documents, not only in chat memory.
- Push task branches to `origin`, merge them through an Azure pull request using squash merge, and delete the source branch after merge.
- GitHub Actions deployment is intentionally disabled. Do not enable, configure, suggest, or rely on it for publishing. Use `azure-pipelines.yml` and `docs/AZURE_DEVOPS_DEPLOYMENT_RUNBOOK.md`.
- Never claim a change is live until the Azure pipeline succeeds and the public production URL is verified.
- Never stage or commit the machine-local `.claude/launch.json`, `.env`, credentials, tokens, publish profiles, or other secrets.
