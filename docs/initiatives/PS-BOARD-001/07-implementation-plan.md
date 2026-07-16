# 07 — Implementation Notes and Refinement Order

## Work-package boundary

Implement the Photo 1 experience baseline on the dedicated task branch. Keep
the existing shared header and current routes. Do not add production
dependencies, database migrations, Azure resources, or a second navigation
system.

## Ordered work

1. Preserve the route and shared `base.html` shell.
2. Build semantic page structure for the title/actions, labeled control rail,
   physical board, four sections, marker tray, and structured List view.
3. Reproduce Photo 1's desktop composition with scoped CSS: bright room,
   board-to-rail scale, aluminum frame, enamel surface, quadrant marker lines,
   handwriting, pinned paper, tray, markers, and restrained shadow.
4. Keep Short Term, Projects, Long Term, and Work as the first view and use
   generic fixture/view-model data.
5. Preserve existing note interactions where practical; add keyboard and menu
   equivalents rather than drag-only behavior.
6. Express the storyboard capture, proposal, Focus, and audience states as
   contextual overlays/drawers in the same Photo 1 language.
7. Mark browser-local, fixture, and unavailable service behavior honestly.
8. Reflow the board for mobile and List mode without shrinking text.
9. Run focused route/UI/accessibility tests, then the broader regression suite.
10. Perform repeated 1440 × 900 and 390 × 844 visual review against Photo 1.
11. Update verification/handoff documents and push only the review branch.

## Likely implementation surfaces

- `templates/slate_board.html`
- `static/css/slate-board.css`
- `static/js/slate-board.js`
- focused Slate Board tests
- this initiative documentation

The same task branch also contains separately requested Interview Studio
usability work. Changes and test evidence must remain clearly separated in the
final handoff even though they share one user-authorized work package.

## Stop conditions

Stop and report rather than improvise if the shared shell cannot support the
layout, a source document is missing, a real data claim cannot be proven, or a
change would require credentials, migration, production dependency, destructive
cleanup, direct `main` work, or bypassing the Azure review workflow.

Peter's visual review is a mandatory stop before merge or deployment.
