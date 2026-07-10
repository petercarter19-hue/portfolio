# PeerSlate Implementation Handoff

**Current approved foundation:** Foundation C  
**Current implementation targets:** PS-FEAT-001 Living Résumé and Slate Board v2  
**Production status:** Planning/prototyping only; preserve existing pages

## Why these two pages are first

The résumé and Slate Board establish two core PeerSlate product patterns:

- a museum-quality, evidence-connected professional record;
- a living visual workspace that turns goals and ideas into progress, AI guidance, and optional human connection.

They should be implemented on the real site and refined there, because final vertical rhythm, section pacing, offsets, and responsive behavior cannot be judged from a single static mockup.

## Approved Résumé experience

### Opening experience

The Living Résumé Ledger is the dominant object. The timeline is part of the résumé itself, not a separate row of cards. Selecting a chapter changes the detailed content inside the same frame.

### Vertical continuation

The page continues below the Ledger with generous space. The Career Constellation materializes beneath it as a connected summary of defining education, experience, credential, project, and future chapters.

### Skills and evidence

Skills remain compact. Selecting/revealing a skill shows two or three strongest approved proof points and their originating role, project, education item, credential, or evidence source.

### Data

Both résumé views use the same approved structured records. Pete is fixture User 001, not the component model.

## Approved Slate Board experience

### Opening experience

The actual whiteboard is front and center. It should feel playful and hand-placed, but more premium than a literal classroom chalkboard.

The first version uses four independently scrollable areas:

- Short Term
- Projects
- Long Term
- Work

Sticky notes may vary in position and slight rotation. They should not become a rigid uniform card grid.

### Concise controls

Permanent top-level Board controls remain limited:

- Add to Board
- AI Help
- Connections
- More / Board Settings

Dates, category, handwriting, color, privacy, completion, move, archive, duplicate, and delete appear contextually inside Add/Edit or the selected note menu.

### Add-to-Board reference flow

Use “Study for the PMP certification” as the first generic fixture:

1. Capture by typing or voice.
2. Choose type, color, handwriting, dates, and audience.
3. Add the note to the Board.
4. Show AI-proposed questions, milestones, reminders, and resources.
5. Show an opt-in people-matching state based only on compatible visible goals.

New content defaults to private. AI proposals require approval. People are never automatically connected.

### Vertical continuation

Below the Board, use generous vertical spacing for relevant experiences such as:

- People on the Same Path
- AI guidance and resources
- date-aware progress/nudges
- selected-item detail
- a future optional Focus Stage

These are not required to fit above the fold.

## Tonight's safe scope

Codex may:

- audit the repository;
- confirm Foundation C implementation and correct base commit;
- create isolated branches/worktrees;
- preserve current pages;
- add alternate routes or disabled flags;
- build shared page shells;
- build initial Ledger and Board components with clearly labeled generic fixtures;
- add focused tests;
- capture screenshots;
- document backend dependencies and deferred work.

Codex may not:

- merge or deploy;
- replace production routes;
- alter production navigation;
- perform database migrations;
- implement fake production privacy or cross-user matching;
- use the retired/MICAP résumé example;
- turn Focus Stage into the default Board;
- guess when repository state or requirements conflict.

## Open decisions to review tomorrow

- Exact approved résumé screenshots to use as visual references.
- Final temporary route names after repository inspection.
- Whether both redesigned pages share a single integration branch after separate review.
- Which existing Board data/actions can be reused immediately.
- Which matching, AI resource, visibility, and date behaviors require backend work.
- Final public/owner/recruiter route map before production navigation changes.
