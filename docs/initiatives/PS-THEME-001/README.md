# PS-THEME-001 — Monochrome & Signal Gold dark theme (delivered 2026-07-16)

## What landed
- **Header theme switch** next to the search box (`templates/base.html`):
  a small `role="switch"` control, keyboard operable, `aria-checked`
  synced. Off = the existing light theme, exactly as before. On = the
  approved "Monochrome & Signal Gold" system from Pete's reference
  package (ink `#0B0C0E` chrome, warm paper `#FAF9F5` pages, signal
  gold `#D8A928` as the single accent, text-safe gold `#8A6500` for
  small text on light surfaces).
- **Persistence + anti-flash**: choice stored in `localStorage`
  (`ps-theme`); an inline script at the top of `<body>` applies a
  stored dark preference before first paint. `static/js/theme-toggle.js`
  owns the click handling.
- **Token layers** in `style.css` under `body[data-theme="dark"]`:
  the Modern-Blue-era shared vars, the Iris Foundry `--ps-*` block, the
  Foundation-C `--ps-product-indigo` family, slate-light's late var
  block, and the `.peerslate-home-page` `--home-*` palette are all
  remapped, so var-driven components re-theme automatically. Room
  accents collapse to gold in dark; the light theme's per-room hues are
  untouched.
- **Page passes** (dark scope only, appended per file):
  homepage-scenes (near-black cinematic hero, one gold CTA, paper
  mid-bands, ink invite band), resume2 + living-resume-v2 (museum
  paper, gold verified/evidence, graphite constellation stage),
  interview-studio (light rail + black question/recording workspace,
  gold progress/timer/primary), slate-board (light writing canvas
  preserved, paper wall, gold actions, mono legend/donut),
  story-acts (ink act stages, gold timeline, natural photos),
  feed-living-stream, people-interests, skills-cinematic,
  sky-glass + editorial-glass (blue-orbit backdrop → flat paper,
  frosted cards → planted mono cards), chat assistant (graphite shell,
  gold send/launcher).

## Decisions
- The light/default theme is **byte-for-byte behavior-identical** —
  every new rule is scoped under `body[data-theme="dark"]`. Rollback =
  remove the toggle; no component was forked.
- The background image asset guarded by `tests/test_site_background.py`
  is untouched (dark theme covers it with scoped backgrounds instead of
  replacing the file reference).
- Slate Board sticky notes, marker handwriting palette, member
  photography, and avatar identity colors stay user-content colors
  (brief rule: the interface must not become sterile).
- Semantic colors survive in dark: green = verified/strength,
  amber = improvement, red = destructive/recording only.
- No `prefers-color-scheme` auto-detection: off by default everywhere,
  the member chooses. (Phase-4 language in the source package treats
  this as acceptable; predictability won.)
- The v1.3-adoption work that merged today (PR 46) reaffirms Iris
  Foundry as the active foundation — this initiative does not replace
  it; it adds an optional member preference documented as rule 78a.

## Verification
- Full suite: **209 tests OK** (`python -m unittest discover -s tests`).
- Browser (dev server, both themes toggled per page): homepage, Living
  Résumé, Interview Studio, Slate Board, My Story, Community/People &
  Interests, Feed Living Stream, Skills. Checked: toggle reachable next
  to search and keyboard-operable, stored preference applies without a
  light-theme flash, no gold body text on white (gold-ink used), the
  whiteboard canvas stays legible, photos stay natural, light theme
  renders identically with the switch off.

## Checklist (docs/INITIATIVE_CHECKLIST.md)
Canonical objects: none touched (presentation only). Owner/audience:
unchanged. Private/public: unchanged. AI vs deterministic: unchanged
(theme choice is client-side preference state). Provenance: n/a.
Accessibility: WCAG-AA-checked accent pairs (#8A6500 on white 5.4:1,
#E3B83A on ink 9+:1), visible gold focus ring on both surfaces,
reduced-motion honored on the switch. Tests: 209 green. Export/delete:
n/a. Truthfulness: the toggle does exactly what it shows; no mocked
controls. Language rules: no new user-facing labels beyond "Dark
theme".
