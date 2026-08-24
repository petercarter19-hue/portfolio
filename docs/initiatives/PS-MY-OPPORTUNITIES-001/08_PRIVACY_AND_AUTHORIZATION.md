# 08 — Privacy and authorization

Identity is server-derived (`identity.get_current_identity`), authorization
happens **before** retrieval, AI, rendering, telemetry, or mutation, and
everything member-side is private by default. The v2 route stack
(`_resolve_identity_or_gate`, `_is_same_origin_write`, `_apply_room_headers`,
`safe_return`) is the reused enforcement pattern for every My Opportunities
surface.

## 1. Owner / record / action matrix

Actors: `anonymous`, `member` (the owner), `other member`, `system jobs`,
`AI (as a tool invoked server-side)`.

| Record family | anonymous | other member | owner (member) | system jobs | AI tool |
|---|---|---|---|---|---|
| Shared discovery objects (policies, receipts, listings, versions, canonical, requirement versions, company claims) | no direct access; only through future public-free surfaces if ever approved (none exist; My Opportunities is signed-in) | read via search results only (they are member-independent) | read via search/dossier | read/write per pipeline role | read per `source_policy.ai_use` only |
| `criteria_draft`, snapshots, executions, results | none | none | full within own `user_key` | owner-bound search worker (§2a) may create/update `search_execution` and write `result_snapshot` for exactly the owning member; TTL cleanup remains content-blind | interpretation input: the member's own request text only |
| `evidence_grant` | none | none | create/revoke/inspect own | expiry sweep (content-blind); the §2a worker reads the owning member's live grants at execution time to compute the admitted evidence set | never sees grants; sees only records the grant admits |
| `assessment`, `practical_fit_observation` | none | none | read/correct own | initial writes by the §2a-bound assessment writer during search execution; recompute triggers (revocation, new version, correction) by the named recompute path | proposes assessment content within grant scope |
| `saved_opportunity`, `slate_link` | none | none | full within own | overlay derivation (listing states) | none |
| `member_import` (paste/upload always via C10; remote fetch only via the separately Pete-gated future child C13) | none | none | full within own | private sanitize (and, only under C13, fetch) pipeline running only under the requesting member's binding; rights-at-point-of-use checks (doc 06 §3); never promotes content to any shared object | extraction is deterministic tooling, not AI (doc 06 §2) |

Enforcement is service-layer: every member-side service method requires the
server-derived `user_key` first parameter (`_require_user_key` convention);
no route or browser-supplied owner identifier is ever trusted (Site Rules §1).
Direct-key probing by another member returns not-found (no existence oracle).

## 2. Evidence grant object and authorization-before-AI

`evidence_grant { grant_key, user_key, purpose: qualification_verification,
scope (evidence classes and/or record sets), granted_at, expires_at,
revoked_at }`

- Grants are explicit member actions created through the
  evidence-authorization boundary surface (approved mobile state), inspectable
  and revocable at any time.
- **Order of operations is fixed**: resolve identity → load live grants →
  compute admitted evidence set → only then may retrieval/AI/assessment read
  it. No pre-fetch, no speculative inclusion, no cross-purpose reuse (a grant
  for qualification verification admits nothing to any other feature).
- AI prompt assembly is a fenced serializer: it may contain the member's
  request text, the requirement clause, and admitted evidence records —
  nothing else (no other members' data, no unadmitted evidence, no telemetry
  identifiers). The fence is code, tested with negative fixtures.

## 2a. Owner-bound search worker and initial assessment writer

The asynchronous search worker (C4's `search_worker`) is the narrow system
actor for search execution, and — through the qualification service it
invokes (C5) — the **initial assessment writer**. Authority is bound, not
ambient:

- **Binding.** The execution record carries the owning `user_key` and
  `snapshot_key` from Apply time; the worker derives everything from that
  binding and accepts no other owner input.
- **Authorized writes, exhaustively:** create/update the `search_execution`;
  write the `result_snapshot`; and — inside the assessing stage, via C5's
  service — **create initial `assessment` rows** for exactly the owning
  member, one current assessment per (member × `requirement_item` ×
  `requirement_version`), reusing an existing current assessment instead of
  duplicating (idempotent by that identity; history append-only). Nothing
  else: no grants, saves, links, drafts, imports, canonical or shared
  objects, and no other member's anything. It cannot extend its own
  authority or create new authorization. **Recompute authority remains the
  separately named recompute path** (revocation, new requirement version,
  member correction — §1 matrix), not the search worker.
- **Read scoping (two record classes, one rule each):** every **member-side**
  read/write is mandatorily filtered by the bound `user_key`. **Shared
  canonical/index** reads are member-independent by design — those records
  contain no member data (doc 02 invariant 4) and carry no `user_key` to
  filter on; instead they pass the projection/fence integrity check
  (doc 04 §10). The admitted owner-scoped context (criteria snapshot,
  grant-admitted evidence) is joined to shared data **only after**
  authorization resolves, never before.
- **Recheck at execution time**: before work begins, re-verify the ownership
  chain (execution → snapshot → member), that the snapshot is still that
  execution's snapshot, that the member's grants are live for the assessment
  reads, and that `source_policy` still permits each content use.
- **Per-assessment-write recheck**: each assessment write re-verifies the
  grant admitting its evidence at write time. An assessment written under a
  then-live grant is durable member truth; if the grant is revoked later
  (even mid-execution), the normal revocation recompute path transitions it
  — history is never silently unwound.
- **Every reported per-item state is backed by a durable row.** Two failure
  classes are distinct: (i) assessment **computation** unavailable (AI down,
  evidence source down, timeout, computation error) with persistence working
  → a durable `Review unavailable(reason)` assessment row is written, and
  the entry may enter the snapshot backed by that row; (ii) assessment-row
  **persistence** itself fails → no state exists to report, so that
  opportunity entry is **excluded** from the snapshot and the execution
  terminates `partial(assessment_persistence_failure)` (doc 04 §11) — a
  per-item state is never fabricated in a snapshot without its backing row.
  Assessment writes are idempotent by identity (member × item × version)
  and precede entry admission; the snapshot write is always last, in its
  own transaction; exclusions emit content-free events (doc 12).
- **Recheck before persistence/return** — precisely: the same checks re-run
  before the `result_snapshot` is written and before results are served. On
  failure, **no additional `result_snapshot` or member-result persistence
  occurs**; the bounded `failed(authorization_changed)` execution status and
  its content-free audit event are recorded. Assessment rows already
  durably written under their prior successful per-write authorization
  remain as prior authorized records, are **not served through any result
  of this execution**, and follow the normal revocation/recompute policy.
- Cleanup/expiry of drafts, abandoned executions, and expired snapshots
  remains a separate TTL-only, content-blind job with no result- or
  assessment-writing authority.

Worker actions emit the same content-free audit events as member actions
(§4), attributed `system:search_worker` (assessment writes:
`system:search_worker/assessment`).

## 3. Authorization-before-retrieval for member reads

Every member-side read (results, saved view + its search/filter, dossier
assessments, history) resolves identity and filters by `user_key` inside the
query — never post-filtering in the browser and never filtering after private
data has already entered a response buffer (Constitution rule 6).

## 4. Audit and logging exclusions

- **Content-free audit events** on: grant created/revoked, assessment
  writes/recompute cause, save/remove, Slate link create/continue, import
  pipeline outcomes, correction actions. Events carry keys, actor class,
  reason codes, timestamps — never request text, criteria values, evidence
  content, requirement text, or extracted source content. For member
  imports, audit and telemetry retain only a **non-identifying host/address
  class and reason code** — never the exact URL, hostname, path, query,
  body, or any content hash that could identify member-supplied material
  (one rule with doc 12 §5); exact provenance lives only inside the
  authorized `member_import` record (doc 06 §3).
- **Logging exclusions** (application logs and telemetry, doc 12): no member
  request text, criteria content, evidence bodies or identifiers-with-content,
  imported content, or company-claim text tied to a member. The Search 3F
  census discipline (record shape and counts, retain no query text) is the
  binding pattern.
- `/healthz` remains member-data-free (Site Rules §5); nothing here adds to
  it.

## 5. Retention, export, delete, projection cleanup

- Member-side objects are member data: included in account export
  (versioned JSON per capture-export precedent) and deleted on member
  deletion — grants, drafts, snapshots, executions, results, assessments,
  observations, saves, links, imports.
- Deletion cascades member-side only; shared discovery data is untouched
  (it contains no member reference, invariant 4, doc 02).
- Projection cleanup: if any per-member derived projection is ever created
  (none is required by this architecture; REC-05 keeps assessments out of the
  shared index), its cleanup is part of the same deletion transaction and
  covered by a negative test proving no orphaned member data survives in any
  derived store.
- TTL cleanup jobs (drafts, abandoned executions) are content-blind deletes
  by key + age.

## 6. Slate handoff authorization

Creating/continuing a Slate from an opportunity is a member-initiated,
explicitly confirmed action (doc 03 §8). The handoff carries only: the
member's identity (server-derived on the Slate side again — no identity
assertion crosses in the payload), the `opportunity_key` +
`source_version_key` references, and the rights-permitted content excerpt
defined in doc 11 §4. No assessments, grants, criteria, or evidence cross
automatically; the Slate workspace starts from source material, and the
member brings anything else deliberately.

## 7. Negative multi-member proof obligations (C3/C4/C5/C6/C7/C10/C13/C8 gates)

Reusing the synthetic two-member QA foundation
(`PS-SYNTHETIC-MULTI-MEMBER-QA-001`, closed; reusable pattern evidence):

- Member B cannot read/modify/observe existence of member A's drafts,
  snapshots, results, assessments, grants, saves, links, or imports — by
  listing, by direct key, by filter probing, or by timing-visible behavior
  difference.
- Revoking A's grant changes nothing for B; B's identical requirement against
  B's own evidence assesses independently.
- Cross-member direct-key requests return the same not-found shape as truly
  absent keys.
- Slate handoff commands (C7): member B's `create_slate_from_opportunity`,
  `continue_slate`, and `list_slate_history` against member A's `link_key`,
  Slate workspace reference, or opportunity relationship are refused with
  the not-found shape; no creation, continuation, listing, or existence
  signal crosses owners.
- AI prompt fence: injected fixture canaries in B's evidence never appear in
  A's assessment inputs (asserted at the prompt-assembly seam).
- Export for A contains all of A's and none of B's records; deletion of A
  leaves B intact and leaves no A-keyed row in any store or projection.
