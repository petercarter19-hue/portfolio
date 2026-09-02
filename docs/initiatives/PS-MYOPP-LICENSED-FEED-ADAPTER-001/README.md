# PS-MYOPP-LICENSED-FEED-ADAPTER-001 — C11 adapter package

## Status and authority

This Protected repository package implements the build-only C11 outcome for
all three source classes selected by Pete in
`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-09-01/include-all-provider-options`:

1. licensed commercial aggregator;
2. permitted government feed; and
3. direct employer feed, with Greenhouse- and Lever-shaped variants.

That decision widens parent document 14 §C11's singular “selected provider”
wording to three class-shaped adapters. It does not change document 14 and it
does not select, contact, purchase, enable, or operate a provider. The package
uses the concurrency variation recorded in its active claim: C11 is disjoint
from C10 except for the serialized `docs/governance/PACKAGE_REGISTRY.json`
tail. Repository authority is through an independently accepted merge;
production authority is withheld.

No migration, production policy row, provider credential, live acquisition,
scheduler, deployment, setting change, feature enablement, spend, member
exposure, or Level 3 operation is part of this package. All observed listings
in its evidence are explicitly fictional P-1 fixtures.

## Implemented boundary

`services/my_opportunities/licensed_feed_adapter.py` implements C2's exact
`describe() → acquire() → normalize()` protocol without giving a connector
write access to canonical truth. `IngestionService` remains the only path from
adapter output into C2 admission.

The shared core provides:

- a closed content-free error vocabulary;
- frozen named-setting resolution whose values are excluded from repr;
- a socket-free `RecordedTransport` and a `LiveTransport` that has no default
  network client and requires a later C9-operated, timeout-enforcing sender;
- current-policy checks before transport and normalize-time rights projection;
- hard page, examined-item, payload, aggregate-byte, elapsed-time, retry,
  per-class request-spacing, and backoff budgets;
- documented provider-envelope parsing with one receipt per valid item; every
  such receipt retains that item's byte-exact contiguous JSON token from the
  response, a common UTC page receipt time, and that item's stable external
  reference;
- deterministic documented-format mapping and HTML-to-plain-text sanitation;
- class/data isolation; and
- removal, termination, export/exit, and member-truth rehearsal helpers over
  C2's existing public seams.

The three production descriptor families are:

| Class | Descriptor identity | Pinned endpoint family | Live gate |
|---|---|---|---|
| Licensed aggregator | `licensed:<provider>` | Adzuna or Jooble documented base | Complete executed provider/counsel packet and complete current policy; the production ledger is deliberately empty now |
| Government | `government:usajobs` | `https://data.usajobs.gov/api/search` | Written approval for PeerSlate's exact use and complete current policy |
| Direct employer | `direct:<ats>:<board>` | Greenhouse or Lever documented base for the registered board | Pete's per-employer go-ahead and one complete policy per employer |

Configured values cannot redirect acquisition to another host. The only
provider choices accepted by the aggregator setting are `adzuna` and `jooble`;
the only direct board tokens are `greenhouse:<slug>` and `lever:<slug>`.
Because the documented Greenhouse and Lever response items do not identify
the employer, `PEERSLATE_MYOPP_FEED_DIRECT_BOARDS` is a strict JSON object
whose canonical `ats:board` keys map to approved, nonblank employer display
names. Direct production construction derives identity only from that binding;
no caller or provider payload may supply or override it. The exported class
constructor enforces the same rule and rejects a production `employer` argument.

## Named setting contract

Values belong only in App Service settings or a later managed operational
binding. Only these names exist in the repository:

| Class | Required names |
|---|---|
| Licensed aggregator | `PEERSLATE_MYOPP_FEED_AGGREGATOR_PROVIDER`, `PEERSLATE_MYOPP_FEED_AGGREGATOR_APP_ID`, `PEERSLATE_MYOPP_FEED_AGGREGATOR_API_KEY` |
| Government | `PEERSLATE_MYOPP_FEED_GOVERNMENT_API_KEY`, `PEERSLATE_MYOPP_FEED_GOVERNMENT_USER_AGENT_EMAIL` |
| Direct employer | `PEERSLATE_MYOPP_FEED_DIRECT_BOARDS` |

The direct-employer value shape is, for example,
`{"greenhouse:approved-board":"Approved Employer Name"}`. It is an exact
board-to-employer approval map, not a CSV list. Keys must already be canonical,
values must be printable nonblank strings, and duplicate, malformed, oversized,
or unregistered bindings fail closed without exposing configured values.

Any absent or blank required setting raises `credentials_missing` naming only
the missing setting. Settings are resolved before `LiveTransport` construction;
no default sender exists. A complete setting set still grants no rights:
registration and pre-transport acquisition independently require the current
matching `source_policy`.

## Rights enforcement and honest C2 seams

The adapter receives a current-policy read view. Immediately before the first
transport call it requires current `acquire` and `persist` decisions matching
the descriptor's source id, source class, and data class. A missing, expired,
mismatched, or denied decision makes zero transport attempts. C2 then checks
the same current rights again before retaining a receipt or admitting a
candidate.

At normalize time the adapter re-parses the exact standalone item token,
requires its identity to match the receipt, and then applies a conservative
projection:

- denied persistence removes every source field from the candidate, and C2
  independently rejects persistence;
- denied full-description use removes description and derived requirement
  clauses;
- denied excerpt or attribution dimensions remove their named residual fields;
  and
- no missing field is invented.

C2's current `SourcePolicy` model carries boolean dimensions, not contract
field allowlists or excerpt lengths. The projection therefore never invents
granular permission beyond those booleans. A later provider packet must fit
the exact C1/C2 model or trigger a separately claimed policy-model correction;
this package is not authority to weaken it. C2 also requires every initial
registration action and all twelve dimensions to be affirmative. Consequently
the licensed production state is honestly represented by no policy row and a
deterministic `policy_missing` registration refusal—not by a fabricated
partially permissive row.

C2 exposes termination per listing rather than source-wide enumeration. The
rehearsal driver therefore validates the explicit listing-key set and a
revision that allows termination while denying display, acquisition, and
persistence before it publishes anything; it then applies the same terminal
operation to each unique supplied listing. An exact-revision replay skips only
listings already tombstoned by that revision and resumes the remaining validated
set. A later C9 run must obtain that complete set from canonical storage before
it can claim source-wide completion.

## Recorded fixture families

No fixture came from a live call, account, trial, provider contact, or captured
provider listing. Each JSON file contains its direct documentation citation,
access date, transcription statement, and `data_class: fixture` label outside
the documented item array. Names, identifiers, and listing text are fictional.

| Family | File | SHA-256 |
|---|---|---|
| Aggregator representative format | `aggregator/representative.json` | `e0d7b576a8ab9425d414168b609a48ad7d7f56f2972327cf4d642a9b96833c75` |
| USAJOBS format | `government/usajobs.json` | `b929df5fd195c5d1d8e1e268d50e3f860bccae8714be7acf5739b7b493f24c8b` |
| Greenhouse Job Board format | `direct_employer/greenhouse.json` | `c1e8b9c478de57614cc5ceeed99011e3c5fffd7e691c7033db9c62487b6c40ab` |
| Lever Postings format | `direct_employer/lever.json` | `c393514d324a6793e0b4c019f82100dd9c94e8eee4a6a709f8ab9cd5acf21846` |

## Failure and budget contract

| Condition | Result |
|---|---|
| Missing setting | `credentials_missing`; transport is never constructed |
| Missing/current-policy denial | `policy_missing` or `policy_denied`; zero transport attempts |
| HTTP 401/403 | `credentials_rejected`; no retry |
| HTTP 429 | at most one retry for the page; a Retry-After above the configured ceiling stops without an early retry; then `rate_limited` |
| Timeout/OSError/5xx | at most two retries, then `transient_exhausted` |
| Malformed individual item | content-free `payload_malformed` refusal; the bounded run may continue |
| Unknown response envelope, response status, identity mismatch, or oversize | `contract_violation`; run stops |
| Page or elapsed-time ceiling | `budget_exhausted`; run stops |
| Item ceiling | bounded result marked `truncated`; no extra request |

Payload size is hard-capped at C2's 5 MiB receipt limit; a run cannot exceed
five pages, 200 examined items, 10 MiB of wire response bytes, or 10 MiB of
retained item-token receipt bytes. Item slicing cannot inflate retained bytes
beyond the already bounded response bytes. Production
government and direct-employer attempts are spaced by at least one second.
Licensed-aggregator construction requires an explicit contract-derived rate
budget and rejects an absent or zero interval. Every wait is capped by the
remaining wall-clock budget, and no request follows a wait that cannot be
fully honored. Every `FeedRequest` carries the positive finite time remaining;
`LiveTransport` rejects missing/invalid deadlines and overdue returns. Because
the sender is an injected synchronous C9 seam, its actual I/O implementation
must enforce that timeout in flight—the adapter does not claim it can preempt an
arbitrary nonconforming callable. Rate delay, total bytes, pages, items, and
elapsed time are independently bounded. The adapter
fully builds its receipt tuple before `IngestionService` begins canonical
admission, preventing a later transport error from creating a partially
admitted feed run.

## Removal, termination, and exit rehearsal

The P-1 suite executes every class through C2 and proves:

- single-listing removal purges content under the current removal decision;
- source termination publishes a restrictive policy and tombstones every
  explicit listing in the rehearsal set;
- the same cross-class canonical opportunity fails over to its other
  rights-permitted head;
- both survivability branches work for every class: explicit title/employer
  retention versus no surviving source-derived facts;
- every export reads the current C2 policy revision and is refused when its
  exit dimension is false, while an allowed export separates PeerSlate-owned
  record keys from rights-permitted source identifiers; and
- actual C4 result snapshots, C5 assessments/revisions, and C6 saves and
  Slate links are persisted in their public repositories, independently
  re-read before and after lifecycle action, and remain byte-equal throughout.

These are P-1 component proofs only. They do not claim a source-wide production
inventory, a real contract disposition, a deployed service, or P-5 live data.

A documented provider page may contain several items. Candidate review exposed
that retaining the complete page in every C2 listing receipt made item-granular
takedown impossible because a removed or malformed item's bytes survived in
sibling receipts. The corrected evidence unit is therefore the exact contiguous
JSON token for one provider item: it is copied from the response without
reserialization, preserves whitespace, key order, escapes, and numeric spelling,
and contains all provider bytes used to normalize that listing. Envelope and
sibling bytes are validated transiently but not retained. This is an explicit
correction to the blueprint's literal complete-response receipt wording, while
preserving its underlying raw-evidence rule. It makes per-listing C2 tombstoning
complete without a migration or activation prerequisite; full response-envelope
retention is deliberately not claimed.

## Stop controls and later gates

- No scraping or browser-login automation exists.
- No live acquire is used in tests or evidence.
- No credential value is committed, logged, placed in a receipt, or included
  in an exception.
- No class registers without the complete current policy C2 requires.
- Licensed commercial use remains locked until Pete accepts the executed
  provider packet and counsel resolves every C1 cell.
- Government use remains locked until written approval is recorded.
- Direct-employer use remains locked until Pete approves that employer and a
  policy row exists for its exact board.
- Deployment, policy seeding, scheduling, configuration, source-wide
  termination operations, and enablement belong to a separately authorized C9
  operation. Merge is not deployment.
