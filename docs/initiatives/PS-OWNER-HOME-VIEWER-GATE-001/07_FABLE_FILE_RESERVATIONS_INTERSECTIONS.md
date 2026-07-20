# PS-OWNER-HOME-VIEWER-GATE-001 — File Reservations and Intersection Register

Recorded 2026-07-19 against `origin/main`
`6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`. This narrows the Codex
`IMPLEMENTATION_DECOMPOSITION.md` "potential reservations" into exact
per-package lists for the first vertical slice. Each implementation package
must recheck this list against then-current `origin/main` at assignment time.

## 1. PS-HOME-BACKEND-001 — exact reservations

| File | Change scope |
|---|---|
| `services/owner_home_service.py` | New bounded aggregation/view-model/serializer service (`owner-home.v1`) |
| `app.py` | Add only `PEERSLATE_OWNER_HOME_ENABLED`, parsed from environment and defaulting false |
| `owner_routes.py` | Add only the flag-gated owner JSON endpoint; preserve Capture/Moment/Settings routes untouched; flag off returns neutral 404 before retrieval |
| `services/database_service.py` | Add only the reviewed Home read procedure to the stored-procedure allowlist |
| `SQL FIles/Migrations/proposed/PS-HOME-001_owner_home_reads.sql` | New read-procedure migration (name availability recheck at assignment) |
| `SQL FIles/Migrations/proposed/PS-HOME-001_owner_home_reads_rollback.sql` | Exact rollback |
| `SQL FIles/Verification/PS-HOME-001_owner_isolation_verify.sql` | Structural, behavioral, and two-owner verification |
| `tests/test_owner_home.py` | New service/route/contract/two-owner tests |
| `tests/test_owner_home_migration.py` | New migration contract tests |
| `docs/initiatives/PS-HOME-BACKEND-001/**` | Package docs, evidence, completion report |

Read-only dependencies: `identity.py`, Capture/Moment/Placement services and
migrations, `templates/owner_workspace.html`, `static/css/owner-app.css`,
`auth_routes.py`, this initiative directory, governance records.

## 2. PS-HOME-FRONTEND-001 — exact reservations

| File | Change scope |
|---|---|
| `templates/owner_home.html` | New page template |
| `templates/partials/owner_home/_*.html` | New partials (inventory in `05_FABLE_FRONTEND_IMPLEMENTATION_ARCHITECTURE.md`) |
| `static/css/owner-home.css` | New route-scoped stylesheet (`--oh-*` tokens) |
| `static/js/owner-home.js` | New optional enhancement script |
| `static/img/owner-home/**` | Atmosphere and abstract section material |
| `auth_routes.py` | Minimal flag-on `owner_home.html` selection/bootstrap integration only, sequential after backend merge (intersection I2) |
| `templates/owner_workspace.html` | Read-only exact flag-off fallback through founding-alpha stabilization (manager decision U4) |
| `templates/base.html` | **Only** the manager-approved server-owned standalone-shell conditional from decisions U1/U3; no path sniffing and no behavior change outside the flag-on Owner Home render |
| `tests/test_owner_home.py` | Extend HTML/state assertions after rebasing on the merged backend |
| `tests/test_owner_home_accessibility.py` | New semantic/state checks |
| `docs/initiatives/PS-HOME-FRONTEND-001/**`, `artifacts/ps-home-frontend-001/**` | Package docs and named evidence |

## 3. Forbidden files and products (both packages)

- Voice: `static/js/owner-capture-voice.js`, Voice sections of
  `owner_capture.html` / `owner-app.css`, Voice services and migrations.
- Capture/Moment/Placement service internals and their migrations (read-only
  foundations; new read procedures only via the reserved migration files).
- `identity.py` (absent a separately approved identity defect package).
- Interview Studio, homepage (`templates/homepage.html`,
  `templates/partials/homepage/**`, `static/css/homepage-scenes.css`,
  `static/js/homepage-interview-demo.js`), Story, resume, Slate Board, Feed,
  Community, Journal files.
- Global chrome beyond U1/U3: `static/css/style.css`,
  `static/css/owner-app.css` (Voice-owned), `static/js/mobile-nav.js`,
  `static/js/theme-toggle.js`, `static/css/editorial-glass.css`.
- Shared governance records (`CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`,
  `ACTIVE_INITIATIVES.md`, Bible, Roadmap) — manager lane only.
- `.claude/launch.json`, `.env`, credentials, publish profiles.
- Legacy dashboard contract: no package may rename, wrap, or call
  `/api/dashboard` as a Home source.
- No new global navigation layer; no viewer/preview/publication/grant/
  connection/insight implementation of any kind in these two packages.

## 4. Intersection register and required sequencing

| ID | File/contract | Intersecting lanes | Control |
|---|---|---|---|
| I1 | `services/database_service.py` | Home backend now; viewer authorization later | One allowlist change per merged package; backend branches strictly sequential |
| I2 | `/app` HTML lives at `auth_routes.py:114`; JSON lives on `owner_routes.py` | Home backend ↔ Home frontend | Backend does not edit `auth_routes.py` or change `/app`; frontend starts from post-backend main and solely owns the flag-on template selection; never two concurrent branches on the shared test file |
| I3 | `tests/test_owner_home.py` | Home backend ↔ Home frontend | Same sequential ownership as I2 |
| I4 | `templates/base.html` server-owned standalone-shell conditional (U1/U3) | Home frontend ↔ every page | Suppress the complete public chrome only when the route passes the flag-on boolean; change must be provably inert for flag-off `/app` and all other routes (full-suite + representative screenshots) |
| I5 | `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/**` | This architecture branch (current writer) | Owned by `work/2026-07-19-owner-home-fable-architecture` until merged; implementation packages create their own package directories instead of editing this one |
| I6 | Interview lane worktree (`portfolio`, branch `work/2026-07-19-interview-public-gate-001`, uncommitted files) | Separate active lane | Untouched by this package; Owner Home packages must not modify `templates/interview_studio.html`, `static/css/interview-studio.css`, `static/js/interview-studio.js`, `tests/test_interview_studio.py` |
| I7 | Governance activation records | Manager lane | Resolved 2026-07-19: close the architecture gate, activate `PS-HOME-BACKEND-001`, and sequence `PS-HOME-FRONTEND-001` after backend merge; implementation writers do not edit shared governance records |
| I8 | `owner_routes.py` and `services/database_service.py` | `PS-CAPTURE-PHOTO-BACKEND-001` ↔ `PS-HOME-BACKEND-001` | Resolved: Capture Photo PR 95 and closeout PR 96 merged with successful pipelines 139 and 140. Its reservations are closed. Home may create its fresh branch from post-correction current main. No unmerged branch blending. |

## 5. Sequencing summary

1. This architecture/manager-acceptance branch merges (docs, artifacts, and
   shared governance activation only).
2. Completed: `PS-CAPTURE-PHOTO-BACKEND-001` and its closeout merged through
   PRs 95/96; pipelines 139/140 passed and both shared files were released.
3. `PS-HOME-BACKEND-001` creates its fresh branch, implements, and merges
   (flag off; no `/app` change).
4. `PS-HOME-FRONTEND-001` implements from post-backend main, passes visual
   acceptance, merges, releases flag-off, then founding-alpha enablement.
5. Viewer/preview packages remain gated exactly as the Codex decomposition
   states; nothing in this register reserves files for them.
