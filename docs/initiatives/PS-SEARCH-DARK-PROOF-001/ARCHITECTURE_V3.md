# Search 3F V3 — Normative Architecture

## 1. Scope and truth boundary

Search 3F is a dark, synthetic reference for a future public-publication
retrieval path. It is not application runtime and not search-engine
discoverability. Canonical member truth remains outside Azure AI Search.
Azure contains a derived projection; the local publication manifest is the
authority used by this proof fence; the seven-field response is a separate
public projection.

The historical experiment ran at `2024-07-01`. All future request builders in
this package pin `2026-04-01`. The two pins coexist only because one describes
past evidence and the other describes future architecture. No V3 execution is
claimed.

## 2. Trust model

The proof shared the existing Search service. Index-scoped data-plane roles
reduced the proof principals' reach, but inherited service/resource-group
readers, service keys, and service administrators may still reach the index.
That is **bounded shared-service exposure, not isolation**. A dedicated Search
service remains the recommendation if service-level isolation is required.

The public fence is authorization-before-return, not Azure deletion:

```text
canonical public projection manifest
        │
        ├── lexical candidate retrieval from Azure
        │
        └── local publication/owner/revision/digest fence
                    │
                    └── exact local seven-field serializer
```

Withdrawal, block, disconnect, or publication-revision change closes locally
before any candidate is returned. Physical index deletion is cleanup and does
not define the member-visible revocation boundary. Member relationship checks
are outside this synthetic package and must be implemented server-side in the
future member-facing package.

## 3. Canonical 20-field index

`schema/public-content-index-v3.json` is complete and generated from the same
function tested by the suite. It has 20 fields, 13 filterable, 5 searchable, 3
sortable, 0 facetable, no vector configuration, and no semantic configuration.
All fields are explicitly `retrievable: true` and `stored: true`, matching the
observed Azure representation. Safety therefore does not depend on an
unsupported `stored:false` claim; it depends on explicit select, the fence,
and the local serializer.

The five searchable fields are `title`, `summary`, `search_text`, `aliases`,
and `member_display_name`. The index key is `document_id`. The three sortable
fields are `document_id`, `title_sort`, and `indexed_at`.

## 4. Canonicalization and fixtures

Fixtures are wholly invented: three synthetic profiles and twenty documents.
Every document uses the `d1_` namespace and carries the explicit marker in the
manifest. Canonical digest v1 includes aliases, destination, locale, member
display name, optional period, profile slug, result type, search text, summary,
title, and title sort. Strings are NFC-normalized; aliases are NFC-normalized
and sorted; `None` optionals are omitted; compact sorted-key UTF-8 JSON is
SHA-256 hashed with prefix `cv1:`.

The manifest has exact-key validation, exact member/document counts, unique
document and projection keys, one immutable owner per projection slot, a
reproducible document digest, and a reproducible content root. Unknown keys,
non-synthetic IDs, invalid enums, inconsistent counts, or digest drift fail.

## 5. Fixed lexical query contract

Every page is constructed with:

| Option | Value |
|---|---|
| API version | `2026-04-01` |
| `queryType` | `simple` |
| `searchMode` | `all` |
| `searchFields` | the five named searchable fields |
| `select` | the explicit canonical 20-field list; never `*` |
| `filter` | `audience eq 'public' and schema_version eq '1'` |
| `orderby` | `search.score() desc,document_id asc` |
| page size | at most 20 |
| candidate ceiling | 200 |
| public result ceiling | 6 |

Paging continues only until six candidates survive the local fence, Azure
returns a short page, or 200 candidates have been inspected. The contract
scans nested body keys and refuses semantic/vector keys or any `queryType`
other than `simple` before dispatch.

## 6. Complete fence order

For every candidate, the implementation checks:

1. candidate object shape and known projection key;
2. immutable slot owner in the local manifest;
3. local `withdrawn is False` publication state;
4. candidate `audience == public`;
5. candidate `schema_version == 1`;
6. accepted lowercase result-type enum;
7. candidate profile owner equals the immutable slot owner;
8. all 19 non-digest canonical index fields equal the local projection after
   NFC/alias-order normalization;
9. candidate digest recomputes from candidate content;
10. recomputed digest and candidate digest equal the local digest;
11. duplicates collapse by document ID and results sort by descending score,
    then ascending document ID.

Any missing, unknown, stale, private, withdrawn, malformed, mismatched, or
tampered candidate is discarded. Fifty shuffled repetitions are tested to
produce one order.

## 7. Exact serializer

The serializer looks up the already-fenced projection in the local manifest
and constructs exactly these keys, including `period_label: null` when absent:

`destination`, `member_display_name`, `period_label`, `profile_slug`,
`result_type`, `summary`, `title`.

No Azure value is copied. Backend identity, owner, digest, revision, schema,
search text, aliases, title sort, timestamps, and score cannot appear through
this serializer.

## 8. Transport census and ceilings

`RequestCensus` records before dispatch: sequence, transport, operation,
method, target hash, API version, recursive body keys, byte count, body-shape
hash, safe `query_type`, command shape, and later status. It stores no URL,
query text, JSON value, token, tenant, subscription, resource ID, app ID,
response body, or command output.

`PersistentBudget` binds request and document counters to the filled
cleanup-manifest hash and persists those counters across invocations. It checks
projected query, index, process, payload-byte, and document totals plus an
invocation-local wall-clock ceiling **before** transport dispatch. A mismatched
manifest or exceeded ceiling fails closed. Importing either script does not
create an evidence, secret, census, state, or fixture file.

## 9. Cleanup contract

The committed cleanup file is a template and cannot execute. A private filled
copy must validate all of the following:

- exact package and historical/future API pins;
- the fixed 2026-08-16 authority and fixed 2026-08-23 23:59 CDT teardown
  date; changing either date is refused;
- exact resource group/service/endpoint and UUID-shaped subscription/tenant
  values;
- only `peerslate-public-content-v1` under the strict allow/deny guard;
- exactly two index-scoped role-assignment resource IDs;
- exactly two service-principal object IDs;
- exactly two application registration IDs;
- SHA-256 equality to the pre-authorized role-assignment and application IDs,
  without committing those private identifiers;
- unique targets, no placeholders, no Ask Pete text, no extra keys;
- teardown-only owner authorization, no silent extension, and a manifest-bound
  confirmation-phrase hash.

Before the first delete, read-only lookups validate every role-assignment
principal/role pair, every service-principal/application pair, and the exact
proof-index endpoint. The ordered convergence procedure then deletes/verifies
the two role assignments, deletes/verifies the proof index, deletes/verifies
both service principals, then deletes/verifies both application registrations.
An absence check must itself succeed and return JSON; a generic CLI failure is
never treated as proof of absence. The procedure never deletes the service,
resource group, pre-existing role assignments, or pre-existing indexes. Live
cleanup is refused before `teardown_not_before`, but remains available after
`expires_at`; expiry can never make cleanup unreachable.

The repository candidate does not execute cleanup. Teardown remains the
existing owner decision for 2026-08-23 23:59 CDT unless superseded separately.

## 10. Evidence and lifecycle claims

The historical proof supports plumbing observations only. The V3 code and
offline suite support architecture/tooling behavior only. Neither supports a
live member feature, dedicated isolation, service-key removal, CMK compliance,
cost dollars, a deployed fence, Ask Pete schema identity, or deletion
completion. Those claims require their own instruments and later authority.

The package stops at a frozen, pushed exact SHA and detailed independent-review
handoff. Merge, deployment, teardown, member-facing search, and the later
lane-concurrency rule are separate decisions and branches.
