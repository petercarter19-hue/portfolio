# PS-OWNER-HOME-VIEWER-GATE-001 — Backend Contract Mapping

Recorded 2026-07-19 against `origin/main`
`6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`. Maps the Codex server-authorized
finite aggregation architecture (`ARCHITECTURE.md`, `FINITE_HOME_CONTRACT.md`)
onto exact repository files, names, and tests for `PS-HOME-BACKEND-001`. This
document maps; it does not redesign or implement the backend.

## 1. Contract → file map

| Codex contract element | Exact repository target |
|---|---|
| `OwnerHomeService :: get_home(owner_identity) -> OwnerHomeViewModel` | New `services/owner_home_service.py` — aggregation, deterministic selection, deduplication, per-category failure isolation, `owner-home.v1` serializer |
| Owner Home data endpoint `GET /api/v1/owner/home` | New route on the existing `owner` blueprint (`owner_routes.py`; the blueprint has no url_prefix, so the absolute path registers cleanly). Flag checked before retrieval: off → neutral `404 not_found`; on → identity via `get_current_identity()`, anonymous JSON → `401 authentication_required` |
| Owner Home HTML `GET /app` behind flag | **Frontend package only, after the backend merge.** Existing `auth.owner_workspace` (`auth_routes.py:113-128`) keeps rendering `owner_workspace.html` unchanged throughout the backend slice. The frontend later owns the flag-on `owner_home.html` selection from the real view model. |
| Feature flag (default off) | `PEERSLATE_OWNER_HOME_ENABLED` env → `app.config`, following `app.py:96-97` convention (DR4; final name owned by the backend package) |
| Stored procedure `sp_owner_home_get_v1(@user_key)` | `usp_GetOwnerHomeForOwner(@UserKey)` (DR2), added to `ALLOWED_PROCEDURES` in `services/database_service.py:11` — the only allowlist change |
| Migration | `SQL FIles/Migrations/proposed/PS-HOME-001_owner_home_reads.sql` + `PS-HOME-001_owner_home_reads_rollback.sql` (DR3) |
| Verification | `SQL FIles/Verification/PS-HOME-001_owner_isolation_verify.sql` |
| Capability-availability registry | Small versioned server-owned structure in `services/owner_home_service.py` (constant/config, no member-data query) emitting `availability.{resurfaced_moment,noticed_item,connection_item}.state = "coming_later"` for the first slice |
| Tests | New `tests/test_owner_home.py` (service/route/contract/two-owner), new `tests/test_owner_home_migration.py` (shape/apply/rollback contract) |
| Package records | `docs/initiatives/PS-HOME-BACKEND-001/**` |

## 2. Preserved invariants (verbatim from the gate contracts)

The mapping keeps every rule; implementation may not weaken any of them:

1. **Nine-object maximum / three-review maximum** — enforced inside
   `usp_GetOwnerHomeForOwner` result sets (TOP 3 / TOP 1 per category) and
   re-checked by the serializer before emission.
2. **Deduplication** — an object appears only in its highest-priority
   category (review wins over recent Moment); implemented in the procedure's
   selection CTEs, tested with overlapping fixtures.
3. **Owner isolation** — `@UserKey` resolved to the owner profile inside the
   procedure exactly like `usp_ListCapturesForOwner`; no
   `owner_profile_id`-style parameter exists in the signature; two-owner
   canaries at SQL, service, and byte layers.
4. **Deterministic selection** — explicit urgency, then oldest waiting time,
   then stable opaque key; no engagement scoring; identical data ⇒ identical
   order across requests (tested by repeat-request assertion).
5. **Failure independence** — one core transactionally consistent query
   boundary; optional future adapters (insight/connection) are separately
   timed calls whose absence/failure yields an explicit unavailable category,
   never a fixture. First slice ships core-only.
6. **No-store** — `Cache-Control: private, no-store` on the JSON endpoint
   (backend) and the later flag-on `/app` HTML response (frontend; precedent:
   `owner_routes.py:507`); no server response cache; no offline persistence.
7. **Lifecycle** — read model only; deleted/tombstoned sources use the
   released Moment tombstone behavior; stale actions return
   `409 state_changed`; no Home-card table, no copied canonical body.
8. **Authorization before retrieval** — identity resolved and owner bound
   before any content query; foreign/unknown opaque selectors return
   non-enumerating `404`-class results; no broad fetch + redact.
9. **Budgets** — ≤64 KiB uncompressed JSON; 1 core query (+ ≤2 future
   adapters); no per-item loops; DB p95 ≤ 250 ms, endpoint p95 ≤ 600 ms under
   the founding-alpha profile; violations recorded as content-free metrics.
10. **Prohibitions** — no `usp_GetPeerSlateUserDashboard` / `/api/dashboard`
    reuse; no raw Capture bodies, transcripts, audio URLs, emails, internal
    numeric IDs, or other-owner data in any Home payload; JSON `null` means
    "no eligible item," never client permission to fetch more.

## 3. Response contract

`owner-home.v1` exactly as specified in `FINITE_HOME_CONTRACT.md` (schema
version, opaque `profile_key`, `generated_at`, `state_version`,
`capture_action`, `review_items[≤3]`, `recent_moment`, `resurfaced_moment`,
`noticed_item`, `connection_item`, `next_step`, `availability` map). First
slice: `resurfaced_moment`, `noticed_item`, `connection_item` are `null` with
`availability.state = coming_later`; `recent_moment` and `review_items` carry
real data; `capture_action` and `next_step` always present for a valid owner
session. The serializer allowlists fields and fails closed on unknown
columns/categories.

## 4. Review-item eligibility (manager decision U6 resolved)

Candidate initial review kinds, all real released workflows:

| Kind | Source state | Destination |
|---|---|---|
| `voice_draft_failed` | Owner-bound Voice media source in `state = 'failed'`, still actionable from its stable review flow | The released Voice review path under `/app/capture` |
| `moment_proposal_pending` | Owner-bound private Moment in `status = 'proposal'` | `/app/moments/<moment_key>/review` |
| `voice_draft_ready` | Owner-bound Voice media source in `state = 'needs_review'` | The released Voice review path under `/app/capture` |

All three kinds enter the first slice. Urgency is failed Voice first, pending
Moment proposals second, and ready Voice drafts third; within a kind, oldest
actionable `updated_at_utc` first, then stable opaque key. Confirmed, deleted,
and deletion-pending records are excluded. No engagement score is permitted.

## 5. Sequencing

`PS-HOME-BACKEND-001` merges first (flag off, JSON route neutral 404, no `/app`
or visual change), then `PS-HOME-FRONTEND-001` starts from the new `origin/main`,
consumes the real view model, and owns the flag-on HTML switch.
`services/database_service.py` takes exactly one allowlist change in this wave
(intersection I1). SQL gate: isolated apply → structural and behavioral verify
→ two-owner seed → canary tests → rollback → reapply, recorded per the released
Capture/Moment/Placement/Voice pattern.
