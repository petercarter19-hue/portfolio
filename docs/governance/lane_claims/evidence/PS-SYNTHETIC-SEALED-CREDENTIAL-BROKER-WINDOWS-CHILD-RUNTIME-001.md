# PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-WINDOWS-CHILD-RUNTIME-001 evidence

Runtime-inert post-review record. The Protected delivery path required an
independent exact-SHA review, which passed with no findings. This tail changes
only this evidence file and its matching receipt; it does not alter the
reviewed implementation candidate.

## Independently reviewed candidate

- Base and reviewed `origin/main`: `eb764906c1a0b7a71f6a6502fc0fc8105603a818`
- Reviewed candidate: `6ff995bc81cebfd0119b1dc59ce5059143468ad1`
- Reviewer: `agent:/root/sealed_broker_reviewer`
- Reviewed at: `2026-08-30T00:14:04Z`
- Result: Pass; findings: none

The reviewer independently assessed the exact remote candidate across these
implementation paths:

- `qa/synthetic_member/sealed_credential_broker/__init__.py`
- `qa/synthetic_member/sealed_credential_broker/child_worker.py`
- `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`
- `tests/synthetic_member_qa/test_sealed_credential_broker.py`
- `tests/synthetic_member_qa/test_sealed_credential_broker_attended.py`

The parent provisions the locked runtime before Graph without importing native
Playwright. One fixed, shell-free locked-venv child owns Playwright, Chromium,
the probe, and all four non-persistent contexts; receives exactly two synthetic
identities through anonymous stdin; returns only structural protocol results;
and must complete the applicable cleanup and exit proof before root removal or
retirement.

Windows Job Object emptiness is proven from
`JOBOBJECT_BASIC_ACCOUNTING_INFORMATION.ActiveProcesses == 0`, not Job-handle
signaling. Root removal remains gated on that tree proof, and the child
environment omits ambient `PATH`, `COMSPEC`, and TLS certificate overrides
while binding `SYSTEMROOT` and `WINDIR` to the canonical
`GetWindowsDirectoryW` result. The non-Windows Noop and uncontained paths never
equate direct-child exit with descendant-tree closure: only an exact cleanup
frame, unforced zero exit, and EOF without trailing output admit non-Windows
root removal. Every abnormal or unproved path retains the root, blocks
retirement, and makes no descendant-reaped claim.

## Verification

- Focused fake-only sealed-broker and attended modules: 46/46 passed.
- Dependency-correct full repository suite: 4,572 passed, 24 skipped.
- Governance pointers: 25/25 passed.
- Repository evidence policy, JSON validation, Python compilation, and
  `git diff --check` passed.
- Azure required build 1924 succeeded and was current for the reviewed
  candidate.
- The guarded clean write preflight passed against the reviewed base before the
  fixed post-review tail was added.

## Boundaries and limitations

No live Azure, Graph, browser, SQL, identity, Workshop, retirement, deletion,
deployment, schema, configuration, feature-flag, role, licensing, billing, or
other production operation occurred. No credential, token, subject, session,
private content, or live-proof material was accessed or recorded. Verification
was fake-only or repository/read-only, and a repository merge does not
authorize a live broker operation.

This post-review tail is limited to the receipt and this fixed runtime-inert
evidence file. It still requires current PR policy acceptance and a separately
validated merge; the claim remains active until the governed close transition,
and deployment and live-operation authority remain withheld.
