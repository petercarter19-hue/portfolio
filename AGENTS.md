# PeerSlate Repository Instructions

## Project purpose

PeerSlate is a multi-user, evidence-backed professional story and growth platform. It is not a Pete-only portfolio. Pete's content is fixture/demo data only.

## Source of truth

Before changing résumé or Slate Board code, read these repository documents in this order:

1. `docs/peerslate/PeerSlate_Design_Bible_v0.3.md`
2. `docs/peerslate/PS-FEAT-001_Living_Resume_Voice_Blueprint.md`
3. `docs/peerslate/PeerSlate_Product_Backlog.md`
4. `docs/peerslate/PS-EXP-002_Slate_Focus_Stage_Experiment.md`

If any source document is missing, stop and report the missing path. Do not reconstruct requirements from memory.

## Approved design foundation

- Foundation C is approved.
- Newsreader is for cinematic/editorial headings.
- Inter is for navigation, controls, forms, metadata, and product content.
- Light-first, cinematic, premium glass UI.
- Product Indigo `#4F5BD5`
- Connection Azure `#4EA3FF`
- AI Cyan `#2EC8D3`
- Evidence Amber `#D7A33E`
- Midnight Ink `#0A1B36`
- Cloud White `#F6F8FC`
- Pink, rose, magenta, and coral are not semantic UI accents.
- Use generous vertical spacing and progressive disclosure. Do not force the experience above the fold.
- One dominant product object per opening viewport.
- Never use the retired résumé example. Never use the MICAP example in redesigned résumé fixtures or visible copy.

## Multi-user and trust rules

- Components must work for students, early-career users, career changers, freelancers, mid-career users, and senior users.
- Never hardcode Pete's employers, dates, role count, metrics, education, or skills into reusable components.
- Every profile-owned record must preserve tenant ownership.
- Default new Board content and voice-created drafts to private.
- AI output is a proposal, not an automatic edit.
- Voice flow is transcript → structured proposal → source/visibility review → explicit approval → save. Publishing is a separate explicit action.
- Never imply production privacy, matching, verification, or AI behavior unless the backend enforces it.

## Living Résumé direction — PS-FEAT-001

- The Living Résumé Ledger appears first.
- Its chronological timeline is integrated into the résumé and acts as its navigation and structural spine.
- Selecting a timeline chapter updates detail inside the same dominant résumé frame.
- The Career Constellation materializes below the Ledger during vertical scroll.
- Skills stay compact and reveal only two or three strongest approved proof points.
- Ledger and Constellation render from the same structured data.
- Keep a traditional ATS-friendly PDF/download path.
- Build with generic data/view models and multiple fixture profiles.

## Slate Board direction

- The whiteboard remains the dominant product experience.
- Preserve its playful, hand-placed quality; do not turn it into a conventional dashboard or card grid.
- Four primary scrollable sections for the first implementation:
  - Short Term
  - Projects
  - Long Term
  - Work
- Sticky notes are the primary board objects.
- Add/Edit supports:
  - To Do, Short Term, Long Term, Project, Work, or Custom
  - sticky-note color
  - cursive or standard handwriting
  - dates
  - privacy/audience
- Keep visible controls concise:
  - Add to Board
  - AI Help
  - Connections
  - quiet More/Board Settings
- Item controls appear contextually, not permanently.
- First interaction fixture: “Study for the PMP certification.”
- Add-to-Board states:
  1. Capture
  2. Details and privacy
  3. Note added
  4. AI guidance
  5. People matching
- Similar-user matching is opt-in and visibility-aware. Never auto-connect users.
- AI may propose milestones, questions, reminders, websites, and videos, but does not save automatically.
- Supporting experiences continue vertically below the opening board. Do not pack everything into one screen.
- PS-EXP-002 Focus Stage remains separate, optional, feature-flagged, and off by default. It must never replace the Board.

## Navigation

Do not add another permanent navigation layer inside Slate Board. Global site navigation, public/member Slate navigation, and contextual Board controls must remain distinct. Do not finalize or replace production navigation without an approved route map.

## Safe implementation workflow

- Never work directly on production or the default branch.
- Preserve current pages and behavior.
- Use alternate routes and/or disabled feature flags for redesigned pages.
- Do not deploy.
- Do not merge.
- Do not perform database migrations unless the user separately approves a reviewed migration plan.
- Do not add production dependencies without reporting why they are needed.
- Prefer small, reviewable commits.
- Before edits, record the current branch, commit, dirty files, test commands, routes, templates, CSS/JS entry points, data sources, and existing feature flags.
- If the working tree is dirty or the correct Foundation C base is ambiguous, stop and report rather than guessing.

## Quality requirements

- WCAG 2.2 AA target.
- Keyboard access, visible focus, 200% zoom, high contrast, and reduced motion.
- Slate Board requires an accessible structured/list alternative.
- Mobile uses readable document flow; never shrink a desktop visualization until it is unreadable.
- Prefer transforms and opacity for motion.
- Run the existing test/lint/format commands discovered in the repository.
- Add focused tests for new routes, rendering states, and interactions.
- Capture desktop and mobile screenshots for review.
- Report changed files, commits, commands run, failures, assumptions, and remaining work.

## Communication

Explain architecture and tradeoffs in plain English. Separate:
- what is implemented,
- what is fixture-only,
- what requires backend/schema work,
- what is intentionally deferred.

## Imported Claude Cowork project instructions
