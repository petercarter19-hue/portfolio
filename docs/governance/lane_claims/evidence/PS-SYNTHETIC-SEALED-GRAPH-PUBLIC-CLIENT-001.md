# PS-SYNTHETIC-SEALED-GRAPH-PUBLIC-CLIENT-001 evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed with no findings. This tail changes only this evidence file and its
matching receipt; it does not alter the reviewed implementation candidate.

## Reviewed candidate and history

- Original implementation base and current `origin/main` at review: `663b73e7735a4fad0220c02094714ecfd98d8a28`
- First public-client candidate: `c52b6beedf88faa2bdbad9e5beff2854997974ff`
- First corrected candidate: `c01f1f0bd66c8e45cf5e66a8ce980d3e9ed6ba75`
- Reviewed candidate: `4644e494cbdbf34a193eab67c05bbfdc2e404f37`
- Reviewer: `agent:/root/graph_public_client_reviewer`
- Reviewed at: `2026-08-30T06:33:26Z`
- Result: Pass; findings: none

Candidate `c52b6beedf88faa2bdbad9e5beff2854997974ff` received an independent
failure and no receipt. Candidate `c01f1f0bd66c8e45cf5e66a8ce980d3e9ed6ba75`
corrected the requested MSAL `offline_access` exclusion, real memory-cache
disposal, and complete hash lock. Its later receipt/evidence tail exposed an
unrelated host-dependent child-protocol fixture failure in Ubuntu CI build
1953: the test assumed `SYSTEMROOT` on a non-Windows host. Candidate `4644e494`
removes the stale review artifacts and corrects only that test fixture by
patching a deterministic temporary Windows root. This independent Pass applies
only to `4644e494`; no verdict was transferred between changed bytes.

## Reviewed scope and validation

The reviewed candidate tree differs from main only in these claimed paths:

- `qa/synthetic_member/sealed_credential_broker/__init__.py`
- `qa/synthetic_member/sealed_credential_broker/msal-requirements.lock`
- `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`
- `tests/synthetic_member_qa/test_sealed_credential_broker.py`
- `tests/synthetic_member_qa/test_sealed_credential_broker_deletion.py`

The public-client provider remains statically bound to the dedicated tenant and
client. It passes exactly the three Graph delegated scopes; MSAL adds only
`openid` and `profile`, while `offline_access` is explicitly excluded. It uses
a new memory-only cache per acquisition, clears the version-bound MSAL 1.31.1
`TokenCache._cache` map, and binds the fixed lock, all ten required
distribution versions, and the imported MSAL module path before Graph HTTP.
Existing exact Graph claim and `/organization` authority checks remain intact.

Writer and reviewer validation evidence includes:

- corrected child-protocol test: 1/1 passed;
- feasible synthetic-member discovery: 123/123 passed, excluding only the
  same three known Windows-host Darwin runtime-layout tests;
- MSAL and Graph creation tests: 7/7 passed;
- package-registry, governance-pointer, and delivery-preflight tests: 156/156
  passed;
- Windows CPython 3.13 hash-required installation and `pip check`, real MSAL
  cache probe, and Darwin arm64/Python 3.14 ten-wheel hash-required resolution
  passed;
- AST and claim-JSON parsing, `git diff --check`, cleanup, and no-bytecode
  audits passed, as did governed read and write preflights.

Azure Ubuntu 24.04 build 1955 succeeded with all 4,640 tests for the candidate
PR iteration. It corroborates the reviewed bytes but does not replace the
independent exact-SHA review.

## Boundaries and tail limitation

No live MSAL, Entra, Azure, Graph, browser, SQL, identity, Workshop,
retirement, deletion, deployment, schema, configuration, role, licensing,
billing, or other production operation occurred. No credential, token,
subject, session, private content, or live-proof material was accessed or
recorded. A repository merge does not authorize a live operation.

This post-review tail is limited to the receipt and this fixed evidence file.
It still requires normal PR policy and CI acceptance and merge; the claim
remains active until the separately governed close transition is merged.
