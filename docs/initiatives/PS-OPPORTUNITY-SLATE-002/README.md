# PS-OPPORTUNITY-SLATE-002 — Opportunity Slate replacement

Owner: Pete. Protected path.

Architecture authority: `artifacts/2026-08-11-opportunity-slate-architecture/OPPORTUNITY_SLATE_ARCHITECTURE.md`, Pete's 2026-08-11 owner decisions, the eleven hash-pinned visual files, and `PeerSlate_Independent_Visual_Experience_Review_2026-08-09.pdf`.

## Current status

R1 stages 1 and 2 are implemented, independently approved, merged through PR 375 as `b7bb92ddd00ba115fddb11c96e2fd52c274833a1`, and deployed dark by successful main run 834. The blueprint remains unregistered, `app.py` is untouched, the flag is unwired/default false, the legacy experience remains live, and nothing is public.

The first governed production schema apply, run 836, failed safely and transactionally when the least-privilege schema principal tried to validate three new `WITH CHECK` constraints by reading protected historical rows. PS-OPPSLATE-004 remained absent and the production ledger stayed at 26. This repair changes only those three existing-table constraint additions to `WITH NOCHECK`: the columns are created nullable in the same transaction, so all old values are already `NULL`; the constraints remain enabled and reject invalid future writes, while their untrusted catalog state honestly records that old rows were not scanned.

The repaired exact forward passed on disposable Azure SQL as a production-shaped `db_ddladmin` principal with zero `SELECT` on both protected tables, then passed the full six-step gate and exact 42-object supplemental rollback. Fresh exact-SHA independent review, repair PR CI/merge, and the governed production re-apply remain pending.

Implementation began under Claude. Writer authority transferred to Root Codex through governance PRs 377 and 376 before Codex changed the package. The transfer is recorded in `CURRENT_LANES.json`; the original authorship history remains intact.

A fresh GPT-5.6 Sol extra-high reviewer audited pre-fix candidate `8a15721926087bde98feeabdace1510119af3418`, then rejected remediation candidate `f2fdbe09293b7d73f21a06328537b03483205b32` after finding transfer-payload, competing-submit, storage-outage recovery, mobile focus-order, multipart-boundary, and completion-truth gaps. Root Codex remediated both review rounds and refreshed the evidence. The reviewer approved `fcb885ad21d1ebc2cf9f5ae3da7ee70bb9f86e43` with zero findings, then rejected post-gate SHA `e54fcca20f05401fad8520d3eb7812582c81b2dd` with zero blocking, three important, and one minor evidence-integrity findings. Those findings are repaired; one final exact-SHA review remains mandatory.

Branch: `work/2026-08-12-opportunity-slate-r1-schema-permission-repair`.

Current authoritative repair base: `origin/main` at `e9d4ce573aa57b4dc89a82072a9d892bb31011aa`.

## R1 outcome

The replacement is a private, signed-in workroom for one member-brought role at a time. R1 delivers:

1. A new Flask blueprint at `/opportunity-slate`, intentionally unregistered in this slice.
2. Stage 1 paste/type/dictate, upload, and public-link import. Upload/import have explicit in-flight status and cancellation when JavaScript is available; plain HTML POST remains the fallback. Draft text and URL values survive validation and service failures. `.doc` is not advertised because the intake service does not support it.
3. Stage 2 source identity, captured wording correction, explicit confirmation, and replace/delete controls. One coordinated HTML form carries every visible draft to each documented action endpoint. Confirmation is refused when visible identity or wording differs from stored state, so stale wording cannot be confirmed and edits are not silently discarded.
4. Additive migration `PS-OPPSLATE-004`: one R1 identity table, the planned R2 table/column shapes named by the architecture, and guarded purge/delete procedure takeovers. The migration refuses malformed or unowned partial surfaces; forward migration stamps independently droppable objects/columns, and rollback verifies those stamps before removal.
5. Owner-scoped service and route behavior with sign-in, feature, same-origin, no-store/noindex, idempotency, and optimistic-concurrency controls.
6. Locked-visual parity evidence for stages 1 and 2 at desktop, 320px, and a 390×844 first-fold check.

The blueprint flag defaults false and the blueprint is registered nowhere. Production behavior is unchanged.

## Writable surfaces used

```text
opportunity_slate_v2_routes.py
services/opportunity_slate_v2_service.py
templates/opportunity_slate_v2/
static/css/opportunity-slate-v2.css
static/js/opportunity-slate-v2.js
SQL FIles/Migrations/proposed/PS-OPPSLATE-004_opportunity_slate_replacement.sql
SQL FIles/Migrations/proposed/PS-OPPSLATE-004_opportunity_slate_replacement_rollback.sql
SQL FIles/Migrations/registry.json
SQL FIles/Verification/PS-OPPSLATE-004_owner_isolation_verify.sql
tests/test_opportunity_slate_v2.py
tests/test_opportunity_slate_v2_migration.py
docs/initiatives/PS-OPPORTUNITY-SLATE-002/
artifacts/2026-08-11-opportunity-slate-v2/
```

`app.py`, the legacy Opportunity Slate implementation, and PS-OPPSLATE-001/002/003 remain untouched.

## Important implementation contracts

- Identity writes and wording writes share `opportunity_sources.row_version`. An accepted identity write advances the source timestamp and therefore the shared rowversion; a second write using the old token is refused.
- Failure rendering distinguishes a known refusal/current state from an unknown database outcome. It preserves attempted drafts and never promises that a timed-out write definitely did or did not land.
- Upload/import enhancement uses `fetch` and `AbortController` only when supported. Cancellation does not erase the member's intake draft.
- Truncation uses a bounded, non-sensitive notice enum on the success redirect. It does not introduce a signing secret or echo member content into the URL.
- Dictation degrades to an explicit visible status when unsupported.
- Mobile Stage 1 orders the dominant paste input and primary action before alternate methods. At 390×844 the primary action bottom measured 842px, with alternatives immediately after it.
- Every stored procedure derives ownership from `UserKey`; no caller-supplied owner id is accepted.
- The migration will not adopt a name-compatible pre-existing object or column. Reapply requires a complete recorded surface and ownership stamps.

## Verification

- Focused package suites after the permission repair: 171/171 green (`test_opportunity_slate_v2.py` 95; `test_opportunity_slate_v2_migration.py` 76).
- Real-browser functional gauntlet: 69/69 green, with zero unexpected console or page errors. It includes real enhanced upload/import success, plain-HTML method-specific fallback, selected-large-file boundaries, competing-submit blocking, cancellation, draft preservation, paste/enhanced-transfer storage failure injection, unknown-outcome retry lockout, mobile visual/focus order, dirty-form confirmation refusal, double-submit idempotency, history navigation, 320px/390px behavior, and 200%-equivalent reflow.
- Full repository suite at the permission-repair candidate: 3,576 tests run; four failures/errors with the exact same unrelated Community maintenance/environment test identities as the established untouched-main baseline; zero Opportunity Slate failures. The repository-wide result is therefore not described as fully green.
- `git diff --check` clean and changed Python modules compile.
- Fresh parity screenshots and measurement records are under `artifacts/2026-08-11-opportunity-slate-v2/parity/codex-final/`.

The authoritative repaired gate passed on `ps-oppslate-004-perm-202608121325` at 2026-08-12T13:27:59Z against executable SHA-256 `f4752c0e9cf176d26bd4239a5cf13bbc99e7614fa1da7fae6087705d79acb73a`. Before the full gate, the exact forward succeeded as a production-shaped `db_ddladmin` principal with zero `SELECT` on `opportunity_analyses` and `opportunity_requirement_sets`; all three checks were enabled/untrusted and the owner-isolation verifier returned `verified = 1`. The six-step gate proved 42 objects, idempotent reapply, verifier success, rollback, and forward-after-rollback. A supplemental governed rollback removed exactly those same 42 catalog objects and restored both takeover procedures to their PS-OPPSLATE-002 fingerprints. The Basic database existed for about nine minutes, was deleted and confirmed absent, and has a conservative under-$0.01 incremental cost expected to be absorbed by existing credits. Production run 836 remains the only production attempt and left no 004 schema behind.

## Review finding disposition

All blocking and important findings from the `8a157219` and `f2fdbe09` reviews, plus all evidence-integrity findings from the `e54fcca2` review, are remediated in the new candidate:

1. Coordinated Stage 2 drafts prevent stale confirmation and cross-form edit loss.
2. Upload/import expose in-flight cancellation and preserve drafts through cancel/failure.
3. Failure copy and recovery no longer overpromise write outcomes.
4. Identity writes advance the shared source rowversion.
5. Migration admission and rollback require complete owned surfaces.
6. Stage 1 mobile first-fold hierarchy puts the primary action before alternate methods.
7. Unsupported dictation has visible accessible status.
8. Completion and evidence records are refreshed rather than inheriting stale claims.
9. `.doc` was removed from the browser accept contract.
10. Historical trailing whitespace was removed from `r3_test_run.txt`.
11. Enhanced transfer payloads are built explicitly by method before controls enter the busy state, and real success is browser-proven.
12. An active transfer blocks every competing capture submit until success, failure, or cancellation.
13. Paste and every Stage 2 pre-write storage outage preserve posted member work in truthful recovery states.
14. Stage 1 DOM, focus, screen-reader, and mobile visual order are all paste → primary action → alternate methods.
15. Only upload opts into multipart encoding; paste/import omit selected file bytes, including with JavaScript disabled.
16. Unknown-outcome intake recovery disables immediate retry until the member reloads verified storage.
17. The production verifier is described truthfully as rollback-contained transactional writes requiring execute/write authority; it is not called read-only.
18. Legitimate explicit delete now keeps an equivalent second-owner data shape alive and asserts it survives, while forged-key and stale-token deletes are refused.
19. Supplemental rollback evidence directly matches all 42 removed catalog objects to the gate inventory and verifies the restored takeover fingerprints.

The same fresh reviewer context that found these issues must review the exact final SHA before technical approval.

## What R1 does not include

- No AI interpretation, requirement review, qualification analysis, save/history, cutover, or legacy retirement.
- No `app.py` registration, limiter attachment, or feature-flag environment change.
- No durably committed production schema or data change and no removal of legacy schema. Run 836 opened production and attempted the 004 transaction, then failed closed and rolled back; the repaired production apply remains a separately governed operation.
- No public or member-visible replacement. R5 remains the cutover package after R1–R4 and its two-mode audit.
- The replacement's shared shell still follows the production `base.html`, not the mockup shell. Shared-shell direction is outside this lane.
- `services/database_service.py` still needs the two R1 procedures added to its allowlist before real-database use; that file is outside this lane.
- Architecture decisions D-1 through D-13 and old PRs 250/251 remain outside this R1 closeout.

## Next governed actions

1. Freeze the repaired post-gate SHA and obtain the same fresh Sol extra-high exact-SHA review.
2. Push the repair branch, obtain green Azure PR CI, and record a fresh exact-SHA merge/release grant.
3. Merge the repair dark and rerun the governed production apply for exactly PS-OPPSLATE-004; verify ledger 26 to 27 and the enabled/untrusted constraint state.
4. Verify `/healthz`, the unchanged legacy route, and the still-unregistered v2 route. Do not call it a public Opportunity Slate launch.
5. Activate the later packages and resolve the `app.py`/allowlist ownership dependencies before R5 cutover.
