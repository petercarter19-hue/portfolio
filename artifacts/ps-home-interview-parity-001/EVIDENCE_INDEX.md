# PS-HOME-INTERVIEW-PARITY-001 Evidence Index

Captured 2026-07-20 from the local implementation at the writer-branch tip,
before release. The released Interview Studio named in the package architecture
is the visual and product authority.

## Primary comparison set

| Viewport | Theme | Poster | Step 1 | Step 2 | Step 3 | Step 4 |
|---|---|---|---|---|---|---|
| Desktop 1440 x 900 | Light | `desktop-light-poster.png` | `desktop-light-step-1.png` | `desktop-light-step-2.png` | `desktop-light-step-3.png` | `desktop-light-step-4.png` |
| Desktop 1440 x 900 | Dark | `desktop-dark-poster.png` | `desktop-dark-step-1.png` | `desktop-dark-step-2.png` | `desktop-dark-step-3.png` | `desktop-dark-step-4.png` |
| Mobile 390 x 844 | Light | `mobile-light-poster.png` | `mobile-light-step-1.png` | `mobile-light-step-2.png` | `mobile-light-step-3.png` | `mobile-light-step-4.png` |
| Mobile 390 x 844 | Dark | `mobile-dark-poster.png` | `mobile-dark-step-1.png` | `mobile-dark-step-2.png` | `mobile-dark-step-3.png` | `mobile-dark-step-4.png` |

## Supplemental evidence

- `mobile-landscape-step-3.png`: 844 x 390 landscape; the modal scrolls
  internally and neither the page nor modal has horizontal overflow.
- `reflow-720x450-step-3.png`: effective 200% reflow check for a 1440 x 900
  desktop reference; no page or modal horizontal overflow.
- Visible focus is recorded throughout the step captures after programmatic
  step changes, including `desktop-dark-step-3.png`.
- The modal-local theme proxy was exercised in both directions while the modal
  remained open. The active step, fixed question/answer content, modal scroll
  position, and proxy focus were retained.
- Background children received `inert` while the modal was open. On close, all
  attributes added by the demo were removed and focus returned to the poster
  trigger.
- Mobile long-content behavior is represented by steps 1, 3, and 4: the modal
  remains internally scrollable while its action and truth area remain usable.

## Non-screenshot checks

- Browser console: zero warnings and zero errors across desktop, portrait,
  landscape, and reflow checks.
- Reduced motion: the existing `prefers-reduced-motion: reduce` homepage rule
  remains in force; the walkthrough adds no timer- or animation-dependent
  state.
- No JavaScript: the poster, fixed question, listening guidance, truth labels,
  and real-Studio fallback link are server-rendered. Automated tests assert the
  no-JavaScript completeness and JS-gated modal trigger.
- Failure state: not applicable. This is a fixed local walkthrough with no
  request, form submission, storage, media capture, or generated response.
- Privacy/security: source and automated tests confirm that the controller
  contains no network, storage, media, or timer APIs. Theme persistence remains
  the responsibility of the already-released global theme controller, which is
  why the truth label is scoped to answer and practice data.

## Automated validation

- Focused homepage/navigation/site/governance set: 81 passed, 55 subtests
  passed.
- Full repository suite: 603 passed, 2 skipped, 205 subtests passed.
- `git diff --check`: passed.

## Production release evidence

Captured after Azure PR 105 squash-merged and automatic pipeline 154
(`20260720.25`) passed Build and Deploy for exact merge
`4deb0a07b6faf2d93d445e212207aeb84b1a71c4`:

- `production-desktop-dark-poster.png`: the live cinematic poster within the
  retained homepage paper-band rhythm.
- `production-desktop-dark-step-3.png`: live score, practice-signal caption,
  focus treatment, and Cinematic Studio modal at 1440 x 900.
- `production-mobile-dark-step-4.png`: live final retry and Studio CTA at
  390 x 844, with internal modal scrolling and no horizontal overflow.
- Live HTML returned HTTP 200 with `interview-parity-1`, `int-parity-1`, the
  converged poster title, and the scoped no-answer/practice-data truth label.
- `/interview-studio` and `/interview-studio/history` each returned HTTP 200.
- Live desktop and mobile browser consoles contained no warnings or errors.
