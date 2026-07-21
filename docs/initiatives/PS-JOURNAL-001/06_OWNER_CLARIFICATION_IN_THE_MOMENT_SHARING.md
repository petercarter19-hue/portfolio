# PS-JOURNAL-001 — Owner Clarification: In-the-Moment Sharing and Audience

**Recorded:** 2026-07-21 · **Owner:** Peter Carter · **Status:** clarification that
reinforces the locked architecture; it does not change any locked requirement.

## What Pete clarified

The capture pop-out must **catch the moment**, not just file it. His words:
"Capturing the moment is capturing the moment. In the moment, lots of times you
want to share it with others or share it in certain places. If you just put it in
a journal, it could get forgotten."

So, in the same pop-out, immediately after **Save Moment**:

- The Moment is **always saved private to the one Journal first, automatically**
  (derived membership, default Only Me). This never depends on the member
  choosing anything.
- In that same breath, the composer offers **first-class `Use This Moment`
  options** — **share to Feed, add to My Story, use in Work, add to Résumé**, and
  other authorized destinations — **together with an audience choice**. These are
  part of the moment, not something the member must dig out of the Journal later
  (though they remain available from the Journal at any time).
- Every one of those options is an **explicit, previewed** action. Nothing is
  auto-shared, auto-published, or auto-audienced. Each share shows the member
  exactly what will post and who will see it before it goes.
- Sharing is an **exact-reference projection, never a copy**. The Journal Moment
  stays the single source of truth; removing a projection never removes the
  Moment from the Journal.

## Interaction model (owner reference)

The composer **pops out over the current page** (like the homepage
"Walk me through it" interview demo that Pete cited), preserves the origin
context, and **returns the member to that exact page** when done. It is not a
route to a separate Capture page and not a multi-screen wizard: one quick act —
Type or Speak → Save Moment → optional in-the-moment share/audience → back to the
page.

## Traceability — this reinforces, and does not override, existing requirements

- `PS-JRN-CAP-013` — post-save shortcuts including Use This Moment.
- `PS-JRN-USE-001` / `PS-JRN-USE-015` — Use This Moment exposes the complete
  authorized destination chooser; suggestions may rank but never hide an eligible
  choice or place anything automatically.
- `PS-JRN-MOM-010` — Save Moment does not publish, broaden audience, or create a
  Feed/résumé/Story/message/Project by itself.
- `PS-JRN-AUD-005` / `PS-JRN-AUD-006` — new Moments default to Only Me; an
  audience change requires exact-audience preview and is never bundled into Save
  Moment.
- `PS-JRN-USE-002` / `PS-JRN-USE-003` / `PS-JRN-USE-007` — downstream use is an
  exact-version reference or governed projection, never an independent copy.
- Site rule 23 (`docs/PEERSLATE_SITE_RULES.md`) extended to state the same.

## Build and visual-authority implications

- **Sequencing is unchanged.** Slice **J1** ships private capture + one Save
  Moment + the derived private Journal. The full `Use This Moment` destination
  chooser and audience projections are **Slice J2+**, enabled as each destination
  (Feed, Story, Work, Résumé, …) is wired.
- **Design the complete moment from the first visual round.** The composer's
  **saved state must be an explicit visual-authority screen** showing: "Saved
  privately to your Journal" + the `Use This Moment` share destinations + the
  audience selector + the "you'll preview before anything posts" reassurance.
  Buttons may render as clearly-disabled `Coming later` where a destination is
  not yet wired, only when the visual-authority package permits it.
- This affects visual-authority images **02 (universal composer)** and
  **04 (saved state)**; see the supplement in
  `visual-authority/chatgpt-first-set/08_OWNER_REFINEMENT_SAVED_STATE.md`.
