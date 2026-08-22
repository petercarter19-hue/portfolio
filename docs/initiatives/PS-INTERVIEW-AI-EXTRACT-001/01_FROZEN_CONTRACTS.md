# PS-INTERVIEW-AI-EXTRACT-001 — frozen slice contracts

Frozen before implementation, as architecture §7 requires. These complete
`telemetry-contract@1` and pin every deferred slice-1 decision. A change to
anything in this file after the candidate freeze is a new contracts version,
never an edit.

## 1. Bundle catalog and instruction segment format (`instruction-format@1`)

Each bundle directory `prompts/interview/bundles/<specialist>/<semver>+<sha8>/`
contains exactly five files. Four are the §2 identity files, hashed in this
fixed order with domain `peerslate.interview.bundle.v1\0` and 8-byte
big-endian length framing (filename length + UTF-8 filename + content length
+ exact file bytes): `constitution.md`, `instruction.md`, `schema.json`,
`provider.json`. The fifth, `manifest.json`, records the full
`{ specialist, semver, bundle_label, bundle_content_sha256, files }`
reference and is outside the identity.

- Every initial `constitution.md` is a **zero-byte** UTF-8 file. A zero-byte
  constitution renders only the current instruction — no separator, newline,
  or whitespace is added.
- `instruction.md` holds named segments. A segment's content is the exact
  bytes between the line `<<<SEGMENT name>>>` (content starts at the byte
  after that line's `\n`) and the byte immediately before the `\n` that
  precedes its `<<<END name>>>` line. No normalization of any kind occurs.
  Templates render with Python `%`-formatting against the exact legacy
  argument tuples.
- Segment inventory (all segments are required; extra segments are invalid):
  - `coach`: `system_template` (5 placeholders: level, family, competency,
    grounding, allowed_dimension_keys), `user_template` (3: question,
    opportunity_block, answer).
  - `revision`: `system_template` (1: evidence_lines), `user_template`
    (6: question, family, opportunity_block, answer, confirmed_context,
    improvement_notes).
  - `planning_hints`: `system_template` (0), `user_template` (6: question,
    level, family, competency, practice_mode, opportunity_block).
  - `grounded_example`: `system_template` (3: level, family,
    evidence_lines), `user_template` (2: question, opportunity_block),
    `followup_suffix_template` (2: prior_answer, follow_up).
  - `generic_example`: `system_template` (2: level, family),
    `user_template` (2: question, opportunity_block),
    `followup_suffix_template` (1: follow_up),
    `followup_prior_best_practice_template` (1: prior_answer),
    `followup_prior_compare_template` (1: prior_illustrative_answer).
- `provider.json` (inside identity):
  `{ "provider": "anthropic-messages", "model": "claude-haiku-4-5-20251001",
  "max_tokens": <int>, "explicit_parameters":
  ["model", "max_tokens", "system", "messages"], "message_shape":
  "single_user_message" }`. `max_tokens`: coach 2400, revision 1300,
  planning_hints 500, grounded_example 1300, generic_example 1300. No other
  provider parameter is ever passed; every omitted optional parameter
  inherits the SDK default exactly as the legacy code does.
- The untrusted-opportunity envelope, evidence-line formatting, and grounding
  header remain guardian/runtime code (architecture §8 owns the envelope),
  inside the guarded dependency manifest — not bundle content.
- Bundle slot order everywhere (candidate digest, registry `bundle_refs`,
  catalog listings): `coach`, `revision`, `grounded_example`,
  `generic_example`, `planning_hints` (§3 specialist-enum order restricted
  to the five present specialists, interim `planning_hints` last).

## 2. Identity computation (`identity-framing@1`)

- Canonical JSON: UTF-8, object keys sorted lexicographically, no
  insignificant whitespace, arrays in stated order, strings NFC-untouched
  (no normalization), integers only (no floats anywhere in identity
  payloads). This is the RFC 8785 subset sufficient for these payloads; the
  implementation rejects floats rather than canonicalizing them.
- `runtime_core_digest`: SHA-256 over the canonical JSON of
  `{ "digest_domain": "peerslate.interview.runtime-core.v1", "entries":
  [{ "path", "sha256" } ... ], "external_artifacts": [...] }` with entries
  sorted by path. The guarded dependency manifest is
  `prompts/interview/contracts/guarded-paths.json`; each entry's `sha256`
  is over the exact committed file bytes. The guarded scope is the FULL
  behaviour-affecting closure (correction C1): every
  `services/interview_ai/*.py` file — which, after the C1 extraction,
  contains the Interview request parsing, refusal copy, validators, signed
  follow-up-context behaviour, rendering, release resolution, telemetry
  and pricing builders, and provider dispatch for all five jobs — every
  `prompts/interview/contracts/*.json` file except `guarded-paths.json`
  itself (a manifest cannot contain its own hash; its integrity is exactly
  what `runtime_core_digest` recomputation proves) and
  `version-anchors.json` (the immutable anchor cannot live inside the
  identity it pins), the database adapter path the telemetry append
  executes through (`services/database_service.py`, `db.py`), the
  dependency-lock artifact (`requirements.txt`), **the manifest builder
  itself** (`scripts/interview_ai/build_release_identity.py`), and —
  correction B2 — the exact Interview-affecting boundary inside `app.py`,
  bound as named source fragments (`app.py#fragment=…` entries over exact
  executed bytes, never line numbers): the signing serializer with its key
  derivation and salt, the effective provider client construction, and the
  complete route boundary (decorators and rate limits, refusal
  ordering/status/copy, request JSON handoff and response serialization,
  the signed-context wrappers, and the `JobDeps` assembly including its
  callback bindings and the app-supplied default public-profile slug; the
  clock/UUID sources live in guarded `telemetry.py` directly). The
  fragment extractor rejects missing, unknown, duplicated, nested,
  unterminated, or expected-symbol-stripped fragments, in the builder AND
  in runtime release resolution (a deployed app.py that fails fragment
  extraction fails closed), and liveness tests bind the executed route
  view-functions and wrappers to the fragment region so behaviour cannot
  leave a dead guarded copy behind.

  **External runtime identity (correction B3), complete and enforced:**
  the external-runtime manifest
  (`prompts/interview/contracts/external-runtime-1.json`) records the
  COMPLETE executable dependency closure reachable from the Interview
  runtime — 30 distributions across the provider, HTTP, validation,
  signing, environment/configuration, and SQL telemetry stacks — each
  with its exact version, dependency edges, production ABI/platform
  (cp314, linux-x86_64, App Service `PYTHON|3.14`), permitted artifact
  filename, full artifact SHA-256, and the installed-file projection
  (sorted normalized paths + raw-file SHA-256 over executable Python,
  native-library, and stable metadata bytes; only install-time
  bookkeeping and bytecode caches are excluded). `external_artifacts` in
  the identity derives from this manifest, never a hand-kept subset.
  Enforcement is the Interview-specific hash-locked production lock
  (`prompts/interview/control/interview-runtime-lock.txt`, every line
  `--hash` pinned) vendored by the deployment pipeline into the artifact
  at `.python_packages/lib/site-packages` with
  `pip install --require-hashes --no-deps --only-binary=:all:` and the
  recorded cross-target flags, then verified byte-for-byte against the
  staged artifact before archiving; at application boot, release
  resolution recomputes the installed projections from the distributions
  the interpreter actually resolves and fails Interview closed
  (`service_not_configured`) on any missing, duplicated/shadowed,
  substituted, wrong-version, or byte-different reachable distribution —
  platform-aware (full byte enforcement on the locked production
  platform and for every platform-independent artifact everywhere; exact
  version + presence for Linux-native artifacts on non-production
  platforms). The Build-stage test install is version-aligned through
  the constraints mirror
  (`interview-runtime-constraints.txt`) so the boot check is meaningful
  in CI; the root `pip install -r requirements.txt` enforces nothing and
  is documented as such. The lock, vendor flags, constraints, generator
  (`scripts/interview_ai/build_runtime_lock.py`), and verifier
  (`services/interview_ai/runtime_lock.py`) are all guarded and
  anchored; executable evidence lives in `08_RUNTIME_LOCK_PROOF.json`
  (real pip: hash-verified wheelhouse, vendored install, staged
  verification, and the wrong-hash / missing-transitive / substituted /
  modified-byte / wrong-version / outside-closure failure modes) and in
  the mutation matrix's B3 cases (lock/manifest/verifier edits trip B1).

  **The version tripwire (correction B1)** compares the working tree
  against an immutable prior anchor —
  `prompts/interview/contracts/version-anchors.json`, append-only,
  hash-chained, written only by the deliberate `--write-anchor` command
  (never by the ordinary build), excluded from the identity it pins, and
  required to exist by candidate verification (deleting it is a
  verification failure, so the bootstrap cannot be reopened). The
  PRODUCTION verification flow itself (`build_release_identity.py
  --verify`) evaluates the tripwire; re-anchoring refuses guarded drift
  under unchanged responsible versions. This round's own boundary change
  was made under that discipline: `contracts_version` was bumped
  `interview-contracts@1 → interview-contracts@2` and the second anchor
  chained onto the first. The executed 24-case mutation matrix (guarded
  code, contracts, adapter, builder, external digest, every B2 boundary
  element, the regenerate-everything defeat sequence, version-bumped and
  unrelated-change controls, and the anchor-discipline proofs) is
  recorded in `07_TRIPWIRE_MUTATION_MATRIX.json`.
- `candidate_system_digest`: SHA-256 over canonical JSON
  `{ "digest_domain": "peerslate.interview.candidate.v1",
  "runtime_core_digest", "bundles": [{ "specialist",
  "bundle_content_sha256" } ...in slot order], "guardian_set_version",
  "contracts_version", "evaluation_set_hash" }`.
- `guardian_set_version`: `"guardian-runtime-legacy@1"` — the existing
  validators and refusal gates, unmodified, without claiming the
  fourteen-guardian runtime exists. `guardian_rejections` is always `[]` in
  slice 1.
- `contracts_version`: `"interview-contracts@1"` — covers this document's
  frozen contracts, `instruction-format@1`, `marker-contract/1` (the live
  `_IMPROVEMENT_MARKER_PATTERN` and revision gate, unchanged), the v1
  dimension registry (`INTERVIEW_FAMILY_DIMENSIONS`, carried unchanged),
  `telemetry-contract@1`, and `guarded-paths.json`.
- `evaluation_set_hash` (correction B5 — `peerslate.interview.evalset.v2`):
  SHA-256 over the canonical JSON of the guarded, DEPLOYABLE evaluation-set
  manifest (`prompts/interview/contracts/evaluation-set-1.json` — the two
  accepted golden files plus every parity fixture, each as
  `{ "path", "sha256" }` over exact file bytes). Release resolution ALWAYS
  recomputes this identity from the manifest — the manifest ships with the
  application (prompts/** deploys; tests/** does not and need not exist at
  production runtime), its bytes are a runtime-core guarded entry under the
  B1 anchor, any evaluation file that IS present must match its recorded
  digest byte-for-byte, and a missing or malformed manifest, a
  manifest/record hash mismatch, or a present-but-different file all fail
  Interview closed. The former fail-open branch (trusting the recorded
  hash when source files were absent) is removed and its defect shape is
  pinned by an adversarial test
  (`test_b5_the_fail_open_defect_is_dead`).
- `interview_release_set_id`: SHA-256 over canonical JSON
  `{ "digest_domain": "peerslate.interview.release.v1",
  "candidate_system_digest", "accepted_run_digests": [],
  "threshold_set_id": "initial-extraction-parity",
  "threshold_set_version": "1" }`. The sentinel
  `initial-extraction-parity@1` is reserved for this initial extraction and
  is invalid for later behaviour-changing releases.
- All identities are stored and compared as full 64-hex SHA-256 values;
  `+<sha8>` and any short prefix are display labels only.

## 3. Active-release resolution (`release-resolution@1`)

- Configuration key: `PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET` (environment,
  surfaced through `app.config` like the existing Interview flags).
- Resolution runs once per process (cached), triggered lazily by the first
  Interview AI request, **after** every existing pre-provider refusal for
  that request. It succeeds only when ALL of the following hold
  (correction C2 — an internally consistent record is not enough; the
  record must be COMPATIBLE with the running system):
  - the configured value is 64 lowercase hex;
  - `prompts/interview/control/registry.json` parses and satisfies the §3
    v1 schema, and the configured id equals the recorded
    `interview_release_set_id` of the active entry or a prior entry;
  - the record's `guardian_set_version` and `contracts_version` equal the
    running system's exact current values, and the guarded manifest
    carries the same `contracts_version`;
  - the sentinel is valid for the record's shape: an
    `initial_extraction: true` record carries exactly the
    `initial-extraction-parity@1` sentinel and zero accepted runs; any
    other record may never reuse that sentinel and must reference at
    least one accepted judged run by full digest;
  - the recorded `bundle_refs` are in exact slot order with complete
    full-hash identities, and every bundle's content hash recomputes from
    the committed catalog bytes;
  - every guarded manifest blob recomputes, the external-artifact records
    are complete full hashes, and `runtime_core_digest`,
    `candidate_system_digest`, and `interview_release_set_id` all
    recompute exactly;
  - D8 configuration-only rollback compatibility follows by construction:
    because every resolvable record must match the current runtime core,
    guardian version, and contracts version, an incompatible prior entry
    is unreachable (adversarially tested).
- Any other state is **unresolved**: the four Interview AI endpoints answer
  HTTP 503 with body `{"error": "Interview AI is not configured right now.
  Retrying will not help until service configuration is restored."}` and
  zero provider dispatch. One `server_call` row is written with
  `outcome: "failed"`, `failure_state: "service_not_configured"`,
  `failure_reason: "active_release_unresolved"`, null release/bundle refs.
  The rest of PeerSlate is unaffected. This state is reachable only where
  release configuration governance exists; it is the fail-closed posture of
  the release machinery, not a change to any currently reachable behaviour.
- Recording the initial release set in `registry.json` is part of this
  slice. **Activating** it (setting the configuration and restarting) is a
  separately authorized release operation that this slice never performs;
  the recorded entry carries `activated_at: null` until that operation.

## 4. `server_call` telemetry — deferred items, now frozen (`telemetry-contract@1`)

Everything §7 states normatively (field allowlist, types, null conditions,
cardinality, prohibitions, sink, access rule, 90-day retention) is binding
verbatim. The items §7 defers to this slice are frozen as follows.

### 4.1 Emission points and slice-1 value ranges

- A row is assembled only for a request that has passed every legacy
  pre-provider refusal; pre-provider HTTP refusals stay outside slice-1
  telemetry, so `outcome: "refused"` does not occur in slice 1.
- `event_kind: "specialist_call"` rows: one per specialist attempt
  (review → `coach`, improve → `revision`, nudge → `planning_hints`,
  model-answer member_history → `grounded_example`, best_practice →
  `generic_example`). A Compare request writes one
  `composition_parent` row (`composition: "compare"`) plus one child row per
  specialist **actually attempted** (grounded always; generic only after
  grounded succeeded), children carrying `parent_attempt_uuid`.
- `outcome`: HTTP 200 with a validated `insufficient` grounded status →
  `"computed_outcome"`; any other 200 → `"success"`; 502/500/503 →
  `"failed"`.
- `failure_state` mapping: validation rejection (502) → `invalid_output`;
  Anthropic SDK exception (500) → `provider_failure`; any other unexpected
  exception (500) → `internal_error`; unresolved release (503) →
  `service_not_configured`.
- `retry_ordinal` is always 0 (no retry machinery exists in slice 1).
- `http_status` on every row (parent and children) is the final HTTP status
  of the member response.
- `validation_result`: `passed` when a validator accepted model output
  (including the `insufficient` computed outcome), `rejected` when
  extraction/validation raised, `not_applicable` when no model output was
  validated (provider exception, unresolved release, and every
  `composition_parent` row).
- Timing: `dur_receive_ms` is 0 in slice 1 (request parsing precedes the
  telemetry boundary and is not measured); `dur_retrieval_ms` measures the
  existing evidence/profile context load; `dur_manifest_ms` the bundle
  prompt render; `dur_provider_ms` the provider call; `dur_validate_ms`
  extraction+validation; `dur_respond_ms` response assembly.
  `dur_total_server_ms` **is at least each recorded stage duration**
  (correction B4 — sum equality is NOT required); every duration is
  bounded 0–86,400,000 ms. Phases that did not run record 0. All are
  monotonic-clock integer milliseconds. Further B4 bounds, enforced
  identically in Python and SQL: `http_status` 100–599; `retry_ordinal`
  0–15 (slice 1 emits 0); source counts 0–32; provider tokens
  0–2,147,483,647; `reply_chars` 0–100,000; exception `status_code`
  100–599; `cost_microusd` 0–(2^63−1).
- `source_class_counts` (complete six-key map, ints 0–32, clamped at 32):
  count of items of each §3 source class included in the provider request
  for this row. Frozen per specialist: `question` 1; `answer` 1 for coach
  and revision else 0; `role_context` 1 iff non-empty opportunity context;
  `member_evidence` = number of evidence lines in the prompt (coach: full
  approved list; revision: selected evidence; grounded_example: full
  approved list; else 0); `confirmed_context` 1 iff revision
  additional_context non-empty; `history_selection` always 0.
  **Follow-up correction (C5):** a public follow-up request really sends
  two questions (the original and the interviewer follow-up) and one prior
  server-validated answer, so a grounded_example or generic_example
  follow-up row records `question: 2` and `answer: 1`; it is not History
  and `history_selection` stays 0. The bundles' concrete input manifests
  describe the same reality (`answer` with `server_derived` provenance on
  those two specialists).
  `composition_parent` rows carry all zeros (the parent makes no provider
  request).

### 4.2 Failure-reason enum (per call kind)

`failure_reason` (non-null iff `outcome = "failed"`) is one closed enum
shared by the five specialists and `composition_parent` (a parent's reason
mirrors the failing child's reason):

- Validation reasons — exactly the legacy low-cardinality labels, carried
  forward: `no_json_object`, `not_an_object`, `wrong_field_type`,
  `empty_required_field`, `incomplete_dimensions`,
  `invalid_dimension_shape`, `invalid_dimension_status`,
  `duplicate_dimensions`, `numeric_universal_field`,
  `numeric_dimension_score`, `invalid_review_shape`,
  `duplicate_review_list_item`, `invalid_evidence_suggestion_shape`,
  `duplicate_evidence_suggestions`, `duplicate_json_field`,
  `opportunity_context_too_long`, `unauthorized_evidence`,
  `no_evidence_reference`, `duplicate_evidence`, `invalid_status`,
  `unparseable_json`, `unexpected_shape`, `unclassified`.
- Provider execution reasons — the canonical §3 taxonomy, exactly
  (correction C6): `transport` (connection-level failure), `timeout`,
  `rejected` (any provider status response), and `abandoned` (reserved for
  the §3 orphan reaper; no slice-1 runtime emission path exists and a
  repository test proves it). SDK-shaped values such as
  `provider_rate_limited` are prohibited in `failure_reason` and the
  proposed DDL's CHECK constraint enforces the restriction whenever
  `failure_state = 'provider_failure'`. The granular normalized SDK
  mapping survives only in the separate closed exception-class field
  (§4.3).
- Server reasons: `unexpected_server_fault` (generic execution fault),
  `active_release_unresolved` (the fixed cross-call pre-resolution value).

### 4.3 Exception class/attribute allowlists (correction B4)

`exception { class, attrs }` is non-null iff a caught execution exception
produced `outcome: "failed"`. A stringified exception is prohibited
everywhere — telemetry and logs alike — and raw SDK/Python class names,
messages, tracebacks, URLs, bodies, headers, provider ids, member text,
and model output are never persisted.

- The persisted `class` enum is closed to exactly nine values:
  `validation_json_decode`, `validation_value`, `validation_key`,
  `validation_type` (mapped from the pinned validator exception types);
  `provider_timeout`, `provider_transport`, `provider_rejected` (mapped
  from the pinned `anthropic==0.112.0` hierarchy: `APITimeoutError` →
  timeout, other `APIConnectionError` → transport, every
  `APIStatusError` → rejected); `provider_response_shape` (a malformed
  provider response envelope — IndexError/AttributeError while reading
  it); and `runtime_unexpected` (everything else). Bounded logs may
  additionally say `database_error` for the database adapter's own
  failure class; no row path emits it.
- Per-class attribute rules, enforced identically in Python and SQL:
  the four validation classes may carry only `provider_stop_reason`
  (∈ `end_turn`, `max_tokens`, `stop_sequence`, `tool_use`,
  `pause_turn`, `refusal`, `unknown`) and `reply_chars` (integer
  0–100,000); `provider_rejected` may carry only `status_code` (integer
  100–599); every other class requires an EMPTY attribute map. Duplicate
  keys, unknown keys, wrong-class attributes, wrong types, and
  out-of-range values are rejected on both sides.
- Canonical identities: every non-null SHA field (release-set,
  bundle-content, pricing-schedule) must be exactly 64 LOWERCASE
  hexadecimal characters; SQL rejects uppercase, non-hex, short, and
  long values case-sensitively (procedure parameters are wider than the
  columns so overlong values reach the check instead of being silently
  truncated into validity).
- Parent/child relations are enforced transactionally in the append
  procedure with locks, beyond the self-referencing foreign key: a
  Compare child must reference an existing `composition_parent` row with
  `composition = compare` and the same release identity (a standalone
  row, another child, a missing row, or a mismatched release never
  satisfies it, race included); a parent carries no parent, bundle,
  tokens, cost, pricing, exception, or nonzero source counts; a resolved
  specialist row carries release AND bundle identity; the pre-resolution
  `service_not_configured` row carries neither; duplicate `attempt_uuid`
  appends are concurrency-safe silent no-ops that never mutate the first
  stored row even when the duplicate carries a different payload.
- The executable evidence is the named hostile matrix: `py_case_1..17`
  in `tests/interview_ai/test_telemetry_contract.py` and
  `sql_case_1..17` (plus the preserved permission/retention/rollback
  battery, 67 checks total) in `05_SQL_DISPOSABLE_PROOF.json`, run on
  the disposable database `ps-interview-extract-gate-b4-20260821`
  (created for the proof, deleted after it, fresh gate digest recorded
  in the migration registry).

### 4.4 Pricing (`interview-ai-pricing@1`)

- The immutable pricing table is
  `prompts/interview/contracts/interview-ai-pricing-1.json`. Its identity,
  `pricing_schedule_id`, is the SHA-256 of that file's exact committed
  bytes.
- One entry: `claude-haiku-4-5-20251001`, integer micro-USD per token:
  `input_microusd_per_token: 1`, `output_microusd_per_token: 5` (derived
  exactly from the provider's published $1.00 / $5.00 per million tokens;
  the same rates apply on Microsoft Foundry billing, recorded 2026-08-20).
- `cost_microusd = input_tokens * 1 + output_tokens * 5`, pure integer
  arithmetic; floating point is prohibited in the pricing path.
- Priceable iff: the provider returned a usage object whose `input_tokens`
  and `output_tokens` are non-negative ints, the model is in the table, and
  no nonzero cache-token or other usage component outside plain
  input/output is present. Otherwise `cost_microusd` and
  `pricing_schedule_id` are both null (never patched later), while valid
  token counts are preserved in `provider_usage`.

### 4.5 Table DDL, procedure signatures, purge job

- Table `dbo.interview_ai_server_calls` — the dedicated append-only sink,
  full DDL in `SQL FIles/Migrations/proposed/PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql`.
  Columns are exactly the §7 schema-1 fields plus a fixed
  `event_type = 'server_call'` (CHECK-pinned; never a caller parameter),
  with `guardian_rejections` and `source_class_counts` stored as bounded
  NVARCHAR JSON documents and `exception` as `exception_class` +
  `exception_attrs`. Content-freedom is ENFORCED (correction C3): every
  enum is CHECK-constrained; `guardian_rejections` is CHECK-pinned to the
  empty list under `guardian-runtime-legacy@1` (the guardian slice alters
  that constraint); `operation_id` is CHECK-pinned NULL in slice 1; the
  Compare parent/child relation is a self-referencing foreign key
  (parents are appended first, carry no parent themselves, and carry no
  usage or cost); and the append procedure shape-closes every JSON
  document with OPENJSON — exact key sets, integer bounds 0–32 for
  counts, and the three allowlisted exception-attribute keys with their
  exact types and the closed stop-reason enum. There is no free-text
  column anywhere.
- `dbo.usp_AppendInterviewAIServerCall` — accepts only the allowlisted
  columns as named parameters, shape-closes the JSON documents before any
  insert, inserts one row, and no-ops silently on a duplicate
  `attempt_uuid` **concurrency-safely**: the racing loser's primary-key
  violation is caught and swallowed, the prior row is never modified, and
  no error surfaces. The application identity receives EXECUTE on this
  procedure only (database role `interview_telemetry_append`); it holds no
  direct table permission — proven executably in
  `05_SQL_DISPOSABLE_PROOF.json`.
- `dbo.usp_PurgeInterviewAIServerCalls(@BatchSize INT, @MaxBatches INT)` —
  deletes rows with `recorded_at` older than exactly 90 days in bounded
  batches (children before referencing parents); `@BatchSize` is bounded
  **1..5000** and `@MaxBatches` 1..1000; returns rows-deleted counts only.
  Only the separately named Interview maintenance identity (database role
  `interview_telemetry_maintenance`) receives EXECUTE on it. It shares no
  identity, enablement variable, or schedule with Community maintenance.
- Purge scheduling — IMPLEMENTED in this candidate (correction C4): a
  dedicated pipeline schedule whose display name is
  `Interview telemetry retention nightly` (cron `41 2 * * *`) and its own
  stage (`InterviewTelemetryMaintenance`), isolated from Community
  maintenance by `Build.CronSchedule.DisplayName` equality on BOTH
  schedule-gated stages (tested both directions), gated by its own
  `interviewTelemetryMaintenanceEnabled` variable (**defaults off** — it
  does not exist until an operator creates it), executing
  `scripts/interview_ai/run_interview_telemetry_purge.py` under the
  dedicated maintenance identity's
  `INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING` — a connection that is never
  the application's and never Community's — and publishing its
  content-free report artifact on every run including failures (bounded
  failure evidence). Merging this slice still enables nothing: until the
  operator creates the variable and the migration is applied, a scheduled
  run records a disabled report and exits. One lawful-surface item remains
  with the manager: the exact pipeline stage list is pinned by
  `tests/test_operational_readiness.py`, outside this lane's writable
  surfaces — the requested control-only lane expansion covers the one-line
  stage-list update, after which that suite is green and the corrected
  candidate can freeze.
- The append call is made once per assembled row, synchronously, after the
  member response is fully determined: one bounded attempt, no retry, any
  failure logged content-free and never altering the member response,
  status, or provider-call count.
- `client_view` (schema 2) ships no DDL, no endpoint, and no emission in
  slice 1; its DDL is the deferred obligation of the slice that introduces
  it.

## 5. Bounded logging correction (`interview-logging@1`)

Fully normalized (correction C7): no raw Python or SDK class name and no
raw provider stop reason ever reaches a log line.

- `log_interview_failure` drops `detail=%s` and the exception argument.
  Logged fields: label, normalized reason (§4.2 validation enum), the
  exception class **from the §4.3 closed allowlist** (plus
  `database_error`; anything unknown becomes `server_fault` — the raw
  class name never appears), the stop reason **through
  `normalize_stop_reason`** (unknown values become `unknown` — the raw
  string never appears), and the reply character count. Nothing else.
- The provider-error and generic handlers log only the label, the
  normalized exception class, and `status_code` when the class carries
  one. No `str(exception)`, no tracebacks with member/model content, no
  URLs, no request ids, no SDK message text.
- Telemetry append/assembly failures and release-resolution failures log
  one warning each with the normalized class only.
- Sentinel tests inject a unique unallowlisted Python class and a unique
  raw stop value and prove neither marker appears in captured logs.

## 6. Parity oracle rules (restating the manager's frozen instruction)

The oracle is **40 fixtures**: 32 recorded in the original round (commit
`7e3f97f7` — the first candidate's documents miscounted them as 31,
corrected per C11) plus 8 recorded post-rejection (correction C10: public
best_practice and compare follow-ups, and authenticated variants) from the
same untouched legacy checkpoint via a detached provenance worktree.
Provenance stated precisely (B6): 30 of the 32 originals are
byte-identical to oracle commit `7e3f97f7`; the two member_history
follow-up fixtures differ from that commit by exactly one recorded-request
line each — the deliberate `__STEP1_CONTEXT_TOKEN__` secret-scanner
normalization from commit `cea5ec67`, outside every parity comparison
surface — and the C10 recording run reproduced the committed (normalized)
bytes of all 32 exactly.

Fixtures are recorded from source checkpoint
`73c4e63dc74a2e67fb6bed0ed4c3d9e58e3525c5` (identical Interview bytes to the
branch base) with `client.messages.create` replaced by a deterministic
capture fake, a fixed signing key, and a fixed clock; authenticated
fixtures reproduce the identity/ownership seams with recorded synthetic
identities only. Each fixture records
provider-call count and order, the exact explicit keyword set, model and
`max_tokens`, exact UTF-8 system and user-message bytes (base64-framed),
message roles and ordering, the omitted-optional-parameter assertion, the
deterministic fake response, validator outcome, exact API body bytes, HTTP
status, relevant headers, signed-context semantics under the fixed clock,
provider-free refusal behaviour, persistence effects (none), and
grounded-before-generic Compare ordering with failure short-circuiting. No
live provider calls, no Anthropic traffic, no paid evaluation, no
production member data — synthetic and repository-fixture content only.
Candidate parity must show zero differences outside the explicitly accepted
telemetry and logging deltas.

## 7. Consolidated B1–B6 corrections (`interview-contracts@6`)

The consolidated review round amends the contracts above as follows; the
sections it supersedes are listed per item.

### 7.1 External anchor trust root and monotonic versions (B1)

The version-anchor chain is bound to an EXTERNAL trust root:
`prompts/interview/contracts/anchor-trust-root.json` pins the
manager-review record (the consolidated-review SHA
`a0402d33d066baa18e446bad2f632a48e2f84380`, whose preservation the review
itself requires), the exact anchors-file blob hash committed at that SHA,
the trusted anchor count (5), the trusted latest chain value, and a
domain-framed digest (`peerslate.interview.anchor-trust-root.v1`) of the
anchor prefix. Verification (`build_release_identity.py --verify`)
requires the current chain to EXTEND that prefix and, where git history
is available, cross-checks the pin against the blob actually committed at
the manager-named SHA. A fresh replacement chain, trailing truncation,
deletion/rebootstrap, trust-root deletion or tamper, and the coordinated
guarded-code + derived-files + anchor rewrite are all executed attacks in
`07_TRIPWIRE_MUTATION_MATRIX.json` (cases b1_8 – b1_15) and all fail.
Governed versions are PARSED (`name@N`) and enforced monotonically: no
regression or reuse along the chain, no candidate below the latest
anchor, and an appended anchor must strictly advance at least one
governed version.

### 7.2 Complete guarded application closure (B2; supersedes the §2
fragment list)

app.py now carries NINETEEN guarded fragments (the closed set in
`services/interview_ai/fragments.py`), covering the route boundary,
signing serializer, provider client and key binding, cross-site refusal,
rate-limit keying and limiter construction, entitlements, evidence and
profile-context construction, the resume fixture registry and loader,
profile projects, canonical-host gating (pattern, helpers, request gate,
platform-hostname check), the legacy path registries and redirect
target, response compression with its support constants, the
privacy/cache hook, and the app-level error contracts (404, 429, 500,
authentication-principal, identity-mapping). The guarded-file set adds
`identity.py`, `owner_authorization.py`, `static/data/resume_data.json`,
and `templates/error.html`. A mechanical transitive free-name closure
(`services/interview_ai/app_closure.py`, enforced by
`tests/interview_ai/test_guarded_app_closure.py`) proves every name each
fragment reads resolves to guarded source, a hash-locked distribution
(cross-checked against the runtime lock), an allowlisted stdlib module, a
builtin, or the single documented boundary global (`app`); the same suite
proves the LIVE registered routes, before-request gate, error handlers,
and rate-limit key function execute from guarded regions, and that every
UNGUARDED after_request hook is a byte-for-byte no-op on an Interview API
JSON response.

### 7.3 Boot-immutable release state (B3; supersedes §3 lazy resolution)

`services/interview_ai/boot.py` freezes exactly one state per process:
the guarded route-boundary fragment calls `interview_ai.boot.initialize`
at import/boot, full verification runs THERE, and the outcome (`ready`
or `service_not_configured`) is immutable for the process lifetime.
Requests read only the frozen state; post-boot configuration, registry,
bundle, guarded-file, or evaluation-manifest changes require a process
restart to take effect. The external closure now includes Flask,
Flask-Limiter, and their transitive distributions (42 total, every
artifact hash-pinned); vendored hash-locked installation and staged
installed-byte verification are unchanged.

### 7.4 Closed telemetry state matrix (B4; amends §4.1–4.3)

One state matrix (`ROW_STATE_MATRIX` in
`services/interview_ai/constants.py`) is enforced identically by
`telemetry.validate_event` and `usp_AppendInterviewAIServerCall` (named
errors 50040–50049 plus table constraints):

| outcome | failure_state | failure_reason | exception_class (specialist) | validation_result (spec / parent) | release id | usage |
|---|---|---|---|---|---|---|
| success / computed_outcome | NULL | NULL | NULL | passed / not_applicable | required | permitted (specialist) |
| failed | invalid_output | the 23 validation reasons | the 4 validation classes, attrs REQUIRE provider_stop_reason + reply_chars | rejected / not_applicable | required | permitted |
| failed | provider_failure | transport / timeout / rejected | exact pair: provider_transport / provider_timeout / provider_rejected (attrs ⊆ {status_code}) | not_applicable | required | FORBIDDEN |
| failed | internal_error | unexpected_server_fault | runtime_unexpected or provider_response_shape (attrs = {}) | not_applicable | required | permitted |
| failed | service_not_configured | active_release_unresolved | NULL | not_applicable | FORBIDDEN | FORBIDDEN |

`refused` (outcome) and `abandoned` (reason) are reserved for later
slices and rejected. Exception class and attrs are null or non-null
together; attrs must be a JSON OBJECT (never an array or scalar).
Source counts, durations, and reply_chars are never clamped or coerced:
a negative, over-limit, Boolean, float, or string value is rejected
outright on both sides. Composition parents carry `not_applicable`
validation, no exception, and all-zero counts always.

### 7.5 Strict deployable evaluation manifest (B5; supersedes the §2
`evaluation_set_hash` definition)

One shared strict parser/projector
(`services/interview_ai/evaluation_manifest.py`) serves build and
runtime. The manifest (`prompts/interview/contracts/evaluation-set-1.json`,
schema `interview-evaluation-set@2`, projection
`peerslate.interview.evalset.v3`) closes its top-level key set (schema,
responsible_version, projection_version, total_source_count,
evaluation_set_hash, files) and its entry key set (path, sha256,
category). Exactly 42 sources are required for the initial extraction —
2 `golden_document` + 40 `parity_fixture` — with unique, normalized,
repository-relative, traversal-free, ASCII, canonically sorted paths and
64-lowercase-hex digests. The aggregate hash is recomputed from the
projection and verified against BOTH the manifest field and the registry
record; any present source file is byte-verified. The check runs at
process boot and the result freezes with the boot state; a post-boot
manifest change cannot alter the running process. The 22-case hostile
matrix lives in `tests/interview_ai/test_evaluation_manifest.py`; B1's
trust root covers the coordinated manifest/registry/guarded-code/anchor
rewrite (matrix case b1_12).

## 8. B1–B3 second round (`interview-contracts@7`)

### 8.1 External-custody trust root + strict adjacency (B1)

The manager trust record moved OUT of the writer's writable surfaces to
`docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/ANCHOR_TRUST_ROOT.json`
(the package manager's own package). Its five reviewed values
(review SHA `a0402d33…`, anchor count 5, blob SHA-256 `a0aa1302…`, latest
chain `670927cb…`, prefix SHA-256 `37f66fc7…`) are ALSO embedded in the
guarded tripwire code (`REVIEWED_TRUST_ROOT`), and verification requires
the record file and the embedded copy to AGREE before either is trusted —
so a locally rewritten record that blesses a different chain is rejected
even where git history is unavailable (both reviewer bypasses,
`rewritten_local_root_verifies` and `same_version_lineage_verifies`, are
now False; matrix cases b1_15, b1_16). EVERY adjacent anchor pair must
strictly advance at least one governed version, so a hand-forged
same-version identity change (a correctly chained anchor under unchanged
versions) is rejected by `verify_monotonic_versions`.

### 8.2 Retired coach route guarded (B2)

The retired `POST /api/interview/coach` endpoint (rate limit, refusal
body, HTTP 410) is a guarded fragment
(`interview_retired_coach_contract`); its live registered function is in
the liveness proof, and rate/body/status mutation attacks are matrix
cases `b2_retired_coach_rate`, `b2_retired_coach_body`,
`b2_retired_coach_status`. It remains provider-free and is not a sixth
bundle or provider job.

### 8.3 Requests never initialize (B3)

`jobs._release_or_refusal` now ONLY reads `boot.state()`: an absent boot
state answers `service_not_configured` 503 with zero provider dispatch
and zero release-file access — a request can never invoke
`boot.initialize` or resolve release files. The lazy
`resolve_active_release` API is a verification/tooling seam only; the
request path does not reference it (`test_boot_state.py` proves both, plus
a fresh-process import freezing the state before any request).
