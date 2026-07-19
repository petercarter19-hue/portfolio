# PS-OWNER-HOME-VIEWER-GATE-001 Implementation Decomposition

## Recommendation

The first released vertical slice should be the **finite owner-only Home**: real protected `/app`, one obvious text Capture action, real bounded review/Moment data where eligible, honest unavailable optional categories, one real next step, complete desktop/mobile/accessibility states, and no non-owner claim. It delivers owner value on the existing identity/Capture/Moment foundations without depending on unproven publication, grant, or connection behavior.

That release slice is assembled sequentially from a backend package and a frontend package. The backend package stays flag-off/non-public until the approved frontend is complete; this avoids releasing a visually downgraded placeholder. ChatGPT Work controls sequencing and acceptance, Codex owns backend packages, and Claude Code owns frontend packages, each on its own short-lived branch from then-current `origin/main`.

Viewer modes and My Slate preview follow only after the authorization/projection foundation and real lifecycle gates. Do not implement all five audiences in a single cross-cutting branch.

## Preconditions before assignment

ChatGPT Work must confirm:

1. This architecture package and early visual-truth handoff are accepted.
2. Owner Home production-intent desktop/mobile/state boards are complete and Pete-approved.
3. The public/member route map and audience vocabulary are decided before viewer UI work.
4. The publication/grant/connection lifecycle owner packages exist before those modes are enabled.
5. `origin/main`, all active worktrees, current reservations, and the relevant package docs are re-read before each branch is assigned.
6. Exact SQL migration names are checked at assignment time to avoid collisions with newly merged work.

The file lists below are **potential reservations**, not permission to edit now. Each future initiative package must narrow and record its exact list before a writer starts.

## Package 1 - `PS-HOME-BACKEND-001`: bounded owner read model

**Owner/writer:** ChatGPT Work / Codex backend lane.

**Outcome:** Versioned owner-only Home endpoint and server-render input contract behind a default-off flag. No visual release.

**Potential reservations:**

- `owner_routes.py` - add/replace only the `/app` data integration behind flag; preserve Capture/Moment/Settings routes.
- `services/owner_home_service.py` - new bounded aggregation/view-model service.
- `services/database_service.py` - add only the reviewed Home procedure to the allowlist/adapter.
- `SQL FIles/Migrations/PS-HOME-001_owner_home_reads.sql` - proposed new migration name; confirm availability.
- `SQL FIles/Migrations/PS-HOME-001_owner_home_reads_rollback.sql` - exact rollback.
- `SQL FIles/Verification/PS-HOME-001_owner_home_reads_verify.sql` - structural/behavioral verification.
- `tests/test_owner_home.py` - new service/route/contract/two-owner tests.
- `tests/test_owner_home_migration.py` - new migration shape/apply/rollback contract tests.
- `docs/initiatives/PS-HOME-BACKEND-001/**` - package, evidence, completion report.

**Read-only dependencies:** `identity.py`, Capture/Moment/Placement services and migrations, `owner_workspace.html`, `owner-app.css`, governing docs.

**Must not reserve/edit:** Voice, Capture Media, Interview, Story, Feed, Community, global navigation/theme, public fixture templates, or `identity.py` absent a separately approved identity defect.

**Acceptance:** `owner-home.v1`; 3-review/9-object/64-KiB limits; owner-before-query; two-owner canaries; no N+1; SQL apply/verify/rollback/reapply; partial failure; default-off flag; full regression.

## Package 2 - `PS-HOME-FRONTEND-001`: finite Owner Home experience

**Owner/writer:** ChatGPT Work / Claude Code frontend lane, after Package 1 is squash-merged and the branch starts from the new `origin/main`.

**Outcome:** Complete owner-approved Home experience wired to the real backend contract, including every named state. Enabling/release is still a manager action after acceptance.

**Potential reservations:**

- `templates/owner_home.html` - new final Home template.
- `static/css/owner-home.css` - new route-scoped styles using current approved tokens.
- `static/js/owner-home.js` - only if dynamic loading/retry requires it; progressive server-rendered behavior preferred.
- `owner_routes.py` - minimal template selection/bootstrap integration; conflicts with Package 1, so sequential only.
- `templates/owner_workspace.html` - retire or preserve as flag-off fallback only; exact decision in package.
- `tests/test_owner_home.py` - extend HTTP/HTML/state assertions after rebasing from merged backend.
- `tests/test_owner_home_accessibility.py` - proposed semantic/state checks.
- `tests/test_navigation.py` - only current `/app` label/link behavior; no global redesign.
- `docs/initiatives/PS-HOME-FRONTEND-001/**` and named screenshot artifacts.

**Intersections requiring coordination:** `owner_routes.py` and `tests/test_owner_home.py` overlap Package 1; therefore no concurrent branches. Avoid `base.html`, `style.css`, `owner-app.css`, `mobile-nav.js`, and global theme/navigation unless the approved design cannot be delivered without them and ChatGPT Work explicitly expands reservations.

**Acceptance:** Recognizable match/exceed approved boards, one dominant Capture action, all finite/empty/loading/failure/stale states, 320-pixel reflow, 200% zoom, keyboard/NVDA/forced colors/reduced motion, Pete and Danielle founding-alpha, screenshots, no fixture/simulated capability.

**First vertical slice release gate:** Packages 1 and 2 merged, default-off deployment verified, Pete/ChatGPT Work visual acceptance recorded, then alpha flag enabled. Insight and connection may remain truthfully absent.

## Package 3 - `PS-VIEW-AUTHZ-001`: projection and authorization foundation

**Owner/writer:** ChatGPT Work / Codex backend lane, after the audience/manifest/lifecycle decisions.

**Outcome:** Reversible schema, authorization-before-retrieval procedures, services, serializers, and tests. No live viewer UI and flags off.

**Potential reservations:**

- `services/viewer_context_service.py` - new actor/subject/mode/purpose resolver adapter.
- `services/slate_projection_service.py` - new narrow projection/view-model service.
- `services/database_service.py` - add only approved authorization/projection procedures; central intersection.
- `SQL FIles/Migrations/PS-VIEW-001_projection_authorization.sql` - proposed name; confirm at assignment.
- `SQL FIles/Migrations/PS-VIEW-001_projection_authorization_rollback.sql`.
- `SQL FIles/Verification/PS-VIEW-001_projection_authorization_verify.sql`.
- `tests/test_viewer_authorization.py` - new service/matrix/two-owner tests.
- `tests/test_viewer_projection_migration.py` - new migration/manifest/privacy tests.
- `tests/test_database_service.py` - procedure allowlist only.
- `docs/initiatives/PS-VIEW-AUTHZ-001/**`.

**Read-only dependencies:** `identity.py`, `services/moment_service.py`, Moment/Placement migrations, PS-PLAT-002/004 schema, Living Resume API as a non-authoritative comparison.

**Required decisions implemented, not inferred:** canonical audience vocabulary; legacy `shared`/`recruiter` handling; reference-only manifest; opaque/concurrent grant management; authorization version; block/expiry/withdrawal order; public cache initially no-store.

**Acceptance:** SQL authorization before content join, two-owner/multi-viewer canaries, reference-only exact versions, atomic revocation/versioning, migration rollback/reapply, no API route yet, full regression.

## Package 4 - `PS-VIEW-MODES-001`: server viewer endpoints

**Owner/writer:** ChatGPT Work / Codex backend lane, after Package 3 is squash-merged and a real lifecycle can create the tested states.

**Outcome:** Versioned JSON endpoints for only the manager-approved modes. Mode-by-mode flags default off. HTML composition remains frontend-owned.

**Potential reservations:**

- `viewer_routes.py` - new blueprint for public and authenticated viewer APIs.
- `app.py` - register the new blueprint and flags; central intersection.
- `services/viewer_context_service.py` and `services/slate_projection_service.py` - only contract defects/extensions discovered against the merged foundation.
- `services/database_service.py` - only if a procedure signature must change; coordinate with all backend lanes.
- `tests/test_viewer_routes.py` - new status/header/schema/negative tests.
- `tests/test_auth.py` - only shared auth redirect/session regressions if necessary.
- `tests/test_site_rules.py` - only if route rules explicitly require it.
- `docs/initiatives/PS-VIEW-MODES-001/**`.

**Mode split option:** If publication/grant/connection lifecycles mature at different times, divide into `PS-VIEW-PUBLIC-001`, `PS-VIEW-SELECTED-001`, `PS-VIEW-CONNECTION-001`, and `PS-VIEW-MEMBER-001`. Do not enable a mode merely because the shared endpoint exists.

**Acceptance:** matrix status codes and headers, payload-level canaries, enumeration resistance, rate limiting, current authorization version, real lifecycle positive/negative evidence, production flag-off verification.

## Package 5 - `PS-PREVIEW-001`: exact owner My Slate preview

**Owner/writer:** ChatGPT Work / Codex backend lane for service/API; any visual frontend is reserved in Package 6. Start after Package 4 is merged for the previewed modes.

**Outcome:** Owner-only preview API that invokes the same context resolver, projection query, and serializer as live viewing.

**Potential reservations:**

- `owner_preview_routes.py` - new owner-only preview API blueprint, preferred over expanding unrelated owner routes.
- `services/preview_service.py` - thin owner/purpose wrapper; no independent projection logic.
- `app.py` - blueprint/flag registration; overlaps Package 4, so sequential.
- `tests/test_owner_preview.py` - byte-equivalence, ownership, mode, block/revocation tests.
- `tests/test_viewer_routes.py` - shared equivalence fixture only if required.
- `docs/initiatives/PS-PREVIEW-001/**`.

**Must not edit/claim:** existing public static `templates/the_slate_my.html` as real preview, global navigation, publication management, or simulated selected/connection viewers.

**Acceptance:** live/preview projection equivalence; owner-only subject; real eligibility; no mutation by GET; withdrawal/block parity; default-off flag; API-only production proof.

## Package 6 - `PS-VIEW-FRONTEND-001`: viewer and preview experience

**Owner/writer:** ChatGPT Work / Claude Code frontend lane, after backend APIs are merged and production-intent viewer/preview designs and route map are accepted.

**Outcome:** One audience-aware visual system rendering the narrow `slate-projection.v1` contract, plus an owner preview wrapper. It does not decide publication or grant lifecycle.

**Potential reservations:**

- `templates/slate_viewer.html` - proposed new generic viewer shell.
- `templates/owner_slate_preview.html` - proposed preview wrapper using the same projection component.
- `static/css/slate-viewer.css` - route-scoped design.
- `static/js/slate-viewer.js` - bounded fetch/state/retry only if needed.
- `static/js/owner-slate-preview.js` - preview mode control only if approved.
- `viewer_routes.py` / `owner_preview_routes.py` - minimal HTML/bootstrap integration; coordinate sequentially with backend owners.
- `tests/test_viewer_experience.py` and `tests/test_owner_preview.py` - DOM/state/context checks.
- `tests/test_navigation.py` - only after the route-map decision; no redesign.
- `docs/initiatives/PS-VIEW-FRONTEND-001/**` and named screenshot artifacts.

**Avoid by default:** `base.html`, `style.css`, `mobile-nav.js`, `theme-toggle.js`, existing Story/resume/Slate Board templates/scripts/styles. If a shared primitive truly needs change, ChatGPT Work assigns a separate shared-shell package rather than silently widening this branch.

**Acceptance:** no owner controls/private fields in viewer DOM; exact context labels; restricted/revoked content clearing; complete desktop/mobile/keyboard/NVDA/zoom/forced-color/reduced-motion states; preview/live equivalence; Pete and Danielle acceptance per mode.

## Merge and release order

1. Accept this architecture package and visual-truth handoff.
2. Approve the Owner Home production-intent design and route-state boards.
3. Merge `PS-HOME-BACKEND-001`.
4. Merge `PS-HOME-FRONTEND-001`; deploy flag off; complete founding-alpha/visual proof; enable the first vertical slice.
5. Approve audience vocabulary, route map, reference-only manifest, and real publication/grant/connection lifecycle ownership.
6. Merge `PS-VIEW-AUTHZ-001`; deploy flags off and prove migration.
7. Merge only ready server mode packages under `PS-VIEW-MODES-001` (or the narrower mode split).
8. Merge `PS-PREVIEW-001` for modes whose live path exists.
9. Approve viewer/preview production-intent designs.
10. Merge `PS-VIEW-FRONTEND-001`, then validate/enable modes independently; public generic projection last.
11. Consider Pete fixture-route convergence only in a separate future package.

Each step starts from current `origin/main`, uses its own `work/YYYY-MM-DD-task-name` branch/worktree, commits/pushes before handoff, and merges through an Azure squash PR. No writer works concurrently on an intersecting file.

## Central intersection register

| File/contract | Intersecting packages | Manager control |
|---|---|---|
| `services/database_service.py` | Home backend, view authorization, viewer modes | Sequential backend branches; one procedure allowlist change per merged package |
| `owner_routes.py` | Home backend/frontend | Backend merges first; frontend starts from new main and owns final route integration |
| `app.py` | Viewer modes, preview | Viewer blueprint first; preview starts after merge; avoid unrelated registrations |
| `viewer_routes.py` | Viewer modes, viewer frontend | Backend API merges first; frontend may add HTML only with exact reservation |
| `owner_preview_routes.py` | Preview backend/frontend | Backend merges first; frontend adds shell only |
| `tests/test_owner_home.py` | Home backend/frontend | Same sequential ownership as route |
| `tests/test_owner_preview.py` | Preview backend/frontend | Same sequential ownership as route |
| Audience vocabulary/manifest | Authorization, lifecycle, modes, preview | One authoritative decision/migration; downstream packages consume it, never redefine it |
| `/app` and public/profile route map | Home/viewer frontend, navigation | Manager/owner decision before templates; no global-nav change in these packages |

## Deferred work and non-owners

- Publication/grant management UI and lifecycle are not assigned here.
- Connection creation/matching, Feed, Journal, Community, Story Composer, Interview Studio, Capture Media, Voice, and global navigation/theme are not implementation dependencies to pull into these packages.
- Governed insight generation/evaluation is a separate future backend package; Home only consumes it after release.
- Existing fixture-backed Pete surfaces remain fixture-backed until a separate convergence package proves data, visual, route, SEO, and rollback parity.

## Gate result

**Conditional.** The decomposition is ready for manager sequencing, beginning with the owner-only Home vertical slice. No implementation writer should be assigned to viewer/preview code until the listed authority, lifecycle, route, migration, and design preconditions are satisfied.
