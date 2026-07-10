# Site-wide sky-glass redesign (2026-07-10)

Pete's direction: make the whole site (outside the Experience film) share the
Living Résumé's summit-sky scene and frosted-glass language, keep only the
light theme, fix the Experience page's background continuity, and rebuild
My Story, Skills, and Projects as cinematic showcases.

## Implemented

### Foundation
- One fixed `.site-sky` summit-sky backdrop (base.html) behind every page;
  the Experience film and the résumé route hide it and keep their own scenery.
- Light theme only: `slate-light` is forced on every route except
  `/experience`; the theme picker, theme-preview.js, the stone-photo pipeline,
  surface-slate, and the gray/stone/paper-slate palettes were deleted
  (~1,150 lines of CSS). The homepage's dark variant went with them.
- `sky-glass.css` converts the site's card families (`ps-card`, `preview-*`,
  contact/interview/slate-feed families, profile band, tab strip, footer) to
  the résumé's frosted glass, adds a soft white halo to on-sky headings, a
  reusable `.sky-haze` veil for full-sky hero text, and shared `[data-reveal]`
  scroll reveals (sky-reveal.js) with a reduced-motion opt-out.

### Experience page continuity
- Every scene's photo and veil are now viewport-fixed and clipped to their
  section (`clip-path: inset(0)` windows). Scrolling inside a chapter leaves
  the scenery motionless; a new chapter wipes in at its boundary. The hero and
  Connect share one aurora photo AND one veil, so that seam is invisible; the
  work trio keeps its shared backdrop. Parallax drift and the Ken Burns hero
  animation were removed (fixed layers must not move); mobile gets the same
  behavior via the missing `-m` image override for Connect.

### Showcase rebuilds (same routes, same facts)
- **My Story** (`my_story.html` + `story-cinematic.css`): a personal film —
  full-sky serif opening with value orbs and the photo collage; six life
  chapters on a glowing jewel ribbon (Domino's years, healthcare, back to
  school at 36, the COVID-era Robins AFB start, industry, the January 2027
  Ph.D.); a serif stat band (36 / 10 states / 10 countries / 100 miles);
  the eight "outside of work" cards; the rotating fun-facts strip; the shared
  values partial; Always Building; and the completed-goals slate. Everything
  factual comes from the previous page or the approved knowledge base.
- **Skills** (`skills.html` + `skills-cinematic.css`): the proof
  constellation — every public skill is a glossy jewel orb sized by its
  evidence count, grouped by category; selecting an orb opens a frosted
  evidence panel with employer citations (aria-expanded/controls, Escape and
  outside-click close). Replaces the resume.css card grid on this page.
- **Projects** (`work.html` + `projects-cinematic.css`): the build log — the
  Interactive Resume leads as a cinematic case with a real screenshot of the
  live build (`static/images/projects/living-resume-build.jpg`); the three
  planned concepts follow as jewel-edged bench cards. All four projects keep
  their original copy, statuses, and stacks; the tab switcher (work.js) is no
  longer needed on this page.

## Validation
- 5/5 unit tests; résumé page 9/9 interaction checks and 5/5
  zoom/touch/overflow/focus checks (unchanged route, shared CSS verified).
- All 14 routed pages screenshot-verified at 1440×900 with zero horizontal
  overflow and zero JS errors; showcase pages also verified at 390×844.
- Experience page verified: backgrounds pinned (no containing-block
  ancestors), hero→connect seam invisible, no console errors after the
  parallax removal.

## Notes
- resume.css/resume.js now serve only the orphaned `templates/resume.html`;
  candidates for deletion in a future cleanup.
- The old four-theme system is gone by design; re-adding themes would start
  from the sky-glass tokens.
