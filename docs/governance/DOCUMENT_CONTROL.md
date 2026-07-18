# PeerSlate Document Control

_Adopted 2026-07-18. Maintained by the ChatGPT Work manager lane._

## Authority order

When repository documents disagree, use this order and report the conflict:

1. The owner’s current explicit decision.
2. `docs/governance/CURRENT_BASELINE.yaml` for current versions, packages, holds, lane ownership, and verified repository/production evidence.
3. The Bible and Roadmap paths named in that baseline.
4. The Repository Source-of-Truth and Multi-Agent Sync Standard named there, plus `docs/AI_WORKFLOW.md`, for Git, handoff, and release procedure.
5. The active initiative package for its bounded scope, files, acceptance criteria, and exclusions.
6. `AGENTS.md`, `CLAUDE.md`, and `docs/PEERSLATE_SITE_RULES.md` for non-conflicting shared implementation rules.
7. Older Bibles, roadmaps, design documents, and initiative records as historical context only.

No agent may silently choose an older instruction because it is more detailed. Stop and escalate a conflict that changes product meaning, privacy, authorization, schema, or package ownership.

## Current controlled set

| Record | Current version/status | Purpose |
|---|---|---|
| Company and Product Bible | v2.3 | Product language, boundaries, principles, and intended model |
| Product Strategy and Architecture Roadmap | v2.3 | Evidence state, package order, gates, and architecture direction |
| Repository Sync Standard | v1.1 | Multi-agent repository coordination |
| Current baseline/state/initiatives | Updated by PS-BASELINE-001 | Operational truth and active ownership |
| Deep Navy Gold visual baseline | Approved | Shared owner visual foundation |

## Known supersessions

- Bible v2.3 supersedes v1.1 through v1.4 for current product decisions.
- Deep Navy Gold supersedes Iris/Direction C as the approved shared theme.
- The controlled data sequence is private Capture source → reviewed canonical Moment → governed placement by reference. Journal is not the current canonical source model.
- Journal UI remains on hold even when older backlogs describe it as active.
- The current public wave is résumé refinement only. Interview Studio receives a later, separate public/private gate.

## Change rule

Update `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, and `ACTIVE_INITIATIVES.md` together when a package, owner, hold, authority version, or verified production boundary changes. Product packages may update only their own initiative records unless the manager reserves a governance-file edit in writing.
