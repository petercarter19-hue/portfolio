# PS-OWNER-HOME-VIEWER-GATE-001 — First-Slice Recommendation

Recorded 2026-07-19 by the Claude/Fable architecture writer against
`origin/main` `6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`.

## Recommendation

Implement exactly one first slice: the **finite, signed-in, owner-only Home**,
released as two sequential packages (`PS-HOME-BACKEND-001` then
`PS-HOME-FRONTEND-001`) behind a default-off server flag. This confirms the
Codex `IMPLEMENTATION_DECOMPOSITION.md` recommendation; the repository audit
(`02_FABLE_REPOSITORY_FEASIBILITY_AUDIT.md`) found nothing that changes it.

**No broader viewer mode is activated.** Selected-person, connection,
authenticated-member, public projection, My Slate preview, Connections,
Journal, insights, sharing, publication, and matching remain future packages;
on Owner Home they appear only as content-free disabled **Coming later**
capability previews per the accepted authority.

## Exact protected route and integration approach

- **Owner Home HTML:** `GET /app` — the existing protected owner landing.
  When `PEERSLATE_OWNER_HOME_ENABLED` is off (default), `/app` renders the
  current `owner_workspace.html` unchanged. After the backend package has
  merged, the frontend package owns the flag-on switch to
  `templates/owner_home.html` from the bounded `OwnerHomeViewModel`.
  Anonymous requests keep today's verified behavior: 302 to
  `/auth/sign-in?return_to=/app`.
- **Owner Home data:** `GET /api/v1/owner/home` — owner-only JSON,
  `owner-home.v1`, `Cache-Control: private, no-store`, ≤64 KiB, `401
  authentication_required` when the flag is on and the caller is anonymous.
  With the flag off it returns neutral `404 {"error":"not_found"}` before any
  owner retrieval. It is used by the server render pathway internally and by
  progressive-enhancement retry; it is not a public API.
- **Integration approach:** server-rendered first. The route handler calls
  `services/owner_home_service.py :: get_home(owner_identity)` and passes the
  view model to the template; the JSON endpoint serializes the same view
  model. No client-side aggregation, no broad fetch + hide, and no use of the
  legacy `/api/dashboard` contract.

## Why this slice and this route

1. **It sits entirely on released, production-verified foundations** —
   identity/two-owner isolation (PS-AUTH-001), private text Capture
   (PS-CAPTURE-001/002), Voice Capture (PS-VOICE-001), canonical Moments
   (PS-MOMENT-001), Placement references (PS-PLACEMENT-001). Every category
   the first slice populates (Capture action, review items, recent Moment,
   next step) reads real owner-scoped data through the existing
   authorization-before-retrieval pattern. Nothing depends on unproven
   publication, grant, or connection behavior.
2. **`/app` is already the protected owner landing** with verified sign-in
   redirect behavior in production. Replacing its rendering behind a flag
   delivers the accepted experience at the owner's natural return-home URL
   without a new route decision, without touching the public route map, and
   with an instant rollback path (flag off → exact current workspace).
3. **The accepted visual authority is composed for exactly this scope**: the
   "current capability" screens (exports 01/03/05) show real-empty categories
   plus dormant previews, and the "future maximum" screens are explicitly
   labeled fixtures. Implementing the current-capability composition with real
   data is truthful on day one; later activations (resurfacing policy,
   insights, connections) are governed state changes, not redesigns.
4. **The finite contract keeps the blast radius small**: one core read
   procedure, ≤9 objects, ≤3 reviews, deterministic selection — implementable
   and testable without schema changes beyond a bounded read migration.

## Manager decisions — resolved 2026-07-19

The binding detail is in `11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`:

- **U1/U3:** a server-owned standalone-shell boolean suppresses the complete
  public chrome and global mobile bar/scripts only for flag-on Owner Home; one
  page-scoped owner mobile nav remains.
- **U2:** the exact accepted alpine PNG ships in the first release.
- **U4:** `/app` stays canonical and `owner_workspace.html` remains the exact
  flag-off fallback through founding-alpha stabilization.
- **U5:** the architecture gate is closed, `PS-HOME-BACKEND-001` is active and
  assigned but queued behind Capture Photo's overlapping shared files, and
  `PS-HOME-FRONTEND-001` is sequenced after the Home backend merge.
- **U6:** all three real workflows are eligible: failed Voice, pending Moment
  proposal, and Voice ready for review, in that urgency order; oldest first
  within kind, then stable opaque key.

The backend package does not select a frontend template. It ships an inert,
default-off API/service/migration slice; the frontend package later owns the
flag-on `/app` render. This keeps the sequential backend release deployable
without a missing or downgraded placeholder page.

## Explicitly out of scope for the first slice

Everything the gate's exclusion list names, plus: resurfacing policy
implementation (dormant preview until a written deterministic policy is
approved), governed insights, connection items, any Settings write contract,
any homepage change (no Owner Home projection exists on `/` today), and any
convergence of Pete fixture routes.
