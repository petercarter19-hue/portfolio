# PeerSlate Repository Instructions

> **MANDATORY PRE-WORK GATE**
> Before a write, code change, migration, deployment, or product decision, open
> and follow [START_HERE.md](START_HERE.md). Fetch authoritative `origin/main`,
> read [CURRENT_BASELINE.yaml](docs/governance/CURRENT_BASELINE.yaml), choose a
> Routine, Bounded, or Protected path, then read only the package and specialist
> authority the path requires. Stop for a real ownership, privacy,
> authorization, migration, or material-visual conflict; do not stop for an
> unrelated historic gate. Use the proportional
> [completion record](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).
> Before a write, also read
> [CURRENT_LANES.json](docs/governance/CURRENT_LANES.json) and pass
> `python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent write
> --fetch --require-clean`. A failed preflight is a stop, not permission to
> create another branch or worktree.

## Authority

Follow [DOCUMENT_CONTROL.md](docs/governance/DOCUMENT_CONTROL.md). The current
Constitution and Roadmap named by `CURRENT_BASELINE.yaml` control durable rules
and sequence. Historical Bibles, roadmaps, status reports, and handoffs are
evidence, not default reading or additional gates.

## Always-on product and trust invariants

- Build a reusable multi-user product; Pete is fixture content, never shared
  product logic.
- Content is private by default. Derive identity server-side and authorize
  before returning or mutating protected data.
- Keep canonical truth, source evidence, AI proposals, and projections
  separate. AI proposes; people decide; it never silently saves, publishes,
  sends, deletes, or makes truth canonical.
- Preserve one authoritative source per fact, truthful demo/fixture labels,
  useful AI-unavailable behavior, and WCAG 2.2 AA expectations.
- Preserve unrelated work, secrets, production data, and user-authored content.

## Ownership and delivery

- One writer owns a mutable surface. Use a clean worktree for a dirty or
  separately owned checkout; do not reset, overwrite, or adopt another
  writer's branch without an explicit handoff.
- Work on a short-lived branch from current `origin/main`; never push directly
  to `main`. Use an Azure DevOps PR for runtime changes. A merge is not a
  deployment.
- The writer implements, validates, and self-reviews once. Manager handoff and
  independent review occur only for an actual transfer, cross-lane conflict,
  Protected risk trigger, package requirement, or owner request.
- Candidate, Launch, Operate, Retire, full-site audits, and visual acceptance
  are event/risk-driven. They must not block unrelated Routine or Bounded work.

## Triggered authorities

| Work area | Read when it applies |
|---|---|
| Shared behavior | [PEERSLATE_SITE_RULES.md](docs/PEERSLATE_SITE_RULES.md) and the package. |
| Material user-facing direction | [OWNER_VISUAL_INTEGRITY_STANDARD.md](docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md) and the locked authority. ChatGPT is the sole creator of materially revised production visual direction; writers implement it. |
| Story | [OWNER_STORY_COMPOSITION_STANDARD.md](docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md). |
| Capture/Journal | [PS-JOURNAL-001](docs/initiatives/PS-JOURNAL-001/README.md). |
| Projects | [PS-PROJECTS-001](docs/initiatives/PS-PROJECTS-001/README.md). |
| Protected operations | [PS-OPS-001](docs/initiatives/PS-OPS-001/README.md). |

Use the lean delivery policy in [AI_WORKFLOW.md](docs/AI_WORKFLOW.md). For a
material closeout, report base/final SHA, changed paths, verification, release
state, honest limitations, and the next action. Do not call a fixture live, a
merge deployed, or an AI proposal accepted without supporting evidence.
