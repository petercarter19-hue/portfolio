# PS-OVERVIEW-SLICE-1-001 visual parity record

## Authority

The comparison used the final Pete-locked composite authority named by
`docs/initiatives/PS-OVERVIEW-001/10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`.
The files were re-hashed before comparison:

| State | Authority file | SHA-256 |
| --- | --- | --- |
| Story rich desktop | `story-and-career-rich-desktop-2026-07-26.png` | `e4dfdb298df3eeb706f3acdb5955e546e526f9b3d0f42475a67b1bf3dd37e1b2` |
| Story sparse desktop | `story-and-career-sparse-desktop-2026-07-26.png` | `14c7b5280ebe727f4fadc5af898c9a40d87549b10a2cf365a1957a582b2c7c57` |
| Story narrow desktop | `story-and-career-narrow-desktop-2026-07-26.png` | `081445064ceac73a47a94450b9e023216aa5d5118238de373e7dd9fd97cf7bc8` |
| Story mobile | `story-and-career-mobile-standard-390x844-2026-07-26.png` | `9e8dd13fa2ddedc9fbaab560ba5555029a7bb5355c0624eee5357c99240ebf25` |
| Work rich desktop | `work-and-impact-rich-desktop-2026-07-26.png` | `959f39e741abc9438891487c031a8093759422ff6266f288e9aad44cfe86a538` |
| Work sparse desktop | `work-and-impact-sparse-desktop-2026-07-26.png` | `6aa51933d4c98e9993b774a98a65575788bd5e99473477ef8bf7d1540f5e7074` |
| Work narrow desktop | `work-and-impact-narrow-desktop-2026-07-26.png` | `052e70263114dcc5c6d701beac14f66a36c9b37b98acd0d427a92f618cd60606` |
| Work mobile | `work-and-impact-mobile-standard-390x844-2026-07-26.png` | `c21b4979b8f72373a47922eb2e1d90da28bb92ed5d6ea4ac657c4b79c857a050` |

## Compare-refine loop

The designated writer performed two complete visual/geometry passes and
reopened the loop after the final media-state CSS changes.

### Pass 1 mismatch register

| State | Mismatch | Correction |
| --- | --- | --- |
| Work mobile, 390 × 844 | The desktop Career grid retained higher selector specificity, leaving the career image as a narrow vertical sliver. | Added explicit media-present classes and a mobile `overview-career--with-media` one-column rule. |
| Sparse/missing-media desktop | Career, Impact, Chapters, and Future could retain an empty visual column when their media was absent. | Made one column the default and enabled split grids only through `--with-media` classes. |
| Story rich, 1440 × 900 | The hero portrait focal point cropped too far right and the uppercase name wrapped too aggressively. | Corrected the fixture focal point and bounded the Story name scale. |
| Story rich impact | Four impact cards were compressed beside a wide media column. | Preserved the Story direction while placing its media below a full-width impact grid. |
| Geometry measurement | A section kicker and organization label were incorrectly counted as primary body copy. | Narrowed the measurement selector to prose/highlight copy; the required labels remain intentionally smaller than body copy. |

### Pass 2 result

The final visual mismatch register is empty. No unresolved visible defect was
accepted as a deviation. The final screenshots were regenerated, compared
again with the locked authority, and measured after the last visual-affecting
change.

## Final side-by-side comparisons

The `comparisons/` directory contains the mandatory final authority/render
pairs:

- `story-career-rich-side-by-side.png`
- `story-career-sparse-side-by-side.png`
- `story-career-narrow-side-by-side.png`
- `story-career-mobile-side-by-side.png`
- `work-impact-rich-side-by-side.png`
- `work-impact-sparse-side-by-side.png`
- `work-impact-narrow-side-by-side.png`
- `work-impact-mobile-side-by-side.png`

## Parity matrix

| Control | Evidence | Result |
| --- | --- | --- |
| Silhouette and composition | Rich, sparse, narrow, mobile side-by-sides for both style manifests | Pass |
| Opening hierarchy | One identity hero, one `h1`, profile imagery when eligible, proof band count-aware | Pass |
| Dominant action | Connect primary; View résumé secondary in both styles and reflow states | Pass |
| Story & Career direction | Warm editorial field, serif hierarchy, gold rules, narrative bands, timeline rhythm | Pass |
| Work & Impact direction | Navy/blue business hierarchy, metric band, structured cards, crisp rules | Pass |
| Content density | Early-career, career-changer, experienced-leader, independent-creative, and text-only fixtures | Pass |
| Missing content | Missing proof/media/awards/credentials omit cleanly without reserved space | Pass |
| Wide geometry | 1440 × 900, 1920 × 1080, 2560 × 1440, and 3840 × 2160 screenshots and measurements | Pass |
| Narrow desktop | 1280 × 800 screenshots and measurements for both styles | Pass |
| Touch mobile | 390 × 844 screenshots; one semantic column and no horizontal overflow | Pass |
| 200% equivalent reflow | 720 × 450 screenshots for both styles | Pass |
| Large text | Server-rendered large-text screenshots at 1440 × 900 | Pass |
| Keyboard focus | Focus screenshots for both styles; forced-colors focus screenshots added | Pass |
| Reduced motion | Reduced-motion screenshots; no essential motion dependency | Pass |
| Long content | Experienced-leader full-page captures in every principal viewport | Pass |
| Failure/unavailable | External host 404, unknown fixture/style 404, submitted identity 400; no public error UI exists in this internal-only slice | Pass |
| Geometry invariants | 60 cases; 0 overflow, edge, scale, copy-size, location, anchor, heading, or alt failures | Pass |

## Permitted narrow adaptations

These are required truth, accessibility, or reflow adaptations rather than new
visual direction:

- Generic illustrative fixtures replace all person-specific authority copy and
  imagery. Every image is truth-labeled.
- The final architecture contract supersedes early raster rail duplication:
  one left résumé-sections rail and one right simulated public Ask rail are
  represented.
- Primary prose remains at least 16 CSS pixels. The real semantic page is
  consequently taller than the compressed illustrative raster.
- Mobile, large-text, and 200%-equivalent states preserve reading order rather
  than shrinking or transforming a desktop canvas.
- Focus, forced-color behavior, reduced motion, alt text, landmarks, and stable
  anchors are explicit even when not literally depicted in a raster.

These adaptations preserve the locked hierarchy, composition language,
actions, and style distinction. They do not add a new visual concept.
