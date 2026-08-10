@AGENTS.md
@docs/AI_WORKFLOW.md

> **MANDATORY PRE-WORK GATE**
> Follow [`START_HERE.md`](START_HERE.md) before a write, code change,
> migration, deployment, or product decision. Fetch `origin/main`, read
> `CURRENT_BASELINE.yaml`, choose the Routine, Bounded, or Protected path, and
> read only the relevant package and specialist authority. Consult
> `DOCUMENT_CONTROL.md` for a genuine conflict, not as a routine reading gate.
> Before a write, read `CURRENT_LANES.json` and pass
> `python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent write
> --fetch --require-clean`. Use the bounded `START_HERE.md` activation flow
> only after Pete selects the exact outcome. It may reserve a lane from
> `controlled_idle` or add a writer during `active_delivery` while the recorded
> three-lane model has class, path, and exclusive-domain capacity. At most two
> implementation/shared-foundation lanes and one direction/authority lane may
> be active; the direction lane is limited to initiative documentation and
> evidence, and only one active lane may be production-capable. Read-only work
> and paused work consume no writer lane; a full or conflicting model remains a
> stop. Pause only through a separate control-only branch after the working
> branch is committed and pushed; record its exact fetched commit so freeing a
> slot never merges or loses unfinished work.

# Claude / Claude Code instructions

Use the current authorities named in `CURRENT_BASELINE.yaml`. Constitution and
Roadmap explain durable direction and sequencing; older Bibles, roadmaps, state
reports, and handoffs are historical evidence.

Claude Code may own an explicitly assigned branch. It preserves other writers'
work, completes one self-review and focused validation, and records a concise
completion report. A manager handoff is only for a real ownership transfer or
cross-lane decision. Do not use a second model to repeat accepted work unless a
Protected risk, package, or owner explicitly requires independent review.

For protected data, identity, privacy, authorization, migration, deletion,
publication, consequential AI, shared infrastructure, or materially revised
visual direction, follow the named package and specialist standard. For material
visual work, `OWNER_VISUAL_INTEGRITY_STANDARD.md` applies: ChatGPT is the sole
creator of materially revised PeerSlate production-intent visual authority;
Claude implements the locked authority and records applicable comparison,
accessibility, truth, and reflow evidence. `OWNER_STORY_COMPOSITION_STANDARD.md`
applies only to Story work.

Azure DevOps is the release authority. Never push directly to `main`; runtime
changes use an Azure PR. Do not call work live until the relevant pipeline and
affected live behavior are verified. Do not stage machine-local secrets,
credentials, `.env`, or `.claude/launch.json`.
