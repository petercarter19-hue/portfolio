# Interview Studio AI — consolidated architecture (v2.8)

**Package:** `PS-INTERVIEW-AI-ARCHITECTURE-001`
**Status:** v2.8 architecture accepted by Pete on 2026-08-16, including D3, D8, and D9
as recommended. This D13-relocated candidate awaits fresh exact-SHA review and Pete's
approval of that exact relocated SHA before any merge grant.
**Base and lineage:** current PR target Azure `origin/main`
`b4d79b217b1b8b68128a5271031390bb2be521b6`; Gate A entered `main` historically at
`6b3f90d5`. The architecture was designed against deployed application SHA `f42e5399`
(Azure run 1096, byte-identical Interview source to diagnosed `f7a71739`).
**Runtime effect:** none. No application, prompt, model, provider, schema, configuration,
pipeline, or live behaviour changed.

**Package roles:** package manager — **ChatGPT Work**, the Pete-designated management
role; initial architect and sole writer through handoff SHA `3fcdb917` — the assigned
**Claude Interview AI session**; current sole repository writer and technical reconciler
after control-only transfer commit `6c188980` — **Codex**; independent review — fresh,
read-only Codex reviewers; material visual creator for later visual slices — **Original
ChatGPT**; owner and final product decision-maker — **Pete**. These assignments grant no
merge, release, deployment, provider-spend, or production authority.

## How to read this package

**This document is the only normative one.** The five sections (`10`–`14`) are
**non-normative historical drafts**: they contain the 31 defects the Opus review found and
the further defects Codex found, and they are retained unedited solely as the audit trail
of how the design was reached. An implementer works from this document alone **for every
architecture decision and cross-slice contract**; the concrete artifacts enumerated at
the end of §3 (specialist output schemas, the evaluation-run schema, telemetry DDL and
enums, and the rest of that list) are supplied by their implementation slices under the
binding requirements here.
Where a section says anything this document does not, the section is detail, and where
it contradicts this document, the section is wrong.

| File | Role |
|---|---|
| **00 (this)** | Normative architecture, complete. |
| `01` + `02` | Diagnosis + errata (errata overrides diagnosis). |
| `03` | Live authenticated evidence, bounded claims. |
| `10`–`14` | Historical drafts. Non-normative. |
| `20` | Opus adversarial review (31 findings). |
| `21` | Codex reconciliation: all rounds' verdicts and change registers. |

---

# 1. The architecture in plain language

Interview AI today is four API endpoints whose coaching instructions are string literals
inside `app.py`, restating the same rules five ways with drift already visible. Nothing
records which instruction text produced a given answer; nothing can be rolled back.

The architecture replaces that with **six named specialists over one shared foundation**:

1. **Diagnostician** — classifies the actual question: parts, listening criteria,
   ambiguity/confidentiality flags, response obligations, and a length band *with reasons*.
   It never sees the member's answer and never coaches. Does not exist today. Pete
   accepted D9: it advises or runs as a prerequisite, but the member's chosen action
   always selects the member-facing specialist.
2. **Answer Coach** — reviews the submitted answer. Exists; works well; is extended.
3. **Revision Partner** — proposes an editable revision with a source-aware change ledger,
   never overwriting the original. Exists in primitive form.
4. **Private History Nudge** — two-step retrieval over the member's own past answers.
   Does not exist; today's "nudge" is a generic tip generator (interim id
   `planning_hints`).
5. **Grounded Example** — an answer from deliberately selected authorized evidence, or an
   honest refusal. Cannot function for ordinary members until member evidence exists (D1).
6. **Generic Example** — a clearly illustrative answer containing nothing private.

Held together by: a **shared constitution** every specialist inherits; **release
identity** that makes every output traceable and every change reversible; and the
**fourteen named guardians of `guardian-registry@2`** — thirteen fully deterministic,
while support-linkage is deterministic *linkage* with semantic support evaluation-gated
— under the package's central rule that
**privacy and authorization never rest on instructions to a model**.

What the live test changed: the empty-evidence path becomes a zero-cost server
short-circuit; answer-version preservation is new construction (the stored record is flat
and proposals are never persisted); and adaptive length is *measured*, not claimed. On
length, the evidence is exactly this: the universal 60–120-second instruction is
source-confirmed in the deployed artifact; one request returned a 111-word draft
(observed); delivery time and adherence were not measured and remain unverified. The
architecture therefore treats length as something to measure in evaluation rather than
assert from prompt wording.

---

# 2. Release identity — the complete released system

*(Replaces the per-bundle-only identity; Codex finding 1.)*

Identity has three levels, each excluding what changes independently of it:

**Digest framing rule:** every structured digest payload in this section is UTF-8 JSON
canonicalized under RFC 8785 with an explicit `digest_domain` value; arrays retain the
order stated here. Raw bundle files use the unambiguous framing defined next.

**Bundle identity** — canonically, the **full SHA-256** over domain bytes
`peerslate.interview.bundle.v1\0`, followed in fixed order by logical files
`constitution.md`, `instruction.md`, `schema.json`, `provider.json`; each entry is framed
as 8-byte big-endian filename length + UTF-8 filename + 8-byte big-endian content length
+ exact committed file bytes. Filenames, lengths, and the domain separator make distinct
file tuples unambiguous; no line-ending or text normalization occurs. The id string
`<specialist>@<semver>+<sha8>` uses the
first 8 hex chars as a **display label only** (§2 canonical-identity rule); every check
compares the full hash. All specialists start at
`1.0.0`. Hashing prompt text alone is prohibited. **Bundle catalog:** released bundles
live at `prompts/interview/bundles/<specialist>/<semver>+<sha8>/`; a released bundle
directory is immutable and retained for as long as any recorded release set references
it. The canonical reference used in candidates, evaluation, activation, rollback, API
stamps, and telemetry is `bundle_ref { bundle_label, bundle_content_sha256 }`; the label
is display/path metadata only and the full hash is the identity. Each catalog directory
contains that full reference in its manifest; the CI byte-lock recomputes the full hash
and rejects a label collision or a label that resolves to any other full hash.

**Runtime-core digest** — `runtime_core_digest`: SHA-256 over the canonical, sorted
**guarded dependency manifest** — a named, closed, CI-enforced list
(`guarded-paths.json`, part of `contracts_version`) whose entries contain each repository
path and its full blob SHA-256, plus any immutable external artifact coordinate and its
full implementation digest. It covers **every behaviour-affecting dependency**: the
Interview routes and request/response transforms, serializers, validators, guardians,
manifest builders, orchestration, and provider adapters (at implementation these are
extracted into `services/interview_ai/`; provider *configuration* lives in bundles and
is bound by bundle refs). Every mutable repo-local transitive implementation and every
dependency-lock artifact it can execute through must enter the manifest. Code may remain
outside only when it is an immutable external artifact whose **full implementation
digest** is itself a manifest entry; a pinned interface or version alone never satisfies
closure. Two CI guards make the set closed and honest: **(closure)** the import and
dependency graph from every guarded entry point must resolve to manifest entries, and
the build recomputes every repo blob and external implementation digest; **(tripwire)**
any diff touching a manifest path
without bumping `guardian_set_version` or `contracts_version` fails the build. The
digest excludes everything that versions independently: bundle content (bound by bundle
refs), the control records, and the rest of the repository — a documentation commit or
an unrelated application change leaves it untouched. **This is what makes rollback executable:** adding a
bundle, recording a run, activating a release, or merging unrelated work changes nothing
inside the core digest, so prior release sets remain selectable across those events. (Two
superseded predecessors, for the audit trail: the whole-tree `runtime_artifact_digest`
contained the bundle files, so any new bundle stranded every prior release; the
tree-minus-prompts variant broke on any unrelated commit. Both dead ends are replaced by
this guarded-path scope.)

**Mutable control records live outside every digest**, under `prompts/interview/control/`:
`registry.json` (the activation record) and `evaluation-runs/<run-digest>.json` — each
run record immutable once written, so recording a run changes no digest it evaluated.

**Canonical identities are full SHA-256 values.** Bundle content hashes, the candidate
system digest, run digests, and release-set ids are stored and compared full-length
everywhere (registry, run records, telemetry, evaluation bindings); the short forms in
id strings (`+<sha8>`, 12-char digests) are **display labels only** and never the basis
of any check.

**Candidate system digest** — `candidate_system_digest`: SHA-256 over the canonical
structured object (`digest_domain: peerslate.interview.candidate.v1`) containing the
ordered tuple of:

1. `runtime_core_digest` as defined above;
2. every candidate bundle slot, in specialist-enum order, as
   `{ specialist, bundle_content_sha256 }`. The associated `bundle_label` is stored for
   lookup/display but is excluded from identity computation; every check uses the slot
   plus full content hash. Each bundle's `schema.json` **contains that specialist's concrete
   input-manifest specification** (its source classes and authorization requirements),
   so the released system identifies actual manifest contents, not merely a versioned
   builder contract);
3. `guardian_set_version` — one version covering validator and guardian code, over
   `guardian-registry@2` (§8);
4. `contracts_version` — one version covering the knowledge/input-manifest builder
   contract (which source classes each specialist's builder accepts, and their
   authorization requirements), the router-token schema, the marker contract, the
   dimension registry, and `telemetry-contract@1` (§7);
5. `evaluation_set_hash` — the fixture/golden-case set identity.

**Evaluation-run record** — immutable, external to every digest, named by its own
`run_digest`. It records: the `candidate_system_digest` it exercised; the full bundle
refs it ran (with the run-digest identity projection using specialist slot + full content
hash, never the display label); the **threshold-set id and version** used;
**calibration-versus-judged status**; the
**case-partition hash** (which fixture partition it judged); the **scorecard/evaluator
version**; the **fatal-class policy version**; a **coverage manifest** — the
mechanically checked list of exactly which changed elements this run exercised (bundle
refs, guardian version, contracts version, provider configuration via bundles,
evaluation-policy elements), which activation consumes as data rather than inferring;
and its results. Its concrete JSON schema
is a deferred obligation of the evaluation slice; these bindings are normative now. It
records no release-set id, because none exists yet. A run whose recorded digests do not
recompute is void.

**Release set** — the *activation* record: `interview_release_set_id` = the **full
SHA-256** over (`candidate_system_digest`, the ordered digests of the accepted
evaluation runs, the threshold-set id those runs were judged against); a 12-char prefix
may label it in displays and file names but is never the basis of any check (§2
canonical-identity rule). Acyclic: candidate
digest first, runs record it, the release record references the accepted run digests.

**Activation coverage proof — per changed element, not per digest.** Activation verifies,
against the previous release set, that **every changed element is exercised by at least
one accepted judged run recorded for this candidate digest**: each changed bundle ref
(provider/model configuration lives inside the bundle's `provider.json`, so a
provider/model change is a bundle change), any `guardian_set_version` change, any
`contracts_version` change, and any evaluation-policy (threshold set, scorecard,
fatal-class) change. An accepted run merely existing at the same candidate digest proves
nothing about an element it never exercised.

**Calibration and judgment never share a result set** (§9): if thresholds were set from
Wave 1, Wave 1 is calibration-only and the activating run judges a **locked holdout
set**. Membership is bound immutably — each run records the explicit, immutable case-id
list behind its `case_partition_hash`, and the harness **mechanically proves the
calibration and holdout id sets are disjoint** (empty intersection) before a judged
batch starts; differing hashes alone prove nothing and are not accepted. **Before a
judged batch runs, its exact case list and count and the authorized spending cap are
already locked.** All runs used for one activation must share one threshold id/version,
scorecard version, fatal-policy version, and judged status — the activation validator
checks that equality. **No
spend authority is created by this architecture**: each future Protected slice carries a
Pete-approved total evaluation cap; the manager may run judged batches within that cap
(batch size set by the slice's harness partition) without returning per batch.

**Active-release authority and precedence:** runtime configuration
(`PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET`) selects the active release; `registry.json` is
the record of what may lawfully be selected. Configuration wins at runtime; a configured
id absent from the registry, or failing the compatibility check, is fail-closed —
interview AI endpoints answer `service_not_configured`; nothing falls back silently.
**Ordered fail-safe activation** (not one atomic transaction — it is a sequence in
which every step is individually verifiable and every failure lands fail-closed): append
the release-set entry to the registry, then set the configuration, then restart; the
boot check validates the configured id against the registry and compatibility rule
before serving. **Rollback** is the same ordered procedure pointing at a prior recorded
entry (already in the registry). A configuration-only rollback may
select only a prior release set whose record shares the current `runtime_core_digest`,
`guardian_set_version`, and `contracts_version` — verified mechanically from the prior
release-set record (§3 registry schema) before the switch. Anything else is a deploy,
not a config change.

When active-release resolution succeeds, every `server_call` telemetry row carries the
release-set id; a `specialist_call` row also carries its one full bundle ref, while a
`composition_parent` carries no bundle ref and its child rows carry their respective
refs. A pre-resolution `service_not_configured` row carries no release/bundle ref and a
Compare failure at that point has no child rows. `client_view` carries neither release
nor bundle identity (§7). Stamping identity
into **API response bodies** is an additive, disclosed API change deferred to slice 3
(§10): every response carries its server-issued `attempt_uuid`; after successful release
resolution, a specialist response carries one full bundle ref and a Compare response
carries the parent attempt id plus two child refs keyed by child and no invented parent
ref. An unresolved `service_not_configured` response carries no ref, and unresolved
Compare has no children. Slice 1 therefore keeps full behavioural parity. A release-set
id never appears in an evaluation run.

---

# 3. The canonical spine

Fixed values. Anything anywhere else that differs is void.

**Specialist ids** (closed enum; primary key of telemetry, versions, History, evaluation):
`diagnostician`, `coach`, `revision`, `history_nudge`, `grounded_example`,
`generic_example`, plus interim `planning_hints` for today's generic nudge — which is never
labelled as specialist 4.

**Source classes:** `question`, `answer`, `role_context`, `member_evidence`,
`history_selection`, `confirmed_context`.

**Provenance:** `member_submitted`, `member_confirmed`, `member_selected`,
`server_derived`, `external_untrusted`.

**Authorization:** `current_practice_authorized` (renamed from `session_authorized` — the
product is session-free and its vocabulary must be too), `member_action_authorized`,
`member_selection_claimed`, `reference_only`, `not_granted`.
`member_selection_claimed` means a single-use server selection row was minted **and
claimed by this operation** (§6.2 lifecycle: minted → claimed → completed | failed, with
`failed → reclaimed → completed | failed` once and `expired` terminal — the architecture
uses no “consumed” state for selections; the §4 envelope *nonce* is consumed, which is
a different object).

**Evidence lifecycle** (a different axis, never confused with authorization):
`evidence_lifecycle_state` ∈ `draft` | `approved_for_interview_ai` | `revoked`.

**Failure and outcome taxonomy** — one registry, three groups. Every response body
carries three fields — `failure_state`, `retryable: bool`, and `retry_policy` — and
clients branch on those, never on HTTP status alone.

`retry_policy` ∈ `none` | `member_initiated` | `after_window` | `after_signin` |
`with_changed_input`; the client renders the truthful next action from `retryable` and
`retry_policy`. The tables give both exactly — policy never appears as prose in the
retryable column.

*Request refusals (no work performed):*

| State | HTTP | `retryable` | `retry_policy` | Notes |
|---|---|---|---|---|
| `sign_in_required` | 401 | true | `after_signin` | |
| `malformed_request` | 400 | false | `none` | |
| `denied_authorization` | 403 | false | `none` | request-time refusal; the post-claim variant is `failed(denied_authorization)` on the operation, reported with `phase: post_claim` (defined in §6.2) |
| `rate_limited` | 429 | true | `after_window` | |
| `conflict` | 409 | see reasons | see reasons | always carries `conflict_reason` ∈ `stale_state` (retryable true, `member_initiated`, with refreshed state) \| `idempotency_key_mismatch` (retryable false, `none` — same key, different bound input; a client defect) \| `in_flight` (retryable true, `after_window` — identical request still running; carries Retry-After) |

*Execution failures:*

| State | HTTP | `retryable` | `retry_policy` | Notes |
|---|---|---|---|---|
| `provider_failure` | 500 | true | `member_initiated` | model call failed; `reason` ∈ `transport` \| `timeout` \| `rejected` \| `abandoned` (orphaned in-flight key, §3 reaper; may carry `dispatch_uncertain: true`) |
| `invalid_output` | 502 | true | `member_initiated` | reply failed validation — **including any truncation that damages a marker or segment; validators reject, they never silently slice** |
| `extraction_failed` | 422 | true | `with_changed_input` | a supplied document/link/paste could not be deterministically extracted; the member's input is preserved and returned |
| `internal_error` | 500 | true | `member_initiated` | non-provider server fault; distinct from `provider_failure` so operator triage and member copy are truthful |
| `unavailable_source` | 503 + `Retry-After` | true | `after_window` | a needed store is temporarily unreachable |
| `service_not_configured` | 503 | false | `none` | operator fault (missing/invalid active release); telemetry reason is the cross-call fixed value `active_release_unresolved`; retrying is pointless and the copy says so |

*Computed truthful outcomes (HTTP 200; `retryable` false, `retry_policy` `none` for all four):*

| State | Meaning |
|---|---|
| `no_history_match` | History was searched; nothing useful. |
| `insufficient_evidence` | Evidence **was consulted** and cannot carry this question. |
| `insufficient_information` | The request itself carries too little to act on (e.g., a question too fragmentary to classify); the response says what is missing. |
| `source_not_available_for_member` | The member has no authorized evidence at all. **Nothing was attempted, nothing was spent.** |

**Retry, spend, and terminal idempotency — two distinct identities, never conflated:**

- **Request principal, defined for everyone:** a signed-in request's principal is the
  server-derived member identity; a signed-out/public Interview request carries a
  **server-issued guest principal** (a signed, browser-scoped identifier with no member
  semantics, used only for idempotency and rate-limit scoping — guests have no History,
  selections, or evidence). “Server-derived identity” below means this principal.
- **Request idempotency key** — identifies one network request. Server-side it is bound
  to the **request principal, the purpose (endpoint/specialist), and a
  digest of the request body**; a reused key with a different bound identity, purpose, or
  request digest is rejected as `conflict` (409) and replays nothing. Duplicate handling
  is **atomic**: the key row is inserted first (unique-insert wins; **the loser initially
  observes `in_flight`** — 409, `conflict_reason: in_flight`, Retry-After — and never
  an immediate terminal outcome) so two simultaneous duplicates can never both spend.
  Once the winner's outcome is recorded, a duplicate with the same key and same digest
  replays it, whether success **or failure** — no new provider call, no new version, no new
  spend, ever. **Stored outcomes are retained 24 hours**, immutable for that window, then
  purged; a key seen after purge is a new request. **The operation-level final result
  (§6.2) shares the same 24-hour retention and purge**; after purge an operation is
  queryable only through its durable products (versions, reviews) in their own tiers.
- **Operation id** (History selections, §6.2) — identifies one authorized member
  operation, which may legitimately span two requests: the original, and the one
  authorized member retry after a failure. **The retry reuses the same operation id with a
  fresh request key.** Replaying the old failed request key returns the stored failure;
  only the fresh key performs the retry.

**Each request key's result is immutable and its own, within the 24-hour retention
window:** the original failed key replays its stored failure; the successful retry key
replays its stored success; after the window both are purged and a reused key is a new
request (§3 retention). **The
operation's final result is stored separately at the operation level** and is what the
UI treats as current. **In-flight lease and orphan recovery:** the key row is inserted as `in_flight` with a
lease expiry **and lease owner (worker id)**, and the row records whether provider
dispatch had begun (pre-dispatch vs dispatched). **Recording an outcome is a
compare-and-swap against the active lease and operation state:** a late worker result
arriving after reaping, lease expiry, or a reclaim fails the CAS and is **rejected and
discarded** — never recorded, never returned to any caller. Request-key and
History-selection state transitions are single-row atomic operations (insert-unique or
CAS); none is a read-then-write. A process that dies
after inserting the key but before recording an outcome leaves an orphan: a **reaper**
marks any lease-expired `in_flight` row `abandoned`. An `abandoned` row whose lease shows
dispatch had begun carries `dispatch_uncertain: true` — **PeerSlate cannot promise that
no provider work or billing occurred** after an indeterminate transport outcome, and no
document claims it. “Duplication prevented” is scoped to what the server enforces:
no second application-initiated dispatch for the same key while its state is knowable.
**Polling versus retrying are different acts:** re-sending the original key polls it —
`conflict`/`in_flight` with Retry-After while the lease runs, then the recorded outcome,
or `abandoned` — treated as a failure whose retry fields are **operation-aware**: in
general `retryable: true`, `retry_policy: member_initiated`; for a History operation the
§6.2 lifecycle governs instead — an abandonment inside the claim maps to the claimed-
phase transitions, and past the selection TTL it answers as §6.2's terminal expiry does
(`retryable: false`, `retry_policy: none`, `next_action: fresh_selection`). A
member-authorized retry is always a fresh key. SDK `max_retries=0`;
the server never auto-retries a provider call. Telemetry counts retries; duplicate
application-initiated dispatch is prevented within the §3 scope stated above.

**Router timeout: 15 seconds** (the per-specialist budget; the 30-second figure in the
Section 1 draft is void). Full budgets: diagnostician 15s, coach 30s, revision 20s,
planning_hints/history_nudge 15s, grounded/generic 20s, compare composition 45s.

**Bound registries and contracts** — either stated here or bound to one exact source, so
an implementer needs no synthesis from the drafts:

- **`question_class`** (closed, 8 values): `behavioral`, `professional_intro`,
  `motivation_fit`, `situational`, `role_specific`, `technical_case` — mirroring the six
  live families — plus `factual_direct` and `ambiguous`, which fix the
  everything-defaults-to-behavioral defect.
- **Family/dimension registry:** the live per-family dimension keys in
  `INTERVIEW_FAMILY_DIMENSIONS` (`app.py`) are the v1 registry, carried into
  `contracts_version` unchanged at extraction; changes to it are a contracts change, never
  a prompt edit.
- **`marker-contract/1`, in full:** a confirmation marker is a bracketed imperative
  sentence — capitalised verb first, ends with a period (e.g.
  `[Describe the specific outcome you achieved.]`); never a bare fragment; produced only
  by the Revision Partner; server-detected by the live `_IMPROVEMENT_MARKER_PATTERN`; and
  rejected in a **revision** submission (`attempt >= 2`) by the live gate at
  `app.py:3889-3900`, which first attempts deliberately pass.
- **`registry.json` schema (v1)** (at `prompts/interview/control/registry.json`, outside
  every digest, §2): `{ schema_version, active_release_set: { interview_release_set_id,
  candidate_system_digest, runtime_core_digest, bundle_refs[] (ordered,
  specialist-enum order; every item is `{ bundle_label, bundle_content_sha256 }`),
  accepted_run_digests[], threshold_set_id, threshold_set_version, guardian_set_version,
  contracts_version, evaluation_set_hash, activated_at }, bundle_catalog: index of
  `prompts/interview/bundles/`, prior_release_sets[] }`, where **every
  `prior_release_sets[]` entry carries the same full field set plus `deactivated_at`** —
  so every component identity needed to reconstruct and validate a rollback target exists
  in the record itself, and rollback compatibility (§2: same `runtime_core_digest`,
  `guardian_set_version`, `contracts_version`) is verified from the record alone before
  any switch. Append-only history; the CI byte-lock recomputes every recorded digest.
  Runtime configuration selects among recorded release sets and never defines one (§2
  precedence).
- **Golden cases and scorecard:** the accepted, unmodified files at
  `docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/03_INTERVIEW_STUDIO_GOLDEN_CASES.md`
  and `04_INTERVIEW_STUDIO_SCORECARD.md`. `evaluation_set_hash` is computed over exactly
  these plus any fixture files a slice adds.

With these bindings this document is self-contained **for architecture decisions and
cross-slice contracts**. What it deliberately defers, enumerated so the claim is honest:
golden-case and scorecard *content* (bound by exact path and hash); **the complete
per-specialist output schemas and failure contracts** (their binding requirements —
spine states, guardians, version identity — are normative here; the concrete JSON
schemas are each implementation slice's obligation); **the evaluation-run record's
concrete JSON schema** (its bindings are normative in §2); per-call-kind telemetry
failure-reason enum values (specialist and composition-parent), telemetry
exception-class/attribute allowlists, and the
remaining numeric bounds,
table DDL, procedure signature, and the purge job (completed by the telemetry slice
under `telemetry-contract@1`, §7 — the general enums and stated types are already
bound there); per-slice package briefs and
their test evidence; ChatGPT-created visual direction (D12); and production
configuration values. Nothing else is external.

---

# 4. The normative state model

*(New; Codex finding 6. Overrides both Section 2's and Section 3's versions.)*

Entities, session-free by construction — there is no Session object, gate, count, or
limit anywhere in this model:

- **Persistence tiers, defined once — every entity is assigned to exactly one:**
  *ephemeral tier* (in-memory/current-practice — lives only in the open page and the
  request; gone on close), *browser tier* (today's localStorage — device-local,
  member-namespaced, honestly disclosed as non-syncing), and *account tier* (the future
  server store — cross-device, authorized, revocable). Assignments: composer draft text —
  browser (existing autosave); submitted answer versions and reviews — browser today,
  account after migration/opt-in; **proposals — ephemeral**; working pointer — browser
  (account after opt-in); History records — browser today, account by migration;
  selections, tokens, request-key/outcome rows, and failure state — server rows,
  account-side by nature (request-key rows expire per §3's 24-hour window); practice
  records and attempts follow their answer versions' tier (browser today, account after
  migration/opt-in). Nothing moves *up* a tier
  silently: only the previewed, per-record, member-confirmed migration or an explicit
  member action crosses a tier boundary. **Guest/public browser namespaces are preserved
  across sign-in and sign-out and are never automatically mixed with, read into, or
  imported into a member namespace** — the existing owner decision Q-B, restated here as a
  model rule.
- **Practice record** — one member + one question. Groups attempts. The browser's existing
  `sessionId`/`sessionContextId` fields are local display grouping only and carry no
  server semantics. They are **never silently imported**: the migration preview shows the
  grouping that would be recorded, and only on the member's confirmation does it import —
  as `practice_context_id`, disclosed as a renamed browser-era label.
- **Attempt** — one submission chain for that question. `attempt_number` is a UX label
  — **server-assigned at creation in the account tier; computed locally as a display
  label in the browser tier** (§4 browser identifiers) — and never derived from
  counting reviews.
- **Browser-tier identifiers, defined:** a browser-only attempt or version cannot carry a
  server-assigned number or server ULID without a server round-trip it never made. The
  browser tier generates its own ids (client ULIDs, prefixed `b-`) and computes display
  labels locally; the migration preview shows the explicit mapping, and on confirmation
  the server assigns authoritative identities, recording `client_record_id →
  version_key` in the migration batch so provenance survives the crossing.
- **Answer version** — immutable, append-only. `version_key` (server ULID at the
  account tier; mapped from the browser id at migration),
  `parent_version_id` (nullable only for the first), `origin` ∈ `member_typed` |
  `member_dictated` | `applied_revision` | `restored_edit`, `from_proposal_id` when origin
  is `applied_revision`. Branching is legal: restoring an old version then editing forks
  lineage, recorded truthfully via `parent_version_id`.
- **Review** — belongs to exactly one answer version, and **exists only for a validated
  success**. A failed provider call or invalid output creates request/failure state (§3),
  never a Review row; the member's retry, if it succeeds, creates the first and only
  Review row for that request chain. A version may accumulate several reviews over time; a
  review never spans versions.
- **Proposal** — a Revision Partner output, with status `proposed` → `applied` |
  `discarded` and its change ledger, **bound to the exact source `version_key`, the review
  id it responded to, and the release set that produced it**. Tier rule: **a proposal is
  ephemeral** — pressing Improve does not persist it to localStorage, and it is never
  silently written to any durable tier. It becomes durable only through an existing
  disclosed opt-in or a separate explicit member action: *applying* it mints the
  `applied_revision` version in the member's answer tier, and an account-tier proposal
  record exists only under the member's disclosed account-saving choice. **Provenance for
  an account-tier apply travels in a signed, expiring proposal-application envelope**
  minted with the proposal, binding: the principal and purpose, the AI proposal text's
  `proposal_text_digest`, the separately computed `proposal_ledger_digest`, the source
  answer `version_key`, the review id, the release set, an expiry, and a
  **server-claimed single-use nonce**. At apply, the server computes `final_text_digest`
  over the member's submitted final text with the same canonical text-digest algorithm
  and derives `member_edited` by comparing it to `proposal_text_digest`; the ledger
  remains independently bound by `proposal_ledger_digest`. An edit is a recorded fact,
  never a refusal. What refuses is envelope invalidity:
  signature, expiry, principal, source-version, review, or release-set mismatch. The
  nonce is consumed **atomically in the same transaction** as the version mint and
  pointer move (a content-free operation receipt row), so a fresh request key can never
  apply the same ephemeral proposal twice — a repeat apply with the consumed nonce
  replays the original apply outcome idempotently. When `member_edited: true`, the
  stored ledger is marked as describing the AI proposal as generated, and the member's
  two digests preserve only the **fact** that the member edited the proposal — hashes
  cannot reconstruct or preserve an exact textual difference — never falsely claiming
  the ledger describes the final text. Exact edit auditing would require a separately
  disclosed, member-authorized snapshot or diff in the appropriate persistence tier and
  is not part of this architecture. Discarding an
  ephemeral proposal simply lets it go; where a durable record exists, discard sets status
  `discarded` rather than deleting.
- **Working pointer** — which version is "current" for the member. **Applying a proposal:**
  the applied revision's parent is **the pointer version at apply time**, with
  `from_proposal_id` recording the proposal, and the proposal permanently recording the
  `version_key` it was generated from. If unsaved composer text exists it is snapshotted
  as a `member_typed` version first (and becomes that parent). **If the pointer has
  diverged from the proposal's source version** — the member edited or restored since
  requesting the improvement — the apply does not proceed silently: the member is shown
  that the proposal was written against an earlier version and chooses to apply-anyway
  (parent = current pointer, divergence recorded) or discard. Restore moves the pointer
  without minting a version; a version is minted at the next commitment point.

**Atomicity — per tier, because localStorage and a server row cannot share one
transaction:**
- *Account-tier apply* is one database transaction or nothing: the unsaved-text snapshot
  version, the `applied_revision` version, the pointer move, the proposal status change
  **where a durable proposal row exists** (§4 tier rule — an ephemeral proposal has no row
  to update and is retired in the client-side swap instead), and the idempotency outcome
  row commit together. The same rule covers restore, discard, and version creation.
- *Browser-only mutations* stay entirely client-side — no server idempotency row exists
  for them — and commit by building the new state completely and swapping it in one
  write.
- *Cross-tier operations* (an apply that calls the server and then updates browser state)
  commit the server transaction first; the browser swap happens only after the server
  outcome is known. **Recovery is idempotent reconciliation:** if the client crashes
  between the two, replaying the request key returns the stored idempotent server
  response and the client **reconstructs its correct state from that response** —
  including retiring the ephemeral proposal the response shows as applied — the server
  never waits on, or rolls back for, a browser write. A partial apply is not a state in either tier.

**Concurrency — defined per tier, because they cannot behave alike:**
- *Account tier:* every transition is optimistic and checked — version creation sends
  `expected_parent_version_id`; apply, discard, restore, and pointer moves each send the
  expected current pointer/proposal state — and any mismatch (second tab, second device)
  is an HTTP 409 with both heads returned for the member to choose.
- *Browser tier:* localStorage has no server and can promise no 409. Its rule is the
  same-page request binding that already exists (epoch counters plus identity tuple,
  which drops any stale response) plus last-write-wins **only** for display-level state —
  never for answer text: an answer-text conflict between tabs is detected by version
  comparison on focus and surfaced to the member, not merged.

No last-writer-wins on member answer text anywhere, in either tier. A failed save must
snapshot-and-hold the member's text locally; a save refusal never discards it.

---

# 5. Specialist contracts

Each specialist ships as a bundle (§2) with: purpose, input manifest (source classes +
provenance + authorization per entry), output schema, guardians, failure behaviour,
evaluation slice, and version identity. The binding contract points:

**5.1 Diagnostician.** Input: question + optional `role_context` (`reference_only`).
Never the answer. Output: `question_class` (8 values), subparts (each a verbatim substring
— the subpart-substring guardian), `listening_criteria[]` (bounded strings; the Coach
consumes these — this field is owned here, in `contracts_version`), obligation enum,
flags, posture (`boundary_first` is a **posture**, not a length), and `length_band` ∈
`brief` | `standard` | `extended` with mandatory `length_reasons`. **No seconds exist
anywhere** — not in schema, template, or any server-rendered prompt line; the no-literal
test runs against the *rendered* prompt. Any member-facing speaking-time figure is
UI-computed from word count with a disclosed words-per-minute assumption, presented as an
estimate, never a quality signal.

**5.2 Coach.** Consumes the diagnostician result via a signed token (bound per §6.1).
**Degraded mode is deterministic and defined:** no valid token → server-derived fallback
dimensions from the family registry, no stated band, `basis: "deterministic_fallback"`
truthfully labelled. Never a refusal, never a silent default to behavioral. The coach
schema has no draft field — exact-field-set validation makes rewriting structurally
rejectable. **Claim anchoring applies to observations too:** every
`whatCameThroughClearly`, strength, and improvement item carries an `anchor` that is a
verbatim substring of the submitted answer (or, for absence findings such as
`missingOrContradictory`, an explicit `kind: "absence"` with no anchor claim) —
server-checked, so the coach cannot attribute to the answer something it does not
contain. **What anchoring proves, honestly:** the quoted text exists in the answer — it
does not prove the coach's *interpretation* of that text is right; interpretation quality
remains evaluation-gated.
No live improve-contract field is dropped without an explicit deprecation note.

**5.3 Revision Partner.** Allowed inputs, in full: the question, the preserved answer and
its version lineage, the Diagnostician result and Coach findings (both `server_derived`),
member-selected authorized evidence, and member-supplied `confirmed_context`. Nothing
else. The ledger fully accounts the revision: the server computes the diff between
preserved answer and proposed draft, and **every changed span must map to a ledger entry**
— `add_from_evidence` (anchored to the selected evidence item), `add_from_context`
(anchored to confirmed context), `marker_added`, `rewrite_of_existing` (anchored to the
answer span it rewrites), or `removal` (recording what was dropped — the live test showed
member framing silently removed). Unaccounted change spans are `invalid_output`. Marker
contract (`marker-contract/1`) preserved verbatim, including the `attempt >= 2` gate.

**5.4 History Nudge.** Two-step boundary per §6. When no match: offer add-a-detail
(becomes `confirmed_context`, one cap: **1,200 characters**), manual search, generic help,
skip.

**5.5 Grounded Example — claim-granular, deliberately selected.**
*(Codex findings 3 and 7.)*

- Input requires explicit `selected_evidence_ids`. **Absent selection → no provider call.**
  "Use all approved evidence" exists only as an explicit member action that populates the
  selection; the server never widens scope by default.
- Output is `segments[]`, each `{text, kind, evidence_id?, anchor?}` with `kind` ∈
  `evidence_claim` | `connective` | `confirmation_marker`. **An `evidence_claim` is a
  syntactic claim unit** — deterministically bounded as at most one sentence (single
  terminal punctuation) and at most 240 characters. Whether one sentence smuggles two
  semantic assertions is **not deterministically decidable** and is evaluation-gated
  (fatal class), never claimed as a validator property. Validation asserts: segment concatenation reproduces the
  full answer (complete coverage); every `evidence_claim` cites a **selected** id and an
  `anchor` that is a verbatim substring of that evidence item; markers are well-formed;
  digits appear only inside an `evidence_claim` whose anchor contains them, or inside a
  marker. The question and `role_context` may shape the response; **their content can
  never substantiate a member fact** — no anchor may resolve to them, which also closes
  the digit-in-question false-positive.
- **What the anchor check is, honestly:** a deterministic *support-linkage* check — every
  claim names its source and the source text it leans on. It is **not** deterministic
  claim support: a valid id and a harmless anchor do not prove the sentence's meaning is
  entailed by the evidence. Semantic entailment cannot be checked deterministically, so
  **for every generated `evidence_claim` — not only connectives — unsupported-meaning is a
  classified residual risk, evaluated per claim unit with a fatal failure class.** No
  document may describe the anchor check as deterministic claim support.
- **Connectives cannot carry claims.** A `connective` segment is restricted by validator
  to non-assertive linking text: at most 120 characters, digit-free, and screened against
  the entity lexicon built per-request from the selected evidence, the question, and the
  role context (employer names, technologies, titles, proper nouns) — any lexicon token
  appearing in a connective is `invalid_output`; assertive content belongs in an anchored
  `evidence_claim` or a `confirmation_marker`. Honest residual, narrowed: an invented
  qualitative claim using *no* digits and *no* known entity ("seamlessly led the team")
  can still pass the deterministic screen; it is assigned to evaluation with a fatal
  failure class, and stated as residual — not claimed solved.

**5.6 Generic Example.** No private member source **and no `role_context`** — the frozen
contract says no private member sources and role context is a member-private input; only
Pete may change that boundary. Validated against an empty evidence map, rejected if it
cites any id, `generic: true` server-set, mode-bound tokens so a generic answer can never
be re-presented as grounded. **Compare is a composition/action contract, not a**
**seventh specialist.** `composition: "compare"` sits **deliberately outside the closed
specialist enum** (§3); its parent telemetry row carries `event_kind: composition_parent`
with `specialist`, `bundle_label`, and `bundle_content_sha256` all **null** (§7 schema) — nothing pretends Compare
has one specialist or one bundle. **Start:** the parent operation **atomically registers
both child request keys against the parent attempt before either child dispatches.**
**Children:** `grounded_example` and `generic_example`, each with its own `attempt_uuid`,
full bundle ref, and request key, each with `parent_attempt_uuid` set (§7); usage and cost are
accounted **per child row** and never duplicated onto the parent. **Outcomes:** the
parent is terminal only once both children are terminal. **Partial failure preserves the
successful half**: its stored result is served, and its request key **replays it — no
second charge**; the member sees the successful half plus the honest failure state of the
other, and a retry **re-runs only the failed half** under a fresh key. **Persistence:**
child results follow the §3 24-hour transient window; any durable product they produce
follows the §4 tier rules. **D3 is accepted:** retain Compare as its own later
preservation slice (§10 slice 10), still behind evaluation and visual gates.

**Compare parent result mapping is mechanical.** When parent orchestration successfully
registers the two child keys and returns their terminal envelopes, the parent row records
`outcome: computed_outcome` and HTTP 200 whether the child mix is two usable results, one
usable plus one refused/failed result, or two refused/failed results; full/partial/no-
result truth lives in the two child envelopes and rows and is never collapsed into one
parent failure. That parent has null failure fields and exception, `validation_result:
not_applicable`, empty guardians, zero source counts, null usage/cost, and zero for any
timing stage it did not perform. A pre-resolution `service_not_configured` execution
failure creates no children and records parent `outcome: failed`,
`failure_state: service_not_configured`, `failure_reason: active_release_unresolved`, and
HTTP 503. A parent orchestration error that cannot return the bounded
child envelopes records `outcome: failed`, canonical `internal_error`, actual 5xx status,
and a reason from the slice-frozen `composition_parent` reason enum; any child row already
committed remains preserved.

**Generic Example receives no private-derived content, structurally — not merely
screened.** The Diagnostician's free-text outputs — `listening_criteria`, subparts, the
obligations rationale — are derived from the raw question and can repeat private names,
employers, or metrics; they are tainted `private_derived` and are **barred from Generic
Example's manifest by the source-allowlist guardian** (§8). The **compare-isolation
guardian is generalized**: it applies to **all** `private_derived` content, not only
grounded evidence, so neither route can hand it to a compare's generic child. Generic
Example receives only a **closed, minimized, deterministic projection** of safe enums and
codes — `question_class`, the obligation enum codes, `response_posture`, `length_band` —
**never free text derived from the question, ever.**

**Pre-Router reconciliation, stated honestly:** today's live generic path still transmits
the verbatim question; that live behaviour **predates this architecture and is not
changed by this documentation package.** Under this architecture the no-private-content
boundary and the projection are inseparable: **the new generic bundle activates only with
the projection available (Router slice or later); no interim new generic bundle ships
that transmits the raw question.** The current live behaviour's echo risk is recorded as
a **known gap that the Router slice closes.**

---

# 6. Private-context tokens and History authorization

**6.1 The token contract — every private-context token, one binding rule.** Every signed
token or server row that carries private context between requests — the router token, the
model-answer `contextToken`, and History selection rows — binds, verbatim: the
**server-derived principal** (§3 — member identity when signed in, the server-issued
guest principal on the public surface; never client-supplied — closing the cross-member
replay hole found in the current `contextToken`, which today carries no identity),
the **purpose** (which specialist may claim it), the **question digest**, the
**practice-context digest**, an **expiry**, and the **`interview_release_set_id`** it was
minted under. Consumption re-derives identity and rejects on any mismatch, including a
release-set mismatch after a rollback — a token minted under one release set is not
honoured by another.

**6.2 History selection — bound, claimable, retry-coherent.** *(Codex finding 5.)*

Step 1 is provider-free and structurally cannot return full content (excerpt precomputed,
content columns absent from the result set). Step 2 requires a server-minted selection row
binding: member, purpose, record id + pinned version, **question digest,
practice-context digest, candidate-set digest**, an opaque `operation_id`, and a 15-minute
expiry. A selection minted for question A is unusable for question B by construction.

**Lifecycle:** `minted` → `claimed(operation_id)` → `completed` | `failed`, with
`failed → reclaimed → completed | failed` once and `expired` terminal. The row is
claimed before the provider call — there is no separate “consume” step. **At mint and again at claim**, the
authoritative record is rechecked: ownership, the pinned version's existence, approval
state, and revocation — a record revoked between the member's selection and the claim
refuses with `denied_authorization`, and the re-check runs against authoritative rows, not
the projection. On `provider_failure` **or `invalid_output`** the claim moves to `failed`
with the reason recorded. The one authorized member retry then reuses **the same
`operation_id` with a fresh request idempotency key** (§3) and may re-claim once within
TTL. **The reclaim re-runs the full authoritative recheck** — ownership, pinned
version, approval, revocation — exactly as at mint and first claim; a recheck failure
is `failed(denied_authorization)` with no further reclaim. Replaying the old failed
request key returns the stored failure and performs nothing. A second failure requires fresh member selection. A **completed** selection's operation
replays its stored final success; its failed first request key still replays that
failure (§3 per-key immutability). It never re-claims, re-calls, or re-spends. Any other
operation, or expiry, requires fresh member selection.

**Every post-claim transition, enumerated — there are no others:**
`claimed → completed` (validated success);
`claimed → failed(provider_failure)` (call failed or timed out);
`claimed → failed(invalid_output)` (reply rejected);
`claimed → failed(internal_error)` (non-provider server fault mid-operation);
`claimed → failed(unavailable_source)` (a needed store became unreachable mid-operation);
`claimed → failed(denied_authorization)` (revocation or approval change detected at the
re-check; **no retry** — fresh selection only);
`claimed → expired` (TTL passed mid-operation, including a server crash that never
recorded an outcome; fresh selection only);
`minted → expired` (never claimed within TTL);
`failed → expired` (TTL passed before any reclaim);
`reclaimed → expired` is enumerated below.
From `failed` — except `denied_authorization` — exactly one further transition exists:
**`failed → reclaimed`** (the §3-authorized member retry: same operation, fresh request
key, within TTL), then `reclaimed → completed | failed` terminally, **or
`reclaimed → expired`** if the TTL passes or a crash records no outcome during the retry
— a second `failed` is final and only fresh member selection can spend again. `expired`
and `failed(denied_authorization)` permit no reclaim. **Terminal responses are
operation-aware:** a second failure or expiry on a History operation answers with
`retryable: false`, `retry_policy: none`, and `next_action: fresh_selection` — never
the global member-retry affordance, which would advertise a retry this operation cannot
perform. A post-claim authorization denial
is reported to the client as `denied_authorization` with **`phase: post_claim`** in the
failure body, distinguishing it from a request-time refusal (`phase: request`).

**The interlock (unchanged from ruling R10, restated as the guardian set's rule):**
`history_selection` is the only source class whose manifest parameter cannot be populated
from request data at all — it accepts exactly the tuple returned by the claim
procedure in this request. One test asserts the builder raises on a non-claim value;
a second asserts no request field reaches it.

---

# 7. Telemetry — content-free, actually

*(Codex finding 4.)*

- Attempt identity is a **cryptographically random UUID**, generated per request, with no
  derivation from question text, role text, or any member content. The binding tuple
  (question/context identity for stale-response dropping) stays in browser memory only and
  is never transmitted as telemetry.
- No content-derived fingerprints: the current `questionId` question-text fallback and the
  role-text `contextId` fingerprint are named defects, not carried forward.
- Member attribution: none in the first slices. If longitudinal per-member telemetry is
  ever needed, it is Pete's decision (D10) and uses a secret-keyed, rotation-bounded HMAC
  — `sha256(user_key)` truncations are dictionary-testable pseudonyms and are prohibited.
  That decision must define purpose, retention, access, and deletion before any identifier
  ships.
- **The telemetry contract is separately versioned** — `telemetry-contract@1`, carried
  inside `contracts_version` (§2). **The boundary, stated once:** the two structural event
  envelopes below, their field names and stated types, required/null conditions,
  cardinality, provenance, content prohibitions (raw member text, model text, URLs, and
  free strings are prohibited values everywhere), sink kind, access rule, and retention
  duration are normative now. Deferred to the telemetry slice, to version and freeze
  before implementation — each call kind's failure-reason enum (per-specialist plus
  `composition_parent`), the exception-class and
  exception-attribute allowlists, the **remaining** exact numeric bounds (the
  `source_class_counts` 0–32 bound is already fixed below), table DDL, procedure
  signature, and purge job definition. A sentinel test enforces the normative fields and
  conditions here plus those slice-frozen, versioned allowlists; this document does not
  claim unnamed allowlists are already executable.

- **Attempt-id transport and validation:** the server generates `attempt_uuid` before any
  dispatch and owns it throughout. Slice 1 writes `server_call` only and does not emit a
  `client_view`. Slice 3's disclosed additive response contract returns that UUID in
  every API response; the client may echo only that value to the `client_view` endpoint.
  The stored procedure inserts a client row only when a matching `server_call` foreign
  key exists and rejects an unknown/malformed id. A specialist view references its
  specialist attempt; a Compare experience emits one view for the parent attempt, not
  separate child-view rows.

- **Schema 1 — `server_call`** (`event_type: "server_call"`, written once by the server
  at response time; at most one per `attempt_uuid`, enforced by unique index — a
  duplicate insert is dropped):
  - Required, server-sourced: `attempt_uuid` (random UUIDv4); `recorded_at` (server UTC
    timestamp — the purge keys on it; a row without it cannot be written); `event_kind` ∈
    `specialist_call` \| `composition_parent`; `outcome` ∈ `success` \| `computed_outcome`
    \| `refused` \| `failed`; `http_status` (int); `retry_ordinal` (int ≥ 0); server
    timing fields `dur_receive_ms`, `dur_retrieval_ms`, `dur_manifest_ms`,
    `dur_provider_ms`, `dur_validate_ms`, `dur_respond_ms`, `dur_total_server_ms` (all
    monotonic duration ints, ms).
  - Required iff `event_kind = specialist_call`, else null: `specialist` (§3 enum).
    `bundle_label` (display only) and `bundle_content_sha256` (the canonical full hash)
    are non-null together iff release/bundle resolution succeeded, forming the §2
    `bundle_ref`; the sole permitted null pair on a specialist row is a pre-resolution
    `outcome: failed`, `failure_state: service_not_configured`,
    `failure_reason: active_release_unresolved` execution failure.
  - Required iff `event_kind = composition_parent`, else null: `composition` ∈
    `compare` (closed enum, currently one value) — a composition parent has no single
    specialist or bundle and the schema does not pretend it does.
  - Nullable, server-sourced (three nullable identities, exactly): `release_set_id`
    (64 lowercase hex characters, the full §2 SHA-256; non-null iff this call resolved an
    active release, otherwise null); `parent_attempt_uuid` (UUIDv4; non-null iff this is a
    child specialist row in a Compare composition, otherwise null); `operation_id`
    (server-generated UUIDv4; non-null iff this call belongs to a History operation,
    otherwise null).
  - Required/null rules, server-sourced: `failure_state` (§3 enum) is non-null iff
    `outcome` is `refused` or `failed`, otherwise null; `failure_reason` is non-null iff
    `outcome = failed`, otherwise null. `guardian_rejections[]` is always present (empty
    when none; guardian-name enum from `guardian-registry@2`, ≤ 14).
    `validation_result` is always present and is `passed` | `rejected` |
    `not_applicable`, with `not_applicable` required when no model output was validated.
    `source_class_counts` is always a complete six-key map of the §3 source classes to
    integer counts, using zero where absent and bounded 0–32 per class — counts only,
    never content. `provider_usage { input_tokens: int, output_tokens: int }` is non-null
    iff the provider returned a valid usage object, otherwise null. `cost_microusd`
    (server-sourced integer, 0..2^63-1) and `pricing_schedule_id` (server-sourced,
    exactly 64 lowercase hex characters: the SHA-256 of the immutable versioned pricing
    table) are non-null together iff that usage is synchronously priceable from the table
    before this append; otherwise both remain null and are never patched later.
    `exception { class: allowlisted enum, attrs: allowlisted scalar map }` is non-null iff
    a caught execution exception produces `outcome = failed`, otherwise null; its
    exact class/attribute allowlists are the explicitly deferred, slice-frozen contract,
    and a stringified exception is always prohibited (closes G7).

- **Schema 2 — `client_view`** (`event_type: "client_view"`, a separate append — never
  an update — referencing the server row by `attempt_uuid`; at most one per
  `attempt_uuid`, unique-indexed, later duplicates dropped; it may never arrive, and a
  missing client row means **unknown**, never recorded or reported as abandonment):
  - Required: `attempt_uuid` (reference); `recorded_at` (server UTC write time).
  - Client-sourced, nullable: `dur_ui_open_to_request_ms`, `dur_request_to_response_ms`,
    `dur_response_to_paint_ms` (monotonic duration ints, ms); `viewport_class` ∈
    `desktop` \| `tablet` \| `phone` \| `unknown`; `member_action_outcome` ∈ `applied` \|
    `discarded` \| `kept_original` \| `abandoned` \| `not_applicable` (`abandoned` only
    when the client actually sends it).
  - **Structural provenance rule:** the `client_view` schema contains no columns for
    server outcomes, provider usage, cost, guardian results, specialist, bundle ref,
    release, or operation identities — a client row is structurally unable to assert any
    server fact.

- Member attribution: none in the first slices (D10 governs any future identifier).
- **"Append-only" defined:** the application writer's database permission is INSERT-only
  on the telemetry table; the scheduled purge identity holds the only DELETE path.

- **Sink and enforcement, named:** telemetry rows go to a dedicated append-only table in
  the existing Azure SQL database, written through a stored procedure that accepts only
  the allowlisted columns (the same `usp_*`/allowlist idiom the rest of the platform
  uses). Access is enforced by the existing owner-only authorization path — no
  member-facing endpoint reads it. Retention is enforced by a scheduled purge job
  deleting rows older than 90 days, and **the telemetry slice does not ship until the
  table, procedure, access rule, and purge job all exist** — the field allowlist alone
  establishes content-freedom, not retention or deletion. If D10 ever adds a keyed member
  identifier, deletion propagation to this table becomes part of that decision.

- **Scope of this contract, honestly:** §7 binds the structural field allowlist, the stated types,
  the prohibitions, the timing chain, the sink kind, the access rule, and the retention
  duration. The telemetry slice must supply the deferred remainder named in the boundary
  above — per-call-kind failure-reason enum values, exception class/attribute
  allowlists, the *remaining* exact numeric
  bounds, table DDL, procedure signature, purge job — **before implementation**; an implementer cannot build
  telemetry from this document alone, and this document does not claim otherwise.

---

# 8. Guardians

**`guardian-registry@2`** — the closed, versioned registry of fourteen named guardians:
identity, authorization, source-allowlist, injection-separation, evidence-entitlement,
support-linkage, content-bounds, rate-limit, timeout, idempotency, malformed-output,
prohibited-action, **subpart-substring** (the Diagnostician cannot invent subparts —
each must be a verbatim substring of the question), and **compare-isolation** (the
generic branch of a compare never receives grounded content). Telemetry's
`guardian_rejections[]` enum is exactly this registry's names at this version. **Thirteen
are fully deterministic; support-linkage is deterministic linkage whose semantic half
stays evaluation-gated (§5.5)** — the set is never described as "fourteen deterministic
guardians". Existing validators (`app.py:3402-3720`) are extended,
never replaced — the evidence-entitlement id check and the strict output validation are
already genuine controls. Their mechanisms are **source-confirmed**; the bounded live
test observed only the safe outcomes and marker behaviour they produce, not the
validators executing.

Corrections binding on the guardian set:

- **Injection-separation is PARTIAL** and says so: the base64 envelope reduces delimiter
  spoofing only. Deterministic backing = structural placement, context minimization,
  claim-granular output validation (§5.5), and a zero-side-effect surface. The envelope
  applies to **all** `external_untrusted` content, owned by the guardian set.
- **Content-bounds reject; they never silently slice.** Overlong model output is
  `invalid_output`. A truncated confirmation marker is a validation failure, not a
  degraded success.
- **Support-linkage** (renamed from claim-support — the deterministic check links claims
  to sources; it does not prove semantic support, which stays evaluation-gated) is the
  §5.5 segment validation for grounded output; for coach/revision prose it is the marker
  contract plus evaluation, labelled residual.
- **Timeout** per the §3 budgets via the `with_options` bounded-client precedent
  (`services/ask_pete/provider.py:174`), replacing inherited SDK defaults with deliberate
  policy. The module client is shared with the homepage chat route, so bounding is
  per-call, never a mutation of the shared client.
- **Idempotency** per the §3 spend rule.
- The `planning_hints` no-History property is **structural** — its builder has no History
  parameter, asserted by test — not a prompt instruction.

Words like "proven", "guaranteed", and "impossible" are reserved for properties with an
existing test or schema constraint; everything else is "designed" or "required".
Provider-budget numbers are chosen engineering constants until slice-instrumented
measurement exists, and are labelled so.

---

# 9. Evaluation — no unevaluated behaviour change activates

*(Codex finding 2. Replaces ruling R8's exception.)*

The predecessor-null exception now applies **only to full behavioural parity — not prompt
text alone**: an extraction bundle qualifies only when parity tests prove, against
recorded golden transcripts, that for identical inputs the system produces identical
rendered prompts **and** identical provider settings (model, max_tokens, every request
parameter), identical request construction, identical schema, identical validator
behaviour, and identical response transformation. Only then may it activate with
`evaluation_runs: []` and `"initial_extraction": true`, because it demonstrably changes
nothing in prompts, provider requests, schemas, validation, or member-visible behaviour.
The telemetry and logging additions in the same slice **are operational behaviour
changes** — disclosed as such, outside the parity surface, and not called zero-behaviour. **Every behaviour change — adaptive length, timeout policy,
constitution wording, evidence short-circuit, member-visible copy — activates only with an
accepted evaluation run recorded against its exact bundle and candidate system digest.**
The harness
therefore precedes all behaviour changes in the slice order below.

Evaluation reuses the existing golden cases and scorecard; run records are void unless
their recorded identity recomputes; fatal-failure classes block activation regardless of
aggregate score; thresholds are Pete's (D5); the ~60–70 paid-call Wave 1 batch runs only
on Pete's explicit spend authorization (D4). **One result set never both chooses and
passes its own thresholds:** if D5 thresholds are set after seeing Wave 1, Wave 1 is
**calibration-only** and activation requires a **fresh evaluation run judged against the
locked thresholds**; the only alternative is committing thresholds before the judged
batch runs. The digit/claim screen is built first as an
offline analyzer inside the harness, promoted to runtime in the guardian slice.

---

# 10. Implementation slices

*(Restructured; Codex findings 2, 6, 10.)* Each is its own Protected/Bounded package with
rollback and test evidence; each lists its member-visible delta honestly.

| # | Slice | Delivers | Member-visible delta | Gate |
|---|---|---|---|---|
| 1 | `PS-INTERVIEW-AI-EXTRACT-001` | Byte-equivalent prompt extraction, bundle + release-set machinery, content-free **server_call-only** telemetry, log-hole fix | No member-visible delta (parity-tested); operational deltas: server telemetry emission, bounded exception logging; no response-body or client telemetry change | Predecessor-null exception, recorded |
| 2 | `PS-INTERVIEW-AI-EVAL-001` | Evaluation harness, fixtures, run records, offline analyzers | None | — |
| 3 | `PS-INTERVIEW-AI-BEHAVIOR-001` | Deliberate timeouts, evidence short-circuit (`source_not_available_for_member`, zero-spend), universal-length literal removed (interim: no stated band), corrected member copy, **attempt-id and conditional release/bundle response shapes added: attempt id always; after successful resolution, one full ref for a specialist response or parent attempt plus two keyed child refs and no parent bundle ref for Compare; unresolved `service_not_configured` returns no refs/children; client_view emission begins under the validated attempt-id contract (all additive changes deferred from slice 1, with contract tests)** | Yes — copy + failure behaviour + additive response fields, enumerated in-slice | Accepted evaluation runs |
| 4 | `PS-INTERVIEW-AI-GUARDIAN-001` | The `guardian-registry@2` set (fourteen) as tested runtime controls; analyzers promoted | Error-path behaviour | Evaluation |
| 5 | `PS-INTERVIEW-AI-ROUTER-001` | Diagnostician; bands-with-reasons; coach token wiring | Yes — disagreement/confirmation surface | Evaluation + **ChatGPT visual direction, Pete-accepted (D12)** |
| 6 | `PS-INTERVIEW-AI-COACH-REVISION-001` | Coach v3, Revision v2, the §4 tier-governed proposal lifecycle (ephemeral by default; durable only by disclosed opt-in or explicit member action), §4 state model, proposal preview/apply/discard/restore | Yes | Evaluation + **visual gate (D12)** |
| 7 | `PS-INTERVIEW-AI-HISTORY-001` | Account-backed store + revocable projections; opt-in previewed migration | Yes — History experience | Migration gate + **visual gate (D12)** |
| 8 | `PS-INTERVIEW-AI-NUDGE-001` | Two-step History Nudge (§6) | Yes — nudge/selection surface | Evaluation + interlock tests + **visual gate (D12)** |
| 9 | `PS-INTERVIEW-AI-GROUNDED-001` | Claim-granular Grounded Example | Yes — evidence selection, insufficiency, refusal, and recovery experience | **Member-evidence contract existing (D1) + its own accepted evaluation runs + visual gate (D12)** |
| 10 | `PS-INTERVIEW-AI-COMPARE-001` | Compare preserved as the §5.6 composition (parent + two children, partial-failure preservation, half-retry) | Yes | **D3 accepted + its own evaluation runs + visual gate (D12)** |

**Smallest safe first slice: slice 1** — no member-visible behaviour change (the
telemetry and logging additions are operational changes, disclosed as such), behaviour
moved to slice 3, single-revert rollback. Dependencies are strictly ordered;
nothing needs a later slice.

Out of scope, unchanged: Opportunity Slate AI, Ask Pete, Workshop AI, Community, Profile,
Journal, O*NET, open-web retrieval, Azure AI Search, the Role-Context question generator,
retiring the public Interview route, the homepage `/api/chat` client, and all production
visual design (ChatGPT's lane).

---

# 11. Corrections register

Binding one-line resolutions of every remaining review finding, so nothing requires
synthesis from the drafts. Opus blocking findings 1–10: resolved by §§2–10 above
(supersedes v1's R1–R10 where Codex revised them — release identity per §2, evaluation
gate per §9, selection binding per §6; R1/R3/R5-provider-500/R6/R7-direction/R9-direction
stand).

| Finding | Binding resolution |
|---|---|
| Opus HIGH-1 | Digit/claim screen validates only against selected-evidence anchors (§5.5); question/role text never substantiate. |
| HIGH-2 | Routerless degraded mode is deterministic fallback, labelled, never refusal (§5.2). |
| HIGH-3 | `listening_criteria[]` is owned by the Diagnostician schema in `contracts_version` (§5.1). |
| HIGH-4 | The four computed states in §3 are canonical; all restatements void. |
| HIGH-5 | Every slice enumerates its member-visible delta (§10); "zero surface" is claimed only where parity-tested. |
| HIGH-6 | `confirmed_context` cap: 1,200 chars, one place (§5.4). |
| HIGH-7 | `planning_hints` no-History is structural + tested (§8). |
| HIGH-8 | "Proven/guaranteed/impossible" reserved for tested/constrained properties (§8). |
| HIGH-9 | Budgets are chosen constants, labelled, pending measurement (§8). |
| MED-1 | Pete accepted D3 on 2026-08-16: retain `compare` as the isolated later composition in §5.6 and slice 10. |
| MED-2 | No live contract field dropped without explicit deprecation (§5.2). |
| MED-3 | Untested behaviour relabelled UNSETTLED. |
| MED-4 | One failure registry (§3); everything else cites it. |
| MED-5 | The gate makes activation conditional on recorded accepted runs; no broader determinism claimed (§9). |
| MED-6 | Session-free: no Session entity (§4); browser session fields are local grouping, renamed on import; authorization state renamed `current_practice_authorized` (§3). |
| MED-7 | A save refusal snapshots-and-holds; it never discards member text (§4). |
| MED-8 | The untrusted envelope covers all `external_untrusted` content, owned by the guardian set (§8). |
| LOW-1 | Cross-specialist interface changes live in `contracts_version`; none is unilateral (§2). |
| LOW-2 | Superseded — this document is the reconciliation. |
| LOW-3 | `provider_failure` stays 500 (§3). |
| LOW-4 | Resolved by the four-state computed taxonomy (§3). |
| Codex 1–10 | Dispositions and locations in `21_CODEX_RECONCILIATION.md`. |

---

# 12. Owner decision register

**Thirteen identifiers; eight remain open or staged.** D2 and D6 were already settled.
On 2026-08-16 Pete accepted the architecture and resolved **D3, D8, and D9** exactly as
recommended. The remaining items gate only their named future evaluation, visual,
implementation, or control steps; they do not reopen this architecture acceptance.

**Settled quality rule — already accepted product direction, not a new choice:**

- **D2 (settled).** Every behaviour-affecting prompt, model, or guardian change requires
  an accepted evaluation run before activation; only full-behavioural-parity extraction is
  exempt (§9). Preserved as a closed rule. **The open operational piece carries a
  recommendation, not a question:** each future Protected implementation slice
  establishes a **capped evaluation budget** in its activation record; the manager may
  execute and report evaluation batches within that cap without per-batch approval. Pete
  is returned to only to exceed the cap, change provider/data/scope, or authorize the
  separate Wave 1 batch (D4).

**Accepted architecture choices (2026-08-16):**
- **D3 (accepted).** Retain `compare` as a **later
  composition** of specialists 5+6 with the isolation guardian. Disclosed costs, plainly:
  it can require two generations per request (latency and spend); its grounded half
  inherits the D1 member-evidence prerequisite; and its surface needs future
  ChatGPT-created, Pete-accepted visual direction. No usage evidence exists either way
  — the recommendation rests on it being already-built behaviour with a working
  isolation control, not on demand data.
- **D8 (accepted).** Configuration override plus App Service restart is permitted only
  for **selecting a prior mechanically compatible release set** (§2), never for mixing
  bundles and never as a substitute for code or deployment rollback. **No downtime-duration
  promise is made.** A future Protected slice supplies the operator authority, audit
  evidence, post-rollback verification, and recovery instructions before this mechanism
  is ever used.
- **D9 (accepted).** The member's explicit action selects the member-facing specialist,
  always. The Diagnostician may **advise** (shape dimensions, band, posture) and may run
  as a **prerequisite stage** of the chosen action — it can never substitute a
  different action for the one the member chose.

**Needed before the evaluation batch runs (1):**

- **D4** Authorize the ~60–70-call Wave 1 evaluation batch when wanted.
  **Recommendation:** authorize when the harness slice lands; the batch is small and
  runs once.

**Needed after Wave 1 results, before the first behaviour activation (1):**

- **D5** Evaluation launch thresholds — deliberately not invented by anyone.
  **Recommendation:** set them after reviewing Wave 1 with Codex — which makes Wave 1
  calibration-only, so activation then requires a fresh run judged against the locked
  thresholds (§9); hold the scorecard's fatal classes as non-negotiable regardless of
  aggregates. (The alternative — committing thresholds before the batch — avoids the
  second run but judges blind.)

**Needed before later implementation slices (4):**

- **D1** Grounded Example stays gated until an authorized member-evidence contract exists
  (Profile work, other package). (Gates slice 9 only.) **Recommendation:** confirm the
  gate; there is nothing to enable it on.
- **D7** Provider/model selection after the evidence-based bake-off. (Follows the
  evaluation results; gates nothing before then.) **Recommendation:** decide from the
  blind bake-off table only; no selection by brand.
- **D10** Is longitudinal per-member telemetry needed at all? If yes: purpose, retention,
  access, deletion, and the keyed-HMAC design first. (Recommendation: no, until a concrete
  need is shown; random per-request UUIDs only. Gates only a telemetry extension.)
- **D11** Account History retention: keep indefinitely until the member deletes/archives
  (recommended — it is their work), or set an expiry policy. (Gates the History slice.)

**Standing workflow and administrative items — not product choices to make now (2):**

- **D12** *Already-assigned future workflow:* visual briefs for every material
  member-facing surface this architecture introduces — the Router-disagreement/confirmation
  surface, the Coach v3 and Revision/proposal experience (apply, discard, restore), the
  History search/import/archive/delete experience, the History Nudge selection flow,
  the **Grounded Example** evidence-selection/insufficiency/refusal/recovery experience,
  and the **Compare** composition surface — go to Original ChatGPT for creation and to
  you for acceptance **before** slices 5–10 implement them. Claude or Codex may
  architect, review, or implement only when named for that later slice; neither sets final
  visual direction. Nothing to decide today.
- **D13** *Pre-merge control-plane sequence — admission and relocation completed; exact-
  SHA acceptance, attestation, grant, merge, and close remain.* The generic grant path
  could not do what D13 needed: it
  cannot add or change this package's owner decisions; the package lacks the required
  code-controlled review attestation; merge authority is absent; current validation
  permits only the defined main-side commit sequence; and a formal close cannot precede
  the merge. **The permanent location is chosen now, before any SHA is granted, because
  relocation changes the candidate:** `docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/`
  (consistent with this package's README). **The executable control repair:** the
  separately authorized, package-specific `PS-DELIVERY-CONTROL-001` admission merged
  through PR 506 as `b4d79b217b1b8b68128a5271031390bb2be521b6`. It (a) records the earlier
  five-request and Gate B authorizations, (b) establishes the lawful owner-decision
  recording and code-controlled review-attestation path, with its permitted commits and
  paths, and (c) permits exactly one candidate tree to move this directory to the chosen
  `docs/initiatives/` home and **add `PS-INTERVIEW-AI-ARCHITECTURE-001` exactly once to
  `PACKAGE_REGISTRY.json` category `future_finish`, incrementing that category count and
  the total count in the same tree**. This is the selected mechanism; the registry test
  is not weakened and no
  general lane-class exception is introduced. **The ordered sequence:**
  1. **Completed in this candidate:** use that admission to relocate the package,
     normalize its links, and register it in the same tree.
  2. A fresh author sweep, internal review, and Codex review of the relocated candidate.
  3. Pete's acceptance recorded against the exact resulting source SHA.
  4. The lawful merge grant issued for that SHA.
  5. PR 502 receives a fresh merge preview and policy build against the changed target.
  6. PR 502 merges only after those policies pass.
  7. A separate post-merge transition records the close and next state.
  Each policy build approves only its exact source/target merge preview and is never
  the final pre-merge build once the target moves.

# 13. Authority, evidence classes, and limits

**Authority state, plainly:** control PR 506 reconciled the lane's stale Gate-A stop and
zero-provider-request language with Pete's separately granted bounded five-application-
request evidence authorization and Gate B continuation. It also records Pete's D3/D8/D9
acceptance and D13 authority. No further provider request, evaluation execution, merge,
release, deployment, enablement, or live authority was granted. PR 502 remains withheld
until Pete approves the exact relocated SHA after fresh review.

**Evidence classes, corrected per Codex (f):** deployment anchoring is sound (run 1096 →
`f42e5399`; live release matched `/healthz`; source blobs byte-identical). Five
application AI requests are proven; provider transport/billing counts are inferred. The
111-word count is observed; no duration was measured and none is stated anywhere in this
package. The
never-invent observation is one bounded case plus source-confirmed mechanism. The
universal empty-evidence claim is source-confirmed; live-observed for one synthetic
account.

**Limits:** specialist 5 is designed against a contract that cannot yet be exercised; no
paid evaluation has run, so no quality claim is measured; real-device behaviour is
unverified (viewport emulation, no screenshots — the pane was not compositing); cost and
latency figures do not exist until slice 1 instruments them.

**Acceptance:** Pete accepted this architecture for implementation planning on
2026-08-16 and accepted D3, D8, and D9 as recommended. Everything else is staged per
§12 and gates only its named later work.
Within D13, pre-merge steps 1–5 complete before PR 502 may merge; step 6 is that merge and
step 7 is its separate post-merge close. No implementation slice activates until the
full D13 sequence has completed.
