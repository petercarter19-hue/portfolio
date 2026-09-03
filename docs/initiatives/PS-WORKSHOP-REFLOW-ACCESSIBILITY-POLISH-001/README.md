# PS-WORKSHOP-REFLOW-ACCESSIBILITY-POLISH-001

## Outcome

This Bounded package makes the accepted Workshop experience usable at narrow
widths, browser zoom, forced colors, with a keyboard, and without JavaScript.
It does not create or restyle Workshop. The owner-accepted 2026-08-02 facelift
(`PS-SLATE-STUDIO-IA-001/visual-authority/workshop-facelift-2026-08-02`,
R01-R17) was already implemented, hash-authorized, unflagged, and loaded by
every Workshop view before this package began.

The shared Workshop hero remains the sole H1. Work opening, focused-question,
and review titles are subordinate H2s inside the one canonical shared-shell
`main#main-content`. Native controls expose visible focus, usable target sizes,
truthful disabled state, and reflow that does not clip long content or settle a
focused control behind the shared sticky header or phone bar.

## Narrow corrections

- Dead fixture actions in the claimed partials are plain inert text or native
  disabled buttons. The three fixture-only anchors emitted by the unclaimed
  suggestion partial are suppressed by an exact Workshop CSS selector, so
  they are absent from presentation, the accessibility tree, and sequential
  focus until a real suggestion capability exists.
- The existing information card remains a real native disclosure at every
  width; desktop no longer visually forces it open while its summary still
  claims that it can collapse.
- Status/mode/selected states retain non-color outlines in forced-colors mode,
  and Workshop motion becomes effectively immediate when reduced motion is
  requested.
- Existing panels, fields, buttons, mode tabs, chips, summaries, and inline
  actions wrap or stack at 640px and below while preserving the accepted
  composition and copy.
- Real server-rendered forms keep their JavaScript-off GET/POST path. An
  unavailable microphone remains disabled rather than becoming a dead stop.

## Semantic boundary

Every covered render has exactly one `main#main-content`, one visible Workshop
H1, and the expected local H2 hierarchy. For the bounded outcome phrase "one
H1 and labelled main per view," the sole H1 names the Workshop view inside the
sole canonical main, and the shared skip link targets that main. That structure
is the required label/ownership relationship here; it does not require an
additional ARIA accessible name on a unique main landmark. The package excludes
the shared base and forbids a nested second main, so editing `templates/base.html`
or creating another landmark would violate both scope and semantic correctness.
Any future literal main-naming hook is separate shared-shell work, not a gap in
this package's accepted interpretation.

## Boundaries

This package changes only the claimed Workshop stylesheet, four Workshop
partials, three W2 templates, focused tests, and package records. It does not
change shared shell/base/navigation, routes, authentication, safe return,
services, data, schema, feature flags, identity/provider state, or the dormant
dark theme. It does not reopen closed Workshop E/F/G work and does not run or
duplicate the separate fresh two-member proof.

Repository merge is not deployment. Production authority is withheld; this
package performs no deployment, flag change, production verification, or live
operation.

## Acceptance

Acceptance requires rendered semantic tests, all Workshop regression suites,
implicated navigation/auth/security coverage, template compilation, registry
and delivery validation, full repository regression, diff/secret checks, and a
fresh independent review of one immutable exact SHA.

The deterministic local browser matrix covers signed-out and generic local
authenticated shells; populated and empty libraries; add, review, saved detail,
and all three W2 views; JavaScript off; forced colors; reduced motion; complete
keyboard traversal; long text and WCAG text spacing; and widths 1440, 1024,
768, 640 (200%-equivalent), 390, and 320 (400%-equivalent). It must prove one
main/H1, no horizontal overflow, all active Workshop targets at least 44 by 44
CSS pixels, visible focus, and no sticky-chrome obstruction.

## Governance status

The initial claim deliberately excluded `docs/governance/PACKAGE_REGISTRY.json`.
That one-path, append-only surface extension passed independent review and CI,
then merged as PR 892 at `5c2bdf891670893978bbe194ef48b608c9567629`.
The implementation is refreshed from that exact main, includes one alphabetized
`current_protect` entry with recomputed counts, and repeats the complete
validation and capture matrix before its fresh final exact-SHA review.
