# PS-SYNTHETIC-SEALED-AZURE-CLI-DARWIN-COMPAT-001 evidence

Runtime-inert post-review record. The Protected delivery path required an
independent exact-SHA review, which passed with no findings. This tail changes
only this evidence file and its matching receipt; it does not alter the
reviewed implementation candidate.

## Independently reviewed candidate

- Base and reviewed `origin/main`: `98b57eac626ee17dd1bc12b7a6d23608649624a4`
- Reviewed candidate: `2c22451b017d8bb4056aa691d07648bf03baa008`
- Reviewer: `agent:/root/darwin_broker_reviewer`
- Reviewed at: `2026-08-30T01:06:47Z`
- Result: Pass; findings: none

The reviewer independently assessed the exact remote candidate across these
implementation paths:

- `qa/synthetic_member/sealed_credential_broker/__init__.py`
- `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`
- `tests/synthetic_member_qa/test_sealed_credential_broker.py`

The reviewed candidate restores a fail-closed Darwin arm64/Python 3.14 host
resolver for the exact `/opt/homebrew/bin/az` launcher and its confined
Homebrew Azure CLI interpreter. It preserves the merged Windows AMD64/Python
3.13 `az.cmd` child-runtime binding, isolated `-I -B -m azure.cli` execution,
and the broker's existing authority, cleanup, and privacy controls. It adds no
broad `PATH` fallback.

## Verification

- Focused fake-only sealed-broker module: 42/42 passed.
- Dependency-correct synthetic-member QA discovery: 124/124 passed.
- Package-registry, governance-pointer, and delivery-preflight modules:
  156/156 passed.
- Python AST checks for the broker, child worker, broker tests, and attended
  tests passed; claim JSON validation and `git diff --check` passed.
- The guarded clean write preflight passed against the reviewed candidate.
- Azure required build 1931 succeeded and was current for PR 742 and the exact
  reviewed candidate.

One local read-only resolver proof ran against the installed
`/opt/homebrew/bin/az` without starting a child. On Darwin arm64 with the
broker under Python 3.14, the resolver bound that exact launcher to the logical
Homebrew Azure CLI Python at
`/opt/homebrew/Cellar/azure-cli/2.87.0/libexec/bin/python`, whose resolved
interpreter was
`/opt/homebrew/Cellar/python@3.13/3.13.14/Frameworks/Python.framework/Versions/3.13/bin/python3.13`.
It produced the exact `-I -B -m azure.cli` command prefix, proved the Windows
child-worker path remained present, and recorded `child_started=False`.

## Boundaries and limitations

No live Azure, Graph, browser, SQL, identity, Workshop, retirement, deletion,
deployment, schema, configuration, feature-flag, role, licensing, billing, or
other production operation occurred. No credential, token, subject, session,
private content, or live-proof material was accessed or recorded. Verification
was fake-only or local/repository read-only, and a repository merge does not
authorize a live broker operation.

This post-review tail is limited to the receipt and this fixed runtime-inert
evidence file. It still requires current PR policy acceptance and a separately
validated merge; the claim remains active until the governed close transition,
and deployment and live-operation authority remain withheld.
