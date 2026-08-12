# PS-OPPORTUNITY-SLATE-002 — R1 completion record

Date: 2026-08-11. Protected path.

Writer: Root Codex after the governance transfer recorded through PRs 377 and 376. Original implementation provenance: Claude. Independent reviewer: fresh GPT-5.6 Sol extra-high, read-only and separate from the writer context.

## Candidate outcome

The R1 application for Opportunity Slate replacement stages 1 and 2 is implemented, independently approved, merged, and deployed dark. It includes the private blueprint/service, resilient intake, coordinated captured-source review, progressive upload/import cancellation, optimistic-concurrency fencing, tests, and visual/functional evidence. The blueprint remains unregistered and `app.py` untouched, so the replacement is not public.

The additive PS-OPPSLATE-004 production apply is the remaining release leg. Governed run 836 failed safely and transactionally because the least-privilege schema principal could not `SELECT` protected historical rows for three `WITH CHECK` validations. The ledger remained at 26 and no 004 surface remained. The repaired migration now uses enabled `WITH NOCHECK` constraints only for the three same-transaction nullable columns; exact restricted-principal proof, a fresh full gate, and an exact 42-object supplemental rollback all pass. Completion remains pending fresh exact-SHA review, repair PR CI/merge, production apply, and live dark verification.

Pete reviewed the local experience and gave product approval on 2026-08-11. The pre-gate exact SHA was technically approved with zero findings. Exact review rejected later SHA `e54fcca20f05401fad8520d3eb7812582c81b2dd` with zero blocking, three important, and one minor evidence-integrity findings; those findings are repaired in the next immutable candidate and require a new exact-SHA verdict. Product approval is not represented as merge, deployment, production schema approval, or a public cutover.

## Branch and authority

- Original implementation branch/SHA: `work/2026-08-11-opportunity-slate-v2-r1` at independently approved `550c7ca87561a8279d571738c5832f3a70fe9bec`
- Original merge/deploy: PR 375, main `b7bb92ddd00ba115fddb11c96e2fd52c274833a1`, successful pipeline 834, dark/unregistered
- Repair branch/worktree: `work/2026-08-12-opportunity-slate-r1-schema-permission-repair` / `portfolio-oppslate-schema-permission-repair-20260812`
- Repair base: `e9d4ce573aa57b4dc89a82072a9d892bb31011aa`
- Exact repaired candidate: this immutable repair commit; its SHA is recorded in the independent verdict and Azure PR rather than self-referentially inside the commit
- Writer-transfer governance: PR 377 added fail-closed transfer preflight; PR 376 recorded Root Codex as writer and fresh Sol extra-high as reviewer

## Scope integrity

All repair changes are within the lane's recorded migration, verifier, test, package-record, and evidence surfaces. `app.py` and every application/visual file have zero repair diff. The legacy Opportunity Slate implementation and PS-OPPSLATE-001/002/003 have zero diff. The schema remains additive only. Run 836's transaction rolled back, so no production schema or data change remained. The repair's one Basic disposable database was deleted and confirmed absent.

## Verification

- Focused suites: 171/171 green (95 route/service/template tests; 76 migration/rollback/verifier/evidence-integrity tests).
- Browser gauntlet: 69/69 green; zero unexpected console errors and zero page errors. Real enhanced upload/import success, no-script fallback, selected-large-file boundaries, competing-submit blocking, mobile focus order, paste/enhanced-transfer outage draft recovery, and unknown-outcome retry lockout are directly exercised.
- Fresh parity: stages 1 and 2 remeasured from the locked source at desktop and narrow widths; all recorded geometry pairs fall within tolerance.
- Full suite at the permission-repair candidate: 3,576 tests run; the same four unrelated Community maintenance/environment failures/errors by exact test identity as the established untouched-main baseline; zero Opportunity Slate failures. The higher total reflects intervening mainline test additions plus this repair's two new migration assertions.
- Static hygiene: `git diff --check` clean; changed Python modules compile.
- Restricted-principal engine proof: the original `WITH CHECK` form reproduced the production `SELECT permission was denied` failure. The replacement `WITH NOCHECK` form succeeded with `ALTER` and denied `SELECT`, remained enabled/untrusted, rejected invalid future DML, and accepted valid DML. The exact repaired migration then succeeded as a production-shaped `db_ddladmin` user with zero `SELECT` on both protected tables; the owner-isolation verifier returned `verified = 1`, and exact rollback removed 004.
- Fresh SQL-engine gate: PASS on `ps-oppslate-004-perm-202608121325` at 2026-08-12T13:27:59Z; executable SHA-256 `f4752c0e9cf176d26bd4239a5cf13bbc99e7614fa1da7fae6087705d79acb73a`; verifier SHA-256 `7bb5a62009c1038779c0f21772e0ef37318525d7051c9998504e9fa20521fe97`; 42 objects created, no-op reapply, verifier `verified = 1`, 42-object rollback rehearsal, and forward-after-rollback. A separate governed rollback removed exactly the gate's 42-object inventory and restored both takeover definitions to their PS-OPPSLATE-002 fingerprints. The database was deleted and confirmed absent.

Evidence:

- `artifacts/2026-08-11-opportunity-slate-v2/codex_final_focused_tests.txt`
- `artifacts/2026-08-11-opportunity-slate-v2/codex_final_full_tests.txt`
- `artifacts/2026-08-11-opportunity-slate-v2/codex_final_origin_main_baseline_failures.txt`
- `artifacts/2026-08-11-opportunity-slate-v2/schema_permission_repair_tests.txt`
- `artifacts/2026-08-11-opportunity-slate-v2/functional_gauntlet_codex_final.json`
- `artifacts/2026-08-11-opportunity-slate-v2/parity/codex-final/PARITY_RECORD.md`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-gate.json`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-permission-proof.json`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-gate-attempts.json`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-rollback-proof.json`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-post-rollback-state.json`

## Independent review

The fresh reviewer withheld approval at pre-fix SHA `8a15721926087bde98feeabdace1510119af3418`, then rejected `f2fdbe09293b7d73f21a06328537b03483205b32` for two blockers and four important issues. The new implementation addresses coordinated Stage 2 drafts, correct method-specific transfer payloads, competing-submit exclusion, in-flight cancellation, paste/Stage 2 outage draft recovery, unknown-outcome truth, shared rowversion fencing, migration ownership/admission, mobile visual/focus order, multipart boundaries, unsupported-dictation status, `.doc` contract mismatch, and evidence truth.

The same reviewer context approved pre-gate SHA `fcb885ad21d1ebc2cf9f5ae3da7ee70bb9f86e43` with zero findings. The SQL-engine gate then found four verifier-only defects that static review could not prove: inline function expressions passed as `EXEC` arguments, failure to carry the latest identity rowversion into confirmation, invalid synthetic expiry backdating, and a missing Owner B identity row before the purge survivor assertion. Each gate failed closed before recording proof; each disposable database was deleted. The fifth database passed, after which exact review rejected `e54fcca20f05401fad8520d3eb7812582c81b2dd` with zero blocking, three important, and one minor finding: the runbook mislabeled the transactional verifier read-only, the legitimate explicit-delete flow lacked a surviving cross-owner canary, the gate's rollback object-count phrase was inferred rather than directly measured, and diagnostic metadata was stale. The sixth database passed the strengthened dynamic delete-survivor/stale-token verifier, and a supplemental governed rollback directly measured the exact catalog reversal and restored procedure fingerprints. The same reviewer context must inspect the next exact SHA before final technical approval.

## Release state

PR 375 is merged and its application code deployed dark. The v2 blueprint remains unregistered and its flag unwired/default false. PS-OPPSLATE-004 is freshly gate-proven but not applied to production after run 836's safe rollback. The repair is not yet reviewed, merged, or production-applied. R1 cannot make the replacement interface public by itself.

## Honest limitations and next actions

1. Obtain fresh exact-repair-SHA independent technical approval and green repair-PR CI.
2. Record a new exact-SHA merge/release grant before merging or applying production schema.
3. Merge the repair, apply exactly PS-OPPSLATE-004 through the governed production stage, and verify ledger 26 to 27 plus the enabled/untrusted checks.
4. Add the two new procedures to `services/database_service.py`'s allowlist and register/limit the blueprint only through a separately authorized writable surface.
5. Treat any R1 merge/deploy as dark additive infrastructure, not a public Opportunity Slate launch.
6. R5 cutover still depends on R2–R4, the two-mode audit, `app.py` ownership, open architecture decisions, and explicit release authority.
