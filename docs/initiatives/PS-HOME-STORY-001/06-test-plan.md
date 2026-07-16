# Test plan

Automated (tests/test_homepage_scenes.py):
- `/` returns 200 with exactly one h1 and the three scene h2s.
- Header links unchanged at `/` (Pete's Slate, Community, Interview Studio,
  About PeerSlate, Ask AI, Sign In) — existing test_navigation still passes.
- CTAs resolve: my-story, slate-board, resume, skills, feed preview,
  daily slate, `#act-becoming` anchor present on the My Story page.
- Live Polaroid captions present; banned mockup captions absent
  ("First marathon — 2018", "Bali — reset & refocus", "Hawaii — perspective").
- Approved future content present (Ph.D., USA, January 2027); banned
  browser-local board notes absent (grocery/guitar/second home).
- No mockup-only nav links (How It Works, For Teams, Pricing, Create My
  Slate, Explore a Slate) anywhere at `/`.
- Full existing suite passes.

Manual (browser): 1440/1280/1024/768/430/390/320 widths, 200% zoom,
reduced-motion, keyboard focus pass, no horizontal overflow, no console
errors; screenshots at desktop/tablet/mobile in 09-verification.md.
