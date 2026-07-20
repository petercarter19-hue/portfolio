# PS-HOME-BACKEND-001 — Finite Owner Home Backend

## Assignment

- Status: **Complete, released, and production-verified at the default-off
  boundary on 2026-07-20**.
- Activated: 2026-07-19 by the designated ChatGPT Work/Codex manager session.
- Implementation writer: ChatGPT Codex, self-managed source branch
  `work/2026-07-19-home-backend-001` at
  `efd19d820986a529d48e2fcf660655b9f4dfc492`.
- Release: Azure PR 99 squash-merged at
  `2db2ca5c93fa221f7092b54ebc17f2068584c07d`; automatic pipeline 145 passed.
- Designated session manager: ChatGPT Work/Codex manager session.
- Controlling brief:
  `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/CODEX_BACKEND_IMPLEMENTATION_BRIEF.md`.
- Manager decisions and corrections:
  `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`.
- Production status: additive SQL migration and verifier passed; the flag
  remains off, `/app` is unchanged, and the JSON route returns neutral 404.
  Exact release evidence is recorded in `COMPLETION_REPORT.md`.

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

The Capture Photo shared-file gate was cleared by PRs 95/96 and pipelines
139/140. All backend exit gates passed: focused tests, both guardrail suites,
the full suite, isolated SQL apply/verify/rollback/reapply, two-owner and byte
canaries, performance results, complete-diff self-review, exact pushed SHA,
Azure PR/pipeline, production SQL, neutral live-route proof, and the
template-compliant completion report. `PS-HOME-FRONTEND-001` is now unblocked
but requires its own fresh branch and visual/product gate.
