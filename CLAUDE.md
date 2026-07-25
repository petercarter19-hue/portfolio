@AGENTS.md
@docs/AI_WORKFLOW.md

> **MANDATORY PRE-WORK GATE**
> Before any analysis that may lead to a write, code change, migration, deployment, or product decision, open and follow [`START_HERE.md`](START_HERE.md). Synchronize from authoritative `origin/main`, then read `docs/governance/CURRENT_BASELINE.yaml`, `docs/governance/CURRENT_STATE.md`, `docs/governance/ACTIVE_INITIATIVES.md`, the current Bible/Roadmap named there, and your assigned initiative package. Stop rather than guess when any pointer or ownership record is unclear. Every material closeout must use [`docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).
>
> **Authoritative versions are always the ones named in `docs/governance/CURRENT_BASELINE.yaml`.** Do not hardcode a Bible or Roadmap version in this file.

# Claude / Claude Code instructions

The live authority is `docs/governance/CURRENT_BASELINE.yaml` and the Bible and
Roadmap paths it names. Consult `docs/governance/DOCUMENT_CONTROL.md` when an
older specification conflicts. Do not treat superseded product language as
current merely because it remains in repository history.

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

Use `docs/AI_MODEL_AND_ROLE_ROUTING.md` for current Claude/Codex role and model
routing. Packages name stable roles, not model versions. The routing document is
the central version authority and its availability check must be followed before
a major package or scheduled audit. Do not spend a second model re-authoring an
accepted package merely to cross-pollinate.

Owner decision, 2026-07-24: Claude self-manages its assigned branch. That means
implementing, reviewing the complete diff, finding and fixing its own issues,
running focused/full/responsive/accessibility/visual checks, producing the
completion report and exact evidence, synchronizing with `origin/main`, and
preparing the Azure PR. After Pete/designated-session-manager product and visual acceptance,
Claude may complete the PR, pipeline, production verification, and closeout.
The designated manager may rely on Claude's coherent `Pass` self-certification rather than
repeat the full technical audit. Report `Conditional` or `Fail` whenever an
issue, conflict, or evidence gap remains.

Use the lean delivery route in `docs/AI_WORKFLOW.md`: architecture only when
needed; the same writer implements, tests, and self-reviews; a fresh independent
reviewer is mandatory only for the defined risk triggers or an explicit package
control; and the same writer corrects accepted findings. Do not add another
architecture pass, final audit, or documentation-only deployment by habit. For
material visual work, Pete reviews the corrected real build last; this does not
replace the visual evidence, accessibility checks, or release verification.

The guardrail suites `tests/test_site_rules.py` and
`tests/test_governance_pointers.py` must stay green.

For every user-facing task, read
`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`. Name the exact approved
visual authority before implementation. A selected mockup or demonstration is a
binding minimum: the real experience must match or exceed it, and material work
requires comparison screenshots plus Pete and the designated session manager's
visual acceptance.
Owner decision, 2026-07-24: ChatGPT is the sole creator of new or materially
revised PeerSlate production-intent visual authority, including concepts,
mockups, responsive and state sets, style exploration, and image edits.
Existing Pete-locked authorities remain valid until materially revised. Claude
may architect non-visual product and technical contracts, implement an exact
locked visual, capture real-browser evidence, report parity or accessibility
findings, and make documented non-material adaptations for semantic structure,
focus, contrast, touch targets, reduced motion, truthful state wiring, or text
reflow. Claude Chat, Co-Work, Code, and Design must not originate or substitute
the visual direction. A change to composition, hierarchy, dominant
object/action, typography family, color language, or responsive interaction
model is material: stop and return it to the ChatGPT visual-creation lane; work
resumes only after Pete locks the revised exact authority.
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

Before any Capture, Moment, Journal, projection, audience, or route work, read
`docs/initiatives/PS-JOURNAL-001/` (README + docs 01–06) and the "Universal
Capture and the one Journal direction" section of `AGENTS.md`. Owner-clarified
emphasis (Pete, 2026-07-21): Capture is an in-context pop-out that preserves and
returns to the origin page; Save Moment always creates one private canonical
Moment with derived Journal membership and no Add to Journal step; and in the same
moment the composer offers first-class `Use This Moment` share destinations (Feed,
My Story, Work, Résumé, and other authorized targets) plus an audience choice —
each an explicit, previewed, reference-not-copy action that is never bundled into
Save Moment or applied automatically. New Moments default to Only Me. Private
capture + Journal ship first (J1); the destination chooser and audience
projections follow (J2+); design the saved state with those options from the
first visual round. `PS-JOURNAL-001` is architecture-complete with the runtime
writer unassigned; do not begin implementation without the package entry gate.

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
- At the start of every session, run the identification block in `START_HERE.md` section 1 before editing. It reports the checkout path, both remotes, the branch, the latest commit, whether the base is stale, and whether `.claude/launch.json` is protected on this clone.
- Azure DevOps is the only source of truth and the only deployment path. GitHub is a backup mirror and an inbox for cloud-agent branches, never a merge target. There is no active remote named `azure`.
- **Verify what `origin` means in this checkout; do not assume.** In a local clone `origin` is Azure DevOps and `github` is the mirror. In a hosted agent session the only remote is GitHub, named `origin`, and Azure is unreachable — a valid configuration, but one whose base can sit behind Azure `main`. Work tested on a stale base must be reconciled onto current Azure `origin/main` and retested there before its evidence is reported. See "Repository map" in `docs/AI_WORKFLOW.md`.
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
