# Codex reconciliation — verdict and disposition

**Reviewed:** PR 502 tip `c0871f49` against base `6b3f90d5`, by Codex as the independent
reconciler, returned 2026-08-16.
**Verdict:** REVISE — "the principal direction is sound; the release identity, evaluation
gate, privacy enforcement, History authorization, and state model need substantive
correction first."
**Disposition:** all ten findings **accepted**. The corrections are integrated into
`00_CONSOLIDATED_ARCHITECTURE.md` v2, which is now the single normative document. This file
records each finding and where its fix landed, so the reconciliation is auditable.

| # | Codex finding | Disposition | Where fixed |
|---|---|---|---|
| 1 | Release identity (`prompt-sha8` per bundle) does not identify the complete released system; permits incompatible mixtures | **Accepted.** New atomic `interview_release_set_id` binds runtime SHA, all active bundles, guardian set, contract versions, and evaluation-set identity. Config-only rollback restricted to release sets sharing runtime SHA and contract versions. | 00 §2 |
| 2 | R8's `initial_extraction` exception lets materially changed behaviour activate unevaluated — slice 1 was not mere extraction | **Accepted.** Slice plan restructured: slice 1 is byte-equivalent extraction with parity tests (the only thing eligible for the predecessor-null exception); every behaviour change (adaptive length, timeout policy, evidence short-circuit, member-visible copy) moves behind the evaluation harness. | 00 §9, §10 |
| 3 | "Never invent" is not deterministically enforced for ordinary prose; answer-level `evidenceIds` lets one valid id carry several unsupported claims; the digit screen can mistake a question-embedded number for a supported fact | **Accepted.** Grounded output becomes claim-granular segments, each carrying a selected evidence id + bounded anchor, or a confirmation marker; full-coverage validation; question and role context may shape but never substantiate; digits permitted only in anchored segments or markers. Residual qualitative-prose risk honestly assigned to evaluation with a fatal-failure class. | 00 §5.5 |
| 4 | "Content-free" telemetry identifiers are content-derived (question-text fallback, role-text fingerprint) and `sha256(user_key)[:20]` is dictionary-testable, not non-reversible | **Accepted.** Attempt identity becomes a cryptographically random UUID unrelated to content; binding values stay in browser memory; longitudinal member attribution only via secret-keyed rotating HMAC **if** Pete decides it is needed (new decision D10), with retention/access/deletion rules required first. | 00 §7 |
| 5 | History selection is not question-bound (a selection for question A is consumable for question B within TTL) and consume-before-call makes the promised `provider_failure` retry impossible | **Accepted.** Selection rows now bind question digest, practice-context digest, candidate-set digest, member, purpose, and an opaque `operation_id`; lifecycle becomes minted → claimed → completed/failed, with idempotent re-claim by the identical operation only. | 00 §6 |
| 6 | No slice delivers Coach v3 / Revision Partner v2, and the attempt/version/review/proposal state model is contradictory and race-undefined | **Accepted.** Dedicated Coach/Revision slice added; one normative state model (practice record, attempt, answer version, review, proposal, working pointer, branching, idempotency, cross-tab rule) now lives in 00 and overrides both sections. | 00 §4, §10 |
| 7 | `all_approved_default` widens an omitted selection to the full approved set, and Generic Example receives `role_context` against the frozen contract | **Accepted.** Absent selection → no grounded provider call; "Use all approved evidence" only as an explicit member action. `role_context` removed from Generic Example entirely — changing that is Pete's, not a section's. | 00 §5.5, §5.6 |
| 8 | The "normative" document still requires implementers to synthesize from known-defective sections; named contradictions remain (router timeout 30s vs 15s, 7 vs 8 failure states, 500/503 inconsistency, duplicate-spend retry, silent validator truncation, incomplete error taxonomy) | **Accepted.** 00 v2 is rewritten to be self-contained on every normative point; the sections are demoted to non-normative historical drafts; each named contradiction is resolved concretely (router timeout 15s; full request/execution/computed failure taxonomy; `provider_failure` 500 with `service_not_configured` 503 distinct; idempotency-keyed spend rule; truncation = `invalid_output`, never a silent slice). | 00 §3, §8, §11 |
| 9 | Durable lane authority contradicts the five-call/Gate B activity; evidence wording overreaches ("exactly five paid calls", "~50 seconds", "never-invent proven live", universal non-owner claim); README self-contradicts; PR metadata stale | **Accepted.** Evidence classes corrected in `03_AUTHENTICATED_EVIDENCE.md` (application requests vs provider billing; word count observed, seconds inferred at a stated rate; one bounded never-invent observation + source-confirmed mechanism; universality source-confirmed, single-account observed). README contradictions removed. PR description updated. The control-plane reconciliation itself is outside this lane's writable surfaces and is recorded as owner decision **D13** — it needs a control-only transition, not a lane write. | 03, README, PR 502 description, 00 §12 |
| 10 | Router-disagreement and History/search/import/delete experiences are material member-facing interactions with no visual gate | **Accepted.** The Router, Coach/Revision, and History slices now carry an explicit dependency: ChatGPT-created, Pete-accepted visual direction before runtime implementation of those surfaces (new decision D12). Claude/Codex architect and implement; neither sets final visual direction. | 00 §10, §12 |

**Codex's seven additional owner decisions** are adopted verbatim as D7–D13 in the decision
register (00 §12).

**Codex's a–f dispositions** are accepted as stated, including the partial refutation in
(d): the claim-support and telemetry gaps it names were real and are now closed as above,
with the honestly-residual parts (qualitative prose invention) labelled residual rather
than solved.

One point of emphasis Codex validated and nothing should undo: the deterministic History
controls (owner-scoped retrieval, authoritative re-check, expiry, revocation, consumed-row
construction) were judged genuine. The corrections tighten their binding; they do not
reopen their design.

---

# Round 2 — change register

Codex's round-2 corrections (2026-08-16), all applied to `00_CONSOLIDATED_ARCHITECTURE.md`
(v2.1) unless noted:

| # | Correction | Where applied |
|---|---|---|
| 1 | Acyclic release identity: immutable `candidate_system_digest` (incl. knowledge/input-manifest contract + guardian compatibility) → evaluation runs bind to it → release set binds digest + accepted run digests | 00 §2 |
| 2 | Extraction exception = **full behavioural parity** (provider settings, request construction, schema, validators, response transformation) proven against golden transcripts; Grounded Example gains its own explicit evaluation gate | 00 §9, §10 slice 9 |
| 3 | Invention loophole closed further: connectives are length-bounded, digit-free, and entity-lexicon-screened; Coach observations quote-anchor to the answer (absence findings labelled as such); Revision diff↔ledger set-equality with `rewrite_of_existing` and `removal` entries | 00 §5.2, §5.3, §5.5 |
| 4 | Every private-context token (router token, `contextToken`, selection rows) binds server-derived member identity, purpose, question digest, practice-context digest, expiry, and release set | 00 §6.1 |
| 5 | History/retry safety: authoritative ownership/version/approval/revocation recheck at mint **and** claim; `failed(reason)` covers `invalid_output` with one same-operation re-claim; completed operations replay their stored result (terminal idempotency) | 00 §6.2, §3 |
| 6 | State model: persistence tiers defined; no silent legacy-session import (previewed, confirmed, disclosed rename); proposals never silently account-persisted and bound to source version/review/release set; concurrency checks on apply/discard/restore/pointer | 00 §4 |
| 7 | Revision Partner's full allowed inputs restored: question, preserved answer + lineage, Router/Coach findings, member-selected evidence, confirmed context | 00 §5.3 |
| 8 | Failure/telemetry completeness: `extraction_failed`, `internal_error`, `insufficient_information` added; `retryable` + `retry_policy` on every response; terminal idempotency; closed telemetry field allowlist; six timing stages; 90-day retention, operator-only access, deletion prerequisites | 00 §3, §7 |
| 9 | D12 + slice gates expanded to ChatGPT-created, Pete-accepted visuals for Coach/Revision and History Nudge, not only Router and account History | 00 §10 (slices 5–8), §12 D12 |
| 10 | Evidence/README wording: observed-vs-inferred distinctions already landed in round 1 retained; stale Gate-A-before-Gate-B instruction removed from the README review-return; link normalization deferred to the authorized relocation | README |
| 11 | Secret-scan false positive: the §7 telemetry line matched `generic-api-key` at entropy 3.51 (keyword "tokens" followed by a dense value-shaped run); reworded as part of the §7 rewrite, and the branch history squashed so the matching blob no longer exists in any scanned commit; required policy re-run recorded in the PR | 00 §7; branch history; PR 502 |

---

# Round 3 — FOCUSED REVISE, change register

Codex round-3 (2026-08-16) verified the PR/build/history claims and accepted the
private-token bindings, authorization rechecks, the dedicated Coach/Revision slice, and
the four visual gates. Seven consistency corrections plus an owner-register regrouping
were required; all applied in v2.2:

| # | Correction | Where applied |
|---|---|---|
| 1 | Release identity made genuinely acyclic: evaluation runs record candidate-system digest + bundle ids **only**; release-set ids exist only in the activation record and post-activation responses/telemetry; the stamped-into-evaluation-runs statement removed, §9's gate rebound to the candidate digest | 00 §2, §9 |
| 2 | Grounded-claim gap honestly bounded: `evidence_claim` becomes an atomic claim unit; the anchor check is named a deterministic *support-linkage* check, **not** deterministic claim support; semantic-entailment risk classified residual + fatal-in-evaluation for **every** generated claim, not only connectives | 00 §5.5 |
| 3 | Two retry identities separated: request idempotency key (duplicate requests replay stored success *or failure*) vs History-selection `operation_id` (the one authorized member retry = same operation, fresh request key); completed selections replay success; no duplicate spend | 00 §3, §6.2 |
| 4 | State/persistence completed: three tiers (ephemeral / browser / account) with every entity assigned; proposals **ephemeral** — never localStorage merely for pressing Improve; guest/public namespaces preserved across sign-in/out with no automatic mixing; applied revision's parent = pointer version at apply time with divergence surfaced to the member; failed provider calls create failure state, never a Review row; browser-tier conflict handling defined separately from account-tier 409; slice 6 wording tier-governed | 00 §4, §10 |
| 5 | Telemetry completed: closed enums/nullability/bounds for every field; restored `source_class_counts`, `validation_result`, usage/cost, `member_action_outcome`; full client+server timing chain (ui_open → final_paint); named sink (append-only SQL table via allowlisted stored procedure), owner-only access path, scheduled 90-day purge — all ship-prerequisites | 00 §7 |
| 6 | Self-containment made true: the eight `question_class` values enumerated; family/dimension registry, `marker-contract/1` (full definition), `registry.json` v1 schema, and the golden-cases/scorecard paths bound exactly; the self-contained claim scoped honestly | 00 §3 |
| 7 | Truth statements corrected: logical provider invocation = inference from 200 + source, not observed transport/billing; nudge negative UI scan observed vs non-retrieval source-confirmed; "production demonstrably ignores" removed in favour of observed-words/inferred-adherence; D8 restated as rollback to a prior compatible release set; README relocation wording no longer claims "unchanged" alongside link normalization | 00 §1, §12 D8; 03; README |
| — | Owner register regrouped: 13 identifiers, D6 resolved, **12 open**, of which only **4 are needed to accept the architecture** (D2, D3, D8, D9); 2 before the evaluation batch (D4, D5); 4 before later slices (D1, D7, D10, D11); D12 marked an already-assigned visual workflow and D13 a control-plane recording prerequisite — neither a product choice to make now | 00 §12 |

---

# Round 4 — FOCUSED REVISE, v2.2 → v2.3 change register

Codex round-4 (2026-08-16) accepted the architecture direction and required one bounded
correction pass (historical register wording; the candidate's status wording is governed
by rounds 6–7 — nothing is "closed" pending Pete's acceptance). All six applied:

| # | Correction | Where applied |
|---|---|---|
| 1 | Release identity made executable: the activation registry is excluded from the evaluated artifact via `runtime_artifact_digest` (git tree hash minus the activation record path); prior release-set records fully defined so rollback compatibility is mechanically verifiable | 00 §2, §3 registry schema |
| 2 | Idempotency finished: request keys bound to server-derived identity + purpose + request digest; reuse with different input → `conflict` (409); atomic unique-insert duplicate handling; exact 24-hour retention with immutable per-key results; one authorized History retry with a fresh key preserved; remaining "consumed" terminology replaced by the claimed → completed/failed lifecycle (authorization state renamed `member_selection_claimed`) | 00 §3, §6.1–6.2 |
| 3 | Atomic transitions: apply/restore/discard/version-creation/pointer/idempotency commit as one transaction or not at all, per tier; every remaining entity assigned a tier (practice records, attempts, failure state, request-key rows); `conflict` 409 added to the taxonomy; every post-claim History failure transition enumerated, including crash/expiry and revocation-at-recheck | 00 §3, §4, §6.2 |
| 4 | Overclaims removed: guardian renamed support-linkage; coach anchoring proves the quote exists, not the interpretation; the 111-word finding no longer claims a proven 60–120s violation; the remaining "provider call observed" statement reclassified as source-supported inference | 00 §1, §5.2, §8; 03 |
| 5 | Telemetry/self-containment honestly scoped: §7 binds shape and prohibitions; the telemetry slice must supply table DDL, procedure signature, per-specialist failure-reason enums, and the purge job before implementation; the "works from 00 alone" claim scoped to decisions and contracts | 00 how-to-read, §7 |
| 6 | Status text reconciled: header/README at v2.3; D5 moved to "after Wave 1 results, before first behaviour activation" (it cannot precede results it judges); final recommendation names only D2/D3/D8/D9 for acceptance; Pete's authorizations described as separately granted with the durable record unreconciled (never "superseded"); D13 marked a pre-merge control-plane prerequisite; slice-1 telemetry/logging no longer called zero-behaviour; every open decision now carries an explicit recommendation (one consolidated sheet, §12); PR description rewritten in plain ASCII with the actual tip and build result | 00 header, §9, §10, §12, §13; README; PR 502 |

---

# Round 5 — FOCUSED REVISE, v2.3 → v2.4 final change register

Codex round-5 (2026-08-16): final bounded consistency pass, five items, all applied:

| # | Correction | Where applied |
|---|---|---|
| 1 | Retry semantics finished: per-key results immutable (failed key replays failure; retry key replays success); operation-level final result stored separately; explicit one-time `failed → reclaimed → completed\|failed` transition; the contradictory "failed row can never produce provider input" removed; simultaneous duplicates receive 409 `conflict` with Retry-After while the winner runs; a server-issued guest principal defined for signed-out/public requests; post-claim failures enumerated completely, adding `internal_error` and `unavailable_source` | 00 §3, §6.1–6.2 |
| 2 | Cross-tier atomicity corrected: account-tier one-transaction commits, browser-only mutations entirely client-side with single-swap writes, cross-tier operations commit server-first with idempotent replay-and-rebuild recovery — no claim that localStorage and a server row share a transaction | 00 §4 |
| 3 | Rollback record completed: the excluded activation-registry path named exactly (`prompts/interview/registry.json`); ordered `bundle_ids[]` and `evaluation_set_hash` stored in every active and prior release record so a rollback target is reconstructable and validated from the record before activation | 00 §2, §3 |
| 4 | Truth contradictions removed: 03's F1 states only the 111-word count was observed and adherence remains unverified; the guardians are "twelve named — eleven fully deterministic, support-linkage's semantic half evaluation-gated"; slice 1's "genuinely zero behaviour change" replaced with the honest member-visible/operational split; README updated to v2.4 and "separately authorized while the durable record remains unreconciled" | 00 §1, §8, §10; 03; README |
| 5 | Telemetry/self-containment reconciled: the contract is separately versioned (`telemetry-contract@1`, inside `contracts_version`); content prohibitions are complete and absolute now; the field set is the normative v1 shape with the slice completing enums/bounds/artifacts before implementation — no longer simultaneously complete and deferred | 00 §7 |

---

# Round 6 — v2.4 → v2.5 register (manager handoff pass, with mandatory internal review)

All Pass-1 corrections applied; locations are final file:line in this tip:

| # | Correction | Final location |
|---|---|---|
| A1 | "accepted and closed" removed everywhere; status = "v2.5 architecture candidate, internally reviewed, awaiting Pete and Codex acceptance" | 00:4; README:3; PR description |
| A2 | Length evidence: instruction source-confirmed, 111 words observed, delivery/adherence unverified; "not reliably followed" and "adherence failure" removed | 00:60-67; 03:96-111 |
| A3 | Provider claim: code path traversed (inference), transport/billing unobserved; "pays for a call" removed; provider-call statements qualified to "no new application AI calls in this pass; five earlier owner-authorized requests on record" | 03:72-79; PR description |
| A4 | Validators no longer "confirmed by the live test": mechanisms source-confirmed, only safe outcomes and marker behaviour observed | 00:591-594 |
| B5 | `telemetry-contract@1` added to the §2 `contracts_version` digest contents | 00:103 |
| B6 | One failure/retry contract: lifecycle summaries include reclaimed/expired (00:141-144); request-time vs post-claim authorization refusal distinguished; 409 reason-coded (`stale_state`/`idempotency_key_mismatch`/`in_flight`) with exact bool + policy per case (00:160-190); policy phrases removed from the retryable column; per-key immutability scoped to the 24-hour window (00:216); "three computed" corrected to four (00 §11) | 00 §3, §6, §11 |
| B7 | Proposal atomicity: transaction touches proposal status only where a durable row exists; ephemeral proposals retired in the client swap; crash recovery reconstructs client state from the stored idempotent response | 00:340-352 |
| B8 | Self-containment: complete deferred-detail enumeration (golden content, telemetry enums/bounds/DDL/procedure/purge, slice briefs, visual direction, production config) | 00:267-273 |
| C9 | D2 split: mandatory evaluation preserved as settled accepted direction; capped per-slice evaluation budget recommended (manager executes within cap; Pete only for cap-exceed/scope-change/Wave 1) | 00:727-737 |
| C10 | D3 disclosed costs (two generations, latency, D1 prerequisite, visual acceptance; no usage evidence claimed); D8 no downtime promise + future Protected slice supplies operator authority/audit/verification/recovery; D9 Diagnostician may advise or run as prerequisite, never substitute | 00 §12 |
| C11 | Wave 1 calibration-only rule: one result set never both chooses and passes its thresholds; fresh judged run required after post-hoc threshold setting | 00:640-646; D5 |
| D12-13 | D13 enumerates the five things the later control-plane transition must record; fresh PR 502 merge preview + policy build required after `main` moves; build 1129 scoped to source `1fe1a25a` vs target `6b3f90d5` only | 00:790-800 |
| — | Acceptance set corrected: D2 settled; the three choices are D3, D8, D9 | 00 §12 intro, §13 |

**Internal review record (round 6, durable):** one fresh-context reviewer, both
checklists, over the final on-disk files. **First pass: architecture checklist FAIL, truth
checklist PASS-with-minors** — 1 blocking (the telemetry contract simultaneously bound and
deferred the same bounds/enums in §7 vs §3 vs the how-to-read note), 5 minor (the §6.2
one-line lifecycle omitted reclaimed/expired; no reclaimed—expired exit; a corrupted
`("+S+"6.2)` character sequence inside the request-refusal table; two competing
response-contract statements with a camelCase `failureState`; D2 restating the parity
exception as byte-equivalence), 3 editorial (an unpriced "~50 seconds" in §13; stale v2
wording; README build-1106-vs-merge coherence). **All fixed; re-verification confirmed
every fix against disk and caught one new inconsistency introduced by a fix (README PR-501
failed-build vs merged, missing the relocation step), which was fixed and re-verified.
Final verdict: both checklists PASS, no open findings.** Reviewed working-tree state was
committed as source tip `3875d893` (v2.5); the reviewer's approval preceded that commit
and no content changed after it. Note: the register above cites file:line positions as
they stood at v2.5; lines shift in later versions — the section anchors named in each row
remain the stable reference.

---

# Round 7 — v2.5 → v2.6 register (final bounded reconciliation)

All eight correction areas applied. Locations are section anchors (stable), not line numbers:

| # | Correction | Where |
|---|---|---|
| 1 | Release/evaluation/rollback made executable: evaluation-run records live at `prompts/interview/control/evaluation-runs/` outside every digest; the whole-tree digest replaced by `runtime_core_digest` (initially scoped tree-minus-prompts in this round; re-scoped by the round-7 internal review and round 8 to the closed guarded dependency manifest) so new bundles never strand prior releases; immutable retained bundle catalog; config-vs-registry authority and atomic activation/rollback procedure; per-changed-element accepted-run coverage proof; threshold-set/calibration-vs-judged/partition-hash/scorecard/fatal-policy bound into run and release identity; locked holdout for post-calibration judging; no spend authority created — per-slice Pete-approved caps; decision count corrected (13 identifiers, D6 resolved, D2 settled, 11 open, 3 choices) | 00 §2, §3 registry, §12 |
| 2 | Idempotency/History recovery: in-flight lease + reaper + `abandoned` (a `provider_failure` reason, may carry `dispatch_uncertain`); polling-vs-retry distinguished; dispatch uncertainty stated honestly and "duplication prevented" scoped to server enforcement; reclaim re-runs the full authoritative recheck; `minted/failed/reclaimed → expired` transitions added; terminal second-failure responses operation-aware (`next_action: fresh_selection`) | 00 §3, §6.2 |
| 3 | Browser identities + proposal provenance: browser-generated `b-` ULIDs with local display labels and explicit migration mapping; signed expiring proposal-application envelope (principal, purpose, draft digest, source version, review, release set, expiry) revalidated atomically at apply; member-edited proposals recorded as `applied_revision` + `member_edited: true` with the ledger marked as describing the proposal as generated | 00 §4 |
| 4 | Specialist/guardian contracts: per-specialist concrete schemas + the evaluation-run schema added to the explicit deferral enumeration and the self-containment claim narrowed; `guardian-registry@2` (fourteen named: the twelve + subpart-substring + compare-isolation) with telemetry using exactly that enum; "atomic claim" replaced by a syntactic unit (≤1 sentence, ≤240 chars) with semantic atomicity evaluation-gated; Generic Example receives the structured Diagnostician projection instead of the verbatim question once the Router exists, with the interim echo risk screened and stated; Compare defined as a real composition (parent+children identities, per-half keys, partial-failure preservation, half-retry, member view) | 00 how-to-read, §3, §5.5–5.6, §8 |
| 5 | Telemetry closed: named timing fields (server `dur_*_ms` set; client set); typed `provider_usage`/`cost_microusd`/`exception` containers; required server `recorded_at` keyed by the purge; two-event model (`server_call` append at response time; `client_view` separate append, never an update, unknown-not-abandoned honesty); field provenance enforced structurally (client rows cannot assert server facts); append-only defined as INSERT-only writer permission with the purge identity holding the sole DELETE; the `source_class_counts` bound named once (fixed, not deferred) | 00 §7 |
| 6 | Slices/visual gates: response stamping deferred from slice 1 and disclosed as slice 3's additive API change with contract tests; slice 9 gains the D12 visual gate for the evidence-selection/insufficiency/refusal/recovery experience; slice 10 `PS-INTERVIEW-AI-COMPARE-001` gives retained Compare its preservation slice with evaluation + visual gates | 00 §2 tail, §10 |
| 7 | D13 made executable: the ordinary grant path's four incapacities stated; the real six-step sequence recorded (control-plane repair with location chosen before any SHA grant → acceptance against the exact reviewed SHA → merge grant → fresh preview/build → merge → post-merge close) | 00 §12 D13 |
| 8 | Durable truth: round-6 internal-review record persisted above (first-pass findings, fixes, re-verification, final verdict, reviewed SHA); register line references declared v2.5-stale with section anchors as the stable reference; README says five Codex rounds plus one manager/internal-review pass; no "accepted/closed direction" statement survives in normative files; build references scoped precisely (1131 = approval of the v2.5 merge preview for `3875d893` vs `6b3f90d5`, never the post-D13 final); evidence wording corrected (credentials-handling sentence, "application AI request", "answer-version UNVERIFIED item", one-instance marker heading) | 21 (this file), README, 00 §12, 03 |

**Internal review record (round 7, durable):** one fresh-context reviewer, both
checklists, over the final on-disk v2.6 files. **First pass:** 4 blocking (a stale
"twelve open" lead-in contradicting the corrected count; the runtime-core digest scoped
as tree-minus-prompts, which any unrelated commit would invalidate — rollback stranded
and endpoints fail-closed; a dangling §7 "cardinality" cross-reference for compare
telemetry with no parent field in the closed allowlist; the telemetry deferral boundary
restated three inconsistent ways), 5 minor (slice-4 "twelve guardians"; `guardian_rejections
≤ 12` below the 14-name registry; an unscoped duplication-prevention closer; an
abandoned-vs-§6.2 retryable contradiction; README rounds accounting), 3 editorial
(`final_paint` naming; missing `threshold_set_version` in the registry schema; the
round-4 historical "as closed" phrasing). **All twelve fixed; re-verification confirmed
eleven against disk and caught one survivor** (the "twelve open" bold lead-in above its
own corrected sentence), **which was then fixed and confirmed in the final pass. Final
verdict: both checklists CLEAN.** The reviewer's approval covers the working-tree state
committed as the v2.6 source tip recorded in the PR; no content changed after that
approval. Line references cited here are v2.6 positions; section anchors are the stable
reference.

---

# Round 8 — v2.6 → v2.7 register

All ten correction areas applied. Locations are section anchors (stable), not line numbers:

| # | Correction | Where applied |
|---|---|---|
| 1 | Release/rollback identity finished executable: `runtime_core_digest` re-scoped to the closed, CI-enforced **guarded dependency manifest** (`guarded-paths.json`), backed by an **import-closure CI guard** (every behaviour-affecting shared import must enter the manifest or sit behind a pinned interface) and a manifest-path tripwire; canonical identities (bundle hashes, candidate digest, run digests, release-set ids) stored and compared **full-SHA**, with short forms display-only; each candidate bundle id pins its bundle's full content hash with the **input-manifest specification carried inside the bundle** (`schema.json`), not merely a versioned builder contract; activation redefined as an **ordered fail-safe sequence** (registry append → configuration → restart, boot-checked, fail-closed) rather than one atomic transaction | 00 §2 |
| 2 | Evaluation made auditable per run: each run record now carries an **evaluation coverage manifest** — the mechanically checked list of exactly which changed elements it exercised — which activation consumes as data rather than inferring; case membership behind `case_partition_hash` is bound **immutably** per run; the harness **mechanically proves calibration/holdout id-set disjointness** before a judged batch starts (differing hashes alone no longer accepted); a judged batch's exact case list, count, and spend cap are **locked before it runs** | 00 §2 |
| 3 | Idempotency/orphan-recovery finished: the in-flight row records a **lease owner (worker id)**; recording an outcome is a **compare-and-swap against the active lease and operation state**, so a **late worker result arriving after reaping, lease expiry, or a reclaim fails the CAS and is rejected and discarded**, never recorded; request-key and History-selection transitions are defined as **single-row atomic operations** (insert-unique or CAS, never read-then-write); the **operation-level final result shares the request key's 24-hour retention/purge window**; polling (re-sending the original key) and retrying (a fresh key) are distinguished as different acts; simultaneous duplicates resolve **in-flight-first** — the loser observes `in_flight`/409, never an immediate terminal outcome | 00 §3 |
| 4 | Proposal-apply provenance closed: account-tier apply travels in a **signed, expiring proposal-application envelope** binding principal, purpose, the AI proposal's own digest, source version, review id, release set, and expiry, plus a **server-claimed single-use nonce** consumed atomically with the version mint; `member_edited` is **derived server-side** — the server digests the member's submitted final draft and compares it to the envelope's proposal digest — never a client-asserted flag | 00 §4 |
| 5 | Generic Example privacy made structural, not merely screened: the Diagnostician's free-text outputs are classified **tainted `private_derived`** and **barred from Generic Example's manifest by the source-allowlist guardian**; the **compare-isolation guardian is generalized** to all `private_derived` content, not only grounded evidence; Generic Example's input is narrowed to a **closed, minimized, deterministic enum/code projection**; the pre-Router live echo gap is stated honestly as unchanged by this documentation package and closed only once the projection exists (Router slice) | 00 §5.6 |
| 6 | Compare defined as an executable composition/action contract: `composition: "compare"` sits **outside the closed specialist enum**, with the parent telemetry row's `event_kind: composition_parent` carrying `specialist`/`bundle_id` both null; the parent **atomically registers both child request keys before either dispatches**; each child gets its own `attempt_uuid` + bundle id + request key + `parent_attempt_uuid`; **partial-failure preservation and single-half retry** are stated as a request-key replay (no second charge); persistence is tiered (§3 transient window / §4 durable-product rules) | 00 §5.6, §7 |
| 7 | Telemetry closed to exactly two schemas: `server_call` (server-written once per attempt, `event_kind` ∈ `specialist_call` \| `composition_parent`) and `client_view` (a separate append, never an update, structurally unable to assert any server fact); exactly **three nullable server-sourced identities** are named (`release_set_id`, `parent_attempt_uuid`, `operation_id`) | 00 §7 |
| 8 | State-model/slice-gate closure: `attempt_number` is defined as a **server-assigned account-tier label vs. a locally computed browser-tier label**, never derived from counting reviews; the §10 slice table carries the **D12 visual gate through slices 5–10**, explicitly including slice 9 (Grounded Example) and slice 10 (Compare, `PS-INTERVIEW-AI-COMPARE-001`) | 00 §4, §10, §12 D12 |
| 9 | D13 made executable: the current generic grant path's incapacities restated precisely — cannot add or change this package's owner decisions, lacks the required code-controlled review attestation, merge authority absent, current validation permits only the defined main-side commit sequence, formal close cannot precede merge; the **permanent location chosen now**, before any SHA grant (`docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/`, consistent with the README); the `PS-DELIVERY-CONTROL-001` repair's three obligations named; the **ordered relocate → review → accept → grant → preview/build → merge → close** sequence given in full | 00 §12 D13 |
| 10 | Evidence/durable-truth reconciled: the round-7 row 1 entry above is annotated to record that `runtime_core_digest` was re-scoped again in round 8 to the closed guarded dependency manifest, superseding the round-7 tree-minus-prompts scope; 03's credentials statement corrected so no absolute no-transmission claim survives, only what was and was not done with the existing signed-in session; README's rounds accounting corrected to eight rounds (five Codex reconciliation rounds plus three manager passes with mandatory internal review) | 21 (this file, Round 7 row 1), 03, README |

**Internal review record (round 8, durable):** one fresh-context reviewer (Opus, maximum
effort), no expected verdict supplied, over the complete on-disk v2.7 files, with
end-to-end scenario tracing and repository-citation verification against the worktree.
**First verdict: NOT READY** — one blocking finding (the release-set id was minted as a
12-character truncation while the canonical-identity rule forbade truncated comparison
— the exact value activation, rollback, token binding, and telemetry check) plus two
non-blocking notes (an unscoped "no consumed state" wording; `composition` defined in
prose rather than as a schema row). **All three fixed; the reviewer then re-read the
complete final files** (00 in full; 03/21/README verified byte-identical to its first
pass), re-ran the failed scenario and the full invariant sweep, and returned **CLEAN**
with: acceptance matrix MET on all ten round-8 areas; scenarios S1—S6 all PASS; sweep
zero hits; all repository citations verified. **Approved content-manifest hash**
(sha256 of each of 00/03/21/README's bytes in alphabetical order, then sha256 of the
concatenated hex digests):
`c0cfcd385b3e71079d2dfc8d8a2a28b55e306e02bb04a5af1a2069481d553652`
That hash binds the approved content of the four files at approval time. **This appendix
is the only change after that approval**; it alters 21 (and therefore any later
whole-package hash) but none of the approved architecture content, and the reviewer
confirmed this exact appendix text in a final reread. The content-to-commit binding is
external — the PR records the source tip carrying these bytes, and the policy build
approves that exact source/target preview; later code-controlled attestation (D13)
formalizes it.

---

# Round 9 — v2.7 → v2.8 focused final reconciliation

Round 8's internal `CLEAN` verdict remains a credible record of the content it reviewed,
but it is superseded for handoff purposes: Codex's fresh focused review found the eight
bounded survivors below. The former Claude writer explicitly relinquished the clean
branch at `3fcdb917e196b3d6f4d09d35c6332f4054e510bc`; the package's control-only writer
transfer then passed 130 focused governance tests, transfer preflight, and all three PR
policies in build 1139, and merged through PR 505 as
`6c188980c1299289b3b0fe146ac73f3a6219600a`. No product/runtime file changed in that
transfer. Codex rebased the still-single-candidate commit onto that exact `main` and
applied only these accepted findings:

| # | Focused correction | Where applied |
|---|---|---|
| 1 | Current base and historical lineage separated: current PR target is `6c188980`; `6b3f90d5` remains only the Gate A history point; deployed/source-analysis pins remain distinct | 00 header; README status |
| 2 | Durable role record added: ChatGPT Work manager; Claude initial architect/writer through the relinquished SHA; Codex current sole writer/technical reconciler; fresh read-only Codex reviewers; Original ChatGPT later material visual creator; Pete owner/final decision-maker | 00 header; README |
| 3 | Runtime closure escape removed: every mutable repo-local transitive implementation and dependency lock enters the guarded digest; only a full immutable external implementation digest can stand outside, never an interface/version alone | 00 §2 |
| 4 | Canonical bundle identity made consistent end to end with `bundle_ref { bundle_label, bundle_content_sha256 }`: raw bundle bytes are domain-separated and length-framed; structured digests use canonical JSON; specialist slot + full hash, never the display label, forms identity; catalog lookup/full-hash collision checks are mandatory | 00 §2, §3 registry, §5.6, §7 |
| 5 | Telemetry boundary made honest and executable: structural field contract and every present/null/type condition fixed; server-issued attempt transport and FK-validated client echo defined; Compare parent and unresolved-release mappings completed; specialist/composition failure and exception allowlists explicitly deferred and versioned; usage/cost capture is iff and immutable under INSERT-only rows | 00 §2 response boundary, §3 deferrals, §5.6, §7, §10 slices 1/3 |
| 6 | Slice ownership corrected: slice 6 owns proposal preview/apply/discard/restore; capitalized Compare remains exclusively slice 10 | 00 §10 |
| 7 | Proposal provenance narrowed to what hashes prove: the two digests preserve only whether editing occurred, not a reconstructable text diff; exact edit auditing would require a separate disclosed member-authorized artifact | 00 §4 |
| 8 | D13 selects one executable relocation mechanism: a package-specific control admission permits the move and the package-registry entry in one candidate tree, followed by fresh review, exact-SHA Pete acceptance, grant, fresh preview/build, merge, and post-merge close | 00 §12 D13; README relocation section |

This round does not reopen product direction, add implementation, authorize provider
spend, merge PR 502, deploy, enable, or change live behavior. Final exact-SHA
confirmation is external PR/review evidence; it is never appended to the commit it
attests, because such an append would create a different SHA.

**Round-9 internal review record (working-tree content, before commit):** Codex completed
the author sweep and then assigned three fresh read-only reviewers with narrow briefs and
no expected verdict. The core reviewer first returned REVISE on universal bundle
stamping and cross-domain proposal digests; after correction it later caught one
unresolved-release response-shape survivor. The authority reviewer returned REVISE on
manager/writer wording, self-mutating SHA-attestation language, an under-specified
registry admission, and merge/close sequencing. The telemetry reviewer and its fresh
skeptic returned REVISE on usage/cost conditions and types, Compare-parent outcome
mapping, pre-resolution bundle nullability, attempt-id transport, digest framing,
display-label leakage into identity, nullable-id types, and the
`service_not_configured` taxonomy. Every finding was accepted and corrected; each
reviewer re-read its corrected scope and returned **ACCEPT**, and the core reviewer also
rechecked the telemetry-driven identity/Compare changes. The focused governance suite
ran 130 tests in 185.819 seconds: **OK**; `git diff --check` passed; all local Markdown
link targets in 00/README/21 resolved. This record binds the reviewed content, not a
self-referential commit SHA; the exact committed SHA and its PR-policy result must be
attested externally after commit and policy execution without changing these bytes.

---

# Round 10 — D13 owner acceptance, control reconciliation, and relocation

Pete accepted Interview AI v2.8 on 2026-08-16 and accepted D3, D8, and D9 exactly as
recommended: retain Compare; permit settings-and-restart rollback only between
mechanically compatible release sets and never as code/deployment rollback; and always
let the member choose the specialist while AI only advises or runs as a prerequisite.
He authorized D13 reconciliation, relocation, and fresh review, while expressly
withholding PR 502 merge until he approves the exact relocated SHA.

Control-only PR 506 reconciled the prior bounded five-application-request and Gate B
authority, installed the one-time relocation/registry admission, passed 107 focused
delivery-preflight tests plus exact activate preflight and independent three-file review,
and merged as `b4d79b217b1b8b68128a5271031390bb2be521b6` after build 1142 and all three
policies passed. It granted no PR 502 merge, release, provider-call, evaluation,
deployment, enablement, or live authority.

This candidate then:

1. rebased the single architecture commit onto that exact control main;
2. moved all twelve package files into
   `docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/`;
3. normalized the sixteen external relative links;
4. added the package exactly once to registry category `future_finish`, changing only
   that category count from 22 to 23 and the total from 115 to 116; and
5. reconciled the normative status and decision register with Pete's accepted choices.

No runtime or live behavior changed. After these bytes are committed, fresh independent
review must attest the exact relocated SHA externally. The candidate must not change
after that review; it returns to Pete for explicit approval of that exact SHA before any
attestation-registration repair or merge grant.
