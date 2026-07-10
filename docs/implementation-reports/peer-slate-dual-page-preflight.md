# PeerSlate dual-page preflight

**Recorded:** July 9, 2026  
**Scope:** Safe, alternate-route first passes for PS-FEAT-001 and Slate Board v2.  
**Outcome:** Proceed with isolated worktrees only. Existing routes, navigation, and shared global styles remain unchanged.

## Repository state

- **Repository root:** `C:\Users\peter\Documents\portfolio`
- **Current branch:** `codex/design-system-foundation`
- **Current commit:** `d92fd677583365ab1594443944c32d1aece77cb1` — `Document PeerSlate Foundation C handoff`
- **Working tree:** clean after committing and pushing the existing Foundation C handoff.
- **Default/stable branch:** `main` / `origin/main` at `599f8e3f3799d61c647bf2ca957dcc41e89f02fb`.
- **Foundation branch and commits:** `codex/design-system-foundation` contains `e2610f7` (Foundation A token/preview scaffold), `e641aa4` (Direction C source documents), and `d92fd67` (Foundation C handoff, required sources, references, and kickoff prompts).
- **Foundation C base decision:** identifiable and safe as this clean, pushed branch. It is intentionally not merged into `main`. Foundation C is approved in documentation, but its final tokens and components are not yet implemented in the shared runtime stylesheet. The two preview routes must use exact Direction C values in route-scoped CSS rather than changing the existing Foundation A/global styles.

## Required sources and references

Read in order before this report:

1. `docs/peerslate/PeerSlate_Design_Bible_v0.3.md`
2. `docs/peerslate/PS-FEAT-001_Living_Resume_Voice_Blueprint.md`
3. `docs/peerslate/PeerSlate_Product_Backlog.md`
4. `docs/peerslate/PS-EXP-002_Slate_Focus_Stage_Experiment.md`
5. `docs/peerslate/IMPLEMENTATION_HANDOFF.md`

All required sources exist. The approved Slate Board reference exists at `docs/design-references/slate-board/approved-slate-board-direction.png` and was reviewed. The resume reference directory contains only `ADD_APPROVED_IMAGES_HERE.md`; `approved-ledger.png` and `approved-constellation.png` are not present. This is not a source-document stop condition. The first pass will use an approved light, museum-style CSS composition and must be visually revisited when those references are supplied.

## Application architecture

- **Framework and entry point:** Flask 3.1.3, `app.py`.
- **Shared shell:** `templates/base.html`, which loads `static/css/style.css`, `static/css/chatbot.css`, shared site scripts, global platform navigation, and profile tabs for most portfolio pages.
- **Current resume:** routes `/resume` and `/petec/resume`; `templates/resume.html`; `static/css/resume.css`; `static/js/resume.js`; data in `static/data/resume_data.json`; PDF path from that data file (`static/files/pete-carter-resume.pdf`). Existing behavior includes role selection, skill-evidence popovers, metric-to-evidence linking, and Ask Pete AI hooks.
- **Current Slate Board:** routes `/slate-board` and `/petec/slate-board`; `templates/slate_board.html`; Board rules in `static/css/style.css`; `static/js/slate-board.js`. It is a static Pete fixture with browser-local compose data (`peerslateBoardEntries`) and board-mode state (`peerslateBoardMode`); it has no Board model or server API.
- **Related platform pages:** `/the-slate`, `/the-slate/my-slate`, `/the-slate/daily`, `/the-slate/pulse`, and `/the-slate/break`; static feed data is served from `static/data/slate_feed.json` by `/api/slate-feed`.
- **Existing design-system seam:** `/_internal/design-system` is local by default and deployment-opt-in through `ENABLE_DESIGN_SYSTEM_PREVIEW=1`. Foundation A tokens/components live under `static/css/design-system/` and `templates/partials/`; they include superseded pink/violet semantic assignments and cannot be used unchanged for Direction C.
- **Feature flags:** no generic feature-flag mechanism. The design-system environment flag above is the only existing isolation pattern.

## Validation discovery

- No automated test suite, lint configuration, formatter configuration, package manifest, or test runner configuration was found.
- Manual Flask test-client baseline: `/resume`, `/petec/resume`, `/slate-board`, `/petec/slate-board`, and `/_internal/design-system` each returned HTTP 200.
- Pre-existing warning: Flask-Limiter uses in-memory storage because no production storage backend is configured. This warning is unrelated to the new preview routes.
- Baseline dependencies are listed in `requirements.txt`: Flask, Anthropic, python-dotenv, Flask-Limiter, and gunicorn.

## Safe implementation plan

1. Create one worktree per first-pass route from this exact commit.
2. Add only alternate local preview routes; do not change current routes or navigation.
3. Keep each v2 page self-contained with its own template, JavaScript, route-scoped CSS, generic fixture/view-model data, and focused Flask route/render tests.
4. Use the exact approved Direction C colors, Newsreader for editorial headings, Inter for product UI, motion-reduction fallbacks, visible focus, and a structured Board alternative.
5. Treat AI, matching, visibility, and persistence as clearly labeled fixture/proposal states unless backend enforcement exists.

## Stop-condition review

- Uncommitted user changes: **not present**.
- Missing required source documents: **not present**.
- Ambiguous Foundation C base: **not present**; the approved documentation base is `d92fd67`, with an explicit limitation noted above.
- Unsafe route isolation: **not present**; Flask supports local-only alternate routes consistent with `/_internal/design-system`.

