# MVP1 publication components: E checkpoint

This package stops at **inactive E contracts and deterministic review**. It does
not complete E, implement F, publish anything, or enable a member journey. Pete's
2026-09-16 scope reduction supersedes the earlier through-F/integration plan.
The active claim records ownership and exact authority; this document does not.

## Implemented boundary

`services/resume_publication_contracts.py` defines contract v1 and immutable
owner-composite entry/source/media versions, exact editorial deltas, independent
display and visitor-AI selections, explicit permission expansions, typed read
ports, and separate reviewed manifests. `services/resume_publication_validation.py`
performs read-only validation and returns either a neutral denial/stale/unavailable
result or `ReviewedCandidate`. There is no default adapter and no write method.

Only the focused synthetic test module calls these components today. No app
registration, route, flag, schema, SQL, live provider, publication transaction,
guest response, or independent citation endpoint is installed.

## Trust and version contract

The private `_context_from_authorized_server` seam is for a later trusted adapter
after authentication/authorization. All arguments must come from server state;
request dictionaries must never be unpacked into it. Its opaque construction
seal prevents accidental dictionary/boolean use, **not malicious in-process
Python**, and does not authenticate anyone. Owner preview must attest the exact
subject as authenticated owner and use a closed owner purpose. Guests cannot
invoke E review, regardless of global sharing. Owner preview can inspect a
sharing-off candidate; that is not a public pointer or permission grant.

Every version tuple binds subject, Resume identity, explicit draft/publication
revisions, sharing epoch, canonical content/access revisions, source identity,
version and digest, and media placement/source/catalog/readiness dependencies.
Zero is a valid explicit initial revision where a producer supports it; media
placement/presentation versions must be positive, matching the media producer. Missing,
boolean, negative, unsupported-schema or wrong-type versions are not defaults.
Draft `None` is representable for non-draft snapshots but unavailable for E review.
Owner-photo catalog revision is explicitly null; generated artwork requires it.
No clock is authorization. Set-like collections normalize by exact reference;
duplicate entry/source identities, fields and placement slots are rejected.

Policy and media ports each return a typed snapshot with the **complete** version
tuple. Both must equal the candidate's prior tuple exactly, and all declared
entry/source/media dependencies must be supplied. A `current` result with missing
authority is unavailable. These separate reads do not establish one atomic
snapshot and do not promise the state remains current after return. The existing
`LivingResumeCanonicalCatalog` is not an adapter: its unavailable policy fallback
and default access revision 1 are expressly insufficient.

Saved/approved/active canonical source eligibility is attested by the future
authoritative port and checked alongside the imported `SourceVersion` digest,
identity and public-profile AI scope. Raw/pending source, private assistance and
generated-artwork metadata must never be attested as canonical evidence. Media
only appears in the display manifest. Display-hidden/AI-selected entries are
possible under explicit existing permission or an exact owner-reviewed expansion.
An expansion is a proposal, never a policy write.

Media review reuses existing alt/caption validators and rejects text that would
need normalization, exceed producer bounds, or contain disallowed controls.
Owner-photo provenance must equal the producer's fixed server-derived label.
Generated media requires an authoritative `CatalogAssetRecord` in `MediaState`,
bound to the selected asset identity/version/digest and source dimensions. Its
frozen catalog provenance derives the exact label; its label/tags feed the
existing catalog-claim safeguard for alt/caption. Client-asserted provenance is
never authority. The digest includes derived provenance and catalog label/tags
as presentation validation evidence. No accepted wording is silently rewritten.

## Review and digest semantics

Only changed editorial fields are deltas; each carries exact before/after text
or explicit null. The current canonical wording must match `before`. Unchanged
draft values cannot act as canonical writes. Manifests include the resulting
review wording for display and the existing pinned source references. They are
**not materialized post-publication canonical/source versions**. A later combined
transaction must apply only the reviewed deltas, produce the resulting canonical
and source versions, and publish complete manifests atomically; it must not
treat proposed wording as already approved AI evidence.

The digest is SHA-256 over UTF-8 canonical JSON with fixed schema/field names,
sorted object keys and reference collections, explicit nulls, exact member
wording, context, permissions/expansions, all versions, source content/use scopes,
and crop/alt/caption/provenance/dimensions/readiness. Nonfinite crop values are
rejected. Numeric crop equivalents and signed zero normalize; crops must already
satisfy the existing media geometry/precision contract so review does not silently
change them. No prose trimming or Unicode normalization occurs. No JSON decoder
is exposed: typed tuples reject duplicate field keys before serialization.

`ReviewedCandidate` is immutable validation output, not a durable authorization,
publication receipt, guest credential, or proof of current permissions. Future
transaction code must recompute/compare the review digest and every dependency
inside its transaction. Private restoration must not regrant permissions.

## Consumer inventory and compatibility

| Producer / existing surface | Actual current consumer | Boundary / failure |
|---|---|---|
| New E contracts and validator | `tests/test_resume_publication_contracts.py` only | Synthetic snapshots; fail closed; no runtime wiring |
| `ai_foundation.contracts.SourceVersion` | New E source validation; existing foundation gateway, Ask Pete manifest/service, My Opportunities canonical service | Imported unchanged; E checks identity/digest/scope, calls no model |
| `ai_foundation.gateway.AIProvider` and citation validator | Existing gateway/Ask Pete flows; **not this E implementation** | No `provider.py` exists in foundation; future F must import the actual protocol |
| `resume_media_repository.MediaPlacement`, `CropRect`, `validate_crop_geometry` | New E review and existing Resume media service | Imported unchanged; complete media versions/readiness required |
| Draft/canonical/policy mutable snapshots | Existing owner draft and entry-policy services | No authoritative E adapter implemented; unavailable/default-version catalog cannot be used |
| Reviewed candidate/manifests | Future combined E transaction and owner preview | Logical consumers only; neither implemented |
| Visitor AI manifest | Future F source adapter and independently authorized citation reader | Logical consumers only; no provider/citation implementation |

The existing public HTML registry in `app.py` allows only Pete's fixture,
`petec -> static/data/resume_data.json`. Existing public JSON/PDF are static
fixture resources. Ask Pete runtime loads its fixed manifest and fixture; its
citations are embedded excerpts and Resume anchors, not an independently
authorized citation endpoint. Generic owner draft/media commands remain distinct
from generic member publication. This checkpoint changes none of those paths.

The later combined E owner must coordinate owner corrections/restrictions/deletion,
canonical/policy versions, sharing pointer/epoch, draft, publication and command
receipts in one consistency boundary. Accepted lock order remains subject sharing,
sorted entries, draft, publication/receipt (or proven equivalent). Receipt identity
binds subject, command, request ID and normalized digest. Media readiness/storage
must be rechecked; asynchronous purge does not define revocation. No transaction
or SQL-engine race/rollback proof is supplied here.

Future F must buffer/schema-check answers, enforce actual supported evidence and
safe summaries, then recheck all dependencies before commitment. Foundation quote
link validation alone does not prove entailment. Conservative extractive output
would still have explicit limits; this checkpoint claims no answer grounding or
citation-access implementation.

## Verification and stopping point

Focused unittest discovery covers malformed/foreign inputs, all top-level version
changes, canonical/access/source/media dependencies, independent permissions,
explicit expansions, exact deltas, digest stability/sensitivity, media readiness
and geometry, source eligibility, unavailable adapters and immutable outputs.
Existing foundation codec/grounding/gateway and media repository/service tests
exercise the unchanged imported contracts. Package registry coverage ensures this
initiative appears exactly once in `current_protect` with correct counts.

Run the focused modules with the repository Python environment:

```text
python -m unittest tests.test_resume_publication_contracts tests.ai_foundation.test_provider_codec tests.ai_foundation.test_grounding_contract tests.ai_foundation.test_gateway_operations tests.test_resume_media_repository tests.test_resume_media_service tests.test_package_registry -q
```

Required Azure checks and independent exact-candidate review remain delivery
gates. No component browser flow is invented; Azure's existing required browser
suites remain its gate. Review/merge/deployment are separate evidence states.
After accepted repository delivery, stop at this E checkpoint. F and full E
integration remain out of this assignment.
