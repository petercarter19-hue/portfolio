# 03 — Provider-neutral connector contract

## Fixed boundary

The accepted shared-source boundary remains:

```text
connector.describe() -> source descriptor and capabilities
connector.acquire() -> immutable source receipts, exactly as received
connector.normalize(receipt) -> normalized candidate plus source-version link
```

`describe`, `acquire`, and `normalize` do not write a canonical opportunity,
member relationship, search projection, or application.  C2 owns shared
admission, versions, dedupe, lifecycle, governing-source selection, and the
Live Opportunity Gate.  C11 implements only the later selected provider
adapter.  No API key, provider call, fixture, or adapter is created by C1.

## Descriptor and rights binding

`describe()` returns a stable `source_id`, `source_class`, `policy_key`,
capabilities (`pull`, `push`, `closure_signal`, `change_signal`), schedule
hints, direct source identity, territory/product, and a current
`source_policy` version.  It must not return a permissive capability merely
because an endpoint exists.

Registration refuses when any of these is absent, expired, ambiguous, or
denied: executed provider authority, policy/evidence version, permitted
actions and surfaces, attribution, removal contact/path, termination/exit
disposition, and a decision about source-derived minimal facts.  The refusal
is deterministic and content-free.

## Point-of-use evaluator

The policy evaluator runs at each of the following places, not just receipt
intake:

| Action | Required decision |
|---|---|
| Acquire / refresh | Current policy permits the provider/product/territory and access method. |
| Persist receipt or normalized field | Storage and retention allow the field and data class. |
| Render list, excerpt, detail, or source link | Display/full-description/excerpt and attribution allow the exact surface. |
| Create cache or shared projection | Caching, indexing, geography, and expiry allow it; member data is never eligible. |
| Send content to an AI system | Explicit AI/ML allowance, purpose, provider/data-flow, and source/version allow it. |
| Handle removal, closure, or termination | Removal/termination and minimal-fact survival dictate purge/withhold/tombstone behavior. |
| Export, audit, or delete | Exit/retention rules distinguish PeerSlate records from source-derived facts. |

Any denial removes the head from current results and withholds the restricted
field.  It does not silently transform a source-derived fact into a PeerSlate
fact.  If another rights-permitted source head remains eligible, the parent
failover rules apply; otherwise the member receives truthful unavailable or
details-no-longer-available language.

## Receipt, normalization, and untrusted input

`acquire()` stores raw provider material only as a bounded receipt with source,
policy, acquisition time, immutable hash, and transport metadata permitted by
the applicable policy.  It never makes the material canonical.  `normalize()`
is deterministic, sanitizes untrusted provider content, identifies parse and
field-confidence outcomes, and preserves source/version linkage.  It cannot
invent missing requirements, employer facts, or closure status.

Provider payload HTML, redirect targets, headers, and content are untrusted.
Future C2 outbound validation, size/type limits, sanitation, and failure
states apply before admission.  C1 does not introduce a network fetcher.

## Termination and exit contract

The later provider adapter must support a rehearsable disable path: stop
acquire, freeze or revoke the policy, re-evaluate cached/indexed/rendered/AI
uses, remove bodies and fields as required, preserve only allowed minimal facts,
and emit content-free completion facts.  Exit is complete only when the
contract says what is exportable, what must be destroyed, how attribution is
handled, and which member history labels become source-detail unavailable.
Neither a raw receipt nor an index copy is an exception to the source policy.

## Explicit exclusions

This contract excludes scraping prohibited services, browser-login automation,
provider passwords, member imports, private member data, application
submission, provider selection, and every runtime/schema/infrastructure change.
The direct-public interface examples in C1 are not a licence to bypass an
employer or provider agreement.
