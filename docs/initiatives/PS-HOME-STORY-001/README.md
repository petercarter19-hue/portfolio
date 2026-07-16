# PS-HOME-STORY-001 — Homepage overhaul (three-scene replacement)

**Scope note (Pete, 2026-07-16, verbal):** the original package covered only the
My Story + Future scene. Pete explicitly combined the sections — "a complete
overhaul of the home page… a clean three-section replacement" — and authorized
implementation and deployment without a review pause ("Don't wait for me.
Don't ask. You have permission."). This package therefore delivers the full
new homepage in the intended page order:

1. Voice-first "Say what happened" hero
2. Living Résumé scene
3. My Story + Future scene (the original PS-HOME-STORY-001 spec, followed in detail)
4. Final invitation band + existing shared footer

**Non-negotiables preserved:** the shared global header from `base.html` is
reused untouched (no mockup-only nav links); all CTAs resolve through existing
Flask endpoints/route helpers; all content comes from the existing
server-side sources (`static/data/story_data.json`, `static/data/resume_data.json`);
no second source of truth; no new JS framework; existing footer.

| File | Purpose |
|------|---------|
| 01-requirements.md | What each scene must contain |
| 02-current-state.md | Repository inspection findings |
| 03-architecture.md | Templates, view models, CSS scoping |
| 05-security-privacy.md | Content approval + privacy rules honored |
| 06-test-plan.md | Automated + manual verification |
| 07-implementation-plan.md | Ordered steps |
| 08-decisions.md | Mockup-vs-reality judgment calls |
| 09-verification.md | Commands run + results (filled during build) |
| 10-handoff.md | Final handoff (filled at completion) |
