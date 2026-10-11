# PeerSlate Repository Instructions

> **MANDATORY PRE-WORK GATE**
> Before a write, migration, deployment, or product decision, follow [START_HERE.md](START_HERE.md):
> fetch Azure `origin/main`, read [CURRENT_BASELINE.yaml](docs/governance/CURRENT_BASELINE.yaml),
> [CURRENT_LANES.json](docs/governance/CURRENT_LANES.json), and the package's
> claim under `docs/governance/lane_claims/`. Choose Routine, Bounded, or
> Protected. Before implementation edits, pass
> `python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent write --task-ref <YOUR-ACTUAL-REF> --fetch --require-clean`.
> A failed preflight stops the write. Use the exact control-only transition in
> START_HERE for activation, authority or scope changes, pause, recovery, and
> close; run `--intent read` first and do not use an implementation branch
> to change its claim. New work requires Pete's selected outcome and the
> one-claim activation flow.

The 2026-08-27 standing bounded Workshop decision expired when its parent
claim closed.

## Authority and trust

[DOCUMENT_CONTROL.md](docs/governance/DOCUMENT_CONTROL.md) gives the current
authority order. The Constitution and Roadmap named by CURRENT_BASELINE govern
durable product rules and sequence. Historical records are evidence, not new
gates. Read only the package and specialist authority the chosen path triggers.

- Build a reusable multi-user product; Pete is fixture content, never shared
  logic. Content is private by default. Derive identity server-side and
  authorize before protected retrieval or mutation.
- Keep canonical truth, source evidence, AI proposals, and projections
  distinct. AI proposes; people decide. Never silently save, publish, send,
  delete, or change canonical truth.
- Preserve one authoritative source per fact, truthful fixture labels, useful
  AI-unavailable behavior, WCAG 2.2 AA
  expectations, unrelated work, secrets, production data, and authored content.

## Ownership and delivery

- Use your actual opaque caller identity, never another task's reference.
  Codex uses native `CODEX_THREAD_ID` as `session:<UUID>`; external runtimes
  follow the registered caller-context procedure. Identity attestation alone
  grants no claim. [WORKTREE_LIFECYCLE.md](docs/governance/WORKTREE_LIFECYCLE.md)
  governs custody, the one registered durable worktree, control leases,
  recovery, and retirement. Do not bypass a refusal with a new checkout,
  reset, clean, force removal, or ref deletion.
- One writer owns each mutable surface. There is no numeric writer cap;
  branch, path, or domain collision stops the affected work. Disjoint claims
  may proceed.
  Reviewers are read-only on implementation branches. Work on a short-lived
  branch from current Azure main, never push directly to main. Use the exact
  review and merge flow in START_HERE and [AI_WORKFLOW.md](docs/AI_WORKFLOW.md):
  freeze a candidate, obtain the claim's required self or independent review,
  and keep any post-review tail to the fixed receipt and evidence paths.
- The assigned writer may implement through accepted merge unless its claim is
  `write_only`. A merge is repository truth, not deployment. Production,
  schema, configuration, enablement, rollback, and destructive actions require
  their separate exact authority. A claim never grants them.
- Any assigned, access-verified capable platform has equal standing: it may
  architect, build, review, merge, and, with Pete's release authorization,
  release within its assignment. No platform needs another's supervision.
- Follow [AI model and role routing](docs/AI_MODEL_AND_ROLE_ROUTING.md) for
  actual role capabilities. Overall audit manager, package manager, visual
  creator, architect, writer, reviewer, and release owner are distinct;
  no role silently inherits another. Coordination grants no exclusive
  technical privilege. Its [capability-use guidance](docs/AI_MODEL_AND_ROLE_ROUTING.md#capability-use)
  covers the local session-health advisory: treat it as approximate,
  non-gating context evidence, not an automatic handoff or authority change.
- Before a PR that changes browser-facing code or browser tests, run the
  affected browser suite normally and once under load (a parallel run or a
  throttled CPU). Rely on Playwright actionability; add explicit waits only
  for real application state, never fixed sleeps. Fix flaky tests or slow
  product paths instead of re-queueing. A changed browser-test module must
  also skip cleanly when Playwright is unavailable, as in the application-test
  job. Documentation-only and control-only changes keep their existing
  shortcuts.

## Triggered authority

| Trigger | Read |
|---|---|
| Shared behavior | [Site rules](docs/PEERSLATE_SITE_RULES.md) and the package. |
| Material visual direction | [Visual integrity standard](docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md) and locked authority. Pete chooses who creates new or materially revised designs and approves the images; writers implement the approved authority. |
| Story | [Story composition standard](docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md). |
| Capture, Moment, or Journal | [PS-JOURNAL-001](docs/initiatives/PS-JOURNAL-001/README.md). |
| Projects | [PS-PROJECTS-001](docs/initiatives/PS-PROJECTS-001/README.md). |
| Protected operations | [PS-OPS-001](docs/initiatives/PS-OPS-001/README.md). |

For writable package work, follow the agent-executed acceptance check in
START_HERE and use the proportional [completion record](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).
Report base/final SHA, changed paths, verification, review, merge and live
states, limits, and next action. Never call a fixture live, a merge deployed,
or an AI proposal accepted without evidence.
