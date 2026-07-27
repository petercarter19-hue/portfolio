# PS-OVERVIEW-PUBLIC-INTEGRATION-001 Visual Evidence

## Authority reviewed

- Lock:
  `docs/initiatives/PS-OVERVIEW-001/10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`
  (`95c1066fed44398cd750cf0d1798bb39999611e8f2a51ec445f05bd5d0bba213`)
- Story & Career rich desktop:
  `docs/initiatives/PS-OVERVIEW-001/visual-authority/generated-direction/story-and-career-rich-desktop-2026-07-26.png`
  (`e4dfdb298df3eeb706f3acdb5955e546e526f9b3d0f42475a67b1bf3dd37e1b2`)
- Ask Pete AI open desktop:
  `docs/initiatives/PS-OVERVIEW-001/visual-authority/generated-direction/ask-pete-ai-overview-open-desktop-2026-07-26.png`
  (`b9d884f34d1cbd9e1c02e69f2cb243043c7883ca28c9993379083444e379f831`)

Pete approved the locked Story & Career direction before implementation and
then directed this task to activate it publicly. His final layout correction
was: the detailed résumé must fit below the Overview at normal scale, while the
Career Constellation remains at its existing large/full-width presentation.

## Final local captures

| Evidence | State | SHA-256 |
|---|---|---|
| `petec-resume-overview-1440x900.jpg` | Public opening with local left rail, dominant Overview, and right Ask Pete AI rail | `68503ac5b32f6611538bda1da55587e935892155c66286ec3981709e28dd0df5` |
| `petec-resume-boundary-1440x900.jpg` | `Résumé begins here` boundary and retained detailed Impact section below it | `b9df82c8daf9888a624bd682fe18de4d78e732342c2a596dad93d03acba31f0f` |
| `petec-resume-overview-390x844.jpg` | Mobile reflow with horizontal local section navigation | `5b2a4f135487211b2b1f2ef77d8a840cf7d0d6eb59848a1d271a541e42115af9` |

## Compare-refine record

The assigned writer completed three authority-review cycles:

1. Opening composition at 1440 × 900. Corrected primary-action contrast, right
   AI-rail sticky behavior, and center-stage scaling.
2. Overview-to-résumé boundary at 1440 × 900. Corrected fixed-header landing
   clearance and Ask Pete AI button contrast.
3. Final desktop/mobile/wide review after adding the contextual `Viewing`
   state. Corrected the desktop reading line so the local rail and AI context
   follow the selected detailed section.

Final visual mismatch register: empty, except for these permitted narrow
adaptations:

- real Pete-owned public data and media replace illustrative authority content;
- semantic landmarks, stable legacy aliases, visible focus, forced colors, and
  reduced-motion rules were added for accessibility and route continuity;
- the left and right rails collapse to the approved horizontal/compact pattern
  before the center composition becomes cramped; and
- the current Career Constellation remains outside the normal-scale center grid
  and retains its pre-existing wide-screen `zoom: 0.9`.

No material change was made to the locked dominant composition, hierarchy,
typography family, color language, style identity, primary actions, or
responsive interaction model.

## Geometry and behavior

| Viewport | Center / Overview | Constellation | Overflow / rail result |
|---|---|---|---|
| 390 × 844 | 366 px, `zoom: 1`, no transform | 390 px; existing mobile behavior | No horizontal overflow; horizontal local nav; desktop rails hidden |
| 1024 × 768 | 992 px, `zoom: 1`, no transform | Full viewport width | No horizontal overflow; horizontal local nav |
| 1440 × 900 | 963.2 px, `zoom: 1`, no transform | 1440 px, `zoom: 0.9` | No horizontal overflow; left and right rails sticky |
| 1920 × 1080 | 1433.6 px, `zoom: 1`, no transform | 1920 px, `zoom: 0.9` | No horizontal overflow; grid 1881.6 px |
| 2560 × 1440 | 1440 px, `zoom: 1`, no transform | 2560 px, `zoom: 0.9` | No horizontal overflow; centered 1888 px grid |
| 3840 × 2160 | 1440 px, `zoom: 1`, no transform | 3840 px, `zoom: 0.9` | No horizontal overflow; centered 1888 px grid |

At 1440 × 900, the `View résumé` action lands `#resume-start` at 144.2 px
below the viewport top, with the detailed Impact section beginning at 315.0 px.
The right AI rail remains sticky at 140 px. Selecting Impact updates both the
local rail `aria-current="location"` and the Ask Pete AI context to `Impact`.

An effective 200-percent reflow was checked at a 720 × 450 CSS viewport:
center content remained at normal scale with no horizontal overflow. Native
anchors are keyboard focusable and showed a 3 px visible focus outline. The
server-rendered page retains its headings, section order, links, fallback, and
content with JavaScript unavailable. Reduced-motion and forced-color behavior
are covered by explicit CSS rules and focused tests.

Semantic checks found one `h1`, no duplicate IDs, no Maya/fixture content, one
Résumé PDF action, one Overview Connect action, one Overview View résumé
action, and this order:

`overview → resume-start → impact → skills → experience → credentials → constellation`

Browser console errors and warnings: none.
