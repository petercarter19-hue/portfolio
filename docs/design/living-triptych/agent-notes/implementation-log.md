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
