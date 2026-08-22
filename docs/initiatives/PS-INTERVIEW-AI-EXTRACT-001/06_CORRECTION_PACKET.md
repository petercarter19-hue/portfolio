# PS-INTERVIEW-AI-EXTRACT-001 — correction completion packet (C1–C11)

Prepared by the sole implementation writer against rejected candidate
`6cdb48aa0f80bfd4ca86937f3fefe12c14f4c5e8`, continuing on
`work/2026-08-20-interview-ai-extract-001` from that SHA without rebase or
oracle replacement. The rejected SHA is preserved in branch history as
review evidence.

**Freeze status: NOT frozen.** Every correction is implemented except one
lawful-surface dependency C4 itself names: the exact pipeline stage list
is pinned by `tests/test_operational_readiness.py`, which is outside this
lane's writable surfaces. The retention stage is implemented in
`azure-pipelines.yml` per C4's authorization, so that one pinned test is
red until Codex lands the control-only lane expansion and this writer
makes the one-line stage-list update. The freeze follows immediately
after, with the full battery re-run.

**Requested lane-surface addition (exact):** add
`tests/test_operational_readiness.py` to the lane's `writable_surfaces`,
scoped to updating the expected stage list in
`test_pipeline_structure_enforces_exact_postdeploy_contract` to include
`InterviewTelemetryMaintenance`.

## C1–C11 reconciliation

| # | Disposition | Evidence (paths) |
|---|---|---|
| C1 | **Done.** The Interview request parsing, refusal copy, validators, signed-context behaviour, rendering, release/pricing/telemetry builders, and provider dispatch were extracted from the route bodies into the guarded package (`services/interview_ai/jobs.py`, `validation.py`, `context_tokens.py`, `contracts.py`); app.py keeps only shared-site boundary glue and aliases. The guarded manifest now covers the full closure: every package file, `services/database_service.py`, `db.py`, the lock artifact `requirements.txt`, and the locked SDK's immutable PyPI digests (`anthropic==0.112.0` wheel+sdist SHA-256, in `guarded-paths.json` `external_artifacts` and inside `runtime_core_digest`). Mechanical guards: import-closure traversal, blob recomputation, and the version tripwire — `tests/interview_ai/test_guarded_closure.py`. Every later-slice deferral statement removed (`01_FROZEN_CONTRACTS.md` §2). | `services/interview_ai/*`, `prompts/interview/contracts/guarded-paths.json`, `tests/interview_ai/test_guarded_closure.py` |
| C2 | **Done.** Resolution now enforces compatibility, not just consistency: exact current `guardian_set_version` and `contracts_version` (registry AND guarded manifest), sentinel validity (`initial_extraction: true` ⇒ exactly the parity sentinel and zero runs; anything else ⇒ never the sentinel and ≥1 full-digest run), full-hash slot-ordered bundle refs, recomputed core/candidate/release identities, and D8-by-construction for prior entries. Adversarial tests recompute internally consistent `incompatible-guardian@999`-style records (plus sentinel misuse, fabricated runs, swapped slots, incompatible prior entry) and prove `service_not_configured` with zero dispatch, with a genuine-record control case. | `services/interview_ai/release.py`, `tests/interview_ai/test_release_resolution.py` (`AdversarialCompatibilityTests`) |
| C3 | **Done.** DDL adds fixed `event_type='server_call'`, pins `operation_id IS NULL` and `guardian_rejections = '[]'`, enforces the parent/child relation with a self-referencing FK (parents appended first, no parent/usage/cost on parents), and CHECK-pins the C6 provider taxonomy. The append procedure shape-closes all three JSON documents with OPENJSON (exact key sets, integer bounds 0–32, closed stop-reason enum, three-key exception-attr allowlist) and handles duplicates concurrency-safely (PK-violation catch; prior row never modified). Purge batch bound is 1..5000. Executable disposable proof: 22/22 checks (permission separation both directions, silent duplicate incl. a cross-connection race, every shape rejection, 89/91-day retention boundary, oversize batch refusal, both rollback-guard branches, forward idempotency) — no production SQL contacted; the governed gate also passed and is recorded in the migration registry. | `SQL FIles/Migrations/proposed/PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql`, `scripts/interview_ai/run_interview_telemetry_sql_proof.py`, `05_SQL_DISPOSABLE_PROOF.json`, `SQL FIles/Migrations/registry.json` (gate) |
| C4 | **Implemented; freeze-blocking surface item returned to Codex.** Dedicated schedule (`Interview telemetry retention nightly`, cron 41 2 * * *), own display-name-gated stage, own default-off `interviewTelemetryMaintenanceEnabled`, dedicated `INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING`, zero Community identity/flag/schedule reuse, both stages pinned so neither cron can trigger the other (tested both directions), purge report artifact published on every run including failures. `tests/test_operational_readiness.py` untouched as instructed; its stage-list pin is the requested lane expansion above. | `azure-pipelines.yml`, `scripts/interview_ai/run_interview_telemetry_purge.py`, `tests/interview_ai/test_slice_governance.py` (`PipelineIsolationTests`) |
| C5 | **Done.** Follow-up rows record `question: 2`, `answer: 1` (grounded and generic), other classes matching the real request, `history_selection` 0; the grounded/generic bundle manifests concretely declare `answer` with `server_derived` provenance and the "never member History" note; per-specialist manifests are now genuinely concrete (planning_hints is structurally question+role_context only). Tested for initial and follow-up, grounded and generic, plus manifest-content assertions. | `services/interview_ai/jobs.py` (`_generate`), `scripts/interview_ai/build_release_identity.py` (`ACCEPTED_SOURCE_CLASSES`), `tests/interview_ai/test_telemetry_contract.py`, `tests/interview_ai/test_slice_governance.py` (`InputManifestTests`) |
| C6 | **Done.** Persisted provider `failure_reason` ∈ {transport, timeout, rejected, abandoned-reserved}; SDK-shaped values prohibited (CHECK `CK_iasc_provider_reason_state` + disposable-proof rejection + code mapping); granular normalized classes remain only in the closed exception-class field; a repository test proves no emission path for `abandoned`. Code, contracts, SQL enums, and tests updated together. | `services/interview_ai/constants.py`, `telemetry.py` (`normalize_provider_error`), the DDL, `01_FROZEN_CONTRACTS.md` §4.2/§4.3, `tests/interview_ai/test_telemetry_contract.py` |
| C7 | **Done.** All Interview logging is fully normalized: exception classes map to the frozen allowlist (`normalize_exception_class`; unknown → `server_fault`), every stop reason passes `normalize_stop_reason` (unknown → `unknown`), and no raw Python/SDK class name or raw stop value can appear — including the generic route handlers, telemetry assembly/append failures, and release-resolution failures. Sentinels inject a unique unallowlisted class and stop value and prove neither marker reaches captured logs; a source-level guard forbids `type(...).__name__` formatting anywhere in the guarded runtime. | `services/interview_ai/telemetry.py`, `jobs.py`, `release.py`, `tests/interview_ai/test_telemetry_contract.py` (`BoundedLoggingTests`) |
| C8 | **Done.** The release plan now requires, at the future separately authorized gate: schema/permissions/purge ready → identity verification → **set the configuration while the legacy runtime (which safely ignores it) is still deployed** → deploy the matching candidate → verify boot compatibility and provider-free smoke. The outage nature of deploying with the setting absent/malformed/unknown/incompatible is stated plainly. This packet authorizes no configuration set and no deployment. | `03_ROLLBACK_EVIDENCE.md` (First-deploy ordering) |
| C9 | **Done.** Ordinary code rollback uses the prior artifact and retains telemetry with the purge operating; configuration rollback is D8-only (enforced by resolution, adversarially tested); the rollback SQL refuses a nonempty table with a retention-naming error and completes only against an empty one (both branches executably proven); nonempty-table retirement is named as its own future retention-safe operation. | `SQL FIles/Migrations/proposed/PS-INTERVIEW-AI-EXTRACT-001_telemetry_rollback.sql`, `03_ROLLBACK_EVIDENCE.md`, `05_SQL_DISPOSABLE_PROOF.json` |
| C10 | **Done.** Eight new deterministic provider-free fixtures recorded from the same untouched legacy checkpoint via a detached provenance worktree: public best_practice follow-up, public compare follow-up (four provider calls across two steps), and six authenticated variants (owner evidence, member empty-evidence, marker gate, member grounded insufficient, follow-up refusal, nudge). The original oracle was not replaced: the C10 run re-recorded all 32 committed fixtures byte-identically to the committed tree; measured against oracle commit `7e3f97f7` itself, 30 of 32 are byte-identical and the two member_history follow-up fixtures differ by exactly one recorded-request line each — the deliberate `__STEP1_CONTEXT_TOKEN__` secret-scanner normalization from `cea5ec67`, outside every parity comparison surface (stated precisely per B6). All 40 replay against the candidate with zero differences. | `tests/interview_ai/fixtures/parity/` (40 files), `scripts/interview_ai/record_parity_fixtures.py`, `02_PARITY_EVIDENCE.md` |
| C11 | **Done.** Every fixture-count statement corrected to 32 original + 8 added = **40**; the replay suite asserts the fixture set equals its expectation map exactly, so the documented count and the discovery result cannot drift. | `02_PARITY_EVIDENCE.md`, `01_FROZEN_CONTRACTS.md` §6, `tests/interview_ai/test_parity_replay.py` |

## Verification (correction round, clean worktree, exact branch)

All commands run with the repository venv Python; placeholder provider key
only; no network provider request anywhere.

| Command | Result |
|---|---|
| `delivery_preflight.py --package PS-INTERVIEW-AI-EXTRACT-001 --intent write --fetch --require-clean` | pass (recorded at hand-back on the pushed tip) |
| `build_release_identity.py --verify` | pass — every bundle hash, guarded blob, external digest, and release identity recomputes |
| `python -m unittest discover -s tests/interview_ai -q` | 79 tests, OK (40/40 parity subtests) |
| `python -m unittest tests.test_interview_studio tests.test_database_service -q` | 320 tests, OK |
| `govern_sql_migrations.py check` | registry consistent; 19 gated incl. PS-INTERVIEW-AI-EXTRACT-001; every proof matches disk |
| `python -m compileall app.py services/interview_ai scripts/interview_ai tests/interview_ai` | clean |
| `git diff --check 5322f105..HEAD` | clean |
| Disposable SQL proof (`run_interview_telemetry_sql_proof.py`) | pass, 22/22 checks (`05_SQL_DISPOSABLE_PROOF.json`) |
| Full `python -m unittest discover -s tests -q` | 3,976 tests; failures: the four disclosed base-reproducible local failures (Community maintenance ×3, disposable-proof permissions ×1) plus exactly one expected red — the `test_operational_readiness` stage-list pin awaiting the requested lane expansion |

## Statement of non-action

No provider call, no real provider key, no evaluation spend, no migration
apply against any production database (the gate and proof used only the
throwaway `ps-interview-extract-gate-20260820`, created for the proof and
deleted after it), no App Service or production configuration change, no
merge, no deployment, no enablement, and no production claim occurred in
this correction round.

## Remaining limitations (none recast as deferrals)

1. The C4 stage-list test update awaits the requested lane-surface
   expansion; until then `test_operational_readiness` is red by exactly
   that one pin and the candidate is not frozen.
2. The four disclosed Windows-local test failures reproduce at the
   untouched branch base and touch no path in this slice.
3. Authenticated fixtures drive the real owner/member context-construction
   code through recorded synthetic identity seams; identity-storage outage
   and signed-out refusals remain covered by the pre-existing
   authenticated-path suite.
4. Pete's Foundry model direction remains outside Extract; the later
   provider/model evaluation package must recover the accepted API Gate
   decisions rather than reopening them.

---

## Consolidated B1–B6 round (review of a0402d33, 2026-08-21)

Disposition received: CORRECTIONS REQUIRED on
`a0402d33d066baa18e446bad2f632a48e2f84380`. All six items implemented;
current `origin/main` (`f6419d4f`) merged without rebase; the oracle and
every rejected-history SHA are preserved.

| Item | Resolution | Evidence |
|---|---|---|
| B1 external trust root + monotonic versions | `anchor-trust-root.json` pins the manager-review SHA, committed blob hash, prefix digest, count, latest chain; `--verify` extends-the-prefix + git cross-check; versions parsed, regression/reuse rejected; append strictly advances | 07 matrix cases b1_8–b1_15 (all executed, all fail as required); sixth anchor at `interview-contracts@6` |
| B2 complete guarded app closure | 19 fragments + identity.py / owner_authorization.py / resume_data.json / error.html guarded; mechanical transitive closure analyzer + live-registration and unguarded-hook no-op proofs | `services/interview_ai/app_closure.py`; `tests/interview_ai/test_guarded_app_closure.py` (9 tests) |
| B3 boot-immutable state + full closure | `boot.py` write-once state, initialized inside the guarded route-boundary fragment at import; requests read only the frozen state; lock recomputed with flask + Flask-Limiter roots → 42 distributions | `tests/interview_ai/test_boot_state.py` (8 tests incl. post-boot mutation); regenerated lock/vendor-args/constraints |
| B4 closed state machine | `ROW_STATE_MATRIX` enforced in Python and SQL (named errors 50040–50049 + table constraints); strict counts/durations/attrs (no clamp/coerce); class+attrs null-together; attrs object-only | 17 py_matrix cases; 21 sql_matrix checks in the 88/88 disposable proof on `ps-interview-extract-gate-b6-20260821` (created and deleted 2026-08-21; fresh gate receipt in registry.json) |
| B5 strict deployable manifest | shared parser `evaluation_manifest.py` (build + runtime + boot); closed key sets; exactly 42 categorized sources; canonical sorted traversal-free paths; recomputed aggregate | `tests/interview_ai/test_evaluation_manifest.py` (22-case hostile matrix + control) |
| B6 runtime replay | all 40 fixtures replayed against the corrected candidate in the provisioned Flask/Flask-Limiter environment (versions congruent with the lock), zero differences | `09_PARITY_REPLAY_RESULT.json` |

---

## B1–B3 second round (review of 7485eae9, 2026-08-21)

Disposition: CORRECTIONS REQUIRED on B1/B2/B3 (B4/B5/B6 and current-main
reconciliation accepted). `origin/main` already current; oracle and every
rejected-history SHA preserved (the @6 anchor is kept; the chain now runs
@1→@7).

| Item | Resolution | Evidence |
|---|---|---|
| B1 external custody + adjacency | Trust record relocated to `docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/ANCHOR_TRUST_ROOT.json` (outside writer surfaces), five reviewed values embedded in the guarded tripwire and required to agree; every adjacent anchor must strictly advance a governed version | Independent recheck: `rewritten_local_root_verifies=False`, `same_version_lineage_verifies=False`; matrix b1_15, b1_16 |
| B2 retired route | `interview_retired_coach_contract` fragment guards the 410 endpoint; live function in the liveness proof; rate/body/status mutation attacks | matrix b2_retired_coach_rate/body/status; `test_guarded_app_closure.py` |
| B3 requests never initialize | `_release_or_refusal` reads only `boot.state()`; absent state → 503; jobs never name `resolve_active_release` | `test_boot_state.py` (absent-state-503-without-init, ready-path-no-init, no-lazy-resolver-in-jobs, fresh-process-import) |

---

## Operational-readiness grant applied (2026-08-21)

`origin/main` `424f2efe` ("Govern Interview Extract review controls
[skip ci]") recorded Codex's acceptance of the B1–B6 corrections on
reviewed unfrozen SHA `75318ec2`, established package-manager custody of
`docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/ANCHOR_TRUST_ROOT.json`
(byte-identical to the writer's copy — same five reviewed values), and
appended `tests/test_operational_readiness.py` to the Extract lane's
writable surfaces. Verified from `origin/main` directly (control record
`interview_extract_review_control_repair`: target package, target branch,
reviewed SHA, and added surface all match) and merged (`origin/main`
reconciled; write preflight passes). The single previously-withheld
change is now applied: the pipeline stage-list assertion in
`tests/test_operational_readiness.py` gains `InterviewTelemetryMaintenance`
(the stage already present in `azure-pipelines.yml`), so the exact-literal
contract matches the pipeline. No other line of that test changed; the
environment-name literal assertion is preserved. That was the last open
lane item.
