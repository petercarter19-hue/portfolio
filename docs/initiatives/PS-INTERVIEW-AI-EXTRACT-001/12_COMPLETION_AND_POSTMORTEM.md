# PS-INTERVIEW-AI-EXTRACT-001 — completion record and postmortem

_Written 2026-08-22/23 by the Extract completion manager (Claude, session
0c6f769d) under Pete's end-to-end completion authority. Plain-English
first; identifiers at the end of each section. Facts marked **(live)**
were read from Azure or the database at the time stated, never from a
repository record._

## 1. Outcome in one paragraph

Everything below the runtime is done and stays done: the telemetry
schema is applied in production, the two least-privilege database
identities are bound and verified, nightly retention is enabled and its
purge path was executed once under the real maintenance identity, and
the fail-closed release-set configuration is set. The extracted runtime
was merged and deployed (run 1450) and the site stayed healthy - but at
startup every worker logged "interview runtime lock failed closed: 29
violation(s)", so the Interview AI path froze as service_not_configured
(fail-closed, by design). That is a named stop condition, and the
runtime was **rolled back** the same hour to the previous build (the
Sign-in deploy, 191fb238), which the schema, identities, retention and
configuration do not affect. No provider call was made and no evaluation
was run. Three real defects were found and fixed before the deploy, and
one was found by the deploy (section 4).

## 2. Final state (live)

| Fact | Value |
|---|---|
| Live `/healthz` after the runtime deploy | `8a2e8854d92e5181e1f2f274` = `release_id_for_build(d066d255…, '1450')` (derived, matched) |
| Live `/healthz` after the rollback | `9a511ab87a776da231f56217` = `release_id_for_build(00f73f86…, '1453')` (derived, matched; runtime paths byte-identical to 191fb238) |
| Runtime deploy | PR 576 squash `d066d2556cb7124a10c499bbc00c9222ca4d709c` (projection `297d6a2f`), automatic run 1450: Build succeeded, ProductionWebDeploy stage succeeded (DeployWebApp phase succeeded, liveness task succeeded); manual fallback 1451 correctly refused as a duplicate |
| Rollback | PR 584 (revert `552b4be2` of `d066d255`, auto-complete, not `[skip ci]`) → main `00f73f86887d80645524626a0def44e52f79c9c9`, run `1453`, ProductionWebDeploy `succeeded (DeployWebApp phase succeeded; liveness task succeeded)` |
| Boot readiness (startup logs only, R9) | **Not reached.** The container log for the 22:43:36Z start shows 5 gunicorn workers booting and then, 5 times, `interview runtime lock failed closed: 29 violation(s)`; no `interview boot state frozen:` line at all (the app's INFO level is not captured, the WARNING was) |
| Schema | `PS-INTERVIEW-AI-EXTRACT-001` applied 2026-08-22T22:27:00Z by governed run 1448 (main `d24b87b2`), digest `83ab8c082ea4e8ba939ca1dcbee1636582295db56ef050f31b42e11a354145ab`, gate `ps-interview-extract-gate-c6-20260822` (deleted) |
| Identities | `interview_telemetry_append` ← `peerslate-pete` (App Service identity); `interview_telemetry_maintenance` ← `peerslate-interview-telemetry-maintenance` (Entra app `852e20b0-…`); explicit DENYs on the application identity for the purge procedure and direct table access; `verify` pass |
| Retention | `interviewTelemetryMaintenanceEnabled=true`; schedule `Interview telemetry retention nightly` (`41 2 * * *`), isolated from Community by schedule display name; purge runs inside `AzureCLI@2` bound to the Interview WIF service connection (`90f8b9b6-…`); readiness execution as the maintenance identity: deleted 0, 1 batch, `more_remaining 0` |
| Configuration | `PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET=1b9441a052593a2a17837572b659325c7ca3d0dfc46f018e9283949ee7caa935` |
| Application logging | enabled (file system, Information; container logging on) before the runtime deploy so the startup line could be read |
| Rollback target | build 1442 / main `191fb238` (release `e233aa24f62f9073f9bf8ed1`), the Sign-in deploy that preceded this one — **not** the 19 August build |
| PR 564 | abandoned (superseded by PR 576) |
| Interview AI in production now | the pre-extraction (legacy) runtime, as before this package; the extracted runtime is merged on `main` history but reverted |

## 3. What was done, in order

1. **Dark telemetry infrastructure** landed repository-only (PR 567 → `28ed3244`, earlier).
2. **Governed schema apply — first attempt refused.** Run 1419 applied the
   reviewed `c3` migration and SQL Server refused it ("user does not have
   permission"); the transaction held and nothing was written.
3. **Correction (PR 578).** Migration carries schema only; roles, grants,
   the maintenance user, memberships and the application DENYs moved into
   `scripts/configure_interview_telemetry_sql_authority.py`; the proof
   runs that script end to end; re-gated on `c4`, then `c5` (aborted —
   see defect 2), then `c6` (132/132). Two independent review rounds
   (corrections, then PASS).
4. **Retention identity fix (PR 577)** — purge runs inside the Interview
   service connection (compile-time guarded).
5. **Governed schema apply — second attempt succeeded.** Run 1448,
   approval registered programmatically under Pete's delegation after
   re-verifying commit, parameters, digest, preflight and rollback.
6. **Identities bound** with the authority script over an Entra
   administrator connection: plan → apply (one transaction, verified
   before commit) → verify.
7. **Retention enabled** and a bounded, provider-free purge executed as
   the real maintenance identity.
8. **Release-set configuration set** while the legacy runtime was still
   deployed (it ignores the key); the restart proved log capture.
9. **Runtime merged and deployed** (PR 576 → `d066d255`; automatic run
   1450), startup logs read per R9.
10. **Stop condition hit and rollback executed** (PR 584 → main
    `00f73f86887d80645524626a0def44e52f79c9c9`, run `1453`): the Interview runtime
    lock failed closed in production; the previous runtime was restored.

## 4. Defects found and fixed (the real ones)

1. **The migration did security work the pipeline identity cannot do.**
   `peerslate-ado-schema` holds `db_ddladmin` only; this was the first
   migration in the repository to embed `CREATE ROLE`/`GRANT`. The
   throwaway gate ran as an administrator, so it could not see the gap.
   Fix: the house pattern — an administrator-run authority script — and a
   gate that runs that script.
2. **The administrator script would have failed at its last step in
   production.** SQL Server refuses `EXECUTE AS` on an external (Entra)
   user from a SQL-authenticated connection, and the house `.env`
   connection is SQL-authenticated. This surfaced only when the throwaway
   proof was made to run the script's own `verify()` — exactly the risk
   the first review round had flagged. Fix: connect as the Entra
   administrator (`ActiveDirectoryDefault`, no credential read), proven on
   `c6` and then in production.
3. **The application identity was broader than the reviewed boundary.**
   It already held `db_datawriter` and a database-wide `EXECUTE`, so it
   could have purged and written the telemetry table directly. Fix:
   explicit `DENY`s, proven on a stand-in carrying the same grants and
   then on the real identity.
4. **The runtime lock does not verify against what App Service actually
   installs.** `SCM_DO_BUILD_DURING_DEPLOYMENT=1` makes Oryx build a fresh
   `antenv` on the App Service (Python 3.14) at deploy time from
   `requirements.txt`; the B3 lock manifest was built against the
   pipeline's own vendored install. The interpreter-resolved closure in
   production therefore differed from the manifest (29 violations), the
   release resolved to `None`, and boot froze as `service_not_configured`.
   Every local and CI check passed because none of them ran the lock
   against an Oryx-built 3.14 environment. **Not fixed here** - rolled
   back; the fix (deploy the vendored closure with Oryx build disabled, or
   build the lock against the deploy-time environment, with a candidate
   deploy that reads its own startup log before production) is its own
   governed change.
5. **Startup logs were not being captured.** Application logging was off,
   so the boot-readiness line could never have been read. Fix: enabled
   before the deploy; the legacy app's restart proved the capture path.
6. **The repository's generated schema record was stale** (it lacked two
   earlier migrations as well as this one); regenerated in this closeout.
7. **A stray backspace byte** in an existing test made one assertion
   vacuous; repaired (disclosed as out of scope).

## 5. Honest limitations

- Anonymous probes of the review endpoint return `401` (sign-in wall)
  before the `415`/`403` checks can answer; those two exact codes need a
  signed-in session and were compared legacy-vs-new on the same anonymous
  probes instead.
- The Interview extraction is **not live**: the extracted runtime was deployed and then rolled back the same hour because its runtime lock failed closed against the App Service's Oryx-built environment. The legacy runtime is serving, exactly as before this package; it ignores the new schema, identities and configuration, which remain in place and verified for the next attempt.
- The nightly purge has not yet run on its schedule; the SQL path was
  executed under the real identity by impersonation, and the pipeline
  path is proven structurally (service connection, guard, variable). The
  first scheduled run's artifact is the remaining evidence.
- Six non-blocking review residuals on the authority script remain
  (optional principal-type assertion, statement timeout, three test nits,
  one wording nit) — listed as N1–N6 in `11_…EVIDENCE.md` §5b and in
  `13_GROK_REVIEW_RECORD.md`.
- **Release authority (Grok F2, stated plainly).** Under Pete's explicit
  override ("take this all the way to the end", "I'm overruling you"),
  the schema apply (run 1448), the App Service configuration and logging
  changes, the retention enablement, and the runtime deploy (run 1450)
  all happened while the legacy ledger's `release_allowed_for` was `[]`
  and its blocked actions listed production deploy and configuration
  mutation; the PR merges likewise preceded any merge admission. No
  admission was recorded afterwards to dress that up (the control owner
  declined to manufacture one, correctly). The ledger could not have
  stopped the deploy in any case: once a non-`[skip ci]` merge lands,
  `ProductionWebDeploy` runs automatically — a design gap the new claim
  model closes by making deployment a separate manual exact-SHA operation. The Azure branch policy (build
  must pass, squash required) was never bypassed — a bypass was attempted
  once under that direction and the platform refused it; every merge
  waited for a green validation build.
- `PRODUCTION_SCHEMA_STATE.md` is regenerated in this closeout PR under
  the documentation-only closeout rule (`[skip ci]`). The baseline
  release block is **not** updated here: `test_governance_pointers`
  requires it to move in lockstep with `CURRENT_LANES.json`'s
  `release_truth`, and that ledger has a single owner
  (PS-DELIVERY-CONTROL-SIGNIN-001). The true values - deployed commit
  `00f73f86887d80645524626a0def44e52f79c9c9`, pipeline `1453`, live
  release `9a511ab87a776da231f56217` - were handed to that owner to
  record in baseline, ledger and `tests/test_operational_readiness.py`
  together. Until then the baseline still shows the (already stale)
  run-722 record.

## 6. Postmortem — why this took as long as it did

**What actually went wrong at the end.** The runtime lock - the control that exists to refuse an unverified dependency closure - did exactly its job in production and refused one. The failure was ours: the lock was proven against the environment the pipeline builds, not the environment App Service builds. A candidate deploy to the isolated slot that reads its own startup log would have caught this before production; the plan's Candidate path existed for Protected change classes and was not used for the runtime deploy.

**Delay causes, in order of cost.**
1. *Serial dependency on another lane's control session.* The merge
   permission file has a single owner; that session chose to finish its
   own release before writing Extract's permissions, and its `main`
   pushes repeatedly expired our passing validation builds (four times in
   45 minutes). Pete's override and a negotiated push-hold resolved it.
2. *A migration that could not run as the pipeline identity*, discovered
   only in production (run 1419). Root cause: the throwaway gate ran with
   more rights than production. Cost: one failed governed run, one
   correction, three throwaway databases, two review rounds.
3. *Verification depth revealed a second real defect* (SQL-auth cannot
   impersonate Entra users). Cheap to fix, expensive to have found later.
4. *Process overhead:* exact-SHA review after every byte change, re-gate
   after every migration text change, approval records, content-free
   evidence. Each is justified individually; together they turn a
   one-hour change into a day. The cost that was pure waste: polling and
   requeuing around another lane's pushes, and a stuck platform checkpoint
   (run 1445, cancelled and re-queued).

**Safeguards that caught real defects:** the governed apply identity's
minimal rights (refused the over-reaching migration), the transactional
applier (nothing written), the first review round's skepticism about
untested functions, and the end-to-end throwaway proof.

**Better choices, next time.**
- Run every throwaway gate as the same identity production will use, and
  run the administrator script's own verify in the gate from day one.
- Treat "who runs this and with what rights" as a reviewed field of every
  migration and operational script.
- Do not serialize independent lanes behind a single control-file owner;
  give merge admission its own fast path or let the owner waive it.
- Set PR auto-complete at creation so a green build merges instantly.
- Enable application logging as part of provisioning, not as a late
  discovery, and emit boot-readiness at WARNING or above so it is captured.
- Deploy any hash-locked runtime first to the candidate slot and read its
  startup log there; never let production be the first environment that
  resolves the locked closure.

## 7. Identifiers

PRs 578 (`8ba76255` → main `0f00e9ca`), 577 (`f30311be` → `d24b87b2`),
576 (`297d6a2f` → `d066d255`), 564 abandoned · governed runs 1419
(refused), 1445 (stuck, cancelled), 1448 (applied) · runtime deploy run 1450 (live `8a2e8854…`, rolled back) · rollback PR 584 → run `1453` · gates c3 (105/105, superseded), c4 (112/112), c5
(aborted), c6 (132/132, governing) · migration digest `83ab8c08…` ·
authority script `scripts/configure_interview_telemetry_sql_authority.py`
· Interview WIF service connection `90f8b9b6-e3ef-4c91-a04a-0e0d1163fb97`
· maintenance Entra app `852e20b0-4eb6-4ba8-aebd-0e6637a22426` · release
set `1b9441a0…` · Site Audit Manager task
`01a01194-f98f-7eb1-8b87-1064cee741a1`.
