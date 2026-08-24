# 05 — Supply and source policy

Provider-neutral by construction: no provider is selected, contacted,
licensed, or paid by this architecture. C1 executes the comparison and rights
work; C2 implements the lifecycle. At least one owner-approved licensed
commercial opportunity feed with exact rights is the standing entry condition
for the first credible live private-sector release (Release Level 3) — an
owner decision this document only preserves.

## 1. Connector contract (provider-neutral)

Every **shared** supply source — licensed feed, permitted public source (e.g.
USAJOBS class), direct employer/ATS feed — implements one interface. Member
URL/document import is **not** a supply source and never enters this
pipeline: it is the owner-scoped private path defined in doc 06
(`member_import`, doc 02), which produces no shared receipt, listing,
version, canonical opportunity, or index input.

```text
connector.describe()   → { source_id, source_class, policy_key, capabilities
                           (pull | push | closure_signal | change_signal),
                           schedule_hints }
connector.acquire()    → source_receipt[]   (raw, exactly as received)
connector.normalize(receipt) → normalized listing fields + content per policy
```

- Connectors never write canonical objects; they produce receipts and
  normalized candidates. The shared ingestion pipeline owns admission,
  versioning, dedupe, and lifecycle — one implementation, N connectors.
- A connector without a live `source_policy` row cannot be registered; the
  registration check is deterministic code, not convention.
- Ownership: C2 implements the neutral interface and the synthetic/fixture
  connector; the selected commercial provider's adapter is the
  decision-gated C11 child (`PS-MYOPP-LICENSED-FEED-ADAPTER-001`, doc 14),
  which must complete before any C9 Level 3 licensed-feed operation.
  Credentials live only in deployment configuration, never the repository.
- Scraping LinkedIn, Glassdoor, Indeed, Google Jobs, or similar services as a
  source foundation is rejected by owner decision. API access is never
  treated as commercial display/AI/storage permission.

## 2. Rights ledger (`source_policy`)

One versioned row per source class, naming every dimension before first use:

| Dimension | Question it answers |
|---|---|
| display | May PeerSlate show this content to a signed-in member? Which fields? |
| excerpt | Excerpt limits (length, attribution form)? |
| full_description | May the full description be stored/rendered? |
| storage | What may persist, and for how long? |
| ai_use | May content enter AI interpretation/assessment prompts? |
| caching | Cache/index permissions and horizons |
| retention | Required deletion horizon after closure/termination |
| attribution | Required source attribution text/link |
| removal | Takedown obligations and response window |
| termination | What must happen to already-stored content at contract end |
| exit | Migration/export rights; identifier portability |

Ingestion, storage, AI use, rendering, and telemetry all check the policy at
the point of use (not only at intake), so a policy version change takes effect
without re-ingestion. Exact rights values per provider are C1 owner-decision
outputs; the ledger structure is fixed here.

## 3. Intake and admission (receipt → listing/version)

Admission checks, in order, each with a named refusal reason
(→ `quarantined`): policy present and permits ingestion; payload within size/
format bounds; required identity fields present (employer, title, application
target); content parseable and sanitizable (doc 06 §3 rules apply to *all*
untrusted source HTML, provider-supplied included); no fixture/production
class mixing. Passing intake creates/updates the `source_listing` head and an
immutable `source_version` when the content hash is new.

## 4. Canonicalization and dedupe (merge/split)

- Candidate keys: normalized employer identity + normalized title + location
  set + application-target host. Exact-key match auto-links a listing to an
  existing `canonical_opportunity`; near-match (bounded similarity on the
  candidate keys) enters a review queue — auto-merge only at the conservative
  threshold C2 fixes with fixtures; anything below is two opportunities until
  proven one.
- Merge/split is reversible with tombstones and unchanged member keys
  (doc 03 §9.2). Cross-source duplicates (same role via two providers)
  resolve to one canonical opportunity carrying both source references; the
  displayed facts come from the deterministically selected governing
  source/version with field-level attribution (doc 03 §§9.3, 9.6) — never
  from paid placement.

## 5. Application-link validation (persisted state; recoverable)

The stated application path carries its own **persisted validation state on
the listing** (doc 02 §1), separate from lifecycle: periodic bounded checks
verify that the application URL resolves (per the doc 06 network rules), is
not a soft-404/closed page per source-class heuristics, and matches the
listing's employer/ATS host expectations.

- `application_link_state ∈ valid | invalid | unknown` (`unknown` = never
  checked or outside the validation window), with `link_last_attempted_at`,
  `link_last_validated_at` (successful validations only), and a closed
  invalidity reason enum (`unresolvable` | `soft_closed` | `host_mismatch`
  | `blocked`).
- **Gate semantics (condition 6, §6):** a head passes only while
  `application_link_state = valid` and `link_last_validated_at` is within
  the validation window; `invalid` and `unknown` both fail that head's gate
  eligibility. The listing's lifecycle state is untouched — link
  invalidity is **neither closure nor outage** (doc 03 §1).
- **Recovery:** a later successful validation flips the state back to
  `valid` and restores eligibility with no lifecycle event and no member-
  history effect. Transitions record attempt/success timestamps and reason
  in the listing's append-only history and emit content-free events
  (doc 12).
- **Outbound safety:** every link check is an outbound request to
  employer/ATS hosts and runs exclusively through the reusable
  **safe-outbound validator** (`services/my_opportunities/safe_outbound.py`,
  C2-owned, doc 14): https-only scheme rules, per-connection DNS/address
  revalidation, the full doc 06 §1 private/link-local/metadata deny set,
  redirect and fetch budgets, content-type/size boundaries as applicable to
  a validation probe, and **no credential or cookie forwarding of any
  kind**. C13 later reuses this same validator for member-URL fetching.
- Validation windows/frequency share the freshness threshold owner decision
  (mechanism fixed; values deferred). C2 owns the model, the validator, and
  their tests (doc 14), including the adversarial outbound matrix (DNS
  rebinding, private-network/metadata targets, redirect chains,
  timeout/outage) and the valid/invalid/unknown/recovery lifecycle proof.

## 6. Live Opportunity Gate

The gate is evaluated **per source head**; a head passes only when all hold:

1. identity complete (employer, title, application target);
2. source authority (policy permits display to this surface; rights current);
3. head lifecycle `current` (not changed-pending-reverification, closed,
   unreachable, stale, invalid, quarantined);
4. freshness within threshold (owner decision pending; mechanism fixed);
5. deduplication resolved (not sitting in a pending link-review,
   doc 03 §9.1);
6. application link `valid` with a successful validation inside its window
   (§5; `invalid` and `unknown` both fail this condition).

**Aggregate rule (doc 03 §9.4):** the opportunity is eligible for *current*
qualified results while at least one rights-permitted head passes; when the
governing head fails but another eligible head exists, governing selection
fails over (doc 03 §9.5); when no head passes, the opportunity leaves current
results with the truthful aggregate reason.

The gate is evaluated at result-assembly time (and inside the index fence when
the index topology is accepted), so eligibility changes take effect without
waiting for reindexing.

## 7. Closure vs. outage vs. removal vs. termination

| Event | Listing state | Member-visible truth | Content handling |
|---|---|---|---|
| Source confirms closure | `closed` | "Closed by source"; alternatives offered; saved/Slate history preserved | Retain per policy retention |
| Source unreachable | `unreachable` | "Could not reverify"; not closed; prior data labeled with last-successful age | No change |
| Provider removal/takedown of one listing | `closed` with `removal` reason | As closure | Content purged per removal obligation; source-derived provenance elements retained **only as the applicable rights permit** (§8; doc 02 §4 tombstone model) |
| Provider termination | All its listings leave gate eligibility; an opportunity another permitted source still covers **fails over** (doc 03 §9.5) and stays eligible | Member history stays explainable (§8) | Termination dimension governs stored content; reindex drops its projections |

## 8. History preservation under rights pressure

Member history (saves, results, assessments, Slate links) must stay
*explainable* even when licensed content must be purged — but retention
authority is honest about what PeerSlate actually owns:

- **Member-authored work is unconditionally retained**, subject only to the
  member's own lifecycle: assessments, corrections, practical-fit
  observations, saves and links as relationships, and the member's own
  notes. This is the only unconditional class.
- **Source-derived facts are rights-bounded — including the "minimal" ones.**
  Role title, employer name, posting dates, content bodies, metadata, and
  provenance details all originate from the source; they survive
  termination/removal **only to the extent the applicable
  `source_policy`/rights permit**, and are never described as
  PeerSlate-authored.
- Where rights require removal, bodies are detached and destroyed under the
  doc 02 §4 tombstone model, and the tombstone itself is rights-bounded:
  PeerSlate's own action records (internal keys, PeerSlate timestamps,
  policy basis, reason/actor) always remain; source-derived tombstone
  elements (hashes, source identifiers) remain only where permitted.
- The member relationship and history rows always survive (they are member
  data), rendered without prohibited source facts when rights so require —
  e.g. "a role you reviewed on <PeerSlate date> — details no longer
  available (provider rights)" — never silently keeping restricted facts in
  view.
- C1 must evaluate, per provider, exactly which reference facts survive
  termination (a named rights criterion and potential per-provider blocker,
  never an assumption), and C11's termination/exit proof must demonstrate
  the honored behavior.

## 9. Refresh and reindex

- Refresh scheduling is per source-class (schedule_hints), budget-bounded
  (doc 12), with per-listing backoff on `unreachable`.
- The discovery projection (if index accepted) is rebuildable at any time from
  canonical truth; reindex is an operational action with no member-data risk
  (nothing member-owned is in the index, REC-05).

## 10. Provider evaluation criteria (C1 checklist, preserved from V2 research)

Coverage; identifier stability; update/closure latency; duplicate rates;
field completeness; display/full-description rights; AI transformation
rights; caching/retention; attribution; removal; rate limits; reliability;
privacy posture; cost per useful live opportunity; exit/migration; §8
metadata-retention compatibility. Output: a comparison record and rights
ledger candidates for Pete — never selection by inference, contact, or spend.
