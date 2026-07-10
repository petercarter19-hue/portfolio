# Tomorrow: PeerSlate Review Order of Operations

## 1. Confirm Codex stopped safely

At the original repository root, check:

```powershell
git status
git branch --show-current
git worktree list
```

The original working tree should be clean and no work should be merged into the default branch.

## 2. Read the preflight before opening pages

Open:

- `docs/implementation-reports/peer-slate-dual-page-preflight.md`

Confirm:

- the Foundation C base commit is correct;
- existing pages were preserved;
- the v2 routes/flags are isolated;
- Codex found the real build and test commands;
- no migrations or production dependencies were added;
- there are no unresolved repository-state warnings.

Stop and resolve any preflight warning before reviewing visual details.

## 3. Review the Living Résumé first

Read:

- `docs/implementation-reports/PS-FEAT-001-first-pass.md`

Open the desktop preview route first, then mobile.

Review in this order:

1. Is the résumé itself the unmistakable dominant object?
2. Is the timeline genuinely integrated into the résumé rather than a separate card row?
3. Does timeline selection update detail inside the same frame?
4. Is there enough vertical space around the Ledger?
5. Does the Career Constellation appear below as a continuation, not a competing first-screen feature?
6. Are skills compact, with only two or three strong proof points?
7. Is the traditional PDF/print path preserved?
8. Does it work with long/short fixture histories?
9. Is any reusable component accidentally Pete-specific?
10. Is the retired/MICAP example absent?

Do not spend time fine-tuning tiny shadows before the structure and spacing feel right.

## 4. Select the exact résumé visual references

From the résumé design thread, choose and copy the final approved images into:

- `docs/design-references/resume/approved-ledger.png`
- `docs/design-references/resume/approved-constellation.png`

Tell Codex these are visual targets, not screenshots to reproduce literally. The real page may use more vertical space and responsive reflow.

## 5. Give Codex one focused résumé correction pass

Group feedback into:

- structure;
- spacing/vertical rhythm;
- typography;
- component behavior;
- responsive/accessibility;
- content/data.

Avoid sending many disconnected one-line changes. Ask for one correction commit, updated screenshots, and updated report.

## 6. Review the Slate Board second

Read:

- `docs/implementation-reports/slate-board-v2-first-pass.md`

Open the Board preview route.

Review in this order:

1. Is the whiteboard immediately the star?
2. Does it retain the fun, hand-placed Board identity?
3. Are Short Term, Projects, Long Term, and Work independently scrollable?
4. Is there comfortable space between notes?
5. Are permanent controls limited to Add, AI Help, Connections, and More/Settings?
6. Are type, dates, privacy, color, handwriting, and note actions contextual rather than always visible?
7. Does the page continue vertically instead of packing everything into one viewport?
8. Is there an accessible list/structured alternative?
9. Is Focus Stage absent/off by default?
10. Are AI and people-matching states clearly fixtures/proposals rather than fake production behavior?

## 7. Walk through the PMP flow

Test:

1. Capture “Study for the PMP certification.”
2. Choose category/type.
3. Choose color and handwriting.
4. Add an optional target date.
5. Confirm visibility defaults to Private.
6. Add the note.
7. Open AI Help and inspect proposed milestones/questions/resources.
8. Open Connections and inspect the opt-in similar-goal presentation.
9. Confirm nothing auto-saves beyond the explicit action and nobody auto-connects.
10. Confirm the note remains editable and movable.

## 8. Give Codex one focused Board correction pass

Prioritize:

- Board scale and width;
- spacing between notes;
- independent scrolling;
- playful irregularity without chaos;
- vertical continuation;
- concise controls;
- mobile/list fallback.

Do not add more features until the core Board feels right.

## 9. Ask Claude Fable for an independent review

Open Claude from the repository root so it loads `CLAUDE.md`. Paste `prompts/CLAUDE_FABLE_KICKOFF.md`.

After it summarizes the project correctly, ask it to review the two Codex branches for:

- requirement drift;
- regressions;
- accessibility;
- mobile behavior;
- fixture versus production confusion;
- duplicate components;
- risky data/privacy assumptions.

Use Claude as reviewer, not as a second agent editing the same files simultaneously.

## 10. Run final checks

For each branch:

- run tests/lint/format;
- open desktop and mobile;
- test keyboard-only navigation;
- test reduced motion;
- check 200% zoom;
- verify original production route;
- review diff and commits.

## 11. Decide the integration strategy

Recommended:

1. Approve and stabilize the résumé branch first.
2. Approve and stabilize the Slate Board branch second.
3. Identify truly shared components.
4. Create a deliberate integration branch only after both are independently understandable.
5. Merge shared foundation changes first, then each page through separate pull requests.

Do not merge both feature branches directly into production in one large change.

## 12. Update durable documentation

After approval:

- update the product backlog status;
- record temporary routes/feature flags;
- record accepted component names;
- record backend work as separate backlog items;
- record any changed design decision in the Design Bible or feature blueprint;
- keep Pete-specific values in fixtures only.

## 13. Then continue the page roadmap

After Résumé and Slate Board:

1. Overview
2. Slate Feed
3. People & Progress
4. Goals
5. My Story
6. Ask AI
7. Interview Me
8. Public Experience / alternative opening page

The original/MVP opening page may remain while the alternative experience is developed and released later.
