# Architecture

- Route: `home()` renders `templates/homepage.html` (new). `/experience`
  keeps the previous cinematic page (existing comparison/rollback pattern).
- View models built server-side in `app.py` (`_build_home_context()`):
  - `story_preview`: acts 1–4 pulled by card id from the SAME
    `static/data/story_data.json` used by My Story (no second copy).
  - `resume_preview`: metrics/roles/skills/credentials/proof pulled by id
    from `static/data/resume_data.json` (same source as the live résumé).
- Templates: `templates/homepage.html` + partials
  `templates/partials/homepage/_voice_hero.html`, `_living_resume_scene.html`,
  `_story_future_scene.html`, `_invite_band.html` (matches repo's partials
  convention; no micro-component explosion).
- CSS: `static/css/homepage-scenes.css`, all rules scoped under `.home-v3`
  (`.ps-home` belongs to the old homepage). BEM-ish classes:
  `.home-v3 .hv-hero`, `.hv-resume`, `.hv-story`, `.hv-invite`.
  Body classes: `peerslate-home-page home-v3-page` (light header treatment
  reused; page excluded from editorial-glass at `/` as today).
- No JavaScript added. Icons are inline SVG. Fonts: Inter + Source Serif 4
  (already loaded by base.html).
- Images: existing `static/images/story/*` assets with their `-m` variants
  via `srcset`; explicit aspect-ratios reserve space; `loading="lazy"` for
  everything below the hero.
