# PS-MVP1-FACT-POLICY-001 candidate evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed. This file does not change application behavior.

Activation PR 990 squash-merged as
`6395963650e49fc5d8944752263133aacbe86d1e`. The active Protected claim assigns
implementation to sole writer
`session:cursor-grok-mvp1-fact-policy-001`; production authority is withheld.

Exact reviewed candidate
`bbebce4b0dc1bd76c0497e6a370b00b5fcede30c` changes only claimed entry-policy
service, route, test, proposed SQL, registry, `app.py`, and
`services/database_service.py` comment surfaces. `ALLOWED_PROCEDURES` bytes stay
the exact previous set. `PACKAGE_REGISTRY.json`, My Data UI, Packages B–G,
identity, providers, and production config are unchanged.

## Outcome

Package A provides an owner-scoped entry-policy command API:

- Closed commands: create, edit, recategorize, change_permissions, delete,
  restore, permanently_delete, resolve_match
- Independent Resume display, visitor-AI, and private-assistance exclusion
- Private defaults for new entries and children; restore does not re-grant
  display or visitor AI
- Payload-aware idempotency and atomic bulk permission conflicts
- 30-day recovery window with counted dependent delete groups
- Project and standalone-achievement commands once; no Projects product
  activation
- Direct corrections do not call an AI provider
- Flag `PEERSLATE_ENTRY_POLICY_ENABLED` defaults off; off and unauthenticated
  are a neutral 404

Proposed additive SQL `PS-ENTRY-POLICY-001` is registered with `gate: null`.
It is not applied. Intended procedure names live in
`ENTRY_POLICY_BROWSER_PROCEDURES` / `ENTRY_POLICY_WORKER_PROCEDURES` and are
not in the live allowlist because `tests/test_database_service.py` is outside
this claim. The SQL adapter is fail-closed.

My Data overlay browser acceptance remains increment M, not A.

## Independent review

Read-only reviewer `agent:cursor-security-review-mvp1-fact-policy-001`
inspected exact candidate `bbebce4b0dc1bd76c0497e6a370b00b5fcede30c` and
returned PASS with no medium-or-higher findings. Local focused tests passed
before freeze; Azure Build on PR 991 is merge-gate proof and is not claimed
by this receipt.

This receipt and evidence file are the only post-review repository tail.

## Release truth

A merge is not a deployment. Schema application, live identity, paid
providers, and `peerslate.com` remain separately authorized. This package
does not enable production entry-policy.
