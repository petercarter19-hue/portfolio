# PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-001 evidence

## Independently reviewed repository candidate

- Base: `f523764095575a4dffbb0d661a95dc58f11f7227`
- Independently reviewed candidate: `a54e3f68a19bf3379a46598b263777c04821d118`
- Reviewer: `agent:/root/sealed_broker_reviewer`
- Result: Pass; no unresolved findings
- Reviewed at: `2026-08-28T15:51:31Z`
- Candidate paths: exactly `docs/AI_MODEL_AND_ROLE_ROUTING.md`,
  `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`,
  `qa/synthetic_member/sealed_credential_broker/__init__.py`,
  `scripts/run_synthetic_sealed_credential_broker.py`, and
  `tests/synthetic_member_qa/test_sealed_credential_broker.py`.

The candidate implements a local sealed broker for exactly two run-scoped
ordinary synthetic QA customer identities. It obtains the active pre-authorized
Graph token without sending prompted input to child arguments or inherited child
environments, verifies the token tenant plus authenticated Graph
organization/verified-domain match before any customer POST, uses injected
adapter boundaries, and reports only closed structural outcomes. Generated
credentials, authorization material, identities, tokens, subjects, and browser
session material have no repository, output, or retained-evidence path.

The browser path uses non-persistent contexts. Its unavoidable engine artifacts
are confined to one explicit run-scoped root, which must be absent before start
and removed and verified before Pass; residue refuses and cleanup uncertainty is
indeterminate. The two in-memory Graph subjects transfer directly to the
unchanged accepted exact-two retirement core. External Identity permanent
deletion remains outside this package.

Writer validation passed focused broker tests (17/17), the full synthetic-member
suite (73/73), and auth plus package-registry tests (36/36). Python compilation
and `git diff --check` passed. The independent reviewer verified the exact
remote candidate, clean worktree, no candidate-path overlap through
`origin/main` `8cb633895c6df5b9b09e0e9f46922fdc60550e49`, focused 17/17, full
synthetic 73/73, and the final Pass with no findings. This tail changes only
this runtime-inert evidence file and its matching receipt; it does not alter any
reviewed implementation byte.

No live Azure, Graph, browser, SQL, identity, retirement, deletion, deployment,
schema, configuration, feature-flag, role, licensing, or billing operation
occurred. Repository merge is pending. Deployment and all live operations remain
withheld. A separately authorized real operation must reconcile any ambiguous
external creation before retrying; Python cannot guarantee physical zeroization
of immutable strings.
