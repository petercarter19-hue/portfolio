# PS-OPS-CANDIDATE-ADMISSION-001 — Package-specific exact-SHA Candidate admission

## Status and authority

- Owner: Pete
- Owner decision: on 2026-07-29 Pete directed, “Assign a fresh independent
  reviewer, correct Candidate admission for this package, then deploy after
  both pass.”
- State: correction 2 implementation and verification in progress after the
  first real queue-time exercise failed closed
- Designated manager and sole writer: current Codex task
- Fresh independent reviewer: current task's read-only
  `performance_independent_review` lane
- Authoritative base: Azure `origin/main`
  `887303792184c5e15aff238f6ee2f59e1576cdbd`
- Branch: `work/2026-07-29-candidate-admission-002`
- Checkpoint authority: this is bounded correction 1 from
  `PS-AI-OPS-CHECKPOINT-001`
- Release relationship: this correction must merge before
  `PS-PERFORMANCE-FOUNDATION-001` may queue its Candidate

## Problem

The released Azure pipeline admits Candidate work only when
`Build.SourceBranch` equals one historical hard-coded branch. A later release
temporarily repointed that historical name to an independently reviewed source
commit. The alias was verified and deleted, but the checkpoint correctly
classified it as a one-time procedural deviation that must not become the
normal release mechanism.

Candidate admission must identify the package, the real source branch, and the
exact full Git SHA supplied by the release operator. Azure must independently
prove that those values equal the branch and commit it actually checked out.
The immutable artifact manifest must retain that proof.

Correction 1 merged the package/branch/SHA contract, but real Candidate run
288 proved that the YAML's empty variable declarations shadowed the
queue-settable values held in Azure pipeline metadata. Azure accepted and
recorded the exact requested values, the build passed, and every Candidate
stage then skipped. That is a failed Candidate, not a release pass.

## Requirements

- **PS-OPS-CAND-ADM-001:** Candidate eligibility shall not depend on a
  hard-coded historical task branch or a repointed alias.
- **PS-OPS-CAND-ADM-002:** Candidate admission shall default disabled and
  require a non-empty package ID, full `refs/heads/...` source branch, and full
  40-character source SHA.
- **PS-OPS-CAND-ADM-003:** The build shall fail closed when admission values
  are incomplete, malformed, target `main`, or differ from Azure's
  `Build.SourceBranch` or `Build.SourceVersion`.
- **PS-OPS-CAND-ADM-004:** Candidate deploy, smoke, and always-run stop stages
  shall require the same non-empty package and exact branch/SHA equality.
- **PS-OPS-CAND-ADM-005:** The immutable Candidate manifest shall record
  whether admission was disabled or package-specific, and when enabled shall
  record the exact package, branch, and SHA.
- **PS-OPS-CAND-ADM-006:** Ordinary `main` production builds and non-admitted
  task builds shall retain their existing stage behavior.
- **PS-OPS-CAND-ADM-007:** Focused tests and a fresh independent exact-SHA
  review shall pass before merge.

## Design

Azure pipeline metadata defines three queue-overridable variables with empty
defaults:

```text
candidatePackage
candidateSourceBranch
candidateSourceVersion
```

The YAML deliberately does not redeclare those names. Azure YAML declarations
take precedence and would replace the reviewed queue values with empty strings.
The pipeline-level variables are configured with `allowOverride=true` and an
empty stored value, so ordinary runs remain disabled while an explicit
operator can supply the exact admission tuple.

The artifact-manifest step receives those values in every build. With all
three empty, it records `mode=disabled`. If any value is present, all three are
required and the script validates:

- the package matches the uppercase `PS-*` package convention;
- the admission branch is a valid `refs/heads/...` branch other than `main`;
- the admission SHA is a full Git SHA;
- the admission branch equals Azure's actual `Build.SourceBranch`; and
- the admission SHA equals Azure's actual `Build.SourceVersion`.

Azure injects the three queue values through the task's `env` map and the Bash
command reads ordinary environment variables. Queue values are never inserted
into Bash source, so shell syntax in malformed input remains inert data for the
Python validator to reject.

The Candidate stages repeat the non-empty package plus exact branch/SHA
equality as their Azure condition. A partial or mismatched request therefore
cannot deploy: the manifest build fails and the stages remain ineligible.

## Operator contract

After the exact source SHA has passed required review, queue Candidate with:

```text
az pipelines run \
  --id 1 \
  --branch <real-task-branch> \
  --variables \
    candidatePackage=<PS-PACKAGE-ID> \
    candidateSourceBranch=refs/heads/<real-task-branch> \
    candidateSourceVersion=<full-reviewed-source-sha>
```

The operator must verify the returned run's `sourceBranch` and
`sourceVersion`, the manifest's `candidate_admission`, and the Candidate
deploy/smoke/stop stage results. A branch movement after review requires a new
SHA review and a new queue request; the old admission values fail closed.

## Scope

Reserved files:

- `azure-pipelines.yml`
- `scripts/candidate_artifact.py`
- `tests/test_operational_readiness.py`
- `docs/initiatives/PS-OPS-CANDIDATE-ADMISSION-001/**`

This package does not change application routes, response behavior, identity,
authorization, member data, database schema, secrets, feature flags, product
UI, visual authority, DNS, production settings, or Candidate environment
boundaries. It does not authorize the separate Work & Impact or Interview
follow-up checkpoint corrections.

## Verification and release gate

Required before merge:

- manifest unit coverage for disabled, exact admitted, partial, malformed,
  branch-mismatch, SHA-mismatch, and `main` rejection;
- structural YAML coverage proving no YAML default shadows the external
  empty-by-default queue variables and exact package/branch/SHA conditions
  remain on deploy, smoke, and stop;
- Azure pipeline-variable evidence showing all three stored values are empty
  and `allowOverride=true`;
- existing operational and full repository suites;
- clean complete-diff review; and
- fresh independent review of the exact correction SHA.

After merge, the normal production pipeline will redeploy an application
artifact whose runtime code is unchanged by this correction. Exact pipeline
and `/healthz` evidence must still be recorded. Only then may the performance
branch incorporate correction 2, receive its final exact-SHA review, and queue
Candidate through the same package/branch/SHA operator contract.
