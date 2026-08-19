# PS-SEARCH-DARK-PROOF-001 — Search 3F V3

## Current truth

This package is a **non-production, synthetic-only Search architecture and
operator-tooling candidate**. It creates no member-facing search, changes no
application route, and gives no browser or application identity an Azure AI
Search credential.

The 2026-08-16 dark proof remains useful, narrow historical evidence. It ran
against Azure AI Search REST API `2024-07-01`; it did **not** execute this V3
contract or the future `2026-04-01` pin. It showed that the existing Basic
service could hold the 20-field lexical index, 20 synthetic documents, and two
index-scoped proof role assignments. It did not prove service isolation,
member-facing authorization, a deployed fence, usage cost, or an Ask Pete
structural digest.

## What V3 fixes

- The default command is `plan` and performs zero network or process calls.
- The future query contract is lexical-only and explicit: `queryType=simple`,
  `searchMode=all`, public/schema filter, fixed search fields, fixed 20-field
  select, deterministic order, and bounded adaptive paging.
- The local fence checks every canonical field, owner, publication state,
  revision, schema, audience, enum, and digest before output.
- The serializer constructs exactly seven public fields from the local
  canonical projection; it never copies the Azure candidate.
- The request census records body keys and body shape before dispatch while
  retaining no query text, token, URL, resource ID, app ID, or response body.
- Ceilings are checked before dispatch and persist across invocations.
- A filled cleanup manifest is private, exact-target, manifest-bound, and
  covers both role assignments, the proof index, both service principals, and
  both application registrations. The validator fixes the service and dates,
  binds the pre-authorized private identifiers by SHA-256, and checks target
  relationships read-only before the first delete. Cleanup remains executable
  after expiry; non-cleanup live mutation is not implemented.
- The proof-only script sources and all generated `__pycache__`/`.pyc` output
  are explicitly excluded from the deployment ZIP selection.

## Safe local commands

```powershell
python scripts/run_public_search_dark_proof.py
python scripts/run_public_search_dark_proof.py validate
python scripts/run_public_search_dark_proof.py teardown
python scripts/build_public_content_fixture_manifest.py
python -m unittest tests.test_public_search_dark_proof -v
```

The first three commands above are zero-network plans. Live teardown requires
all of `teardown --execute`, a filled private cleanup manifest, a matching
confirmation phrase, an explicit persistent state file, and an explicit
census file. The committed template cannot execute.

## Package map

- `ARCHITECTURE_V3.md` — normative future contract and trust boundaries.
- `OWNER_DECISIONS.md` — closed V3 decisions; no inherited V2 ambiguity.
- `REVIEW_RESOLUTION.md` — disposition of both prior reviews.
- `HISTORICAL_EXECUTION_EVIDENCE.md` — instrument-bounded 2024 proof record.
- `VERIFICATION_MATRIX.md` — requirements mapped to offline tests.
- `INDEPENDENT_REVIEW_CHECKLIST.md` — the sixteen-question fresh-review brief.
- `schema/public-content-index-v3.json` — complete 20-field future schema.
- `fixtures/public-content-proof-manifest.json` — 20 synthetic projections.
- `fixtures/cleanup-manifest.template.json` — identifier-free private template.

## Explicit exclusions

No Azure proof rerun, Azure resource mutation, Ask Pete request, search service
configuration change, key disablement, CMK change, capacity change, schema
migration, deployment, merge, enablement, Gate L2 claim, or live capability
claim is authorized by this candidate. The standing proof expiry remains
**2026-08-23 23:59 CDT** unless Pete separately records another decision.
