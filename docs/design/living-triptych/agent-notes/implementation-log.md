# Living Triptych — Implementation Log (Claude branch)

Chronological log of what Claude Code actually did on
`experiment/living-triptych-claude`. Newest entries at the bottom.

## 2026-07-12

- **Worktrees created:** `../peerslate-claude` (`experiment/living-triptych-claude`) and `../peerslate-codex` (`experiment/living-triptych-codex`) off `c0a015a`.
- **Read** the full vision package: `LIVING_TRIPTYCH_VISION.md`, `KICKOFF_PROMPT_FOR_BOTH_AGENTS.md`, `REPO_CONTEXT_SETUP.md`, all five mockups, AGENTS.md/CLAUDE.md rules.
- **Audit** completed → `claude-audit.md` (stack, routing, tokens, glass system, real content, a11y baseline, risks).
- **Scaffold wiring landed:**
  - `app.py` — `@app.route('/atrium')` → `atrium.html`.
  - `templates/base.html` — "Atrium" nav link (leftmost) + `/atrium` excluded from `profile_tabs`.
  - Route/label "Atrium" chosen with Pete.
- **Exploration workflow** `atrium-arrival-exploration` launched (3 competing Arrival implementations → adversarial synthesis blueprint).
- **Next:** implement `templates/atrium.html` + `static/css/atrium.css` (+ `atrium.js`) from the synthesis; run Flask on a non-5000 port (Codex holds 5000); verify + screenshot; a11y/fidelity review pass; add `tests/test_atrium.py`.

### Build — 01 Arrival vertical slice (shipped on this branch)

**New / changed files**
- `app.py` — `/atrium` route + `build_atrium_view_model()` (assembles the three-dimension model from real `resume_data.json` + `story_data.json`; MICAP excluded).
- `templates/atrium.html` — the Arrival stage (3 slabs, identity, Ask the Slate) extending `base.html`.
- `templates/base.html` — "Atrium" nav link (leftmost) + `/atrium` excluded from `profile_tabs`.
- `static/css/atrium.css` — full Atrium styling on Foundation A tokens (glass tint families, 3D fan, cylindrical edge-light, entrance keyframes, responsive tablet + mobile reinterpretation, reduced-motion + forced-colors fallbacks).
- `static/js/atrium.js` — progressive enhancement only (pointer parallax + Ask-the-Slate → assistant handoff). Slabs are fully usable without it.
- `tests/test_atrium.py` — 8 tests (route, nav link, real destinations, real chapters + `$36M+` evidence, **no MICAP**, story photos, no profile tabs, reduced-motion/forced-colors CSS).
- `.claude/launch.json` (main worktree) — `atrium-claude` preview config on **port 5057** (Codex holds 5000); uses a placeholder API key (Atrium makes no API calls — real secret untouched).

**Rendering approach** — DOM/CSS `preserve-3d` triptych (one `perspective` stage → `transform-style: preserve-3d` group → three `.slab`s). Centre (Projects) at `translateZ` forward + scale, wings `rotateY(±15deg)`. Curvature is faked with light: a cylindrical side-shading `::before` + travelling sheen `::after` + edge-light rail. Glass = `backdrop-filter` over the site sky. Identity lives **inside** the indigo centre slab (white on dark). This matches the exploration workflow's winning direction (Approach 1, score 84 — best a11y/maintainability/overlap).

**Verification**
- `python -m unittest discover -s tests` → **33 passed** (25 existing + 8 new), no regressions.
- Live on `127.0.0.1:5057/atrium`: desktop triptych centred, real content in all three slabs, overlap readable, no console errors. Mobile (375px) reinterprets as a cinematic vertical stack. Chat bubble hidden; Ask the Slate bar present.

**Known gaps vs mockup (deferred to next milestone)**
- Curvature is gradient-faked, not a true bowed silhouette → graft the synthesis's **SVG `clipPath` barrel outline + feGaussianBlur rim** onto the decorative surface layer only (biggest fidelity lever).
- Hover/focus lift is ad-hoc → replace with a single `data-focus` state machine on the stage (sets up focus states 02–04 + the 05 entry transition).
- `Proof →` is a visual cue, not yet a per-chapter evidence link (awaiting evidence anchors).
- WebGL refractive glass deferred behind a `?gl=1` desktop-only flag (synthesis Approach 3; perf/maintainability cost too high for slice 1).

## 2026-07-13 — Editorial-glass pass + five-scene Overview

- **Editorial-glass visual pass** (commit b0b4b3d): approved pale field
  background + card finish sitewide under `body.ps-editorial-surface`;
  root `/` (+ `/experience`) fully protected and verified pixel-identical.
- **Overview overhaul**: `/petec` now renders `templates/overview.html` —
  five editorial scenes from Pete's approved mockups (Editorial Opening,
  My Story, Projects, Living Résumé, Closing the Ribbon), styled by
  `static/css/overview-scenes.css` (Newsreader headlines + Inter UI).
  All content is real fixture/knowledge data via
  `build_overview_view_model()` in app.py: real headshot & story photos,
  the true "back to school at 36" turning point, real belief quote,
  real dashboard numbers (54 systems, 9 redesigns/$19.2M, 35%, 70%),
  real chapters (Northrop/L3Harris/USAF) with accomplishment-count
  evidence chips, $36M+/30+/7/4.0 metrics, PMP, résumé PDF. Fictional
  mockup data (impact score 9.2, endorsements, invented employers)
  replaced; MICAP excluded. index.html kept on disk for rollback.
- Verified desktop scene-by-scene + mobile 375px; 33/33 tests pass.

## 2026-07-13 — Living Résumé card spacing + Skills relocation

- **No more overlapping cards** (Pete's request): experience chapter cards
  restaggered to a gentle downward-only offset (0/2/1rem) so they never
  overlap the header above or the section below; the Education/Skills/
  Development "collage" grid was flattened to a clean vertical stack with
  generous spacing.
- **Skills & Evidence moved up**: relocated from the vertical composition to
  a new `.r2-exp-header` row beside the Experience intro card (below the
  ledger, above the experience chapter cards) — a playful right-hand offset
  with real spacing, stacks under the intro on mobile. Section order + tests
  updated (test_resume2, test_living_resume_preview). 33/33 pass.

## 2026-07-13 — Projects Exhibition build (PAUSED at Pete's request, resume 12:35p CST)

Branch: feat/cinematic-projects-experience
- Phase 0 ✅ (f3a05fd): mockup reference structure + audit.
- Phase 1 ✅ (dd9c611): projects data (3 entries) + /petec/work data-driven
  + /petec/work/<slug> gated case-study route. 65 tests pass.
- NEXT (Phase 2): rewrite templates/work.html as the exhibition
  (hero → sticky 3-panel stage → scroll markers → continue strip),
  create static/css/projects-exhibition.css + static/js/projects-exhibition.js.
  Then Phase 3: templates/project_case_study.html (chapter rail + 6 scenes,
  approved copy already in resume_data.json case_study_sections).
  Then Phases 4-6 (states/docs, a11y, tests + screenshots).
  Verify on port 5057 (Codex holds 5000). Do NOT deploy without Pete's OK.
