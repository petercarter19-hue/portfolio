# Handoff — PS-HOME-STORY-001

**Implemented:** the full three-scene homepage at `/` (voice hero, Living
Résumé scene, My Story + Future scene, invitation band), per Pete's combined
scope. The previous cinematic homepage is untouched at `/experience`.

**Reused:** base.html global header/footer (unchanged); existing URL helpers
(`portfolio_*_url`, `portfolio_url`, `url_for`); existing fonts (Inter,
Source Serif 4); existing story/résumé image assets with their `-m` variants
and authored alt text.

**Content sources:** `_build_home_context()` in app.py pulls approved cards
by id from `static/data/story_data.json` and `static/data/resume_data.json`
— the same sources behind the live My Story and résumé pages. No second
copy of Pete's content exists.

**Files changed:** app.py (home route + view models), templates/homepage.html,
templates/partials/homepage/_voice_hero.html, _living_resume_scene.html,
_story_future_scene.html, _invite_band.html, static/css/homepage-scenes.css,
tests/test_homepage_scenes.py, docs/initiatives/PS-HOME-STORY-001/*.

**Intentionally unchanged:** global navigation, My Story page, Slate Board,
résumé pages, auth, Ask AI, footer, Azure configuration, database.

**Deviations from mockups:** see 08-decisions.md (no fabricated trusted-by
logos; no dead tab strip on the résumé card; live Polaroid captions; act
index after the copy column in mobile reading order).

**Tests:** 188/188 passing (09-verification.md).

**Rollback:** revert the merge commit, or point `home()` back to
`experience.html` (one line). No data, schema, or Azure changes.
