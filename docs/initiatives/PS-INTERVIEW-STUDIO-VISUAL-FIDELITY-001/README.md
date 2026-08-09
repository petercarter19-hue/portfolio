# PS-INTERVIEW-STUDIO-VISUAL-FIDELITY-001

## Purpose

Owner-directed finish-fidelity pass on the live public `/interview-studio`:
make the implementation match the locked visual authority's material depth
("more texture... way more layers... deep shadow... it should have more of a
3D look... just like the mockups"), correct typography scale and spacing,
widen the center stage and narrow the right rail inside the locked
composition, and debug page interactions (the experience-level picker in
particular).

This is fidelity to the existing lock, not new visual direction: the
controlling material remains
`PS-INTERVIEW-STUDIO-CALIBRATION-001 / 34 - Green Hue Only - Smoked
Eucalyptus.png` and the hash-locked Functional V1 compositions.

## What changed

- **Depth system:** three-tier ink-green elevation tokens (`--is-shadow-soft`
  / `--is-shadow` / new `--is-shadow-deep`) with a shared top-edge light
  (`--is-edge-light`). The task stage is the front layer (deepest lift,
  brightest gradient), floating cards sit mid, chips soft. The composer is
  the one intentionally recessed surface (inset shadow) so raised layers read.
- **Canvas texture:** real SVG `feTurbulence` grain (measured on-canvas
  luminance stddev ≈ 3.0 — present, not noisy) over tonal mottles and a
  genuine corner vignette; the previous 2%-alpha hairline stripes averaged
  away at screen density. Texture stays off text surfaces.
- **Typography/spacing:** the practice question rises to
  `clamp(1.9rem, 3.3vw, 2.7rem)` serif; mode cards grew with legible labels
  (0.86rem/0.66rem); sub-legible sizes (0.48/0.584rem) raised to ≥0.62rem;
  card padding and rail spacing opened up.
- **Proportions:** practice/video/complete grids `18.25rem → 15.75rem` right
  rail with a wider gap (center gained ~36px at 1920); base content grid
  `21rem → 19rem`. Shell stays 1536px = 80% of 1920 per the lock.
- **Interaction fix:** the experience-level picker no longer fires the
  unrelated "Move to another question?" confirm (which blocked the change and
  snapped the value back on cancel); the level now applies immediately,
  preserves question and draft, keeps the video-recording guard, and
  announces itself to the live region.
- **Cosmetic correction:** the light primary button's blue-theme shadow
  leftover replaced with warm-tinted lift.

## Evidence

See `OWNER_TECHNICAL_COMPLETION_REPORT.md` in this folder after closeout.
