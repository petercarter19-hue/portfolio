# Living Triptych — Unresolved Questions (shared)

Open questions for Pete and/or the other agent. Tag answers with author + date.

## For Pete (product)
1. **Front-door intent:** if the Atrium lands, does it replace `/` (the Experience film) or `/petec` (profile Overview), or live alongside both permanently? Affects how much of each it must absorb.
2. **Ask the Slate wiring:** should the Atrium's bottom bar open the existing Ask-Pete-AI chat panel (`data-open-chat`), or route to a dedicated conversational Overview? Slice 1 will reuse the existing chat unless told otherwise.
3. **Photography rights/assets:** the amber My Story slab wants real photography. Which images in `static/images/` are cleared for a public front-door hero? (Slice 1 uses existing story imagery + texture, not the mockup's generated photos.)
4. **Scope of "3 ways in":** are Story/Projects/Résumé the only three entrances, or should Ask the Slate / The Slate be a fourth affordance on the Atrium?

## For the other agent (Codex)
5. **Rendering approach:** what did your exploration conclude for architectural feel (curved edge-light)? Compare against Claude's `atrium-arrival-exploration` synthesis in `visual-comparison.md`.
6. **Shared view model:** can we agree one Jinja/data shape for a "dimension slab" so both prototypes read the same structured data and the winner is a swap, not a rewrite?
7. **Motion ownership:** whose focus-state (02–04) motion model do we build on once Arrival is proven?

## Technical / to validate with evidence
8. **backdrop-filter budget:** how many overlapping blurred slabs before paint cost hurts on mid hardware? (Measure, don't assume.)
9. **Overlap contrast:** exact scrim recipe that keeps identity text ≥ AA over three tinted glass layers.
10. **Curvature in CSS vs SVG:** can pure CSS convincingly bow a slab, or is an SVG silhouette/clip-path required? (Exploration deliverable.)
11. **Structured list alternative:** the accessible non-3D representation of the triptych — one `<nav>`/list of three dimension links; confirm it satisfies the "accessible structured alternative" requirement.
