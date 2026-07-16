# Verification (2026-07-16)

## Automated
- `venv/bin/python -m unittest tests.test_homepage_scenes -q` → 17 tests OK
  (single h1; shared header intact; no mockup-only nav; live act labels;
  live Polaroid captions present + banned mockup captions absent; approved
  future content; no browser-local board notes; live résumé metrics; no
  fabricated trusted-by logos; every CTA href present AND resolving 200/302;
  `#act-becoming` anchor verified on the live My Story page; Polaroids are
  semantic figures with live alt text; act index is an <ol>; /experience
  still serves the old homepage for rollback.)
- `venv/bin/python -m unittest discover -s tests -q` → **188 tests OK**
  (171 pre-existing + 17 new; no regressions, navigation suite included).

## Browser (Chromium dev preview, http://127.0.0.1:5056/)
- 1440 / 1280 / 1024 / 768 / 430 / 390 / 320 px: rendered each scene;
  `document.documentElement.scrollWidth > clientWidth` → **false at every
  width** (no horizontal overflow). 200% zoom equivalence covered by the
  ≤768px layouts.
- Desktop composition matches the mockups: hero (mic stage + destination
  cards + week strip), résumé preview card (metrics/skills/constellation/
  proof/credentials/step strip), story scene (act rail, Maui + current
  chapter, four chapters, overlapping Polaroids with live captions, future
  card with Ph.D. banner), invitation band.
- Mobile: single-column order per brief; Polaroids un-overlapped; buttons
  full-width; captions unclipped.
- Fixed during review: Polaroid images honored the height="480" attribute
  because the CSS lacked `height:auto` (rendered as tall strips) — fixed;
  Polaroid width bumped to min(36%, 15rem).
- Console: no errors. No JavaScript on the page at all.
- Reduced motion: page is CSS-only; the only transforms/hovers are wrapped
  in a prefers-reduced-motion block that freezes them.

## Screenshots
Captured at 1440 (all four scenes), 1024, 390, and 320 during the session
(desktop hero, résumé card, story stage, mobile stack, mobile Polaroids).
