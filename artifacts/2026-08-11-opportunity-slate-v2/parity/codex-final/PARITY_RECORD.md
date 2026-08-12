# Opportunity Slate v2 R1 — Codex final parity record

Date: 2026-08-11. Writer: Root Codex. This pass was measured from the locked
rasters and newly rendered pages; no prior writer measurements were used as
evidence.

## Locked inputs and fresh outputs

- Mockup 04 SHA-256: `2B42F845C8ADC71435D3F4306F20D914E1FF840165BD42AB257FC65119C9CE59`
- Mockup 05 SHA-256: `1AC6233F1B701EAD882C8D74B3364B87F666D4597CC2BF3F28E66E7FF6D6FDD5`
- Fresh stage-1 desktop SHA-256: `192CBB5F24CA2D8F5E9463251F8CC1B17DB7B25CFC19438D9682951390CB1D97`
- Fresh stage-2 desktop SHA-256: `4519D3760F8D2DB029ACFEE86732B6667A07CBDE40CA891DC063D09A5D8B0D0E`
- Fresh stage-1 320px SHA-256: `D29B2C87CA879FD12EC7131EE9B3E14EE42299D72562704C3C793D9DAEE13172`
- Fresh stage-2 320px SHA-256: `82AD475C0BB0255930C6994C76E6D39FEC756C3132590E1E8350D81F3003D1B2`

Instruments: `shot_v2.py`, `measure_v2.py`, `sample_colors.py`, and
`geometry_probe.py`. Raw selector, computed-style, raster-probe, desktop, and
320px evidence lives beside this record.

## Structural geometry

Vertical coordinates are normalized to each image's detected shared-shell
bottom because the locked mockups draw a different site shell. Tolerance is
8px. Every measured pair passes.

| Pair | Reference | Build | Delta |
|---|---:|---:|---:|
| Stage 1 top rule y | 297 | 294 | 3 |
| Stage 1 textarea top y | 384 | 380 | 4 |
| Stage 1 textarea left x | 55 | 55 | 0 |
| Stage 1 column divider x | 878 | 884 | 6 |
| Stage 1 closing rule y | 901 | 896 | 5 |
| Stage 2 rail edge x | 293 | 291 | 2 |
| Stage 2 identity-input top y | 222 | 225 | 3 |
| Stage 2 meta-rule top y | 289 | 291 | 2 |
| Stage 2 document top y | 432 | 433 | 1 |
| Stage 2 document bottom y | 956 | 956 | 0 |
| Stage 2 footer rule y | 985 | 985 | 0 |

The final pass found and fixed the only prior hard-geometry exception: the
stage-2 document was 24px too tall. It is now 524px with a 20px baseline;
Chromium reports `clientHeight == scrollHeight == 522`, so the complete locked
Meridian fixture remains visible without a scrollbar at 1372px.

## Color, type, spacing, and copy

Representative rendered pairs (reference dominant/edge sample → build flat
token) meet the 6-per-channel color tolerance: canvas `#FDFBFA → #FDFBFA`,
stage-1 textarea vertical edge `#B0ADAB → #B1AEAB`, disabled action
`#EAE4DE → #EAE3DD`, stage-2 rail `#FAF9F7 → #FAF9F7`, rail edge
`#DED3CA → #DFD3CA`, identity edge `#D1CDCA → #D1CDC9`, and confirm fill
`#43511F → #43511F`. The locked rasters contain antialiasing and gradients;
the build intentionally uses stable flat tokens, so exact individual raster
pixels are not treated as separate design tokens.

Rendered heading/body/control ink bands were inspected at original resolution
against both locked rasters. Authored sizes are recorded in the computed-style
JSON; key type sizes, gaps, and control heights stay inside the package's 1px
type and 4px gap tolerances. Stage copy and the Meridian source fixture match
the locked screen text. AI-rendering noise in the reference letterforms is not
copied as product typography.

## Professional-eye and responsive result

The dominant-plane hierarchy, stage-1 paste/alternate-source split, stage-2
earned rail, source identity, captured wording, truth line, and next action all
read as the same experience. Both 320px captures reflow to one column with no
horizontal overflow, overlap, clipped action, or lost truth label. Following
the controlling mobile first-screen rule, Stage 1 now orders the dominant paste
input and `Review source` before the alternate methods; a separate 390×844
browser measurement places the primary action bottom at 842px and the
alternate-method group immediately after it. The rail follows the dominant
document in DOM and narrow visual order. The 69-check functional gauntlet covers
real transfer success, method-specific fallback, competing-submit exclusion,
keyboard focus, explicit upload/import cancellation, dirty-form coordination,
390×844 first-fold hierarchy, reduced motion, and 200%-equivalent reflow. It is
not presented as a screen-reader or forced-colors audit.

The shared production shell remains intentionally different from the mockup
shell (logo treatment, nav inventory, account/search treatment, and footer).
`base.html` and shared shell CSS are outside this lane; this is recorded as a
shell-direction dependency, not disguised as Opportunity Slate parity.
