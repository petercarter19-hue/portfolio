# PS-HOME-BACKEND-001 — Finite Owner Home Backend

## Assignment

- Status: **Active, assigned, and cleared to start; implementation not started
  by this record**.
- Activated: 2026-07-19 by the designated ChatGPT Work/Codex manager session.
- Implementation writer: ChatGPT Codex, self-managed on one fresh branch.
- Required branch: `work/YYYY-MM-DD-home-backend-001` from current Azure DevOps
  `origin/main` after the manager unblock correction merges. Capture Photo PR
  95 and closeout PR 96 are complete; pipelines 139 and 140 passed; the
  overlapping `owner_routes.py` and `services/database_service.py`
  reservations are closed.
- Designated session manager: ChatGPT Work/Codex manager session.
- Controlling brief:
  `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/CODEX_BACKEND_IMPLEMENTATION_BRIEF.md`.
- Manager decisions and corrections:
  `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`.
- Production status: not implemented, deployed, enabled, or live.

## Scope

Build only the default-off, owner-authorized finite Home read contract:

- `PEERSLATE_OWNER_HOME_ENABLED`, default false;
- `usp_GetOwnerHomeForOwner(@UserKey)` and exact rollback/verification;
- bounded `owner-home.v1` service/serializer;
- flag-gated `GET /api/v1/owner/home`;
- all three approved review kinds with deterministic priority;
- owner isolation, no-store, 64 KiB / 9-object / 3-review limits;
- tests, SQL evidence, performance evidence, and the standard completion report.

The backend package does not edit `auth_routes.py`, select or render
`owner_home.html`, modify templates/CSS/JavaScript, or change `/app`. Flag-off
JSON is a neutral 404 before retrieval; flag-on anonymous JSON is 401. The
later frontend package owns the protected `/app` template switch after this
backend is merged.

## Entry and exit gates

The Capture Photo shared-file gate is cleared by PRs 95/96 and pipelines
139/140. Follow `START_HERE.md`, synchronize from post-correction `origin/main`, read the
current governance authority and the complete architecture package, and recheck
file reservations. Exit requires focused tests, both guardrail suites, the full
suite, isolated SQL apply/verify/rollback/reapply evidence, two-owner and byte
canaries, performance results, complete-diff self-review, a pushed exact SHA,
and a template-compliant completion report. Runtime or production claims require
the later Azure PR, pipeline, and explicit verification evidence.
