# PS-OWNER-HOME-VIEWER-GATE-001 — Feasibility Matrix

Recorded 2026-07-19 against `origin/main`
`6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`. Scores each major component and
state for the first vertical slice (finite signed-in owner-only Home).

Scoring: **Pass** — implementable now on released foundations with no open
decision. **Conditional** — implementable now once the named decision or
sequenced dependency closes; these are implementation-time refinements or
manager decisions, not architectural blockers. **Fail** — a true blocker.

A missing future backend is **never** scored as a blocker to displaying its
truthful disabled **Coming later** silhouette; those silhouettes are
presentation states fed by the server-owned availability registry.

## Backend components

| Component | Result | Basis / condition |
|---|---|---|
| Owner identity boundary reuse | **Pass** | Released `get_current_identity()` + per-route enforcement pattern (`auth_routes.py:113-128`) |
| `GET /api/v1/owner/home` on the `owner` blueprint | **Pass** | Blueprint has no url_prefix; route registers cleanly |
| Flagged `/app` render integration | **Pass** | Manager correction: backend leaves `/app` unchanged; frontend solely owns the later flag-on switch in `auth_routes.py` after backend merge |
| `usp_GetOwnerHomeForOwner(@UserKey)` + migration | **Pass** | Additive read procedure following the released `proposed/` migration + verification pattern; no table changes |
| Allowlist change | **Pass** | One entry in `ALLOWED_PROCEDURES` |
| Review-item selection | **Pass** | U6 resolved: failed Voice → pending Moment proposal → ready Voice; oldest-first within kind, stable opaque-key tie-break |
| Recent-Moment selection | **Pass** | Confirmed Moments exist; TOP 1 with review-dedup is a bounded read |
| Deterministic next step | **Pass** | Rules defined; inputs all first-party |
| Deduplication / determinism / limits / 64 KiB | **Pass** | Enforced in procedure + serializer; testable |
| Failure independence | **Pass** | First slice is core-query-only; adapter seams defined for later categories |
| No-store + header contract | **Pass** | Precedent at `owner_routes.py:507` |
| Two-owner / payload canaries | **Pass** | Test patterns exist across Capture/Moment/Voice suites |
| Performance budgets | **Conditional** | Requires the founding-alpha dataset profile run at implementation time; single bounded query makes the budget realistic |
| Feature flag default-off | **Pass** | `PEERSLATE_*` config convention (DR4) |

## Frontend components

| Component | Result | Basis / condition |
|---|---|---|
| `owner_home.html` + partials composition | **Pass** | Conventions audited; reading order defined |
| Route-scoped chrome handling for the cinematic shell | **Pass** | U1/U3 resolved: server-owned standalone-shell conditional suppresses complete public/global chrome only on flag-on Owner Home and retains the skip link/single main |
| Route-scoped palette + typography (`--oh-*`, Newsreader/Inter) | **Pass** | Owner decision recorded; fonts already loaded; D5/D6 approved deviations |
| Dominant Capture action | **Pass** | Real destination released (`/app/capture`) |
| Coming-later capability previews (audience rail, Resurfaced, Noticed, Connections, nav reservations) | **Pass** | Voice pattern released and accepted; registry-fed; zero routes/requests; missing future backends are presentation states, not blockers |
| Review list (≤3) + bounded remainder | **Pass** | U6 kinds and deterministic priority are fixed; bounded remainder remains non-record shell context |
| Loading state | **Pass** | JS-initiated refresh only; initial load is a full server render |
| Empty state | **Pass** | Export 13 composition; honest copy |
| Partial failure state | **Pass** | Server flags per category; export 14 |
| Complete failure state | **Pass** | 503 pathway + safe Capture destination; export 15 |
| Stale state | **Pass** | `state_version` + `409 state_changed`; export 16 |
| Restricted state | **Pass** | Bounded neutral unavailable item; export 17 |
| Retry / recovery states | **Pass** | Idempotent GET; announcements/focus defined; export 18 |
| Session-expired state | **Pass** | 401 → validated local sign-in return path |
| Desktop 1440 composition | **Pass** | Exports 01/02 |
| 390px composition | **Pass** | Exports 03/04 |
| 320px composition | **Conditional** | R1/D1 reflow correction required (Noticed + Next Step collisions in the accepted export); design intent otherwise complete |
| Landscape 844 | **Pass** | Export 23 |
| 200% zoom / reflow | **Pass** | Export 07 + fluid sizing conventions |
| Long content / bidi / missing media | **Pass** | Export 08 |
| Visible focus | **Pass** | Export 09; WCAG 2.2 focus appearance specified |
| Forced colors | **Conditional** | Export 10 direction exists; `owner-app.css` precedent gap means Owner Home must author its own block (known work, not a blocker) |
| Reduced motion | **Pass** | Export 11; static atmosphere |
| Keyboard / NVDA | **Pass** | Semantics defined; NVDA evidence is implementation-time work in the charter |
| Truthful-label copy (R2/D2) | **Conditional** | Copy inventory review at V2 |
| Distinct section personalities (R3/D3) | **Conditional** | New abstract material to be produced; constraint: no fabricated member content |
| Homepage-impact check | **Pass** | No Owner Home projection exists on `/` today; reassessment step defined |

## Package/process gates

| Gate | Result | Basis / condition |
|---|---|---|
| Architecture package completeness | **Pass** | This branch |
| Governance activation records | **Pass** | U5 resolved in `11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md` and shared governance: backend active/assigned but queued behind Capture Photo shared files; frontend sequenced |
| Guardrail + full suite | **Pass** | Architecture writer: 25/25 and 494 pass / 1 environmental skip; manager disposition on current merged baseline: 27/27 and 496 tests run / 1 environmental skip |
| Windows generator fix (R4) | **Conditional** | Patch + dependency record complete; runtime execution pending a machine with Node.js (documented in `GENERATOR_NOTES.md`) |
| Viewer modes / My Slate preview / insights / connections activation | **Out of scope** | Gated exactly as the Codex decomposition states; not scored here because the first slice never activates them |

## Overall result

**Accepted — implementation-ready.** No component scored **Fail**. U1–U6 are
resolved. Remaining Conditional items are owner-directed implementation work
(R1/D1, R2/D2, R3/D3, R4 runtime proof) or implementation-time evidence
(performance run, forced-colors block, copy review). True blockers: **none**.
