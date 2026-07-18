# PS-RESUME-PUBLIC-REFINE-001 — Measured evidence

Base `origin/main` `6f9f22c34d791dac2466a957450dfc18e9285176`. Headless Chromium
(Playwright), reveal blocks forced visible for the static full-page captures;
geometry measured from `getBoundingClientRect` (opacity-independent).

## Perceived desktop compression (document scrollHeight)

| Viewport | Before | After | Δ | Reduction |
|---|---:|---:|---:|---:|
| 1440×900 (desktop) | 5419 px | 4924 px | −495 px | **−9.1%** |
| 1920×1080 (desktop) | 5636 px | 5169 px | −467 px | **−8.3%** |
| 390×844 (mobile) | 14219 px | 13273 px | −946 px | −6.6% |

Both desktop viewports land in the Roadmap's ≈8–9% perceived-compression band.
The reduction comes from spacing/grouping and collapsed optional depth, not from
smaller body type or deleted meaning (all approved content still ships in the DOM
and/or the on-demand chapters and the ATS PDF).

Where the desktop reduction comes from (1440×900):
- Opening identity de-duplication + trimmed summary floor (removed the dead space
  under the identity; summary now content-bound at 522 px, was floored at 533 px).
- Experience: preview bullets moved to the on-demand chapter → cards 735→590 px.
- Credentials: 3-record preview + tighter rows → cards 640→593 px.
- Section rhythm: inter-section gap, section padding, heading margins, impact tile
  height all tightened a step.

## Accessibility / interaction / responsive verification

Driven headless (see `a11y-verification.txt`): 26/27 automated checks pass.
The one reported FAIL is a false negative — the check hard-coded a portless
canonical URL, but the dev server correctly emits
`http://localhost:5000/petec/resume` (confirmed separately; unit tests
`test_canonical_resume_tag_points_directly_to_the_rendered_route` and the
forwarded-HTTPS test pass).

Confirmed:
- Experience "View Full Chapter": default `aria-expanded=false` + hidden region →
  opens with full-record bullets (7), `aria-expanded=true`, focus moves into the
  chapter; Escape closes and restores focus to the toggle.
- Credentials "Open category": education opens to the full 4-record set (preview
  shows 3), correct `aria-expanded`, focus into panel.
- Skills: compact overview → panel reveals the ≤3 strongest approved proof points.
- Canonical URL + legacy `/petec/resume2 → /petec/resume` redirect intact; Ask AI
  panel, Contact, and ATS/PDF path all present; Career Constellation present.
- 200%-zoom proxy (720-CSS-px viewport): no horizontal page scroll.
- Reduced motion: chapter disclosure still functions.
- No-JavaScript: sections render in logical order (summary→impact→skills→
  experience→credentials→constellation); role summaries, the 12 skill names, the
  Contact action, and the ATS PDF fallback are all visible without JS.

## Test suite

`python -m pytest` — 264 passed, 132 subtests passed, 1 warning (pre-existing
flask-limiter in-memory-storage notice). Includes the three reserved résumé
suites, `test_site_rules.py`, and `test_governance_pointers.py`.
