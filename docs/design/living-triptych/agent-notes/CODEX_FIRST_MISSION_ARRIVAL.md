# Codex First Mission — Repository Audit and 01 Arrival Vertical Slice

**Date:** 2026-07-12  
**Agent:** Codex  
**Branch:** `experiment/living-triptych-codex`  
**Baseline commit:** `c0a015a`  
**Prototype route:** `/petec/atrium`  
**Production Overview status:** unchanged

## Outcome

The first working Living Triptych vertical slice now exists on an isolated,
`noindex` Atrium route. It renders one semantic installation with three
overlapping glass slabs, authentic Story photography, an authentic Projects
build fragment, a résumé timeline derived from the canonical résumé fixture,
shared identity in the overlap, pointer and keyboard focus selection, direct
destination links, and the existing evidence-grounded Ask AI behavior relabeled
as **Ask the Slate**.

The current `/petec` Overview and `index.html` were not replaced or modified.

## 1. Repository and Architecture Audit

### Repository state

- The active implementation worktree is `/Users/petercarter/peerslate-codex`.
- It is isolated from Claude's worktree at `/Users/petercarter/peerslate-claude`.
- The Codex worktree was clean before this mission.
- The branch has no front-end build step or package manifest.
- GitHub Actions are not the publishing path. Azure DevOps is the documented
  deployment path, but this experiment was not deployed.

### Framework and rendering model

- Flask 3.1 application in a single `app.py` module.
- Jinja server-rendered templates.
- Vanilla JavaScript for route-local browser behavior.
- Global styles are large and layered; page-scoped CSS is the safest extension
  seam.
- No React, Vue, Storybook, GSAP, Three.js, Canvas/WebGL framework, ORM,
  database, or central client state store.
- Existing JSON fixtures provide structured Story and résumé content.
- Projects currently combine one structured project record with additional
  template-authored content.

### Existing Overview and shared-shell map

- `app.py` — routes, context-injected URLs, fixture loading, résumé view models.
- `templates/index.html` — current profile Overview at `/petec`.
- `templates/base.html` — global header, profile tabs, footer, search, chat,
  shared scripts, and tablet viewport behavior.
- `templates/partials/profile_tabs.html` — canonical six-item profile tabs.
- `templates/partials/profile_shell.html` — profile identity band.
- `templates/partials/portfolio_ai_search.html` — reusable semantic Ask form.
- `static/css/style.css` — global design generations and shared chrome.
- `static/css/sky-glass.css` — site-wide light sky/glass override layer.
- `static/js/chatbot.js` — shared Ask form and chat-panel behavior.
- `static/js/mobile-nav.js` — mobile cloning of profile navigation.
- `tests/test_navigation.py` and `tests/test_resume2.py` — current navigation
  contracts.

### Authentic content sources

#### Story

- `static/data/story_data.json`
- `static/images/story/`
- Values used: Curious by nature, People first, Purpose driven.
- Four existing photographs are rendered from fixture paths. No childhood photo
  matching the generated mockup exists.

#### Projects

- `static/data/resume_data.json` → `applied_projects`
- `templates/work.html`
- `static/images/projects/living-resume-build.jpg`
- The Arrival slab uses the real Living Résumé build screenshot and project
  progress fragments. The visible descriptor says “evidence-grounded,” not
  “verified.”

#### Résumé

- `static/data/resume_data.json`
- Timeline chapters are joined from `living_resume.events` and `career_roles`.
- Evidence metrics are selected by the existing
  `career_highlight_metric_ids` configuration.
- The retired MICAP example is explicitly filtered out.
- No employer, role, date, or metric is hardcoded in the reusable slab template.

### Design-system evidence

- Approved Foundation C typography: Newsreader for cinematic/editorial display,
  Inter for controls and product content.
- Approved colors used by the slice:
  - Product Indigo `#4F5BD5`
  - Connection Azure `#4EA3FF`
  - AI Cyan `#2EC8D3`
  - Evidence Amber `#D7A33E`
  - Midnight Ink `#0A1B36`
  - Cloud White `#F6F8FC`
- `static/css/design-system/tokens.css` was not imported because it is an older
  Foundation A artifact containing Playfair and retired pink/violet semantics.

### Important repository risks discovered

1. `base.html` forces most real tablets into a synthetic 1280px viewport. The
   Atrium path is now exempt so tablet/mobile CSS can actually run.
2. Profile tabs previously rendered on every non-root route. Atrium is excluded
   because it uses the global temporary header link and must remain one dominant
   object.
3. Adding Atrium to the six canonical profile tabs would change the current
   résumé navigation contract and mobile cloned bar. The temporary link therefore
   lives in the global header.
4. `style.css` contains multiple generations of global and profile overrides.
   The new implementation uses route-scoped `.living-triptych-page` selectors.
5. `app.py` requires `ANTHROPIC_API_KEY` at import time, even for route tests.
   Test commands use a harmless placeholder and do not call the remote API.
6. The mountain background asset is large and no approved atrium background
   exists. Arrival uses CSS architecture, light, and floor layers instead.

## 2. Relevant Implementation File Map

### New

- `templates/atrium.html` — semantic Arrival composition.
- `static/css/living-triptych.css` — route-scoped environment, glass slabs,
  depth states, tablet/mobile, reduced-motion, forced-colors, and solid fallbacks.
- `static/js/living-triptych.js` — small interaction-state controller.
- `tests/test_atrium.py` — route, semantic structure, authentic content,
  navigation, and fallback assertions.
- `artifacts/living-triptych/arrival-1600x900.png`
- `artifacts/living-triptych/arrival-1440x900.png`
- `artifacts/living-triptych/arrival-mobile-390x844.png`
- `docs/design/living-triptych/agent-notes/CODEX_FIRST_MISSION_ARRIVAL.md`

### Modified

- `app.py`
  - adds the canonical Atrium URL to shared navigation;
  - adds `/atrium` and `/petec/atrium` routes;
  - builds a compact Triptych view model from existing fixtures;
  - canonicalizes production `/atrium` to `/petec/atrium`.
- `templates/base.html`
  - adds the temporary global-header Atrium link and search entry;
  - prevents double-active Example Slate state on Atrium;
  - excludes Atrium from the profile-tab row;
  - exempts Atrium from the synthetic tablet viewport.
- `templates/partials/portfolio_ai_search.html`
  - adds optional label and placeholder variables while preserving existing
    defaults.

## 3. Component and Interaction-State Architecture

### Server view model

```text
triptych
├── identity
│   ├── name
│   ├── first_name
│   ├── dimensions
│   └── summary
├── story
│   ├── title / dimension / lead
│   ├── values[]
│   ├── images[]
│   └── destination
├── projects
│   ├── title / dimension / lead
│   ├── featured
│   ├── featured_label
│   ├── signals[]
│   └── destination
└── resume
    ├── title / dimension / lead
    ├── chapters[]
    ├── metrics[]
    └── destination
```

### Semantic component tree

```text
TriptychAtrium
├── TriptychIdentity (single h1)
├── TriptychPanels
│   ├── StorySlab (article + focus button + real link)
│   ├── ProjectsSlab (article + focus button + real link)
│   └── ResumeSlab (article + focus button + real link)
├── AccessibleStatus
├── ArrivalStageLabel
└── AskTheSlate (shared portfolio AI form)
```

### Client state

```text
state = {
  committed: null | story | projects | resume,
  hovered: null | story | projects | resume,
  focused: null | story | projects | resume
}

active = focused ?? hovered ?? committed
phase  = active ? focused : arrival
```

Behavior:

- Fine-pointer hover previews a slab.
- Keyboard focus creates the same visual state.
- Touch/click on the explicit slab selector commits a state with
  `aria-pressed`.
- Arrow keys and Home/End move among the three selector buttons.
- Escape returns to Arrival.
- Enter links remain ordinary links to existing destination pages.
- Inactive slabs remain visible and reachable.
- No-JavaScript output keeps all content and links visible.

## 4. Implementation Approach and Alternatives

### Chosen: semantic DOM + route-scoped CSS + inline SVG

This approach best fits the repository and first-mission acceptance criteria:

- normal links, headings, images, buttons, and forms;
- direct keyboard and screen-reader support;
- no new production dependency or build pipeline;
- CSS perspective, transforms, blur, edge light, inset reflection, and layered
  shadows create the sculptural illusion;
- inline SVG supplies lightweight technical structure;
- authentic image and fixture content remains inspectable and maintainable;
- graceful solid, mobile, reduced-motion, and forced-colors fallbacks.

### Alternative considered: Canvas

Canvas could create richer distortion and particles, but it would require a
duplicate accessible DOM representation, manual hit testing, more complex
responsive layout, and harder screenshot/text QA. It offers little advantage for
Arrival's content-first baseline.

### Alternative considered: WebGL

WebGL could eventually add physical refraction, curved geometry, and lighting,
but introduces shader/runtime complexity, heavier assets, more browser risk, and
an accessibility duplication burden. It remains an optional later enhancement
after the semantic composition is approved.

### Alternative considered: static-image composition

A single generated hero could match the still mockup more literally but would
make text, links, focus, real data, and responsive interpretation brittle. The
implemented hybrid keeps real DOM content while using one existing product
screenshot inside the Projects slab.

## 5. Accessibility, Responsive, and Performance Decisions

- WCAG 2.2 AA target retained.
- One page `h1`; slab headings are ordered after it.
- Three semantic `article` elements remain in Story → Projects → Résumé DOM
  order regardless of visual depth.
- Every state has an explicit button and an explicit destination link.
- All interactive targets are at least 44px tall.
- Focus rings remain visible on both light and dark slabs.
- Dynamic state is announced through a polite status region.
- Motion uses transforms, opacity, and filter; there is no timer or repeating
  decorative animation.
- `prefers-reduced-motion` removes transitions and pointer lighting.
- `forced-colors` removes glass/depth effects and restores system colors and
  borders.
- Lack of `backdrop-filter` receives solid amber, indigo, and cloud surfaces.
- Mobile uses a readable vertical cinematic stack rather than shrinking the
  desktop installation.
- Browser QA at 390px reported document and body `scrollWidth` of 390px: no
  horizontal page overflow.
- Only the first Story image receives high fetch priority. Other Story images are
  lazy and use existing mobile sources.

## 6. Commands and Tests Run

### Repository and source audit

- `git status --short --branch`
- `git worktree list --porcelain`
- `rg --files`
- `rg`, `sed`, `nl`, `jq`, `sips`, and `wc` across routes, templates, fixtures,
  styles, scripts, tests, source-of-truth documents, and mockups.

### Automated verification

```text
ANTHROPIC_API_KEY=test-placeholder \
PYTHONDONTWRITEBYTECODE=1 \
/Users/petercarter/portfolio/venv/bin/python \
-m unittest discover -s tests -v
```

Result: **31 tests passed**.

Expected existing warning: Flask-Limiter uses in-memory storage locally.

```text
/Users/petercarter/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
--check static/js/living-triptych.js
```

Result: passed.

```text
git diff --check
```

Result: passed.

### Browser verification

- Local server: `http://127.0.0.1:5010/petec/atrium`
- Reviewed at 1600×900, 1440×900, and 390×844.
- Verified no console errors or warnings from the page.
- Verified Story selector click sets `data-active-panel="story"` and
  `aria-pressed="true"`.
- Verified ArrowRight moves focus from Story to Projects and activates the
  Projects visual state.
- Verified Escape restores the empty active state / Arrival.
- Verified mobile has no horizontal document overflow.

## 7. Working Screenshots

- `artifacts/living-triptych/arrival-1600x900.png`
- `artifacts/living-triptych/arrival-1440x900.png`
- `artifacts/living-triptych/arrival-mobile-390x844.png`

## 8. Known Gaps From the Approved Mockups

1. The repository has no approved photorealistic atrium environment. The current
   room is a CSS-built luminous architectural abstraction.
2. There is no childhood photograph. Arrival uses authentic adult Story images.
3. CSS approximates curved glass, refraction, and floor reflection; it does not
   model physical optics.
4. Arrival implements depth selection, but not the fully expanded 02 Story,
   03 Projects, or 04 Résumé content compositions.
5. The 05 Entry Transition is intentionally not implemented yet. Enter links
   navigate directly and reliably.
6. The Projects slab has one real product screenshot and a lightweight diagram,
   not the mockup's dense laptop/phone/architecture collage.
7. The résumé slab uses authentic data but does not yet show proof thumbnails or
   the full Ledger visual grammar.
8. The shared global header is denser than the mockup's minimal single-row
   profile navigation.
9. Ask the Slate reuses the current Ask Pete AI backend and approved portfolio
   knowledge. It is a visual/product-language treatment, not a new AI context.
10. Mobile uses a vertical stack rather than the possible active-card carousel.
11. The experimental route currently selects Pete's fixture in Python. A future
    multi-profile Atrium should accept a tenant-safe profile slug and corresponding
    Story source.
12. Real-device Safari/iPad, 200% zoom, increased contrast, and throttled network
    performance still require manual device-lab validation.

## 9. Unresolved Questions

1. Should Atrium remain in the global header throughout experimentation, or move
   into a private/internal preview entry once review begins?
2. Should the final public Triptych use a newly art-directed atrium background,
   the existing mountain/sky room, or remain an abstract luminous environment?
3. Should mobile stay a vertical journey or become a swipeable one-active-panel
   carousel after usability testing?
4. How much résumé evidence is appropriate in focus state before the slab becomes
   a mini résumé rather than an invitation?
5. Should pointer hover be a preview while click locks focus, or should pointer
   movement alone continuously choose the dominant slab?
6. Should Ask the Slate remain persistent during destination transitions, and if
   so, does it retain one conversation across rooms?

## 10. Recommended Next Milestone

Build and compare the three canonical focus states on the same architecture:

1. **02 Story Focus** — expand the authentic collage and values while keeping
   Projects and Résumé visible.
2. **03 Projects Focus** — reveal a stronger systems diagram, the real Living
   Résumé build, and two restrained project signals.
3. **04 Résumé Focus** — enlarge the authentic timeline and evidence metrics using
   the same joined fixture data.
4. Capture focus-state screenshots at 1600×900 and 1440×900.
5. Review comprehension, contrast, focus behavior, and motion before beginning
   **05 Entry Transition**.

The next milestone should refine the depth choreography and content reveal—not
replace this semantic baseline with a new rendering stack.
