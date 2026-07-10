# Codex task: PeerSlate dual-page safe implementation kickoff

Work from the PeerSlate repository root.

## First: load instructions

1. Read `AGENTS.md`.
2. Read:
   - `docs/peerslate/PeerSlate_Design_Bible_v0.3.md`
   - `docs/peerslate/PS-FEAT-001_Living_Resume_Voice_Blueprint.md`
   - `docs/peerslate/PeerSlate_Product_Backlog.md`
   - `docs/peerslate/PS-EXP-002_Slate_Focus_Stage_Experiment.md`
   - `docs/peerslate/IMPLEMENTATION_HANDOFF.md`
3. Inspect the approved screenshots under `docs/design-references/`.

Do not edit until this preflight is complete.

## Objective

Begin safe implementation of two redesigned pages without altering the current production pages:

1. PS-FEAT-001 Living Résumé Ledger with integrated timeline, followed vertically by Career Constellation.
2. Slate Board v2 with the whiteboard front and center, four scrollable note sections, and the approved five-state Add-to-Board flow.

The work should be reviewable tomorrow. Do not merge or deploy.

## Phase 0 — repository preflight

Record in `docs/implementation-reports/peer-slate-dual-page-preflight.md`:

- repository root;
- current branch and commit;
- `git status`;
- default/stable branch;
- branches/commits containing Foundation C;
- whether Foundation C is merged into the intended base;
- framework and app entry points;
- route structure;
- base templates and navigation partials;
- design-system token/component locations;
- current résumé route, templates, CSS, JavaScript, data sources, PDF path, tests;
- current Slate Board route, templates, CSS, JavaScript, models/APIs, tests;
- feature-flag mechanism, if any;
- discovered build, test, lint, and formatting commands;
- missing source documents or visual references;
- existing failures before changes.

Stop without editing when:
- the working tree contains uncommitted user changes;
- the correct Foundation C base cannot be identified;
- any required source document is missing;
- repository architecture makes the requested isolation unsafe.

If stopped, give a concise report with the exact action needed from Pete.

## Phase 1 — isolate the work

From the same clean Foundation C base, create separate branches and worktrees when supported:

- `codex/ps-feat-001-living-resume`
- `codex/slate-board-v2`

Use clear sibling worktree directories. Do not alter or delete an existing worktree.

If worktrees are not appropriate for this repository, create the two branches but work sequentially. Explain the choice in the report.

Never commit to the default branch.

## Phase 2 — Living Résumé first pass

In the résumé worktree:

1. Preserve the existing résumé page and PDF path.
2. Add a temporary v2 route or disabled feature flag consistent with the existing routing pattern.
3. Reuse Foundation C tokens and existing shared components.
4. Create generic structured fixtures/view models for at least:
   - student;
   - early career;
   - mid career;
   - career changer;
   - freelancer;
   - senior career.
5. Build the first reviewable page slice:
   - restrained page introduction and existing practical actions;
   - dominant Living Résumé Ledger;
   - integrated chronological timeline rail/spine;
   - selected chapter updating content inside the same Ledger;
   - compact skills with accessible two/three-proof reveal;
   - generous vertical transition;
   - initial Career Constellation section below, driven from the same data.
6. Do not implement voice recording or AI persistence tonight. A static, accessible structured-change preview may be scaffolded only when clearly labeled fixture/prototype.
7. Do not use Pete-specific values in reusable component logic.
8. Never use the retired/MICAP example.
9. Add focused route/render/interaction tests and reduced-motion behavior.
10. Capture desktop and mobile screenshots.

Commit in small phases using `PS-FEAT-001` in commit messages.

## Phase 3 — Slate Board first pass

In the Slate Board worktree:

1. Preserve the current Board page and behavior.
2. Add a temporary v2 route or disabled feature flag consistent with the existing app.
3. Keep the whiteboard as the dominant opening object.
4. Build four independently scrollable sections:
   - Short Term
   - Projects
   - Long Term
   - Work
5. Keep the Board playful: hand-placed notes, supported sticky colors, optional cursive/standard handwriting, slight controlled offsets/rotations. Do not create a rigid dashboard grid.
6. Keep permanent visible controls concise:
   - Add to Board
   - AI Help
   - Connections
   - quiet More/Board Settings
7. Implement a reviewable, fixture-backed five-state Add-to-Board flow using “Study for the PMP certification”:
   - capture;
   - details/privacy;
   - note added;
   - AI guidance;
   - people matching.
8. Add type choices:
   - To Do
   - Short Term
   - Long Term
   - Project
   - Work
   - Custom
9. Include color, handwriting, optional dates, and visibility. Default fixture state to private.
10. AI help and matching are presentation/proposal states only. Do not query other users, save AI suggestions, auto-connect, or imply backend enforcement.
11. Add generous vertical continuation below the board, but do not overcrowd the opening viewport.
12. Keep PS-EXP-002 Focus Stage off by default and out of the main first-pass UI.
13. Provide an accessible structured/list representation of Board content.
14. Add focused route/render/interaction tests and reduced-motion behavior.
15. Capture desktop and mobile screenshots.

Use a stable Slate Board feature identifier in commit messages and document whether a new backlog ID is needed.

## Phase 4 — verify and report

For each worktree:

- run discovered tests/lint/format commands;
- report pre-existing failures separately from introduced failures;
- check keyboard navigation;
- check visible focus;
- check reduced motion;
- check 200% zoom where tooling permits;
- check 1440×900 and approximately 390×844;
- verify existing production routes still behave as before;
- list fixture-only states and backend dependencies.

Create:

- `docs/implementation-reports/PS-FEAT-001-first-pass.md`
- `docs/implementation-reports/slate-board-v2-first-pass.md`

Each report must contain:

- branch and commit list;
- changed files;
- route/flag used;
- screenshots;
- commands run and outcomes;
- implemented behavior;
- preserved behavior;
- fixture-only behavior;
- deferred backend/schema work;
- known issues;
- exact review steps for Pete.

## Hard stop rules

Do not:
- merge;
- deploy;
- change production navigation;
- replace existing page routes;
- perform migrations;
- add new production dependencies without documenting and justifying them;
- silently change Foundation C tokens;
- use pink/rose/magenta/coral as semantic accents;
- invent matching/privacy/AI backend behavior;
- continue after an ambiguous destructive choice.

At completion, leave both branches unmerged and provide a concise terminal summary telling Pete which preview route to open first tomorrow.
