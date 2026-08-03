# PS-AZURE-RELEASE-RELIABILITY-001 - atomic Azure production release

## Authority and scope

- Owner authorization: Pete Carter, 2026-08-03, requested immediate site
  recovery and a comprehensive repair of repeated Azure PR, merge, deployment,
  branch, and workflow failures.
- Delivery path: **Protected** because this changes shared production release
  orchestration and branch-policy behavior.
- Manager and sole writer: the current root Codex session.
- Branch: `work/2026-08-03-azure-release-reliability-001`.
- Authoritative base: Azure DevOps `origin/main` at
  `f0a802b6bdd9b388facb07b786d76b1809759ae9`.
- Writable repository scope: `azure-pipelines.yml`, the focused operational
  regression, the one delivery-workflow clarification, this package, and the
  release pointer after exact deployment evidence exists.
- Azure scope: the production pipeline and exact `main` branch build policy.
  The active Community disposable SQL-proof pipeline and every active product
  branch remain read-only and owned by their existing writers.

## Verified incident facts

Production is currently healthy on exact `main` and pipeline 411. Live
`/healthz` returns release `4bb066e8e1467248bf68fffc`, which is the immutable
identity for source `f0a802b6bdd9b388facb07b786d76b1809759ae9` and build
411. The canonical Azure Web App hostname intentionally redirects to
`https://peerslate.com/`; Azure management access remains available.

Current live performance evidence also passes the prior performance boundary.
Five direct samples measured homepage totals of 0.31-0.38 seconds; warm résumé
samples were 0.43-0.44 seconds with two intermittent 1.56-1.76-second samples;
Interview Studio was 0.31-0.77 seconds; and signed-out `/auth/session` was
0.20-0.25 seconds. The homepage still returns dependency-free gzip (73,389
identity bytes, 14,010 transferred bytes), and an exact-token JavaScript asset
retains `public, max-age=31536000, immutable` plus gzip. This package changes no
application response, asset, cache, compression, HTTP/2, or Always On behavior.

The production failures were not failed `AzureWebApp` deployments. Automatic
run 410 deployed successfully, then a manually queued run 411 for the same SHA
redeployed the site before run 410 could verify itself. Run 410 saw `/healthz`
return 404 during the second recycle and then correctly rejected build 411's
different release identity. The same deterministic interleaving occurred with
runs 290/291, 319/320/321, and 346/347.

The existing pipeline permits every `main` run, including Manual, to deploy.
It also releases the production-environment deployment job before a separate
ordinary smoke stage begins. Rapid merges are not batched. Those three facts
permit an unnecessary run to replace production between another run's deploy
and exact verification.

The other red Azure records are separate and must not be presented as
production outages:

- 15 of the 17 failed primary-pipeline runs in the inspected window were
  Build, PR, scanner, Candidate, or test validation failures; zero failed the
  production `AzureWebApp` task.
- PR 256 run 394 caught two real release-pointer test defects before corrected
  run 396 passed; no deployment stage ran.
- The manually triggered Community disposable SQL-proof pipeline produced 19
  failing iterations through run 414 on its active feature branch. It has no
  production Deploy stage, forces the feature flag off, and confirmed exact
  cleanup. That unresolved proof remains with its active writer.

## Repair contract

1. Batch `main` CI so merges arriving during an active run produce one later
   cumulative build instead of a deployment for every intermediate commit.
2. Keep automatic `main` deployment, but make a manual production deployment
   a typed, false-by-default queue-time decision.
3. Put production deployment and exact release smoke in the same deployment
   job and stage, protected by a stage-level `runLatest` lock. A later run may
   not replace the live artifact before the current run finishes verification.
4. Preserve the build-specific release identity and exact smoke contract.
   Weakening the verifier would hide the race rather than repair it.
5. Tighten the `main` PR build policy so target-branch movement requires fresh
   validation instead of retaining a result for 12 hours.
6. Clarify that documentation-only `[skip ci]` must reach the final squash
   commit; a PR-title marker alone is not sufficient.
7. Add one durable Azure release-reliability section to the existing PS-OPS
   authority so every initiative follows the same run-selection, locking,
   failure-classification, and current-target PR rules without creating a
   competing new standard.

## Evidence and rollback gate

Before merge, the exact branch must pass the operational regression, relevant
governance tests, YAML/pipeline validation, complete-diff self-review, and a
fresh independent review of this shared-infrastructure change. The Azure PR
must validate without a production deployment.

After squash merge, allow only the automatic `main` run. It must pass Build and
the single atomic production release stage, and live `/healthz` must match that
run's exact source/build identity. Recheck canonical public routes, signed-out
auth boundaries, availability, and that no duplicate main run exists.

Rollback is an Azure PR reverting the pipeline commit. If the automatic release
cannot start or verify, do not queue overlapping retries. First confirm whether
ZipDeploy began; if it did, let that run finish and inspect exact live identity
before choosing a single explicit manual recovery.

## Honest limits and deferred work

- In-place ZipDeploy/Oryx still recycles the one production Web App and can
  return temporary 404s while the new worker starts. Deployment slots and a
  health-gated swap are the appropriate availability follow-up, but they add
  Azure resources/configuration and are not silently introduced by this
  incident repair.
- The configured Candidate Web App no longer exists. A future Protected release
  that elects Candidate remains blocked until its package provisions and proves
  an exact isolated target or replaces that stale path deliberately.
- Branch/worktree cleanup is separate. The audit found 51 worktrees, 12 dirty
  worktrees, active same-name/divergent Community history, and several active
  file collisions. Nothing is deleted during production recovery.
