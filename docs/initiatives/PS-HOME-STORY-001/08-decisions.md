# Decisions — mockup vs. reality judgment calls

Pete authorized "use your best judgment too if needed" (2026-07-16). Every
deviation below exists to keep the page honest, functional, and inside the
Bible's rules.

1. **Global header**: base.html header reused untouched (per the brief). None
   of the mockup-only links (How It Works, Explore a Slate, For Teams,
   Pricing, Create My Slate) are added.
2. **"Trusted by" logo row dropped** (hero mockup showed Google/Microsoft/
   amazon/Deloitte/NVIDIA). PeerSlate is pre-launch; displaying those marks
   would fabricate endorsement — the Bible bans implying what the backend
   (or reality) doesn't enforce. Replaced with an honest audience line.
3. **Voice hero CTAs** resolve to the real, labeled Feed design preview:
   "Talk about what happened" → `/feed-living-stream?state=voice` (a working
   voice-capture demo), "Try a sample" → `/feed-living-stream`. No invented
   `/signup` or `/create` routes.
4. **Hero destination cards** (Private Journal / Project Update / Skill
   Evidence / Interview Story / Future Goal) link to the real experiences:
   My Slate journal, Work, Evidence, Interview Studio, Slate Board. Nothing
   looks clickable without being clickable.
5. **"Your week, made visible" strip**: illustrative timeline is decorative
   (aria-hidden); "See a sample week →" links to the real Daily Slate.
6. **Résumé scene card** renders from `resume_data.json` (same source as the
   live résumé). The mockup's Summary/Impact/Skills/Experience/Credentials
   tab strip is omitted — fake tabs would be dead controls; the four-step
   "From career impact to the story behind it" strip links to real
   destinations instead.
7. **Story scene** follows the PS-HOME-STORY-001 brief exactly: live act
   labels, brief-approved chapter preview lines, live Polaroid captions
   ("100 miles. 10 days. One goal." / "Places that changed me." / "Always
   get outside.") — NOT the mockup's illustrative captions. "Read the
   chapters →" deep-links to the verified `#act-becoming` anchor.
8. **Act index** is non-interactive (per brief allowance), ordered-list
   semantics, full titles visible, Act One highlighted in Product Indigo.
9. **No new JS**: no scroll reveals, no carousels, no IntersectionObserver.
   The only motion is CSS hover/focus polaroid straightening, disabled under
   `prefers-reduced-motion`. Page is fully usable with JS disabled.
10. **Old homepage kept** at `/experience` (existing precedent) as the
    rollback/comparison path; `/` now renders the new page.
11. **Fonts**: Source Serif 4 (already loaded site-wide) is the editorial
    serif; Inter for UI. No new font requests (perf rule) — the mockups'
    serif is matched by the site's own display face.
12. **Ph.D. status language**: `resume_data.json` marks it "Admitted,
    expected January 2027 start" — the scene says exactly that; no progress
    percentages are invented.
