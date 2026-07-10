# PS-FEAT-001 approved visual implementation

- **Branch / base commit:** `codex/ps-feat-001-living-resume`; latest committed base is `bec2d86 PS-FEAT-001: implement approved living resume`.
- **Preview route:** `/_internal/living-resume-v2`, local-only unless `ENABLE_DESIGN_SYSTEM_PREVIEW=1`.
- **Approved references used:** `static/images/mockups/resume1.png` and `static/images/mockups/reume2.png` only.
- **Public promotion:** `/resume` and `/petec/resume` now render the approved Living Résumé; the public PDF remains available from the Documents section. The internal route remains gated and no-indexed.

## Implemented

- Rebuilt the preview as one continuous real-data page in the PeerSlate application shell.
- Made the Living Résumé Ledger the hero, with the seven-chapter timeline integrated into the Ledger frame.
- Bound every Ledger chapter, outcome, skill, evidence reveal, education record, contact link, PDF link, and role-specific AI prompt to Pete's approved public résumé data.
- Continued the same page into the Career Constellation after a generous chapter transition.
- Matched the approved Constellation composition with the editorial intro, two career arcs, education/experience/credential/future nodes, evolution callout, project-management evidence, skill chips, outcomes rail, and quote/traits footer.
- Added roving tab focus and Arrow/Home/End keyboard behavior. Constellation nodes return to the corresponding Ledger chapter and focus its tab.
- Preserved visible focus, forced-colors support, reduced-motion behavior, no-indexing, and local/feature-flag route isolation.
- Added true responsive reflow: the Ledger timeline and Constellation become vertical stories on narrow screens instead of compressed desktop diagrams.
- Expanded the Ledger into one long, continuous résumé with Overview, Experience, Education, Skills & Evidence, Development, and Documents sections. Every rail item is an in-page anchor; none opens a separate résumé page.
- Made the left section rail sticky throughout the full résumé. A compact persistent index takes over when the reader reaches the Constellation, with synchronized current-section highlighting.
- Made Ask Pete AI continuously available through a job-specific upper-right Ledger button and the always-visible floating launcher. Both open the existing grounded assistant.
- Added a route-local SVG icon system for contact details, section navigation, timeline milestones, outcome cards, Constellation nodes, metrics, and traits.
- Increased visual fidelity with the Ledger's layered glass frame and luminous career ribbon plus the Constellation's glowing dual paths, central junction, dotted evolution connector, future arrow, selected skill state, and icon-led outcomes rail.
- Expanded visible role evidence while correcting `$9.1M` CAM attribution to L3Harris, in line with Pete's approved source data.
- Promoted the shared Living Résumé renderer to both public résumé URLs while keeping preview-only labels and robots metadata exclusive to the gated internal route.

## Validation

- `venv/bin/python -m unittest discover -s tests` - passed, 5 tests.
- `jq empty static/data/resume_data.json static/data/living_resume_fixtures.json` - passed.
- Bundled Node `--check static/js/living-resume-v2.js` - passed.
- `git diff --check` - passed.
- Route smoke test - HTTP 200 for `/resume`, `/petec/resume`, and `/_internal/living-resume-v2`.
- Public-route checks confirm the Living Résumé title and sections render without the internal preview label or `noindex,nofollow` metadata.
- Browser interaction checks passed for tab selection, Arrow navigation, skill evidence, exact metric-to-evidence focus, and Constellation-to-Ledger navigation.
- Browser layout checks passed at 1440x900 and 390x844 with no page-level horizontal overflow, clipped Constellation labels, or desktop node-copy collisions.
- Browser scroll checks passed for all in-page jumps, sticky desktop/mobile section indexes, dock handoff at the Constellation, synchronized active states, and persistent AI visibility/opening from the middle of the page.

## Screenshots

- `docs/implementation-reports/screenshots/PS-FEAT-001/desktop-ledger-1440x900.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/desktop-overview-1440x900.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/desktop-constellation-1440x900.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/desktop-experience-1440x900.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/desktop-education-1440x900.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/desktop-skills-1440x900.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/mobile-ledger-390x844.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/mobile-constellation-390x844.png`
- `docs/implementation-reports/screenshots/PS-FEAT-001/mobile-education-390x844.png`

## Refinement pass 1 — Ledger vertical rhythm (2026-07-10)

Feedback: the résumé body sections (Overview, Experience, Education, Skills & Evidence, Development, Documents) carried too much empty vertical space, and the left section rail showed a large blank gap between its links and the last-updated note.

- Tightened `.lr-vertical-section` padding from 5rem to 2.75/3rem and section-header margins; reduced section headings from 2.6rem to 2rem so they sit on one or two lines instead of three.
- Reduced experience-row padding (2.5rem to 1.5rem), list spacing, credential-card padding, evidence-index padding, and the Documents/page tail paddings (6rem/10rem to 3rem/5rem).
- Rebuilt the rail/detail seam as two separate rounded cards with a small gutter: the rail no longer stretches to a forced 37rem with `space-between`, so the last-updated note tucks directly beneath the section links.
- Dropped the ledger-panel forced min-height from 37rem to 24rem so short chapters (education) no longer trail dead space, while chapter switches remain visually stable.
- Restructured the Key Outcomes cards to match the approved mockup: the metric value now sits beside the icon with the label under it and context text full width, which shortens the cards.
- Applied matching mobile reductions (section padding 4rem to 2.5rem, tighter headers and rows).
- Result at 1440x900: page height 6478px to 5329px (-18%); ledger frame 5014px to 3945px (-21%). Content unchanged - only spacing, type scale, and card composition.
- Validation: 5/5 unit tests pass; desktop and mobile screenshots refreshed below.

## Refinement pass 2 — Ledger-to-Constellation transition and Constellation (2026-07-10)

- The Career Constellation now materializes during vertical scroll: an IntersectionObserver reveals the scene with a transform/opacity entrance. The hidden pre-state only applies when JavaScript runs, and reduced-motion users always see the scene immediately.
- Added a bidirectional selected state: the Constellation node for the active Ledger chapter carries a white halo ring, updated on every chapter change (tab click, arrow keys, outcome-metric jumps, node clicks). The default chapter is synced on load.
- Improved connection clarity where node copy crosses the glowing career path with a soft dark text-shadow in the night-side region.
- Finished the chapter transition with a glowing cyan terminus dot on the descent line.
- Node-to-Ledger navigation, keyboard operation, the mobile structured vertical story, and reduced-motion behavior verified in-browser: 9/9 scripted interaction checks pass (initial node sync, tab/panel/node sync, Arrow/Home roving focus, scroll reveal, node-to-chapter focus return, single-open evidence, reduced-motion visibility, mobile constellation structure).
- Validation: 5/5 unit tests pass; `node --check` clean; desktop and mobile screenshots refreshed.

## Refinement pass 3 — Sky-glass restructure (2026-07-10, per Pete's direction)

Pete approved a structural evolution beyond the original mockups: separate the résumé into floating glass pieces over the Experience page's summit-sky backdrop, with Experience-page-style breathing room between sections.

- Page backdrop is now `static/images/cinematic/together-summit.jpg` (the blue-sky scene from the bottom of the Experience page; mobile uses the `-m` variant), fixed behind the story with a soft light veil.
- The identity card (portrait, name, positioning, contact, career-ribbon quote) is detached from the Ledger frame and floats alone directly under the site header, removing the doubled identity-above-timeline feel.
- The chapter timeline is its own detached glass strip below the identity card.
- The Ledger frame now holds only the section rail and the selectable chapter detail (Overview).
- Experience, Education, Skills & Evidence, Development, and Documents are standalone glass bubbles with about a third of a viewport of sky between them (`min(28vh, 17rem)`, scaled down on smaller screens), each revealing gently on scroll like the Experience page but less dramatic. The reveal is JavaScript-gated and disabled under reduced motion.
- All tiles and cards are translucent (frame, rail, detail, outcome tiles, impact strip, credential cards, evidence rows) with backdrop blur, so the sky shines through while palette colors stay intact.
- Existing behavior preserved: tablist keyboard interaction, chapter/node syncing, dock handoff, mobile structured fallback, PDF path, and both public routes. 5/5 unit tests and 9/9 scripted browser interaction checks pass; screenshots refreshed.

## Refinement pass 4 — Identity split, persistent rail, opaque bubbles (2026-07-10, per Pete's direction)

- The portfolio profile band (avatar, "Open to conversations" chip, name/title block) no longer renders on the Living Résumé page — the base template's new `profile_band` block lets this page suppress it while every other portfolio page keeps it, and the profile tab strip stays for navigation. This removes the doubled Pete Carter identity that production visitors saw on `/petec/resume`.
- The Living Résumé identity is now two side-by-side glass cards under the header: a condensed who-card (portrait, name, positioning, summary) and a reach-card (location, email, LinkedIn, career-ribbon quote), stacking on smaller screens.
- The outer ledger frame layer is gone. The section rail is its own floating card that stays sticky beside the entire résumé, and the chapter detail (Overview) is its own bubble — the first in a single right-hand column where Experience, Education, Skills & Evidence, Development, and Documents all share the same width, keeping the sky gaps and scroll reveals between them.
- All content cards are now near-opaque glass matching the identity and timeline treatment.
- Skill evidence popovers dismiss automatically on any outside click, in addition to Escape and single-open behavior.
- Validation: 5/5 unit tests, 9/9 browser interaction checks, 5/5 zoom/touch/overflow/focus checks, `node --check` clean; screenshots refreshed from `/petec/resume` (the production route, with the tab strip).

## Refinement pass 5 — Slim chrome, colorful timeline, centered rail, flip skills (2026-07-10, per Pete's direction)

- Site header is slimmer on this page only (52px bar, smaller logo/Sign-In/theme controls); other pages keep the standard header.
- Identity cards sit higher; the reach card now centers the contact rows beside a square career-ribbon quote tile.
- The timeline lost its glass card and sits directly on the sky, with kind-colored markers (indigo education, blue experience, amber credentials, cyan future), larger labels, and darker secondary text with a soft light halo for contrast.
- The section rail now glides to the vertical center of the viewport while the reader scrolls and releases with the bottom of Development, leading straight into the Constellation. A quiet Résumé PDF button in the rail preserves the ATS/download path.
- Section bubbles are more see-through again (66/54% glass with blur) per Pete's request to see the sky through them.
- Experience is ordered most-recent-first (Northrop Grumman, L3Harris, DoD/USAF), shows up to seven accomplishment bullets per role, and adds per-role skill chips drawn from the shared skill data.
- The Education heading sits on one line.
- Skills & Evidence is a compact grid of 18 flip cards (three even rows): front shows the skill and proof-point count, clicking flips to up to two evidence bullets; one card flips at a time, outside click or Escape restores, reduced-motion gets an instant swap. Life Cycle Management, EVMS, and Provisioning were promoted to featured to complete the grid.
- The Documents section is removed per Pete; its PDF link lives in the rail (tests updated accordingly).
- Validation: 5/5 unit tests, 9/9 interaction checks, 5/5 zoom/touch/overflow/focus checks, flip/rail-centering/release verified in-browser; screenshots refreshed (desktop-development view added).

## Refinement pass 6 — Merged identity+AI card, richer panels (2026-07-10, per Pete's direction)

- The two identity cards are now one card: left holds the portrait, name, positioning, a smaller summary, and the contact row; right is an "Ask Pete AI" panel — a recruiter-view / career-tour / top-skills pill row plus a longer "Ask anything" bar. The career-ribbon quote is removed.
- The floating Ask Pete AI launcher is hidden while the identity card is on screen and fades in only after the reader scrolls past it. This reuses the existing chatbot.js anchor behavior by tagging the identity AI panel `.resume-ai-panel` and dropping the override that pinned the launcher visible.
- Each chapter panel drops its own Ask Pete AI button and moves the role title (e.g. "Lead Systems Engineer / Systems Engineer") to the right of the header. The panel and its Key Outcome cards are taller for a more spacious read.
- Every experience chapter now renders exactly five Key Outcome cards: metrics first, then filled from accomplishment bullets (skipping ones a metric already cites) so L3Harris and Northrop read as full as DoD. Core-skill chips expanded from five to eight per chapter.
- All glass cards (bubbles, rail, outcome cards, skill cards, identity) are more see-through; the gap between sections was tightened (`min(15vh, 9rem)`); the Skills & Evidence flip-card font is larger.
- The default-open first skill popover was removed so the panel loads clean over its outcomes.
- Validation: 5/5 unit tests (updated for the removed panel button), 9/9 interaction checks, 5/5 zoom/touch/overflow/focus checks; launcher hide/reveal confirmed in-browser; screenshots refreshed.

## Refinement pass 7 — Per-job experience cards, tighter section rhythm (2026-07-10, per Pete's direction)

- The Experience section is no longer one bubble. It is a thin intro card ("The work, in full context.") followed by one rounded glass card per job, sitting close together with a slim strip of sky between each. This is generic: N jobs render as N cards, so it holds for any profile's history.
- The vertical gap between the résumé sections (Overview → Experience → Education → Skills → Development) is cut by roughly a third via a single `--lr-gap` custom property (`min(10vh, 6rem)` desktop, scaled at each breakpoint), so scrolling between sections feels tighter without losing the floating-card rhythm.
- Validation: 5/5 unit tests, 9/9 interaction checks, 5/5 zoom/touch/overflow/focus checks; page height at 1440 dropped from ~6,443px to ~5,876px purely from spacing; screenshots refreshed.

## Remaining visual differences

- The approved placeholder identity is replaced by Pete's real name, photo, contact links, employers, dates, evidence, metrics, and education data.
- The implementation uses a consistent route-local pictogram set rather than reproducing the mockup's bespoke Air Force, L3Harris, and Northrop brand artwork.
- Real role titles and evidence vary in length, so label widths and connector curves adapt instead of using fixed screenshot coordinates.
- The PeerSlate navigation and Ask Pete AI control remain visible around the experience because this is the real application route.
- The Ledger and Constellation are intentionally taller than a single viewport. Content is not compressed to reproduce the 1672x941 mockup boundary.
- Pearlescent texture, sparkle density, and exact ornamental details are simplified so the design remains performant and responsive.

These differences preserve real application functionality, accessibility, dynamic data, and responsive behavior; the approved hierarchy, composition, spacing, typography, palette, and continuous Ledger-to-Constellation architecture are substantially matched.
