# 02 — Current State and Workflow Map

## Current implementation baseline

Both `/slate-board` and `/petec/slate-board` render `slate_board.html`. At task
start, the route provided a public interaction prototype with browser-first note
storage and optional opaque per-member browser storage scoping when the database
UI flag is enabled. This is not authenticated canonical board persistence.

The experience-baseline work on the task branch is rebuilding the presentation
around the Photo 1 physical-whiteboard composition while preserving current
page routes and the shared site shell. Any capture, share, invitation,
publication, AI, or collaborator behavior that lacks a proven service remains
explicitly labeled preview or fixture-only.

## Board-state workflow

```text
Board at rest
  ├─ select an item ──> Focus panel ──> close ──> same item and board state
  ├─ Add note ────────> note editor ──> save/cancel ──> board at rest
  ├─ Chalk It Up ─────> listening/typing
  │                       ├─ cancel ────────────────> board at rest
  │                       └─ review transcript ─────> proposal review
  │                                                   ├─ edit/remove/cancel
  │                                                   └─ explicit approve
  ├─ Board/List ──────> equivalent structured list ─> board at rest
  └─ Share/Publish ───> audience preview only until real services exist
```

## State contract

1. **At rest:** Photo 1 appearance dominates. Permanent controls are concise.
2. **Capture:** listening is always visible; text input is an equal alternative;
   the status says nothing has been saved or shared.
3. **Proposal:** AI-shaped output is a proposal, not a write. Each proposal shows
   destination, type, source, and audience before approval.
4. **Focus:** object depth is contextual, not another permanent navigation
   layer. Closing restores visual and keyboard state.
5. **List:** same objects, meaning, visibility, and essential actions as Board;
   spatial position, handwriting, and color are never required to understand it.
6. **Responsive:** the visual metaphor survives on wide screens; mobile becomes
   readable document flow rather than a shrunken desktop board.

## Initial information fixtures

The four fixed first-view sections are Short Term, Projects, Long Term, and
Work. The first-interaction fixture remains “Study for the PMP certification.”
Fixtures prove layout and behavior only; they are not reusable logic, verified
member records, or evidence of backend persistence.
