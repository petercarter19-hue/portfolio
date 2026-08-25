# PS-SYNTHETIC-BROWSER-OPERATOR-BOUNDARY-001 evidence

## Accepted repository candidate

- Base: `0a694e7a44509e331489a1034679025ba91b5a04`
- Independently reviewed candidate: `a6ad37788c0b55e108f3665d87de4d4f0b1ea97f`
- Reviewer: `agent:/root/browser_operator_boundary_r2_review`
- Result: Pass; no unresolved findings
- Reviewed at: `2026-08-25T17:41:12Z`
- Candidate paths: exactly `docs/AI_MODEL_AND_ROLE_ROUTING.md`,
  `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`, and
  `tests/synthetic_member_qa/test_browser_operator_boundary.py`.

The accepted correction assigns routine visible browser operation to the
browser-capable operator while reserving credential entry, QA-identity
confirmation, material decisions, specified authorizations, and physical-only
actions to Pete. A manager without browser capability routes ordinary browser
work to a browser-capable executor in the same task.

During credential entry, operator commands, observation, and capture pause.
Ordinary UI may later render an identity label incidentally; the operator does
not intentionally inspect, transcribe, export, capture, record, or retain it and
uses only `member_a` and `member_b`. Unmasked secrets stop the operation without
capture. The retained-proof boundary expressly excludes DOM/page content,
sentinel text, identity data, credentials, tokens, sessions, cookies, claims,
authentication headers, browser profiles, and private session files.

Verification passed 56 Synthetic QA tests, including all 6 focused boundary
tests, 25 governance-pointer tests, `git diff --check`, and governed write
preflight. The fresh reviewer verified the exact remote branch tip, base, full
three-path scope, both prior finding closures, and the focused tests. The review
was static and repository-only; direct `unittest` execution passed and `pytest`
was unavailable in the reviewer's Python environment.

No live or browser proof, identity creation or retirement, production access or
mutation, deployment, configuration, schema, feature-flag, role, licensing, or
billing action occurred. Repository merge is accepted. Deployment and every
production operation remain withheld.
