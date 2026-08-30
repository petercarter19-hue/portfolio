# PS-SYNTHETIC-SEALED-GRAPH-PUBLIC-CLIENT-REBIND-001 evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed with no findings. This tail changes only this evidence file and its
matching receipt; it does not alter the reviewed broker, runbook, or test
bytes.

## Independently reviewed candidate

- Activation base: `914a03c487809924467a6e0994f70f206cda1557`.
- Reviewed candidate: `8cbeae0fc1d853de0d8f063c3bad02d2c362e8e8`.
- Reviewer: `agent:/root/sealed_broker_writer/child_runtime_protocol_review`.
- Reviewed at: `2026-08-30T13:07:08Z`.
- Result: Pass; findings: none.

The reviewer verified exactly these candidate paths:

- `qa/synthetic_member/sealed_credential_broker/__init__.py`
- `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`
- `tests/synthetic_member_qa/test_sealed_credential_broker.py`

## Rebound contract

The sealed broker and attended runbook now bind the dedicated, non-secret
public-client application ID `4e5fd52b-5c0b-4f7c-8266-f571284a31f1` in tenant
`b6cac548-9b4b-43da-b366-e95be960ec2f`. The direct focused test pins that exact
literal. The previous public-client ID is absent from the active broker,
runbook, and focused test surfaces.

The replacement application's separate owner-authorized provisioning was
reported as single-tenant, with exactly one public-client redirect
`http://localhost`, no web or SPA redirect, no secret or certificate, and
exact delegated consent for `User.Read`, `User.ReadWrite.All`, and
`User.DeleteRestore.All`. This repository package did not perform or authorize
that provisioning.

The exact tenant, delegated scopes, MSAL system-browser authorization-code and
PKCE flow, memory-only token and HTTP caches, token validations, organization
proof, and absence of runtime-configurable authority are byte-identical to the
reviewed predecessor contract.

## Verification

- Writer focused MSAL token-provider tests: 5/5 passed.
- Writer full sealed-broker module: 47/47 passed.
- Writer browser-operator-boundary module: 6/6 passed.
- Writer governance-pointer and delivery-preflight modules: 154/154 passed.
- Reviewer focused checks: 7/7 passed; full broker: 47/47 passed; runbook:
  6/6 passed.
- Python compilation, `git diff --check`, the clean task-bound write preflight,
  exact three-path diff, and secret scan passed.
- Azure required build 2003 succeeded for PR 774 and the exact reviewed
  candidate.

## Boundaries

No live proof, role change, public-client cleanup, Azure, Graph, browser, SQL,
identity, deployment, configuration, schema, or other production operation was
performed by this package. The rebind records only the non-secret application
client ID; it records no token or credential and grants no production
authority. A repository merge does not authorize a live broker invocation.

This post-review tail is limited to this fixed evidence file and its receipt.
The claim remains active until its separately governed close transition merges.
