# PS-INTERVIEW-FOCUS-UI-001 Candidate Evidence

Date: 2026-07-29

## Decision

**Gate Candidate: Pass.**

The isolated Candidate proved the exact reviewed Interview Focus source before
Azure PR 201 or any production deployment.

## Exact identity

- Reviewed source:
  `da6f93946adf4f3ba3c29d39362b71b0946501a7`
- Frozen runtime contained by that source:
  `0b2d5ffa6aac56dbb6736bbeb5cee13c8baffeb7`
- Azure pipeline: 278 (`20260729.2`)
- Candidate artifact: `278.zip`
- Artifact SHA-256:
  `d784562d4b1349c3ade69fddc4340382c5f745f8428f71356560223c32a70724`
- Exact Candidate release:
  `15c44c8f758582dfffc61a98`

## Environment boundary

The Candidate used a temporary Linux Basic B1 Web App and its own separate
plan. It was distinct from production, had no managed identity, no connection
strings, no production data, and no production provider access. Its only two
application settings were the inert `ANTHROPIC_API_KEY` test placeholder and
`SCM_DO_BUILD_DURING_DEPLOYMENT`.

The pipeline's existing Candidate branch selector was not queue-time settable.
A diagnostic build, 277, therefore ran Build only while every Candidate and
production stage skipped. It is not Candidate or release evidence. The
temporary editor variable used during that diagnosis was deleted immediately.

For the exact promotion run, a temporary remote alias at the pipeline's
existing Candidate branch name pointed byte-for-byte to reviewed source
`da6f93946adf4f3ba3c29d39362b71b0946501a7`. Its exact pointer was verified
before the run and the alias branch was deleted afterward.

## Admission-control deviation and disposition

Pete's overnight release authorization delegated the bounded Candidate,
merge, production, verification, rollback, and cleanup sequence to the current
manager. Under that authority, the manager accepted this one-time,
exact-SHA alias as a procedural admission-control deviation after the
queue-time selector proved unavailable.

The deviation did not change the pipeline source, reviewed runtime, production
configuration, production identity, secret or data boundary, or Candidate
environment. Pipeline 278 still built and exercised the exact reviewed source.
The alias was deleted after the run.

This is not the reusable control promised by PS-OPS-001. Before another package
uses Candidate, a separately reviewed PS-OPS correction must provide auditable
package-specific admission without repointing the historical branch name. The
alias workaround may not be repeated without new explicit owner approval.

## Pipeline results

| Stage | Result |
|---|---|
| Build | Pass |
| CandidateDeploy | Pass |
| CandidateSmoke | Pass |
| CandidateStop | Pass |
| Production Deploy | Skipped |
| ProductionSmoke | Skipped |

The Build stage completed the Azure test contract, dependency audit, and
redacted full-history secret scan. The Azure test report contained 1,077 tests
with 18 environment-dependent skips. `pip-audit` reported no known
vulnerabilities and Gitleaks reported no leaks.

Candidate smoke passed:

- `/healthz`
- `/`
- `/interview-studio`
- `/robots.txt`
- `/sitemap.xml`

The smoke matched exact release `15c44c8f758582dfffc61a98`. CandidateStop
then passed and returned the app to `Stopped`.

## Cleanup

After production pipeline 279 and independent live verification passed, Azure
enumeration confirmed that both the temporary Candidate Web App and its
separate B1 plan were deleted. Production remained on its original App Service
plan and continued running.

No production/security bootstrap exception, production setting change,
production identity change, member-data access, or Candidate-to-production
resource reuse occurred. The bounded admission-control deviation above is
recorded explicitly and remains a required PS-OPS correction before Candidate
is reused.
