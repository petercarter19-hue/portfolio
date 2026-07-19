# PeerSlate Document Control

_Adopted 2026-07-18. Maintained by the currently designated governance manager lane._

## Authority order

When repository documents disagree, use this order and report the conflict:

1. The owner’s current explicit decision.
2. `docs/governance/CURRENT_BASELINE.yaml` for current versions, packages, holds, lane ownership, and verified repository/production evidence.
3. The Bible and Roadmap paths named in that baseline.
4. `OWNER_VISUAL_INTEGRITY_STANDARD.md` for the operational interpretation of
   owner-approved visual authority, demonstration parity, and visual release gates.
5. The Repository Source-of-Truth and Multi-Agent Sync Standard named there, plus `docs/AI_WORKFLOW.md`, for Git, handoff, and release procedure.
6. The active initiative package for its bounded scope, files, acceptance criteria, and exclusions.
7. `AGENTS.md`, `CLAUDE.md`, and `docs/PEERSLATE_SITE_RULES.md` for non-conflicting shared implementation rules.
8. Older Bibles, roadmaps, design documents, and initiative records as historical context only.

No agent may silently choose an older instruction because it is more detailed. Stop and escalate a conflict that changes product meaning, privacy, authorization, schema, or package ownership.

## Current controlled set

| Record | Current version/status | Purpose |
|---|---|---|
| Company and Product Bible | v2.5 | Product language, boundaries, principles, visual integrity, Story composition authority, and intended model |
| Product Strategy and Architecture Roadmap | v2.4 | Evidence state, package order, gates, architecture direction, and Story Composer allocation |
| Repository Sync Standard | v1.1 | Multi-agent repository coordination |
| Shared AI and Git Workflow | Current; self-managed lanes adopted 2026-07-19 | Branch ownership, writer self-review/certification, final acceptance, Azure release, handoff, and closeout |
| Current baseline/state/initiatives | Updated by PS-BASELINE-001 | Operational truth and active ownership |
| Deep Navy Gold visual baseline | Approved | Shared owner visual foundation |
| Owner Visual Integrity Standard | Approved | Demonstration parity, visual evidence, and owner/manager acceptance gates |
| Owner Story Composition Standard | Approved | Member-controlled Story layout, accessible manipulation, responsive projection, persistence, and publication gates |
| Manager Session Handoff | Current snapshot | Active-lane state, stop conditions, and next-manager kickoff |

## Known supersessions

- Bible v2.5 supersedes v2.4, v2.3, and v1.1 through v1.4 for current product decisions.
- Roadmap v2.4 supersedes Roadmap v2.3 for current sequencing and architecture decisions.
- Deep Navy Gold supersedes Iris/Direction C as the approved shared theme.
- The controlled data sequence is private Capture source → reviewed canonical Moment → governed placement by reference. Journal is not the current canonical source model.
- Journal UI remains on hold even when older backlogs describe it as active.
- The current public wave is résumé refinement only. Interview Studio receives a later, separate public/private gate.

## Change rule

Update `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, and `ACTIVE_INITIATIVES.md`
together when a package, owner, hold, authority version, or verified production
boundary changes. Product packages may update only their own initiative records
unless the manager reserves a governance-file edit in writing. Under the
self-managed delivery model, the assigned writer owns complete-diff review,
evidence, PR readiness, and post-acceptance release/closeout, but this does not
silently grant shared-governance-file ownership. The Bible changes only for
constitutional product direction; routine implementation/release status belongs
in initiative architecture, completion, Roadmap, and current-state records as
applicable.
