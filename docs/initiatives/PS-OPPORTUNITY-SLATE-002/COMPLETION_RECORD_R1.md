# PS-OPPORTUNITY-SLATE-002 — R1 completion record

Date: 2026-08-11. Protected path.

Writer: Root Codex after the governance transfer recorded through PRs 377 and 376. Original implementation provenance: Claude. Independent reviewer: fresh GPT-5.6 Sol extra-high, read-only and separate from the writer context.

## Candidate outcome

The R1 implementation is a dark, additive candidate for Opportunity Slate replacement stages 1 and 2. It includes the private blueprint/service, resilient intake, coordinated captured-source review, progressive upload/import cancellation, optimistic-concurrency fencing, the additive PS-OPPSLATE-004 migration/rollback/verifier, tests, and visual/functional evidence. The lane-mandated disposable-database gate and supplemental exact rollback inventory are complete. Package completion remains pending final exact-SHA review, PR CI, and recorded merge/release authority.

Pete reviewed the local experience and gave product approval on 2026-08-11. The pre-gate exact SHA was technically approved with zero findings. Exact review rejected later SHA `e54fcca20f05401fad8520d3eb7812582c81b2dd` with zero blocking, three important, and one minor evidence-integrity findings; those findings are repaired in the next immutable candidate and require a new exact-SHA verdict. Product approval is not represented as merge, deployment, production schema approval, or a public cutover.

## Branch and authority

- Branch: `work/2026-08-11-opportunity-slate-v2-r1`
- Worktree: `portfolio-opportunity-slate-v2-20260811`
- Final base after rebase: `f745b39b72d2c8e5a3595f88d7f9524d8d8e41cf`
- Repair implementation/evidence commit: `01d85aea2dcfb11c6d6823e5ebb68f8ba32560df`
- Exact final candidate: the next immutable commit containing this record; it will be reported to the reviewer and pushed to PR 375 only after local verification
- Writer-transfer governance: PR 377 added fail-closed transfer preflight; PR 376 recorded Root Codex as writer and fresh Sol extra-high as reviewer

## Scope integrity

All changes are within the lane's recorded surfaces. `app.py` has zero diff. The legacy Opportunity Slate implementation and PS-OPPSLATE-001/002/003 have zero diff. The schema change is additive only. No production schema was applied and no production data was mutated. Only disposable gate databases received the migration; all were deleted and confirmed absent.

## Verification

- Focused suites: 169/169 green (95 route/service/template tests; 74 migration/rollback/verifier/evidence-integrity tests).
- Browser gauntlet: 69/69 green; zero unexpected console errors and zero page errors. Real enhanced upload/import success, no-script fallback, selected-large-file boundaries, competing-submit blocking, mobile focus order, paste/enhanced-transfer outage draft recovery, and unknown-outcome retry lockout are directly exercised.
- Fresh parity: stages 1 and 2 remeasured from the locked source at desktop and narrow widths; all recorded geometry pairs fall within tolerance.
- Full suite: 3,466 tests run; four unrelated Community maintenance/environment failures/errors, identical in class to the untouched-main baseline; zero Opportunity Slate failures. The count is two higher than the pre-remediation run because of the new delete-survivor and evidence-integrity regression tests.
- Static hygiene: `git diff --check` clean; changed Python modules compile.
- SQL-engine gate: PASS on `ps-oppslate-004-gate-202608112343` at 2026-08-12T04:42:32Z; executable SHA-256 `346c29008d4bbdabcf4f81224f8d708788ac12c27a9909dbfbcac37a756ba739`; verifier SHA-256 `f0d768340721cb93133b0335130a2a8203695c4bd6d15f83479884b09cd04710`; 42 objects created, no-op reapply, strengthened two-owner verifier returned `verified = 1`, rollback completed, and forward-after-rollback restored the ledger row. A separate governed rollback at file SHA-256 `f4ac53dfa0c53454afe67dd9836830cbe433391241cbfb48ac47cb16f946a9b7` then measured exactly 42 removed catalog objects matching the gate's created-object inventory and verified the additive columns/new procedures absent and both takeover procedures restored to their exact PS-OPPSLATE-002 fingerprints.

Evidence:

- `artifacts/2026-08-11-opportunity-slate-v2/codex_final_focused_tests.txt`
- `artifacts/2026-08-11-opportunity-slate-v2/codex_final_full_tests.txt`
- `artifacts/2026-08-11-opportunity-slate-v2/codex_final_origin_main_baseline_failures.txt`
- `artifacts/2026-08-11-opportunity-slate-v2/functional_gauntlet_codex_final.json`
- `artifacts/2026-08-11-opportunity-slate-v2/parity/codex-final/PARITY_RECORD.md`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-gate.json`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-gate-attempts.json`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-rollback-proof.json`
- `artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-post-rollback-state.json`

## Independent review

The fresh reviewer withheld approval at pre-fix SHA `8a15721926087bde98feeabdace1510119af3418`, then rejected `f2fdbe09293b7d73f21a06328537b03483205b32` for two blockers and four important issues. The new implementation addresses coordinated Stage 2 drafts, correct method-specific transfer payloads, competing-submit exclusion, in-flight cancellation, paste/Stage 2 outage draft recovery, unknown-outcome truth, shared rowversion fencing, migration ownership/admission, mobile visual/focus order, multipart boundaries, unsupported-dictation status, `.doc` contract mismatch, and evidence truth.

The same reviewer context approved pre-gate SHA `fcb885ad21d1ebc2cf9f5ae3da7ee70bb9f86e43` with zero findings. The SQL-engine gate then found four verifier-only defects that static review could not prove: inline function expressions passed as `EXEC` arguments, failure to carry the latest identity rowversion into confirmation, invalid synthetic expiry backdating, and a missing Owner B identity row before the purge survivor assertion. Each gate failed closed before recording proof; each disposable database was deleted. The fifth database passed, after which exact review rejected `e54fcca20f05401fad8520d3eb7812582c81b2dd` with zero blocking, three important, and one minor finding: the runbook mislabeled the transactional verifier read-only, the legitimate explicit-delete flow lacked a surviving cross-owner canary, the gate's rollback object-count phrase was inferred rather than directly measured, and diagnostic metadata was stale. The sixth database passed the strengthened dynamic delete-survivor/stale-token verifier, and a supplemental governed rollback directly measured the exact catalog reversal and restored procedure fingerprints. The same reviewer context must inspect the next exact SHA before final technical approval.

## Release state

PR 375 is active and unmerged. The candidate is not deployed. The v2 blueprint is unregistered and its flag is unwired/default false. PS-OPPSLATE-004 is gate-proven but has not been applied to production. R1 cannot make the replacement interface live by itself.

## Honest limitations and next actions

1. Obtain new exact-final-SHA independent technical approval and green PR 375 CI.
2. Record merge/release authority in governance before merging or applying production schema; the current lane does not yet grant either authority.
3. Merge/deploy only after those records exist, then run the separately governed production apply and post-apply verification for PS-OPPSLATE-004.
4. Add the two new procedures to `services/database_service.py`'s allowlist and register/limit the blueprint only through a separately authorized writable surface.
5. Treat any R1 merge/deploy as dark additive infrastructure, not a public Opportunity Slate launch.
6. R5 cutover still depends on R2–R4, the two-mode audit, `app.py` ownership, open architecture decisions, and explicit release authority.
