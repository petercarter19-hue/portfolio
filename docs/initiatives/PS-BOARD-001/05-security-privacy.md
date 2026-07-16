# 05 — Security, Privacy, Accessibility, and Mobile

## Trust boundaries

- Treat all board, transcript, proposal, media, collaborator, and audience data
  as private unless server policy proves otherwise.
- Never expose private content through public HTML, JSON, logs, screenshots,
  telemetry, search, public AI retrieval, or client-side bootstrap payloads.
- Never infer that a preview save, attachment name, presence dot, or share
  control represents a completed backend action.
- Do not put secrets or provider credentials in the browser or repository.
- Public projection must be an allow-list of approved canonical records, not a
  filtered dump of owner board state.

## Accessibility contract

- Target WCAG 2.2 AA, visible focus, keyboard operation, screen-reader names and
  state, forced colors, high contrast, reduced motion, and usable 200% zoom.
- Board and List views expose equivalent objects and essential actions from the
  same state. List is not a diminished fallback.
- Moving a note has keyboard/menu alternatives; drag-and-drop is optional.
- Handwriting, position, rotation, pin color, and connector direction are never
  the only carriers of meaning.
- Live capture and save states use an appropriate status/live region without
  repeatedly interrupting the user.
- Dialogs and contextual panels have accessible names, logical focus order,
  Escape/cancel behavior, and focus return to their trigger or selected item.
- All controls remain at least 44 × 44 CSS pixels where touch interaction is
  expected. Text remains selectable semantic content.

## Mobile contract

At approximately 390 × 844, do not scale the desktop whiteboard until its text
is unreadable. Preserve the physical-board cues, then reflow into readable
section flow:

1. shared header and concise page identity;
2. essential Board/List and private-status controls;
3. control rail as compact tools, not a persistent narrow sidebar;
4. one readable section at a time or a structured vertical sequence;
5. drawers/dialogs as full-width sheets with visible submit/cancel actions;
6. no horizontal page overflow, clipped labels, hover-only tools, or fixed
   controls covering content.

Long titles, empty boards, dense boards, large text, landscape phones, device
safe areas, reduced motion, and virtual-keyboard behavior are required review
states.
