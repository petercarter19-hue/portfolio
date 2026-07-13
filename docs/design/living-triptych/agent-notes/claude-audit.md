# Claude Code — Repository & Architecture Audit (Living Triptych / Atrium)

_Author: Claude Code · Branch: `experiment/living-triptych-claude` · Worktree: `../peerslate-claude` · Date: 2026-07-12_

This is the audit half of the First Mission. It records the repository **as it
actually exists** (discovered, not assumed) and the decisions that follow. The
build half (the working `01 — Arrival` slice) is logged in
[`implementation-log.md`](implementation-log.md); cross-agent decisions live in
[`architecture-decisions.md`](architecture-decisions.md); open questions in
[`unresolved-questions.md`](unresolved-questions.md).

---

## 1. Stack, rendering model, tooling

| Concern | Reality |
|---|---|
| Framework | **Flask 3.1.3** (Python) with **Jinja2** server-rendered templates |
| Other deps | `anthropic` 0.112 (chat route), `Flask-Limiter` (abuse guard), `python-dotenv`, `gunicorn` (Azure prod server) |
| Build step | **None.** No npm, no bundler, no transpile. CSS and JS are hand-authored static files served as-is. |
| JS | **Vanilla only.** No React/Vue/Svelte, no jQuery, **no Three.js / no animation library.** Small progressive-enhancement scripts in `static/js/`. |
| Styling | Hand-written CSS. One monolith `static/css/style.css` (~349 KB) **plus a per-experience file convention** (`story-cinematic.css`, `projects-cinematic.css`, `resume2.css`, `living-resume-v2.css`, …). New experiences get their own CSS file. |
| Design system | **Foundation A** design tokens in `static/css/design-system/tokens.css` (`--ps-*` namespace) + a reusable `.ps-glass-card` component. **`tokens.css` is NOT loaded globally** — only on the design-system preview — so a page must opt in. |
| Fonts (loaded in `base.html`) | **Inter** (UI), **Playfair Display** (cinematic serif), Source Serif 4. `tokens.css` maps `--ps-font-display: Playfair Display`, `--ps-font-ui: Inter`. |
| Routing | `@app.route` decorators in `app.py`. A single `@app.context_processor` injects `portfolio_url()`, `platform_brand_name`, `is_portfolio_path`, and `portfolio_*_url` helpers into every template. |
| Data | JSON fixtures in `static/data/`, loaded per-route with `json.load`. No DB for content. |
| Tests | **pytest** in `tests/` (`test_navigation.py`, `test_resume2.py`, `test_my_story.py`, `test_living_resume_preview.py`) — Flask test-client, assert on rendered HTML. |
| Deploy | **Azure DevOps pipeline** (`azure-pipelines.yml`) → gunicorn. **GitHub Actions disabled** (see CLAUDE.md). |
| Local run | `PORT` env var → `app.run(port=PORT)`, default 5000. macOS AirPlay squats `localhost:5000`; use `127.0.0.1`. **Codex is running on :5000, so this worktree runs on a different port.** |

**Implication for the Atrium:** the winning approach for slice 1 must work with
**server-rendered Jinja + hand-written CSS + vanilla JS and no build step.** A
DOM/CSS(/SVG) approach is native to this repo; anything requiring a bundler or a
framework is friction. WebGL/Three.js is *possible* (vendored file + CDN-free per
the artifact/CSP habits) but is a dependency decision to justify with evidence,
not a default — deferred candidate, not slice-1.

---

## 2. Current Overview surfaces & routing (what "Overview" means today)

There is no single "Overview" — there are several front-door candidates, which is
exactly why the Atrium is a *separate* link Pete can judge without replacing them:

- `/` → `experience.html` — the cinematic scenic homepage (the current site root).
- `/petec` (`/portfolio`, `/pete`) → `index.html` — Pete's profile "Overview".
- `/experience` → `experience.html` — same film, standalone link for comparison.
- `/petec/my-story` → `my_story.html` — **My Story** (amber source content).
- `/petec/work` → `work.html` — **Projects/Work** (indigo source content).
- `/petec/skills` → `skills.html` — Evidence/skills.
- `/<slug>/resume2` → `resume2.html` — **Living Résumé** (frosted source content); `_render_living_resume()` builds its view model.
- `/the-slate*` → the product hub (feed, my-slate, daily, paths, pulse, break).

**Global chrome** lives in `templates/base.html`:
- `.global-header` → `.platform-nav` (brand + `.platform-nav__links` + search + Ask AI + Sign In).
- `partials/profile_tabs.html` — the profile sub-nav (Overview / My Story / Evidence / Projects / Slate Board / Resume), included on every path except `/`.
- `partials/profile_shell.html` — the profile identity band.
- `sky-glass.css` paints a fixed mountain-sky backdrop (`.site-sky`) behind `body.slate-light`, with frosted-glass surfaces floating over it — **the same visual language the Atrium wants.**

---

## 3. Reusable design-system elements the Atrium should build on

- **`design-system/tokens.css`** — `--ps-*` tokens: color (ink-950 `#061a3a`, accent-blue `#4ea3ff`, accent-gold `#f3be4f`, accent-cyan `#50d6e8`), type scale (`--ps-type-display-hero` etc., Playfair + Inter), spacing, radius, **glass tiers** (`--ps-glass-*-bg`, blur, saturation), **shadows** (`--ps-shadow-hero/card/focus`), **motion** (`--ps-motion-*`, `--ps-ease-standard`), z-index. Includes `@media (prefers-reduced-motion)` overrides. → **Load in the Atrium's `extra_head`.**
- **`design-system/peerslate-glass-card.css` + `partials/peerslate_glass_card.html`** — `.ps-glass-card` (+ `--hero/--feature/--evidence/--ai/--compact` variants, `data-tone="dark"`), with hover/focus lift, reduced-motion, and **`forced-colors` fallbacks already built in.** The slab inner content cards should reuse this vocabulary.
- **`sky-glass.css`** — `--glass-bg`, `--glass-border`, `--glass-shadow`, `--glass-blur` utilities; the `.site-sky` backdrop; heading halo; `sky-reveal.js` scroll-reveal pattern (`[data-reveal].is-revealed`).
- **Approved palette (AGENTS.md):** Product Indigo `#4F5BD5`, Connection Azure `#4EA3FF`, AI Cyan `#2EC8D3`, Evidence Amber `#D7A33E`, Midnight Ink `#0A1B36`, Cloud White `#F6F8FC`. **Pink/rose/magenta forbidden** as accents — I will *not* use `--ps-color-accent-pink` even though tokens.css defines it.

---

## 4. Authentic content sources (real data, no fictional/MICAP copy)

All three slabs must render from real fixtures, not the mockups' invented data.

- **My Story** ← `static/data/story_data.json`: acts "This is me now." / "How I became this person." / "The life around the work." / "Still becoming."; `closing_values`: **Curious by nature · People first · Purpose driven · Always learning**. Link → `/petec/my-story`.
- **Projects** ← `work.html` / `resume_data.json.applied_projects` + `case_studies`: systems-thinking framing; pillars Architecture / Data layer / Product flow / Impact loop. Link → `/petec/work`.
- **Living Résumé** ← `static/data/resume_data.json`:
  - Real chapters (newest→oldest): **2025–Present · Northrop Grumman · Systems Engineer, Integration & Test** · **2024–2025 · L3Harris · Systems Effectiveness Engineer** · **2021–2024 · U.S. Air Force / DoD · Lead Systems Engineer (Robins AFB)**.
  - Real metrics (**MICAP excluded per AGENTS.md**): `$36M+` contract oversight · `7` aircraft platforms · `70%` repair/test improvement · `$4.6M` navigation modernization · `4.0` graduate GPA.
  - Quote: _"Every chapter changed what came next."_; traits: Leader/Engineer/Problem Solver/Communicator/Learner.
  - Education: B.Sc. Kennesaw State · M.Sc. University of Arkansas (+ PMP, PhD in progress, MS Azure/AWS certs). Link → `/petec/resume2`.
- **Multi-user proof** ← `living_resume_fixtures.json`: six generic personas (student → senior). The slab **view model must be data-driven** so it renders any of these, not just Pete (AGENTS.md: never hardcode employers/metrics into reusable components). Pete is fixture/demo data.

---

## 5. Accessibility, responsive, performance, test patterns already in place

- **A11y baseline:** skip-link, `aria-current="page"`, semantic landmarks, `prefers-reduced-motion` overrides in tokens + sky-glass, `forced-colors` fallback in the glass card, visible focus via `--ps-shadow-focus`. Target is **WCAG 2.2 AA** (AGENTS.md). The Atrium must add: keyboard slab selection, focus order, readable-at-overlap contrast, reduced-motion still, 200% zoom, and a structured list alternative to the 3D scene.
- **Responsive:** mobile = readable document flow; "never shrink a desktop visualization until unreadable." Atrium mobile must be a **reinterpretation** (vertical stack / one-active carousel), not a scaled-down triptych.
- **Performance:** `backdrop-filter` is already used site-wide; multiple large blurred slabs are the main cost to watch. Prefer transform+opacity for motion.
- **Tests:** extend `test_navigation.py` (Atrium link + `/atrium` 200) and add `tests/test_atrium.py` (renders, real content present, no MICAP, has landmarks + list alternative).

---

## 6. Risks of the Atrium / of eventually replacing Overview

1. **Backdrop-filter stacking** — three overlapping blurred slabs + the sky backdrop can be GPU-heavy and can wash out overlap text. Mitigate with a solid-ink scrim behind identity text and a capped blur budget.
2. **Overlap legibility & contrast** — the hardest a11y risk; text at the slab overlap must stay AA. Needs a dedicated readable layer, not just translucency.
3. **Fidelity gap** — the mockups are 3D-rendered curved glass; flat CSS rectangles risk "three cards." Curvature/edge-light technique is the make-or-break (subject of the exploration workflow).
4. **Chrome collision** — Atrium is full-bleed; it opts out of `profile_tabs` (done) and must not double the global header. If it ever becomes `/` it must absorb the current homepage's role gracefully.
5. **Data coupling** — must stay generic/tenant-safe; do not bake Pete's specifics into shared CSS/JS.
6. **Two-agent divergence** — Codex is building a parallel version; keep components isolated + notes current so the strongest pieces can be combined.

---

## 7. Wiring already landed on this branch (scaffold before the slice)

- `app.py` → added `@app.route('/atrium')` → `render_template('atrium.html')`.
- `base.html` → added **Atrium** nav `<li>` (leftmost, front-door position) + excluded `/atrium` from the `profile_tabs` include so it stays full-bleed.
- Route name chosen with Pete: **"Atrium"** at `/atrium` (names the rotunda the slabs stand in; distinct from "Overview"; can become the front door if it lands, retire if not).
- `templates/atrium.html` — pending the exploration synthesis (build half).

---

## 8. Recommendation going into the build

Build slice 1 as **server-rendered Jinja + a dedicated `static/css/atrium.css` on Foundation A tokens + a small vanilla `atrium.js`**, with a **data-driven slab view model** (works for any profile), real Pete content, and the curved/edge-lit glass technique chosen by the exploration workflow (`atrium-arrival-exploration`). Treat **WebGL as a later, evidence-gated milestone**, not slice 1. Verify live on a **non-5000 port** (Codex holds 5000).
