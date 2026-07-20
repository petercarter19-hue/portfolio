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
| Company and Product Bible | v2.7 | Product language, boundaries, principles, visual integrity, Story composition authority, Projects system covenant, connected-system spine, return-value engine, and intended model |
| Product Strategy and Architecture Roadmap | v2.6 | Evidence state, package order, gates, architecture direction, Story Composer allocation, Projects system sequencing, and connected-system sequencing amendment |
| Repository Sync Standard | v1.1 | Multi-agent repository coordination |
| Shared AI and Git Workflow | Current; self-managed lanes adopted 2026-07-19 | Branch ownership, writer self-review/certification, final acceptance, Azure release, handoff, and closeout |
| Current baseline/state/initiatives | Updated by PS-BASELINE-001 | Operational truth and active ownership |
| Deep Navy Gold visual baseline | Approved | Shared owner visual foundation |
| Owner Visual Integrity Standard | Approved | Demonstration parity, product-to-homepage projection convergence, visual evidence, and owner/manager acceptance gates |
| Owner Story Composition Standard | Approved | Member-controlled Story layout, accessible manipulation, responsive projection, persistence, and publication gates |
| Manager Session Handoff | Current snapshot | Active-lane state, stop conditions, and next-manager kickoff |

## Known supersessions

- Bible v2.7 supersedes v2.6, v2.5, v2.4, v2.3, and v1.1 through v1.4 for
  current product decisions.
- Roadmap v2.6 supersedes v2.5, v2.4, and v2.3 for current sequencing and
  architecture decisions.
- The connected-system spine, connected-room contract, and return-value engine
  are constitutional. Connective patterns are canonical experience patterns
  inside existing rooms, never top-level destinations.
- Preservation of a connective or retention idea is not implementation
  authorization. Every such idea carries an explicit Locked / Open / Later /
  Tabled / Rejected-current status.
- Deep Navy Gold supersedes Iris/Direction C as the approved shared theme.
- The controlled data sequence is private Capture source → reviewed canonical Moment → governed placement by reference. Journal is not the current canonical source model.
- Journal UI remains on hold even when older backlogs describe it as active.
- The current public wave is résumé refinement only. Interview Studio receives a later, separate public/private gate.

## Open items — the supersession list above is known-incomplete

### OPEN-DOC-001 — `PeerSlate_Company_and_Product_Bible_v1.5.1.pages` authority is unresolved

**Status: OPEN. Pending an owner decision. Raised 2026-07-20 at the Bible v2.7
activation and deliberately not resolved by it.**

A file named `PeerSlate_Company_and_Product_Bible_v1.5.1.pages` sits **untracked**
in the repository root. It is dated 2026-07-17 and presents itself as an
implementation baseline that supersedes v1.3 and v1.4. It appears in **no**
supersession list in this document, which stops at v1.4, and in no
`superseded_documents` entry in `CURRENT_BASELINE.yaml`. It carries at least two
positions that collide with current authority: "the Journal is the member
profile," while Journal UI is on hold under `PS-JOURNAL-001`, and Iris Foundry
colour direction, which Deep Navy Gold retired under `PS-BRAND-NAV-002`.

**Consequence, stated plainly.** The line above says Bible v2.7 supersedes "v1.1
through v1.4." If v1.5.1 is in fact a real intermediate authority, then that
list is **incomplete**, and v2.7 supersedes an ambiguous rather than a known set.
This activation was approved by Pete on 2026-07-20 **without** this question
being answered. It is recorded here rather than papered over: the supersession
list in this document is **known-incomplete pending that answer**, and no agent
may read it as a settled and exhaustive set.

**Interim handling until Pete rules.** v1.5.1 is not a controlling document. It
is not in the controlled set, it is not tracked in Git, and nothing in it may be
implemented or cited as authority. Where it conflicts with Bible v2.7, Roadmap
v2.6, or `CURRENT_BASELINE.yaml`, the current baseline wins and the conflict must
be reported. This is an interim safeguard, not the decision.

**Owner decision required.** Pete must state one of: (a) v1.5.1 was never an
authority and is a personal draft, so no supersession line changes; (b) v1.5.1
was a real intermediate baseline, so it must be tracked, recorded, and added to
the supersession list as superseded by v2.7; or (c) some part of v1.5.1 is still
live and must be reconciled into the current baseline. Until then this item stays
OPEN.

### OPEN-DOC-002 — standalone Experience System and Architecture and Data Standard not established

Activation step 8 of
`docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/10_ACTIVATION_CHECKLIST.md` asked
whether to establish standalone Experience System and Architecture and Data
Standard documents in the controlled set. **No owner decision was given, so the
"no" branch was taken.** Package files `03_ARCHITECTURE_AND_DATA_STANDARD_CONNECTED_SYSTEM.md`
and `04_EXPERIENCE_SYSTEM_CONNECTIVE_PATTERNS.md` remain PROPOSED and
package-local; the rows drafted in
`07_SOURCE_PRESERVATION_AND_SUPERSESSION.md` §2.3 were **not** added to the
controlled set above; and the Bible's operating-system table keeps naming both as
intended-but-not-yet-established artifacts. Establishing them is a separate
governed change.

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
