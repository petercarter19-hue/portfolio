# Wide-desktop canvas and evidence amendment

## 1. Decision

Pete's 2026-07-25 review identified a real visual-authority risk: the two
direction images are tall, narrow presentation boards. If a later visual lock
treated their 941- and 864-pixel raster widths as target browser geometry, the
Overview could become an undersized page nested inside PeerSlate's already
resolved résumé content column.

That result is prohibited.

The supplied images remain valuable direction inputs for hierarchy, editorial
rhythm, content families, image treatment, and tone. Their pixel dimensions and
portrait aspect ratios are not CSS widths, browser viewport specifications, or
permission to preserve their narrow outer silhouette.

This is a requirements clarification before visual lock. It does not change
the current website and does not create runtime implementation authority.

## 2. Screen size is recorded in CSS pixels

A 27-inch or 32-inch diagonal does not determine browser layout. Native
resolution, operating-system scaling, browser zoom, device-pixel ratio, and
window size determine the CSS viewport.

Every visual and implementation evidence item therefore records at least:

- `window.innerWidth` and `window.innerHeight`;
- device-pixel ratio;
- browser zoom when it is not 100 percent;
- the full browser-shaped page frame rather than a cropped concept board; and
- the measured résumé shell, content-column, and Overview-root rectangles.

Physical monitor size may be useful evidence context, but it is never the
breakpoint or acceptance value.

## 3. Current résumé-shell reference geometry

At the amendment base, the current public résumé shell uses:

- `.r2-page-grid { width: min(96vw, 100rem); }`;
- an `8.75rem` contextual ribbon column; and
- `gap: clamp(1rem, 2vw, 2rem)`; while
- `.resume-v2 > * { zoom: 0.9; }` scales the desktop child layout.

With a 16-pixel root size, the approximate visible reference geometry after
the current CSS zoom is:

| CSS viewport | Visible résumé grid | Outer gutter per side | Visible ribbon | Visible gap | Visible center column |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1440 | 1244.2 px | 97.9 px | 126 px | 25.9 px | 1092.2 px |
| 1920 | 1440 px | 240 px | 126 px | 28.8 px | 1285.2 px |
| 2560 | 1440 px | 560 px | 126 px | 28.8 px | 1285.2 px |
| 3840 | 1440 px | 1200 px | 126 px | 28.8 px | 1285.2 px |

These values explain the current composition at common wide desktop viewports.
At 2560 and 3840 CSS pixels, intentional outer margins remain because the shell
is capped; the page is not expected to stretch from edge to edge. The current
CSS zoom also makes the 1440-wide page materially smaller and is not a suitable
future Overview fit technique.

The CSS selectors and numeric values above are current-shell reference
evidence, not a permanent implementation API. If the approved Context Rail or
shared shell later changes, the invariant below controls.

Pete approved the Studio-aligned starting target for ChatGPT's first visual
candidates on 2026-07-26:

`shell inline-size: min(92vw, 90rem)` at 100-percent browser zoom, with
computed CSS `zoom: 1` and `transform: none`.

Keeping the current external ribbon proportions for comparison gives:

| CSS viewport | Candidate shell | Outer gutter per side | Ribbon | Gap | Candidate center canvas |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1440 | 1324.8 px | 57.6 px | 140 px | 28.8 px | 1156 px |
| 1920 | 1440 px | 240 px | 140 px | 32 px | 1268 px |
| 2560 | 1440 px | 560 px | 140 px | 32 px | 1268 px |
| 3840 | 1440 px | 1200 px | 140 px | 32 px | 1268 px |

This target aligns the Overview visual exercise with the newer Studio stage
scale without importing Studio's visual authority. It is approved starting
geometry, not a substitute for Pete's exact visual file/hash lock. Complete
2560- and 3840-pixel frames may lead Pete to widen or otherwise adjust the
exact stage.

The planned [PS-SHELL-001 package](../PS-SHELL-001/README.md) still records an
older approximate
1120–1200-pixel universal content stage. That estimate would narrow the current
résumé center canvas and conflicts with the newer wide-stage concern. This
Overview package does not silently override a separate package, but the older
estimate does not narrow or block the Overview visual exercise. The exact
Pete-locked Overview geometry and shared shell must be reconciled before
runtime implementation.

## 4. Durable width invariant

The published Overview root has an inline size of 100 percent of the resolved
résumé content column.

- Its outer inline edges align with the content column within normal
  subpixel/rounding tolerance.
- It does not add a second 864-, 941-, 960-, 1000-, or similar arbitrary
  `max-width` stage inside that column.
- Major hero regions, proof bands, feature media, credential bands, and
  count-aware grids may use the available canvas according to the exact locked
  style manifest.
- An individual card may occupy a declared subset of a grid. That is
  composition inside the canvas, not permission to narrow the Overview root.
- A future shared-shell or rail migration recalculates the available content
  column; it does not preserve a stale Overview pixel width.

A materially narrower outer silhouette requires a new ChatGPT-created visual
authority and Pete's explicit file/hash lock. Architecture or implementation
may not introduce it as an undocumented convenience.

## 5. Canvas width and reading width are different

Using the full center canvas does not mean stretching every sentence across
it.

- Body copy receives a readable inner measure, initially targeting
  approximately 55–70 characters per line and validated against the locked
  typeface, size, language, zoom, and content.
- Multi-column composition, media, rules, background bands, and grouped proof
  can establish the wide page silhouette while text remains readable.
- Sparse states use intentional proportion and whitespace. They do not become
  a narrow centered card merely because fewer blocks exist.
- Rich states reduce repetition and member selection before reducing type size.
- Missing blocks collapse without shrinking the surviving Overview root.

## 6. Required visual evidence before lock

For both Story & Career and Work & Impact, ChatGPT's production-intent visual
set must include full shared-shell frames at:

- 1440 × 900 CSS pixels;
- 1920 × 1080 CSS pixels;
- 2560 × 1440 CSS pixels; and
- 3840 × 2160 CSS pixels.

The set must show:

- the Overview in the actual résumé center-content relationship;
- the owner-approved `min(92vw, 90rem)` normal-scale starting target, unless
  Pete explicitly redirects the visual exercise after reviewing the frames;
- the applicable external contextual control outside that canvas;
- at least standard and rich public states at wide desktop;
- a sparse state proving that width does not collapse into a skinny card;
- representative readable text measure inside the wide composition;
- the real résumé boundary below; and
- at least one wide owner-editor/visitor-preview pair proving that editing
  furniture does not change the published canvas.

The two tall source composites may appear beside this evidence as direction
references. They cannot be the sole desktop visual evidence, be simply
upscaled, or be centered at their source width inside a larger blank browser
frame.

At 2560 and 3840, the exact stage, rail, and outer gutters still require Pete's
explicit visual file/hash approval. The current declared unscaled approximately
1428-pixel center canvas is not the visible current result because of desktop
CSS zoom, and neither the current zoomed canvas nor the working target is
automatic acceptance for the eventual shared shell.

## 7. Implementation acceptance

The future activated implementation captures browser-computed geometry at the
four desktop viewports above.

1. Measure the resolved résumé content column and Overview root with
   `getBoundingClientRect()`.
2. Confirm their inline-start and inline-end edges agree within two CSS pixels
   after expected layout rounding.
3. Confirm no descendant is acting as an undocumented page-level narrow stage.
4. Confirm computed CSS `zoom: 1` and `transform: none` on the future Overview
   fitting chain at 100-percent browser zoom.
5. Confirm primary body copy is at least 16 CSS pixels and measure its line
   length separately from canvas occupancy.
6. Check sparse, standard, rich, missing-media, and missing-optional-section
   states.
7. Record horizontal overflow, clipped content, and two-dimensional scrolling
   as failures.
8. Re-run at 200 percent zoom and the package's intermediate/mobile widths;
   wide-desktop acceptance never replaces reflow acceptance.

## 8. Scope and evidence limits

This amendment is based on:

- direct inspection of both package source images at their original
  dimensions;
- the current résumé shell CSS at the exact amendment base;
- an existing full-desktop résumé screenshot used as corroborating, not new
  visual authority; and
- comparison with the concurrent Studio width review as a consistency check,
  not as controlling Overview authority.

No browser DOM measurement was claimed for this documentation amendment. The
local Playwright package was available, but its browser binary was not
installed. Real browser measurements are explicitly required at the future
visual/implementation gates rather than being inferred from these direction
boards.
