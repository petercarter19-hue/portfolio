# PS-SYNTHETIC-SEALED-AZURE-AUTH-SHAPE-001 evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed with no findings. This tail changes only this evidence file and its
matching receipt; it does not alter the reviewed broker, runbook, or test
bytes.

## Independently reviewed candidate

- Base: `297d6f891857c7c4bbc02f50990e830af74574c1`.
- Reviewed candidate: `176c1756fe47ae0d3df5812ba1b279c2533dd7ae`.
- Reviewer: `agent:/root/sealed_broker_writer/child_runtime_protocol_review`.
- Reviewed at: `2026-08-30T12:12:20Z`.
- Result: Pass; findings: none.

The reviewer verified exactly these candidate paths:

- `qa/synthetic_member/sealed_credential_broker/__init__.py`
- `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`
- `tests/synthetic_member_qa/test_sealed_credential_broker.py`

## Corrected contract

The fixed `az webapp auth show` command now reads Azure CLI 2.87's ARM response
at `properties.platform.enabled` and
`properties.identityProviders.azureActiveDirectory.registration.openIdIssuer`.
Its JMESPath projection still returns exactly the closed top-level
`{enabled,issuer}` mapping consumed by the broker. The resolver's exact-key,
literal-enabled, issuer, tenant, metadata, authorization-origin, and live
App Service setting validations are unchanged.

Focused regression coverage pins the exact command projection, retains the
closed projected fake result, and refuses an unprojected nested ARM response
before metadata, browser, or Graph work. The attended runbook now describes
the same boundary.

## Verification

- Writer authority-resolver tests: 5/5 passed.
- Writer full sealed-broker module: 47/47 passed.
- Writer governance-pointer and delivery-preflight modules: 154/154 passed.
- Reviewer resolver tests: 5/5 passed; full broker: 47/47 passed; runbook:
  6/6 passed.
- Python compilation, `git diff --check`, the clean task-bound write preflight,
  exact three-path diff, and leak checks passed.
- Azure required build 1994 succeeded and was exact for PR 770 and the reviewed
  candidate.

## Boundaries

No Azure, Graph, browser, SQL, identity, public-client, role, deployment,
configuration, schema, or other production operation occurred. No live proof
or retry was performed. The change emits no sensitive value and grants no
production authority. A repository merge does not authorize a live broker
invocation.

This post-review tail is limited to this fixed evidence file and its receipt.
The claim remains active until its separately governed close transition merges.
