# PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-USERNAME-CONTROL-001 evidence

Runtime-inert post-review record. The Protected delivery path required an
independent exact-SHA review, which passed with no findings. This tail changes
only this evidence file and its matching receipt; it does not alter the
reviewed implementation candidate.

## Independently reviewed candidate

- Candidate base: `c2a7cb2da89eea1fdbbe2845a80bf011bf9fc303`
- Candidate: `b14f24abe43ba6a02126c14e6b6e6c1b506681fb`
- Reviewer: `agent:/root/sealed_broker_reviewer`
- Reviewed at: `2026-08-30T07:51:37Z`
- Result: Pass; findings: none

The reviewer independently assessed these implementation paths:

- `qa/synthetic_member/sealed_credential_broker/__init__.py`
- `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`
- `tests/synthetic_member_qa/test_sealed_credential_broker.py`
- `tests/synthetic_member_qa/test_sealed_credential_broker_attended.py`

The reviewed broker waits no more than 15 seconds for exactly one visible
`input[type='text']` at the already-bound Microsoft identity origin. Username
entry uses a document-bound handle and a synchronous browser-side callback
that checks the exact top-level origin, text type, visibility, connectivity,
and exact-one cardinality before writing. Navigation at the former live-locator
resolution boundary sends no identifier to a replacement document, blocks
submission, and disposes the handle. Password binding, browser isolation and
cleanup, no-capture limits, Graph-before-identity ordering, and Workshop
behavior remain unchanged.

## Verification

- Python compilation and `git diff --check` passed.
- Focused sealed-broker and attended tests: 22/22 passed.
- Broader selected sealed-broker and attended tests: 51/51 passed.
- Delivery-preflight and package-registry tests: 131/131 passed.
- Full synthetic-member discovery ran 129 tests: 126 passed; the only three
  errors are pre-existing, unclaimed Darwin Azure CLI fixture failures, each
  refusing `production_authority_unavailable` at the current shared resolver.
- The independent reviewer verified the exact immutable candidate and returned
  Pass with no findings.

## Boundaries and limitations

No live Azure, Graph, browser, identity, Workshop, SQL, retirement, Entra,
deletion, deployment, schema, configuration, feature-flag, role, licensing,
billing, or other production operation occurred. Tests use fake identities and
fake adapters only; no credential, token, subject, session, or private content
was accessed or recorded. A repository merge does not authorize a live broker
operation or deployment.

This post-review tail still requires current policy acceptance and a separately
validated merge. The claim remains active until its governed close transition;
deployment and live-operation authority remain withheld.
