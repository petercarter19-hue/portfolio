# 16 — Shared Shell and Cross-Mode Responsive Contract

## One product, not four unrelated pages

Interview Me, Interview AI, Video Practice, and History share one visual and interaction system. Codex should reuse structure where the repository stack supports it, but must not force unrelated business logic into one mega-component.

## Shared hierarchy

1. Global PeerSlate shell.
2. Interview Studio identity/context.
3. Mode selector: Interview Me, Interview AI, Video Practice.
4. History as adjacent destination.
5. Session summary and Edit Session.
6. Mode-specific task stage.
7. Contextual rail/drawer.
8. Concise truth/footer language only where needed.

## Shared visual rules

- Light canvas: true white/neutral white.
- Primary ink: deep navy.
- Primary action/active selection: cobalt.
- Status/success/support: restrained teal.
- Errors/destructive: restrained red.
- Surfaces distinguished by border, spacing, and very restrained shadow—not beige fills.
- Serif display type may identify questions/major results if it matches the existing PeerSlate type system; controls and body copy remain highly readable.

## Mode switching

- Active mode is route/state-driven using current semantics.
- Switching modes preserves or confirms work according to existing behavior.
- Do not invent cross-mode persistence.
- A live recording must receive existing safe stop/exit handling before navigation.
- Theme and session configuration remain consistent across modes.

## Desktop

- Main stage/rail relationship generally 72–78% / 22–28%.
- Question or active composer appears within the first viewport.
- Rail never causes the main task to become cramped.
- At 1366×768, the current mode's primary input/control and primary action remain discoverable without hunting.

## Tablet

- Collapse the rail when it would reduce the main task below usable width.
- Use a side drawer, bottom sheet, or inline disclosure based on existing primitives.
- Preserve selected basis/device status/session summary in a compact visible form.

## Mobile

- One-column task-first order.
- Compact mode control; History remains separate.
- Session summary collapses to one line or sheet.
- Primary action remains reachable and does not cover focused inputs or camera controls.
- Question continuity uses a compact sticky summary when long content scrolls.
- Context rail content becomes sheets/disclosures.
- No horizontal page scrolling at 390×844 or 320×568.

## Dark theme

- Same DOM, order, actions, focus behavior, state machine, and responsive rules.
- Only tokens and atmospheric treatment change.
- No dark-only or light-only capability.
- All contrast and recording/error/status meanings remain accessible.

## Long-content behavior

Test:

- long interview questions;
- 5,000-character answer where allowed;
- long AI generated answer;
- long reasoning and evidence list;
- compare output;
- long follow-up;
- camera permission error copy;
- long transcript;
- History item detail.

Content expands naturally without overlapping sticky controls or hiding the current question/primary action.

## Accessibility and focus continuity

- Heading hierarchy follows route and active state.
- Mode selection, basis selection, device state, progress, and actions are programmatically named.
- Drawers/sheets trap and restore focus using existing patterns.
- Sticky headers/actions do not obscure focused elements.
- At 200% zoom, reflow works without two-dimensional scrolling for the main task.
- Reduced motion disables decorative transitions without removing status communication.
