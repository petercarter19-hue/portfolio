# PS-BRAND-NAV-001 — Iris Foundry, navigation, About (delivered 2026-07-16)

## What landed
- **Iris Foundry tokens** in style.css: canvas #F7F4EE, surface #FFF, ink
  #191821, muted #5D5766, warm border #E6E0D4, primary iris #5A2D82 (+strong
  /soft), bronze #B87422 with text-safe #8A5410, success teal #16705F, and
  room accents (teal/plum/amber/pine/ultraviolet with strong+soft pairs).
- **Room plumbing**: base.html sets `data-room` on <body> from the route
  (home=iris, work/resume/skills=bronze, interview=teal, my-story=plum,
  slate-board=amber, community/feed-preview=pine, default=iris). Header
  active links, profile-tab active states, and marketing primary buttons
  use `--ps-page-accent`. Global header/footer surfaces warmed to canvas.
- **Newsreader** replaces Source Serif 4 as the editorial serif site-wide
  (v1.2 Iris Foundry standard); base.html font pipeline updated.
- **Navigation**: About PeerSlate removed from the header (footer link
  "Why PeerSlate" added on every page); public sub-header tab Evidence →
  **Work** (→ /petec/projects; the skills page stays reachable and is
  retitled "Skills in practice").
- **Why PeerSlate**: /peerslate rewritten in the approved eight-part
  mission-led order; recruiter value appears only as a late secondary
  outcome; OG/meta updated.
- **Language migration** (user-facing): skills page, resume2, homepage
  scenes, experience page, daily slate, header search records —
  Evidence/evidence-backed/proof → Skills in practice / Grounded in
  approved work / Featured achievement / See sources / Supporting work.
  Internal data-model names (evidence_items etc.) intentionally kept
  (rule 17: trust infrastructure stays).
- **Guardrail tests extended**: no Evidence label in nav templates; no
  About PeerSlate in the header nav; footer Why link present.

## Decisions
- The blue "light orbit" backdrop asset remains until a warm-canvas
  backdrop is approved — swapping the atmosphere is an asset decision for
  Pete, not a token change. Solid surfaces (header, footer, canvas
  fallbacks) are already warm; flagged as the one visible remnant.
- Deep page-internal blues (resume constellation viz, corkboard notes,
  cinematic pages) keep their tuned palettes this pass; room accents are
  applied at orientation/action level per rule 76 ("neutral by default,
  expressive at the focal point"). Full per-page repaints are follow-ups.
- Logged-out marketing nav keeps the existing real destinations; the
  Bible's "Create My Slate / How It Works" nav arrives with the auth
  phase when those destinations become real (recorded conflict, rule 85).
- Feed design preview page keeps its approved preview palette (it is a
  labeled design artifact, not a product room).

## Verification
- Full suite: **202 tests OK** (updated expectations: header without
  About, Work tab, migrated strings; new nav guardrails).
- Browser: homepage renders warm canvas + iris accents; /peerslate renders
  the new eight-part page; /the-slate header active link = pine #1F5C3D;
  header bg = #F7F4EE everywhere checked.

## Checklist (docs/INITIATIVE_CHECKLIST.md)
Canonical objects: none touched (visual/copy/navigation only). Owner/
audience: unchanged. Private/public: unchanged. AI: unchanged. Provenance:
data-model names kept. Accessibility: focus/contrast preserved — accent
values chosen ≥4.5:1 on white for text use; bronze reserved for
highlights. Tests: green. Export/delete: n/a. Truthfulness: no new
controls; nothing mocked.
