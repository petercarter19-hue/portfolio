# PS-PROJECTS-001 - Experience and visual direction

## Status

Direction baseline only. No final visual authority is selected and no product
implementation is authorized.

## One experience, three distinct contexts

### Private Project Workspace

The authenticated owner record. This is where the member creates, links,
reviews, corrects, organizes, pauses, completes, archives, deletes, and chooses
what may become a projection.

### Project summary inside Work and My Slate

A compact, server-authorized view of the same Project. It orients the member or
viewer and links into the appropriate workspace or projection. It is not a
second record.

### Project Projection

A separately drafted and published audience-specific story. It may emphasize a
problem, role, build, decisions, outcomes, learning, and sources, but every
factual statement remains traceable to approved canonical records.

## Dominant product object

The opening experience is a **Project Ledger**, not a dashboard of unrelated
cards. The ledger is a working name for the composition, not a new top-level
brand. It should show:

1. Project identity: title, purpose, type, owner, privacy, and lifecycle status.
2. Current movement: latest confirmed update, next member-controlled action,
   and any missing or stale context.
3. Connected record: linked Moments in time order, important decisions,
   milestones/outcomes, roles, skills in practice, sources, and approved media.
4. Progressive depth: inspect original language, exact versions, relationships,
   and history without placing everything in the opening viewport.

The opening viewport has one primary action based on state, such as **Add an
update**, **Review linked Moment**, or **Finish Project reflection**. Secondary
actions remain quiet.

## Core journeys

### Journey 1 - Start a private Project

1. Member chooses Create Project from Work, My Slate, or an eligible contextual
   action.
2. Product states that the Project is private and asks for only title, purpose,
   and starting status.
3. Optional type, dates, role, and goal relationships follow through progressive
   disclosure.
4. Member reviews and explicitly creates the Project.
5. Project Ledger opens with an honest empty state and one next action.

### Journey 2 - Connect real work

1. Member opens a confirmed Moment or finishes Moment review.
2. Use This Moment offers **Connect to Project** only when eligible.
3. Member selects an existing Project or chooses to start a new private draft.
4. Product previews the exact Moment version, target Project, and effect.
5. Explicit confirmation creates a placement reference.
6. Both the Moment and Project show the relationship; neither record is copied
   or rewritten.

### Journey 3 - Understand movement

1. Project Ledger shows a finite recent window and meaningful status.
2. Member filters or expands to decisions, outcomes, sources, people, or the
   full chronology.
3. Missing, deleted, revoked, or unavailable sources appear as honest
   tombstones or restricted states rather than broken cards.
4. The member can correct Project metadata or remove a relationship without
   altering the underlying Moment.

### Journey 4 - Complete and reflect

1. Member chooses Complete Project.
2. Product asks for review of dates, current status, outcomes, and missing
   context; AI may suggest questions but not answers as fact.
3. Member may connect existing Moments or capture missing context privately.
4. Member confirms completion and can later reopen or archive according to the
   lifecycle contract.
5. Reuse options appear separately: Work, Story, Resume, Studio/Moment Lab,
   Replay, export, or future Project Projection.

### Journey 5 - Prepare a Project Projection

This is a later slice. The member chooses purpose and audience, selects approved
material, edits projection wording, previews the exact responsive and audience
result, saves privately, and publishes through a separate explicit action.

## Required states before visual approval

- first private Project;
- active Project with a short history;
- long Project with many Moments, sources, and roles;
- paused, completed, archived, restored, and deletion-review states;
- no linked Moments;
- linked source deleted but confirmed Moment retained;
- linked Moment revoked or placement removed;
- unavailable or restricted media/source;
- duplicate submission and stale edit;
- no AI, AI unavailable, AI proposal, proposal corrected, and proposal rejected;
- loading, empty, partial, success, validation failure, service failure, retry,
  offline/interrupted, and permission-denied;
- private workspace, exact audience preview, projection draft, published,
  revoked, and unavailable projection;
- desktop, mobile portrait, applicable landscape, keyboard focus, screen reader
  order, 200-percent reflow, reduced motion, high contrast, and long content.

## Visual system

- Deep Navy Gold is the shared foundation.
- Newsreader may support editorial Project and case-study headings; Inter
  controls navigation, status, forms, metadata, and product content.
- The Project Ledger is the dominant object. Use generous vertical flow and
  progressive disclosure rather than an above-the-fold grid.
- Marigold may mark confirmed milestones, sources, or meaningful movement; it
  does not become a decorative accent on every card.
- Teal communicates successful completion only.
- Project type is not encoded by color alone.
- Desktop may show a relationship rail or chronology beside detail; mobile and
  200-percent zoom use one readable document flow.

## Historical Projects design status

`docs/design/projects-experience/` and `static/data/projects_board.json` are
preserved evidence from the retired public Projects experience. Their museum/
documentary pacing and artifact sensitivity may inform future projection
exploration, but they do not control the authenticated product because:

- they predate the current owner-system and Deep Navy Gold authority chain;
- they describe Pete-profile fixtures rather than a multi-user owner workflow;
- standalone Project routes are retired in current production; and
- they do not contain the required identity, privacy, lifecycle, accessibility,
  failure, placement, or publication states.

The future V1 package may deliberately reuse, revise, or reject that reference.
It must name one exact current visual authority and record every decision.

## Homepage assessment

The current logged-out homepage contains Project language inside broader
product demonstrations but no dedicated Projects product section or canonical
Projects link. This direction package changes no homepage behavior.

Before a real Project product releases, the implementation package must audit
`/` again. If a Projects section, card, walkthrough, or link exists then, it
must be updated in the same release wave or assigned an exact downstream parity
package. The accepted and live Project product remains upstream authority.
