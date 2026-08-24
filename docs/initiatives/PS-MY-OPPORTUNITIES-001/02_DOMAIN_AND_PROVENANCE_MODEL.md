# 02 — Domain and provenance model

One rule generates this model: **different lifecycles are different objects.**
A stale source listing must never rewrite member-owned history; a member's
private assessment must never leak into shared discovery data. Azure SQL
remains the working canonical-truth direction (owner ledger, preserved V2
direction); nothing here selects final topology (REC-02, doc 15).

Identifiers are opaque keys per the `_opaque_key` convention in
`services/opportunity_slate_v2_service.py`. Every mutable row carries a
rowversion-style concurrency token (`_version_token` convention). Timestamps
are UTC; display localization is a UI concern (doc 04 §7).

## 1. Object catalog

### Shared, member-independent (discovery side)

| Object | Identity | Mutability | Purpose |
|---|---|---|---|
| `source_policy` | `policy_key` | Append-only versions | One row per source/provider class: legal basis and the full rights dimensions — display, excerpt, full description, storage, AI use, caching, retention, attribution, removal, termination, exit. Nothing may be ingested, stored, displayed, sent to AI, or retained except as its current policy version permits. |
| `source_receipt` | `receipt_key` | Append-only; immutable while retained | The raw payload exactly as received from a **shared supply connector** (never a member import, which is the private `member_import` object below), plus transport metadata (source id, fetched/received timestamp, declared content type, byte count, payload hash). Retention bounded by `source_policy`; rights-driven removal follows the §4 tombstone model — the payload body is detached and destroyed, PeerSlate's own action facts (internal keys, PeerSlate timestamps, policy basis, removal reason/actor) always remain, and source-derived tombstone elements (payload hash, source identifiers) remain **only where the applicable rights permit**, so provenance stays walkable to the rights-permitted extent. |
| `source_listing` | `listing_key` | Mutable head + versions | One opportunity as one source currently presents it: provider identity, external reference, canonical URL, current lifecycle state (doc 03 §1), `last_attempted_at`, `last_successfully_verified_at`, and the separately persisted **application-link validation state** — `application_link_state ∈ valid \| invalid \| unknown`, `link_last_attempted_at`, `link_last_validated_at`, invalidity reason (doc 05 §5). Link validity is neither lifecycle closure nor outage; it is its own recoverable fact. |
| `source_version` | `version_key` (parent `listing_key`) | Immutable | One observed content state of a listing: normalized fields, permitted stored content per policy, content hash, `observed_at`, the producing `receipt_key`. New observation with a different hash ⇒ new version. |
| `canonical_opportunity` | `opportunity_key` | Mutable head + history | The deduplicated role identity across sources: employer identity, title, location(s), arrangement, the set of linked source listings, the deterministically selected **governing source head and governing `source_version`** (doc 03 §9), field-level source attribution for displayed facts, derived aggregate eligibility, and the merge/split audit trail. |
| `requirement_version` | `requirement_version_key` (parent `opportunity_key`) | Immutable | The atomized requirement set derived from one governing `source_version`: ordered `requirement_item`s, each with clause text span reference, classification `required` \| `preferred`, classification basis (doc 07 §2), and stable `requirement_item_key`. **One invariant everywhere:** every accepted content change creates a new `source_version`, but a new `requirement_version` is derived **only when the normalized requirement clauses materially differ** (doc 03 §§9.5, 10) — non-requirement content changes still surface truthful posting-changed/source-history UI without assessment churn. Old versions are never edited. |
| `company_context_claim` | `claim_key` | Immutable versions | One neutral company statement: claim text, claim class, source reference, `source_policy` reference, `as_of` date, limitation label. No claim exists without a permitted, linked source (doc 06 §5). |

### Member-owned, private by default (member side)

| Object | Identity | Owner | Purpose |
|---|---|---|---|
| `criteria_draft` | `draft_key` | `user_key` | The visible, editable interpreted criteria: structured criterion list, verification scope (`fully_verified` \| `not_fully_verified` \| `both`), direct filters, the originating natural-language request text, interpretation provenance (`ai_interpreted` \| `member_edited` \| `manual`), parent `snapshot_key` when refining. Mutable until applied or discarded. |
| `applied_criteria_snapshot` | `snapshot_key` | `user_key` | Immutable copy of a draft at the moment of explicit Apply; the only thing a search executes against. Chain: `previous_snapshot_key`. |
| `search_execution` | `execution_key` | `user_key` | One run against one snapshot: stages, coverage state, degraded reasons, cancellation, timing. |
| `result_snapshot` | `result_key` | `user_key` | The immutable result identity of one completed **or partial** execution (completeness-marked, doc 04 §11): ordered member entries, each binding `opportunity_key` + governing `requirement_version_key` + **the governing `source_version_key` at result time + the per-field attribution references used for displayed facts (doc 03 §9.6)** + gate outcome + ordering inputs at result time; partial snapshots carry their reason and contain only fully evaluated entries. All bindings are **references, never copied source facts**. Restoration and pagination read this exact basis, never a re-query, so a later non-requirement source change cannot rewrite an old result; rights-removed referenced content renders as unavailable (doc 05 §8), never substituted. |
| `assessment` | `assessment_key` | `user_key` | One member × one `requirement_item` (of one `requirement_version`): type `required` \| `preferred`; state `Verified` \| `Not established` \| `Appears unmet` \| `Review unavailable`; reason code (doc 07 §4); evidence links (references to authorized evidence records — never copies); assessed_at; correction history (append-only). |
| `practical_fit_observation` | `observation_key` | `user_key` | Separate practical-fit notes/observations; never an input to the required gate or preferred ordering. |
| `evidence_grant` | `grant_key` | `user_key` | The authorization object: purpose (fixed: `qualification_verification`), scope (evidence classes/records), granted_at, expires_at, revoked_at. No member evidence is read for assessment outside a live grant (doc 08 §2). |
| `saved_opportunity` | `save_key` | `user_key` | The Saved relationship: `opportunity_key`, the `source_version_key` the member last reviewed, saved_at, removal state with undo window. A reference, never a copy of the canonical role. |
| `slate_link` | `link_key` | `user_key` | The explicit relationship between a canonical opportunity and one member's Opportunity Slate workspace: Slate workspace reference, created_at, created_from (`result` \| `saved`), the `source_version_key` handed off (doc 11 §4). |
| `member_import` | `import_key` | `user_key` | Private member-supplied source material (pasted text, uploaded document, or — only if Pete later enables fetching — a fetched URL): sanitized extracted content, import provenance (submitted URL, final URL, resolved address, fetch time, content hash, sanitizer version), and pipeline outcome states (doc 06 §2). Exists solely for that member's own private use under Site Rules §3. It is **never** a shared `source_receipt`/`source_listing`, never discovery-index input, never a `canonical_opportunity`, and never visible to any other member. |

### Fixture isolation

Every shared-side object carries `data_class` ∈ `fixture` \| `production`.
Fixture rows (Astraeus, LumenWorks, Northwind, Canopy and their details) are
design fixtures and never mix with production rows in a query result; the
service layer refuses cross-class joins (doc 13 §1). Fixture rows are labeled
in every rendering context.

## 2. Provenance chain

```text
source_policy (rights)
  └─ source_receipt (raw, immutable)
       └─ source_listing (per-source head)
            └─ source_version (immutable content states)
                 ├─ canonical_opportunity (deduped identity; governing version per source)
                 │    └─ requirement_version (immutable atomized requirements)
                 │         └─ assessment (member-private, per requirement_item, evidence-linked)
                 ├─ company_context_claim (separately sourced; never derived from member data)
                 └─ member relationships (saved_opportunity, slate_link, result_snapshot entries)
                      — all reference opportunity_key + the exact version reviewed
```

Every member-visible fact must be walkable to its source: a displayed
requirement traces to a `requirement_item` → clause span → `source_version` →
`source_receipt` → `source_policy`. A displayed `Verified` traces to an
`assessment` → evidence links → live `evidence_grant`. A company statement
traces to a `company_context_claim` → source → policy. Anything that cannot
complete its walk is not displayed.

Member imports form a deliberately separate **private** chain —
`member_import` (owner-scoped) → that member's own private use — which never
joins the shared chain above at any node.

## 3. Separation invariants

1. **No copied truth.** Saved, results, Slate links, and projections reference
   `opportunity_key`/version keys; they never copy role content (Constitution
   rule 3; the one narrow exception is the rights-governed Slate handoff
   excerpt, doc 11 §4).
2. **Search relevance is not qualification.** Retrieval ordering inputs live in
   `result_snapshot` entries; assessment states live in `assessment`. No score,
   probability, percentage, or employer prediction field exists on any object,
   API, or UI surface.
3. **Attempt is not verification.** `last_attempted_at` and
   `last_successfully_verified_at` are distinct columns on `source_listing`;
   no code path may update the second on a failed attempt (doc 16 binds the
   `Last checked` label to these semantics).
4. **Member data never enters shared objects.** Nothing on the discovery side
   references `user_key`. The discovery index (if the index candidate is
   accepted) is built only from shared-side objects (REC-05).
5. **A source update never rewrites member history.** An accepted content
   change creates a new `source_version`; a new `requirement_version` (and
   therefore new assessments) follows **only when the normalized requirement
   clauses materially differ** (§1 `requirement_version` row; doc 03 §§2,
   9.5, 10). Either way, prior `result_snapshot`, `saved_opportunity`,
   `assessment`, and `slate_link` rows are untouched and remain labeled
   historical (doc 03 §§1, 6).
6. **Closure, outage, and missing evidence are three different facts** carried
   by three different objects: listing lifecycle state, listing verification
   timestamps, and assessment state respectively.
7. **One authoritative fact body per fact.** Requirement text lives only in
   `requirement_version`; evidence bodies live only in their source-of-truth
   store (doc 07 §6); assessments hold references and reason codes.
8. **Member imports never become inventory.** A `member_import` never
   produces a shared receipt, listing, version, canonical opportunity, index
   document, or any cross-member-visible content (Site Rules §3; doc 06). No
   pipeline, correction, or operational action may promote one.

## 4. Retention and cleanup ownership

| Object family | Retention driver | Cleanup behavior |
|---|---|---|
| `source_receipt`, stored content in `source_version` | `source_policy` retention/termination rights | Policy-driven purge **detaches and destroys content bodies** and leaves an auditable tombstone. Tombstone contents are themselves rights-bounded (doc 05 §8): PeerSlate's own action records (internal keys, PeerSlate timestamps, policy basis, removal reason/actor) always remain; source-derived elements (payload hash, source identifiers, provider reference data) remain only where the applicable rights permit. Rows are append-only and immutable while retained; the tombstone is the one permitted terminal mutation, so provenance stays walkable to the rights-permitted extent after removal. |
| `member_import` | Member lifecycle **and** content rights at point of use | Deleted with the member (and included in export); individually deletable by the member at any time. Any applicable source-content obligation (e.g. a takedown class) is honored at point of use and, where required, by targeted body removal under the same tombstone discipline (doc 06 §3). |
| `criteria_draft` | Member action + inactivity expiry | Discarded drafts hard-delete on expiry; applied snapshots persist. |
| `search_execution`, `result_snapshot` | Member retention window (owner decision at C4, the persistence owner per §6) | Expired snapshots delete with their entries; saved items persist independently. |
| `assessment`, `evidence_grant`, `practical_fit_observation`, `saved_opportunity`, `slate_link` | Member-controlled: export and delete per account data rights | Deletion cascades member-side only; shared side is untouched. |
| Discovery index documents | Rebuildable projection | Full rebuild from canonical truth at any time; deletion of a canonical row fences its projection out on next read (local fence pattern, doc 04 §9). |

## 5. What this model deliberately does not contain

- No application, application-status, or employer-contact object (application
  product is out of scope by owner decision).
- No notification/monitoring object (deferred to a separate future
  owner-approved package, if ever).
- No member-facing score field of any kind.
- No public projection of any member-side object.
- No `journal_*` reference.
- No committed table names, column types, or index definitions — physical
  schema is proposed by the §6 owners under the migration conventions
  (`SQL FIles/Migrations/registry.json` gate discipline), and **only after
  Pete records the REC-02 topology decision** (doc 14 §1). Nothing in this
  model selects Azure SQL, Azure AI Search, or any physical design.

## 6. Storage and migration ownership (all REC-02-gated)

Exactly one child owns each object family's persistence, migration, and
rollback; consumers arrive only after the owner (doc 14 §1 serial order).

| Object family | Owning child | Proposed migration |
|---|---|---|
| Shared canonical: `source_policy`, `source_receipt`, `source_listing`, `source_version`, `canonical_opportunity`, `requirement_version` | C2 | `PS-MYOPP-001_canonical_foundation` |
| `criteria_draft`, `applied_criteria_snapshot` | C3 | `PS-MYOPP-002_criteria_state` |
| `assessment`, `evidence_grant`, `practical_fit_observation` | C5 | `PS-MYOPP-003_qualification` |
| `search_execution`, `result_snapshot` | C4 | `PS-MYOPP-004_search_execution_results` |
| `saved_opportunity`, `slate_link` | C6 | `PS-MYOPP-005_relationships` |
| `member_import` | C10 | `PS-MYOPP-006_member_import` |
| `company_context_claim` | C12 | `PS-MYOPP-007_company_context` |
| Content-free telemetry | C9 | `PS-MYOPP-008_telemetry` |
