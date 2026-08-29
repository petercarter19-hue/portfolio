# PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-WINDOWS-RUNTIME-001 evidence

Runtime-inert post-review record. The Protected delivery path required an
independent exact-SHA review, which passed with no findings.

## Independently reviewed candidate

- Candidate base: `b28cb69b1bb99f5f24297fd3dee2474aa4f63e66`
- Candidate: `10aab8e68acf6a2dda9e54b0e0b8cd090b381d76`
- Reviewer: `agent:/root/sealed_broker_reviewer`
- Result: Pass; no findings
- Reviewed paths: `qa/synthetic_member/sealed_credential_broker/__init__.py`,
  `qa/synthetic_member/sealed_credential_broker/playwright-runtime.lock.json`,
  `qa/synthetic_member/sealed_credential_broker/playwright-requirements.lock`,
  `qa/synthetic_member/docs/ATTENDED_PROOF_RUNBOOK.md`, and
  `tests/synthetic_member_qa/test_sealed_credential_broker.py`.

The candidate preserves the approved sealed-browser contract while adding the
Windows AMD64 / Python 3.13 runtime target. It validates the installed Azure
CLI2 layout before either bounded App Service read, never executes the
discovered `az.cmd`, and launches only the confined sibling `python.exe` with
`-I -B -m azure.cli` and one of the two fixed read-only argument sets. The
pinned Playwright runtime keeps the accepted Darwin arm64 / Python 3.14 target,
uses exact binary-wheel hashes, validates the bound Chromium executable before
the isolated no-capture browser boundary, and refuses before Graph work on a
missing launcher or unsupported runtime.

## Verification

- Writer focused fake-only broker suite: 18/18 passed.
- Full synthetic-member fake-only suite: 92/92 passed.
- Python compilation, lock/hash consistency, exact Azure CLI runtime-prefix
  probe, and `git diff --check` passed.
- The independent reviewer verified the exact immutable remote candidate,
  including the corrected CLI2 layout binding and adversarial fake paths for
  unrelated files, missing or escaped Python, wrong adjacency, and missing
  discovery. Result: Pass with no findings.

## Boundaries and limitations

No live Azure, Graph, browser, PeerSlate, SQL, identity, Workshop, retirement,
deletion, deployment, schema, configuration, feature-flag, role, licensing,
billing, or other production operation occurred. All evidence is fake-only or
read-only; no actual Windows CLI2 executable, browser runtime, tenant,
credential, session, identity, or private content was accessed. No live proof
is represented by this repository candidate.

This post-review tail changes only this runtime-inert evidence file and the
matching receipt. It does not alter the independently reviewed implementation
candidate. Repository merge is pending; the claim remains active and
deployment and live-operation authority remain withheld.
