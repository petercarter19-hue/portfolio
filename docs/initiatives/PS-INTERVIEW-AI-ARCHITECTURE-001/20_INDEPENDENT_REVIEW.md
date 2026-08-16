# Independent review — Gate B Sections 1–5

**Package:** `PS-INTERVIEW-AI-ARCHITECTURE-001`
**Reviewer role:** independent. I did not write any of the five sections. My job was to find what is wrong.
**Scope:** documentation review only. No code, prompt, schema, test, configuration, or section file was changed. No branch, commit, or PR was created. Zero provider calls.
**Evidence used:** the five sections; `01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md` as overridden by `02_GATE_A_ERRATA.md`; the live authenticated evidence gathered today against production (deployed SHA `f42e5399`, synthetic account "PeerSlate Test", five provider calls); and direct reading of `app.py`, `static/js/interview-studio.js`, `services/ask_pete/provider.py`, `services/database_service.py`, `services/opportunity_slate_v2_service.py`, `templates/interview_studio.html`, and `requirements.txt` in this worktree.

---

## Verdict: **REVISE**

Not because the thinking is weak — it is strong, and Section 12 of this review lists what must survive untouched. It is REVISE because **ten separate times, two sections define the same object differently**, and in five of those cases both definitions are written as settled fact rather than as an open reconciliation item. A consolidation that merges these five files as they stand would ship a design containing two version-identity formulas, two answer-version models, three length vocabularies, four transports for one failure state, and one privacy interlock that every section assigns to a different section.

There is also one hard circular dependency that blocks the recommended first slice from ever passing its own build.

This is a reconciliation revise, not a redo. No section needs to be rewritten from scratch.

**Plain-language version for Pete:** the five authors each did good work, and their descriptions of the current code are accurate — I checked about twenty-five of them line by line and every one was right. The problem is that they were writing at the same time without seeing each other. So the same thing gets two different names, two different shapes, or two different rules in different documents. Left alone, whoever builds this would have to guess which one is real, and a guess in this area is exactly where privacy bugs come from. The fixes below are mostly "pick one and write it down once".

**Counts:** 31 findings — 10 blocking, 9 high, 8 medium, 4 low.

---

# Blocking findings

*Definition of this tier: two sections define the same thing incompatibly, or a section claims a control that does not exist and cannot be built as described.*

## BLOCK-1 — The empty-evidence outcome is designed two different ways, and Section 5's version deletes the exact distinction Section 4 calls a truthfulness requirement

**What is wrong.** Section 4 and Section 5 both redesign what happens when a member has no approved evidence. They reach opposite answers, and neither flags the other.

Section 4, `13_SECTION_4_GROUNDED_AND_GENERIC_EXAMPLES.md` §B.2:

> **Truth 1 — evidence capability is absent for this member: `unavailable_source`.** … Decided deterministically, **before any provider call**.
> …
> **The distinction in one line:** `unavailable_source` means "you have no approved evidence at all — nothing was attempted"; `insufficient_evidence` means "your evidence was consulted and honestly cannot carry this question." Collapsing them would tell a capability-absent member their evidence was consulted (false) or tell an evidence-holding member they have none (false).

Section 5, `14_SECTION_5_GUARDIANS_TELEMETRY_EVALUATION_ROLLOUT.md` §5.1 guardian 2:

> **if the authorized `member_evidence` set is empty, return the `insufficient_evidence` result with zero provider calls.** Same member-visible outcome, no spend, no model in the loop…

Section 5 performs precisely the collapse Section 4 forbids, and asserts "Same member-visible outcome" as a benefit.

**Ruling against the live evidence.** Today, a non-owner requesting a grounded example gets HTTP 200, an insufficient state, and **one provider call is made** (`POST /api/interview/model-answer` → 200). I confirmed the mechanism in source: `interview_model_answer()` builds `evidence_lines` as `'- No approved public evidence is available.'` (`app.py:4299-4301`), calls `client.messages.create` (`:4340`), and the insufficient copy is server-normalized inside `validate_interview_model_answer` (`app.py:3559-3565`). The member-facing panel adds static template copy at `templates/interview_studio.html:1001` ("Nothing was invented or borrowed from another person."), rendered off `setAiState('insufficient')` and `[data-is-ai-insufficient]` (`static/js/interview-studio.js:3751`, `:3800`).

So: **Section 4's description of today is correct** (§B.4 is accurate, including the retry-trap analysis), and **Section 5's zero-provider-call rule is correct**. What is wrong is Section 5's *label*. The right design is Section 4's state taxonomy plus Section 5's short-circuit: capability absent → `unavailable_source`, zero provider calls, distinct copy.

**Why it matters.** This is the single most common member-facing AI outcome in production today — every non-owner hits it. Getting the state name wrong means the member is told their evidence was consulted when nothing was consulted, which is the class of untruth the whole package exists to prevent. It also determines whether the fix is a copy change or a no-op.

**Correction.**
1. Section 5 §5.1 guardian 2 replaces `insufficient_evidence` with `unavailable_source` and deletes "Same member-visible outcome"; the outcome deliberately changes.
2. Section 5 §5.0's transport table gains the Section 4 §B.3 shape (see BLOCK-5).
3. Both sections state that this changes member-visible copy and therefore touches `templates/interview_studio.html` and the `[data-is-ai-insufficient]` render path — it is not a server-only change (see HIGH-5).
4. Section 4's "no `contextToken` on a non-answer" cleanup is correct and should be carried; I verified the token is signed regardless of status today (`app.py:4386-4395`).

---

## BLOCK-2 — `prompt-sha8`, the identity every telemetry record, run record, and rollback binds to, has two incompatible definitions

**What is wrong.** Section 1 §2.2:

> `prompt-sha8` = first 8 hex characters of SHA-256 over the canonical release bundle: the pinned constitution bytes, `instruction.md`, `schema.json`, `provider.json`, concatenated in that fixed order… The hash therefore covers *everything behavior-affecting*, not just wording — a model change or schema change changes the identity too.

Section 2 §2.10:

> `<prompt-sha8>` is the first 8 hex chars of the SHA-256 of the canonical, un-interpolated system-prompt template bytes (UTF-8, exact).

Section 4 §C.1: "The prompt template is hashed at build."

Section 2's and Section 4's preimage is the prompt text alone. It excludes the constitution, the schema, and `provider.json`. Under their definition a model swap or a schema change ships **under an unchanged version id** — the exact failure Section 1 designed the bundle hash to prevent.

**Why it matters.** Three of Section 1's controls depend on the bundle definition and silently break under the other: the immutability CI test that "recomputes every released bundle's `sha8` from its bytes and fails the build on any mismatch" (§2.2) would fail every Section 2 and Section 4 bundle; the evaluation binding "a run whose recorded sha8 does not recompute against the prompt files in the tree is void" (Section 5 §5.4) becomes meaningless; and rollback selects a version id that no longer identifies the model or schema it ran with.

**Correction.** All sections adopt Section 1 §2.2 verbatim. Section 2 §2.10 and Section 4 §C.1 delete their own definitions and cite Section 1. Add one line to Section 1 §2.2 making the ordering rule and separator explicit enough to implement without ambiguity (it already is — just make it the single normative statement).

---

## BLOCK-3 — The six specialist identifiers are spelled four different ways, and they are the primary key of telemetry, version identity, saved History, and evaluation runs

**What is wrong.**

| Section | Identifiers used |
|---|---|
| 5 §5.0 (declared closed enum) | `diagnostician`, `coach`, `revision`, `history_nudge`, `grounded_example`, `generic_example`, interim `planning_hints` |
| 1 §2.1 (directory layout) | `diagnostician/`, `answer_coach/`, `revision_partner/`, `history_nudge/`, `grounded_example/`, `generic_example/` |
| 2 §2.10, §3.9 | `answer-coach@2.0.0+<sha8>`, `revision-partner@2.0.0+<sha8>` |
| 3 §3.4, §3.6 | `history-nudge@1.0.0+<sha8>`, `nudge-generic@1.0.0+<sha8>` |

Section 5 §5.3 declares `specialist` a **closed enum** in the telemetry record. A response stamped `answer-coach@2.0.0+…` (Section 2 §2.4, injected into every review body and therefore into every saved browser History record) is not a member of that enum. Section 3's `nudge-generic` is Section 5's `planning_hints`.

Section 2 additionally starts its version numbering at `2.0.0` ("because the output schema (v3) breaks v2 consumers") while every other section starts at `1.0.0` under Section 1's scheme.

**Why it matters.** These strings are written into member browser storage, log lines, evaluation run records, and `registry.json`. A mismatch is not cosmetic: it breaks the telemetry enum, breaks `registry.json` lookup, and makes an evaluation run unattributable to the specialist it exercised. It is also the cheapest possible fix now and the most expensive one after data exists.

**Correction.** Section 5's list is the canonical enum (it is the one used by the telemetry contract). Section 1's directories rename to match (`coach/`, `revision/`). Section 2 uses `coach@…` / `revision@…`. Section 3 uses `history_nudge@…` and `planning_hints@…`. Either Section 2 drops `2.0.0` or Section 1 §2.2 records the exception and its reason in one line.

---

## BLOCK-4 — Sections 3 and 4 invent their own values for the two spine enums Section 1 declares fixed for all sections

**What is wrong.** Section 1 §0 declares the closed value sets, and §4.6 states they are "shared and fixed by this section":

> - `provenance` ∈ `member_submitted` | `member_confirmed` | `member_selected` | `server_derived` | `external_untrusted`
> - `authorization` ∈ `session_authorized` … | `member_action_authorized` … | `reference_only` … | `not_granted`

Section 3 uses at least eight values that are in neither set:

> §3.4: "provenance `account_history@v<n>`; authorization state `member_selected_consumed` — **the only state the manifest builder accepts for this class**"
> §3.5: "provenance `member_typed_current_practice`, authorization state `member_confirmed_current_practice`"
> §5.2: `"provenance": "member_confirmed_role_context@v3"`, `"authorization_state": "member_confirmed_current"`
> §5.3: `provenance: "client_supplied_unconfirmed"`, `authorization_state: "unconfirmed_untrusted"`

Section 4 §A.1 defines a third vocabulary for the same two fields:

> `provenance enum member_authored | member_imported | owner_fixture`
> `authorization_state enum draft | approved_for_interview_ai | revoked`

Neither section flags this. Section 3 in particular specifies its `source-allowlist` guardian *by* one of these values ("the only state the manifest builder accepts for this class").

**Why it matters.** The source-allowlist and evidence-entitlement guardians are specified as "the builder accepts only manifest entries in state X". If three sections mean three different things by "state", no single builder can implement the check, and the most likely failure mode is a builder that accepts an unrecognised value rather than rejecting it — a fail-open on the package's central control.

**Correction.** One crosswalk table in the consolidated spine. Do not just delete the new values: Section 3's `member_selected_consumed` is genuinely *stronger* than `member_action_authorized` (it means a single-use server row was minted and consumed this request) and deserves to be added to the spine as a fifth authorization state. Section 4's envelope enums are a different axis (they describe an evidence item's lifecycle, not a manifest entry's authorization) and should be renamed to say so — e.g. `evidence_lifecycle_state` — so they stop colliding with the spine field name.

---

## BLOCK-5 — One failure state, four transports; and Section 5 declares its own conflicting table canonical

**What is wrong.** Section 5 §5.0 presents its mapping as the no-variants spine:

> **Failure state → transport mapping** … `unavailable_source` | **503 + `Retry-After`** | workspace-waking copy | Yes — `app.py:3747-3752`

Section 4 §B.3:

> `unavailable_source` (**HTTP 200** — a truthful computed state, not a transport failure; no provider call, no charge, no `contextToken`…)

Section 2 §2.8 uses the same state for two more transports:

> `unavailable_source` | Identity store outage; expired/invalid `router_token` presented | **503 (+`Retry-After: 5`) / 400**

Section 3 §3.3 uses it for a revoked/expired selection with a uniform not-found body and no status named.

`provider_failure` is also split: Section 5 §5.0 moves it to **502**; Section 2 §2.8 keeps **500** (today's actual behavior, `app.py:3983-3985`).

**Why it matters.** `failureState` is being added to response bodies so the client can render distinct, truthful fallbacks. A client cannot branch on a state that arrives as 200, 400, 500, 502, or 503 with four different body shapes, and "retry is meaningful" is exactly opposite between the 503 case (identity store waking) and the 200 case (you have no evidence; retrying can never help — Section 4 says so explicitly).

**Correction.** Section 4's argument is right and should win: a computed, permanent, member-specific absence is not a transport failure. Either (a) give it its own spine state — `source_not_available_for_member` — and leave `unavailable_source` meaning "a source this request needed is temporarily unreachable, 503", or (b) keep one state and make the transport a documented function of a `retryable: bool` field. Pick one, put it in Section 5 §5.0, and have Sections 2, 3, and 4 cite it rather than restate it. Also resolve 500 vs 502 for `provider_failure` — see LOW-3, the stated justification for the change is wrong.

---

## BLOCK-6 — Section 3's account-backed schema is built against the v2 review and cannot store Section 2's v3 review, while claiming to be the storage contract for it

**What is wrong.** Section 2 §2.4 defines a new review contract and says the server injects `reviewVersion: "v3"`. Section 3 §2.3 defines the persistence for reviews:

> `review_generation NVARCHAR(20) NOT NULL CHECK IN ('v2','legacy-v1','local-recording')`

and §4.4: "`review_generation` mapped from the record's `reviewVersion`". The moment Section 2 ships, every new record violates that CHECK constraint.

It is not only the version literal. Section 3's `dbo.interview_reviews` stores:

> `stronger_approach NVARCHAR(900) NULL`

Section 2 §2.4 makes `strongerApproach` an **object** (`steps[]` of `{label, guidance}` plus `whyThisFits`). It does not fit in an `NVARCHAR(900)` column. Section 3's `dbo.interview_review_findings` has `finding_class CHECK IN ('strength','improvement','came_through_clearly')` — with no place for Section 2's `priorityImprovement` (action + why + dimensionKey), `additionalImprovements`, `missingOrContradictory` (kind + detail), `lengthFit` (assessment + evidence), or the server-assembled `basis` block.

Section 3 §2.3 nonetheless asserts:

> Text bounds mirror the browser sanitizer's existing bounds (`sanitizeHistoryRecord`, `interview-studio.js:1908-1967`) so import loses nothing.

True of the v2 shape only. I verified the live shape: the browser record is written with a hardcoded `reviewVersion: 'v2'` at `static/js/interview-studio.js:3170`, alongside flat `improvements`, `strongerApproach` as a string, and no `lengthFit`/`basis`/`priorityImprovement` — exactly matching today's `validate_interview_review` output (`app.py:3446-3457`).

**Why it matters.** The account-backed store is a migration. Getting its column set wrong against a schema change landing in the same architecture means either a second migration immediately, or Section 2's v3 quietly not shipping. Migrations are the most expensive thing here to get wrong.

**Correction.** Section 3's review tables are rewritten against Section 2 §2.4's v3 object, `review_generation` gains `'v3'`, `stronger_approach` becomes a child table or a bounded JSON column with its own set-equality check, and `finding_class` gains the v3 classes. Additionally, name the coupled client site: the browser record's `reviewVersion` is a **hardcoded client literal** independent of the server's injected value — two authorities for one fact — and Section 2's change must update `static/js/interview-studio.js:3170`, not only the server.

---

## BLOCK-7 — The answer-version model is defined twice, incompatibly, and Section 3 calls its version "the storage contract behind Section 2's Revision Partner"

**What is wrong.** Section 3 §2.8 claims ownership of Section 2's model:

> `interview_answer_versions` is the storage contract behind Section 2's Revision Partner…

The two definitions do not agree on anything load-bearing:

| Concern | Section 2 §5.2–5.4 | Section 3 §2.3, §2.8 |
|---|---|---|
| Identity | `versionId`, opaque client-generated (ULID) + `ordinal` | `version_number INT`, `UNIQUE (record_id, version_number)`, no external key |
| Lineage | `parentVersionId` required (R1); **branching** designed | no parent column; `current_version_number INT` presumes one linear chain |
| Origin enum | `member_typed \| member_dictated \| applied_revision \| restored_edit` | `member_original \| member_edit \| ai_revision_accepted \| restored_from_version` |
| Proposals | **R3: "Proposal persistence with status transitions"** — a MUST | no proposal table; "Compare/discard need no storage — discard simply appends nothing" |
| `fromProposalId` | required by R1 | no column |
| Restore | "no new version is minted by restoring itself — a version appears only at the next commitment point" | "restore appends `restored_from_version` copying an earlier version's text forward" |

Four origin values each, zero overlap, no crosswalk. `member_dictated` has no Section 3 equivalent at all, and dictation is a live capability today.

The branching point is the sharpest: Section 2 §5.4 deliberately designs a fork —

> the new version carries `origin: "restored_edit"` with `parentVersionId` pointing at the restored source, so lineage records the true ancestry rather than appearing to fork from the latest version.

— and Section 3's schema cannot represent it.

**Why it matters.** "Original answers and versions are preserved" is frozen product direction. This is the object that implements it, and the package contains two mutually unimplementable definitions, one of which claims to be the other's storage layer.

**Correction.** Section 2 owns the semantics; Section 3 owns the physical schema and rewrites it to carry `version_key UNIQUEIDENTIFIER`, `parent_version_id BIGINT NULL`, `origin` using Section 2's enum, `from_proposal_id`, and a `dbo.interview_revision_proposals` table with the status enum — or Section 2 formally withdraws R3 and the branching design and says why. Do not leave both.

**Verified against the live evidence, in Section 2's favour:** the live browser record is `id, createdAt, mode, question, family, competency, reviewVersion, dimensions, answer, verdict, encouragement, whatCameThroughClearly, strengths, improvements, strongerApproach, focusedFollowUp, context, contextIdentity, sessionContextId, sessionId, experience, attemptNumber, durationSeconds, status` — no version array, no parent lineage, no persisted improve draft. Section 2 §5.5's assessments are **all true**: R1 "(Today: absent — records are flat.)" ✔; R2 "(Today: violated — merge can rewrite `answer`.)" ✔ — `updateHistoryRecord` does `Object.assign({}, record, updates, {createdAt: record.createdAt})` at `static/js/interview-studio.js:1986-1995`, so `answer` is overwritable and only `createdAt` is protected; R3 "(Today: absent — DOM-only.)" ✔; R4's `records.slice(0, 100)` silent eviction ✔ at `:1983`; R6's namespace isolation ✔; R7's local deletion ✔. Section 2 did not overstate its storage claims.

---

## BLOCK-8 — Section 1's release gate and Section 5's slice order block each other; the recommended first slice cannot pass its own build

**What is wrong.** Section 1 §2.4:

> A repository test refuses a `registry.json` that activates any version whose manifest has no accepted evaluation run — release-by-evaluation becomes deterministic, not procedural.

Section 5 §5.7 slice 1 contents include "(e) prompts extracted from inline literals into versioned modules with `<specialist>@<semver>+<prompt-sha8>` identity", and slice 2 is the evaluation harness, which "**Depends on:** slice 1 (identity + telemetry)".

Slice 1 must therefore ship a `registry.json` that activates every specialist, at a time when no evaluation run can exist for any of them, into a build that fails on exactly that condition. The gate can only be satisfied by waiving it on first use — and a gate waived on first use is not deterministic.

A second circularity in the same rollout: slice 3's contents include "the digit screen (grounded first, false-positive rate measured in slice 2 before any extension)" while slice 3 "**Depends on:** slice 2 (measured digit-screen behavior)". Slice 2 cannot measure a control that slice 3 builds.

**Why it matters.** This is the recommended first slice, and Section 5 argues persuasively that everything else depends on it. A blocked slice 1 blocks the package.

**Correction.**
1. Section 1 §2.4's test asserts the binding for any version that *has* a predecessor, and permits an initial release whose manifest records `evaluation_runs: []` with an explicit `"initial_extraction": true` flag — or slice 1 ships the versioning machinery with the activation test skipped by a recorded, dated exception and slice 2 turns it on. Either is fine; silence is not.
2. Slice 3's digit screen is built as an **offline analyzer inside slice 2's harness** (it costs nothing — it runs against recorded outputs) and promoted to runtime enforcement in slice 3. Restate both slices accordingly.
3. **Flag for Pete, not a defect:** Section 1 §2.2 ("even a patch reruns its evaluation slice") combined with Section 5 §5.2(5) and §5.4 ("every paid bake-off call happens … under Pete's explicit in-session spend approval") means every prompt typo fix requires an owner spend approval. That may well be the right rule, but it should be an accepted decision rather than an emergent consequence.

---

## BLOCK-9 — Section 4 reinstates the timer the whole package is retiring, inside the design that retires it

**What is wrong.** Section 1 §3.3 fixes the band as seconds-free:

> `length_band` (exactly one): `brief` | `standard` | `extended`, **with `length_reasons` mandatory**… No seconds appear anywhere in the schema or any prompt.

and its constitution C9 says: "Never justify length feedback by a timer; justify it by missing or excessive content."

Section 4 §6 proposes:

> ```json
> "length_band": {"seconds_low": 30, "seconds_high": 60, "class": "factual", "reasons": [...]}
> ```
> Both specialist prompts render a **server-built** length line from that band — e.g. `Length: aim for about 30-60 seconds spoken (factual question needs a direct response); shorter is fine when every obligation is met.`

and repeats seconds in its response provenance block (§C.1: `"lengthBand": {"seconds_low": 45, "seconds_high": 75, …}`).

Section 4's own no-regression guardrail cannot catch this: it is specified as "a unit test asserts no Interview specialist prompt **template** contains a hardcoded seconds range (regex `\d+\s*[-–]\s*\d+\s*second`)". A server-built line assembled at request time from `seconds_low`/`seconds_high` never appears in a template. The defect class returns through the exact hole the test leaves.

Section 2 §3.5 adds a **third** band vocabulary — `brief_direct`, `standard_structured`, `extended_reasoning`, `boundary_first` — which also folds Section 1's `response_posture` value `boundary_first` into the *length* enum, making "how long should this be" and "should you answer at all" the same field.

**Why it matters against the live evidence.** Improve returned a 111-word draft (~50 seconds) under a prompt demanding a "60-120 second spoken answer". The universal-length instruction is present in the deployed artifact (verified: `app.py:4067`, `:4309`, `:4324`) and **is not reliably obeyed**. That does not falsify any section's claim — no section claims the rule is obeyed, and all three describe it correctly as "present in the deployed artifact" — but it does mean a server-built seconds line is the same weak instrument, and it will not deliver adherence either. Replacing an unreliable universal timer with an unreliable per-question timer is not the accepted direction.

**Correction.**
1. Adopt Section 1 §3.3's seconds-free enum verbatim. Delete `seconds_low`/`seconds_high` from Section 4 §6 and from its provenance block.
2. Section 2 §3.5 drops its parallel vocabulary and removes `boundary_first` from anything length-shaped — it is a posture, and Section 1 already has it as one.
3. Keep Section 1's rule that any speaking-time figure is **UI-computed from word count with a disclosed words-per-minute assumption, presented as an estimate, never a quality signal** — that is the only place seconds belong.
4. Extend the no-literal test to the **rendered** system prompt string, not only the template file, so a runtime-assembled seconds range fails too.
5. Section 2's formulation is the honest one and should be shared: "Band adherence is **not** a validator rejection… Band fit is measured in the evaluation slice." No section may describe adaptive length as achieved by prompt wording.

---

## BLOCK-10 — The package's most privacy-critical interlock is assigned to a section that does not define it

**What is wrong.** Section 3 §11.1 states the dependency plainly:

> **Section 1 (Constitution/platform)** owns the single provider call site, the knowledge-manifest builder… this section's evidence-entitlement rule (selection row → `history_selection` manifest entry) must be enforced *there*, at the call site, or the two-step boundary has a bypass.

Section 1 does not define it. `history_selection` appears in Section 1 only as a source-class name (§0), as explicitly absent from the Router (§3.2), and as somebody else's problem (§4.4: "the Nudge receives the router result like any specialist but runs its own retrieval under its own manifest"). Section 1's §1.4 source-allowlist row covers the four existing endpoints' builder signatures only.

Section 5 guardian 5 covers the **output** side only:

> **Extension:** the same id-allowlist mechanism covers `history_selection` ids when the History Nudge ships…

That is checking ids cited in a reply. It is not the input-side rule that full prior-answer content may only enter provider context when a single-use selection row was consumed in this request.

So the rule exists as one sentence inside Section 3 §3.3 ("Only the procedure's returned content — question, metadata, the pinned answer version text — is placed into the prompt") with no owner outside Section 3 and no test outside Section 3's own P3 list.

**Why it matters.** This is the rule that makes the entire two-step nudge boundary meaningful. Everything else in Section 3 — the selection table, the expiry, the single-use flag, the consumption re-check — is worthless if some other code path can put History content into a prompt without a consumed selection. The package's own standing rule is that privacy must not rest on prompt wording alone; here it currently rests on a sentence in a section that disclaims ownership of the call site.

**Correction.** Section 5 §5.1 guardian 3 gains an explicit named sub-rule, since Section 5 owns the guardian mechanism:

> `history_selection` is the only source class whose builder parameter may not be populated from request data at all. The parameter accepts exactly the tuple returned by `usp_ConsumeInterviewHistorySelectionForOwner` in this request. A unit test asserts the builder raises when handed a `history_selection` value that did not come from a consumption call, and a second asserts no request field can reach it.

Section 3 §11.1 then cites Section 5, not Section 1. Section 1 adds one line disclaiming ownership so the gap cannot re-open.

---

# High findings

## HIGH-1 — Section 5's digit screen validates against a source class Section 4 forbids that specialist

Section 5 §5.1 guardian 6(5): every digit-bearing token in a `grounded_example` answer

> must appear as a substring of the authorized support text for that call — the concatenation of the question, the cited evidence items' text, and `confirmed_context`.

Section 4 §C.1 input manifest: `confirmed_context` — **No** — "Belongs to the Revision Partner's flow, not 5A".

A guardian cannot validate against a source the specialist is structurally forbidden to receive; the support set would always be missing a term the screen expects, or the screen forces the forbidden class into the manifest.

**Correction.** For `grounded_example`, the support set is question + cited evidence text. `confirmed_context` and the member's own `answer` join it only when the screen extends to `revision`, which Section 5 already defers.

## HIGH-2 — Sections 1 and 2 give opposite answers to "what happens when there is no router token"

Section 1 §3.1: "When a request arrives without a valid `router_token` (§3.6), the endpoint routes first, then runs its own specialist, and returns both." §3.6: "Any mismatch or expiry silently re-routes; it never errors at the member."

Section 2 §2.3(3): "When no valid `router_token` is presented (Router not yet shipped, token expired, or Router output was rejected by its own validator), the coach falls back to today's behavior… **The fallback is deterministic — no second provider call.**" §2.8: expired token produces member-visible copy; a tampered token is rejected **400**.

One says always route (an extra provider call and its latency at the start of every chain); the other says never route without a token. A 400 on a tampered token also contradicts "never errors at the member", and is a small oracle besides.

**Correction.** Pick Section 1's route-on-absence as the target state and Section 2's deterministic fallback as the explicit pre-slice-4 interim, labelled as such in both. Make tampered-token handling identical to expired-token handling (silently re-route or silently fall back) — there is no member-useful difference between the two, and no reason to tell a caller which one happened.

## HIGH-3 — Section 2 consumes a Router field Section 1 does not define, and never answers the constraint Section 1 bound it to

Section 2 §2.2 requires the token carry `dimension_keys` ("`dimension_keys` must be a subset of the server dimension registry") and §2.3(1) says "The Router **selects** 3–6 keys from the registry for the actual question". Section 1 §3.3's Router schema contains no such field — it emits `listening_criteria` (free strings, 2–6, ≤120 chars) and `question_class`, with `rubric_family` **server-stamped, never model-emitted**.

Worse, Section 1 §4.2 binds Section 2 to something Section 2 never addresses:

> **Section 2:** `rubric_family` can be `null` (`factual_direct`, `ambiguous`). The Answer Coach contract must define a null-rubric review (obligations-driven) and must not fall back to the behavioral dimension set.

Section 2 never uses the term `rubric_family`, never defines a null-rubric review, and its only fallback is `_normalize_interview_family` — which I verified maps every unrecognised value to `'behavioral'` (`app.py:3329-3337`). That is exactly the default Section 1 forbade.

**Correction.** Either Section 1 adds `dimension_keys` to the Router output (model-selected, membership-validated against the closed registry — which is compatible with its design) or Section 2 derives the keys server-side from `question_class` + `response_obligations`. Separately, Section 2 must add the null-rubric review contract, or Section 1 must withdraw the constraint.

## HIGH-4 — Section 3 restates Section 4's central distinction backwards while believing it is agreeing

Section 3 §11.3:

> **Section 4 (Examples)**: `insufficient_evidence` stays the Grounded Example's state for missing `member_evidence`…

Section 4 §B.2 says missing member evidence is specifically **not** `insufficient_evidence` — that is `unavailable_source` — and calls collapsing the two a truthfulness failure. Section 3 wrote this as a cross-section agreement.

**Correction.** Section 3 §11.3 becomes: "`insufficient_evidence` is the Grounded Example's state for evidence that exists and cannot carry the question. Capability absence is `unavailable_source` (Section 4 §B.2). The nudge's `no_history_match` is distinct from both." The last clause is already correct and should stay.

## HIGH-5 — Slice 1 is described as "zero new surface area" while its own contents add response fields, a config flag, and a UI state

Section 5 §5.7 slice 1: "**Rollback:** one revert — no new endpoint, schema field, data store, flag, or UI dependency" and "**Why this is the smallest safe first slice:** … with zero new surface area".

Its own contents contradict this:
- (g) the insufficient-evidence short-circuit, which per Section 4 §B.3 adds `failureState`, a `capability` object, and `nextActions` to the response, and removes `contextToken` from one path — all schema fields.
- Section 2 §2.8: "Response bodies gain an additive `failureState` field from the shared enum so the client can render distinct, truthful fallbacks."
- Section 4 CR-10 adds server configuration `INTERVIEW_MEMBER_EVIDENCE` (default off) — a flag.
- The `unavailable_source` copy needs a UI state that does not exist: today's panel is a static template block (`templates/interview_studio.html:1001`) driven by `setAiState('insufficient')` and `[data-is-ai-insufficient]` (`static/js/interview-studio.js:3751`, `:3800`).

**Correction.** Restate slice 1 truthfully — new response fields, one flag, one new UI state, rollback = revert plus flag off — or move the short-circuit and capability work into slice 3 and keep slice 1 genuinely server-internal. The rest of slice 1's argument (five confirmed gaps, offline-testable, single revert) is strong and survives either choice.

## HIGH-6 — `confirmed_context` carries two different caps

Section 2 §3.2 binds it to today's `additional_context` at ≤1,200 chars (matches `app.py`'s existing bound). Section 3 §3.5 defines the add-detail path as "bounded at 2,000 UTF-16 units". Same source class, same member action, two `content-bounds` values — and `content-bounds` is a named deterministic guardian, so the discrepancy is a real ambiguity in a control, not a doc nit.

**Correction.** Use 1,200 (today's, no code change) or state the raise once with a reason and update both.

## HIGH-7 — The generic nudge's "no History" property is described as a property of its prompt

Section 3 §3.6:

> `POST /api/interview/nudge` … remains exactly what it is — generic planning hints with **no** History access, its prompt's history prohibition now load-bearing rather than ironic…

Once specialist 4 exists in the same process, this path's safety cannot rest on a prompt sentence — that is precisely the rule this package exists to enforce. The deterministic control does exist today (I verified `interview_nudge()` resolves no evidence and no history at all, `app.py:4118-4200`; it does not even look up a profile when authenticated), but Section 3 names the prompt rather than the structure.

**Correction.** Replace with: "the generic nudge's context builder has no `history_selection` or `member_evidence` parameter; a unit test asserts the builder's signature and that its rendered content contains neither class. The prompt sentence is a quality instrument, not the boundary."

## HIGH-8 — Three claims say "proven", "true by construction", or "structurally impossible" about things that are not yet built or not owned here

1. Section 3 §6 claim 5: "Deleting a record removes it from every index, cache, and AI eligibility | … **proven by P1–P4, not asserted**". P1–P4 are designed artifacts that do not exist. → "provable by P1–P4 once built; unproven until then."
2. Section 3 §2.2: "There is **no server-side cache of History content anywhere** — request-scoped memory only — so 'removed from every cache' is true by construction and stated as such, not enforced by a purge job that could fail." Nothing enforces it. P4 checks result-set field shape, not memoization. A single `@lru_cache` added later to a read helper silently breaks the revocation guarantee with no test failing. → either name a CI control (an assertion that no History read path is memoized and no module-level container retains record content) or downgrade to "an invariant maintained by review, with no automated detector — labelled residual".
3. Section 4 CR-7: "**Cross-member retrieval is structurally impossible.** The provider-side query is scoped `member_key == identity.user_key`". That describes Profile's future query, which this package does not own. → "is a contract requirement on the provider side, verified by the CR-7 negative test named in A.4(3); this package cannot guarantee it."

These matter because the package's credibility rests on the distinction between confirmed and designed, and the errata was returned for exactly this class of error.

## HIGH-9 — The provider budgets are presented as measured; the cited source shows chosen constants

Section 5 §5.2 table basis column: "Ask Pete **proves** 30 s covers up to 3,000 output tokens **live** (`provider.py:46`, `:63`)", and §5.8(2): "The only **measured** internal datum is Ask Pete's 30 s / 3,000-token bound."

I read both lines. `PROVIDER_TIMEOUT_SECONDS = 30.0` is chosen because the browser aborts at 45 s and "the server has to give up first" — a budget derived from a client abort, not a latency measurement. `DEFAULT_MAXIMUM_OUTPUT_TOKENS = 3_000` was raised from 1,600 because a real run truncated mid-array — evidence about a token *ceiling*, not about how long a 3,000-token generation takes. Nothing at either line measures latency at that ceiling.

**Correction.** "The budgets are engineering choices derived from Ask Pete's browser-abort budget and its token ceiling; no Interview latency distribution exists until slice 1's telemetry runs." Section 5.8(2) is one word away from this already — delete "proves" and "measured datum". The numbers themselves are sensible and should not change.

---

# Medium findings

## MED-1 — `compare` is decided in one section and declared an open owner question in another

Section 4 §C.3: "**Compare mode — decision: it survives, as composition, not as a specialist**". Section 5 §5.7 "Deliberately out of scope": "the `compare` mode's product fate (owner decisions, surfaced not made)" — while Section 5 §5.2's own table budgets a "`compare` route total … **45 s** route budget". Section 1 §4.5 flagged it to "Sections 4/5" and got two answers.

**Correction.** Section 4's engineering design is sound and should be recorded as designed-and-retained. The only genuinely open owner question is whether the product keeps the feature; state that narrowly in Section 5 instead of putting the whole thing out of scope.

## MED-2 — Section 2's improve schema drops a live field while claiming it removes nothing

Section 2 §3.3: "Validator rules, all deterministic, extending `validate_interview_improvement` (`app.py:3675`) **without removing anything it does today**." Today's validator requires `changes` (non-empty, ≤4) and returns it (`app.py:3679`, `:3684`, `:3701-3705`), and the deployed client renders it (`static/js/interview-studio.js:3365`, `renderList(one('[data-is-changes]'), payload.improvement.changes)`). Section 2's v2 schema has no `changes` — `changeLedger` replaces it.

Also worth correcting in the same paragraph: unlike `validate_interview_review`, today's `validate_interview_improvement` has **no** field-set equality check. Section 2 §3.6's prohibited-action row ("validator field-set equality blocks any model-emitted action field") describes a **new** control for this endpoint, not a preserved one. It is a good addition; it should be labelled as one.

## MED-3 — Section 1 states an untested behavior as a current fact

Section 1 §1.1: "So a member **can, today, receive** a hiring prediction from the nudge endpoint without any instruction against it — only the output validator's narrowness limits the damage."

The prompt's silence is verified (I read it: `app.py:4159-4167` forbids example answers, invented stories, specific outcomes, and profile history — it does not forbid a score or prediction). The *behavior* was never tested, and today's live nudge returned ordinary generic hints.

**Correction.** "The nudge prompt contains no prohibition against a score, ranking, or hiring prediction, and its validator bounds only shape and length (`{"hints":[…]}`, ≤240 chars each). Whether the model would emit one is untested."

## MED-4 — The failure-reason registry is fragmented across four sections while being declared a closed enum

Section 5 §5.3 declares `guardian_reason` a closed enum and lists the extension set as `truncated`, `unsupported_numeric_claim`, `unexpected_link`. Sections 1, 2, and 3 mint at least eleven more: `router_invented_subpart`, `invalid_router_shape`, `router_token_invalid`, `coach_token_invalid`, `incomplete_priority_improvement`, `invalid_missing_entry`, `invalid_length_fit`, `invalid_stronger_approach`, `invalid_change_ledger`, `unsupported_ledger_anchor`, `unaccounted_evidence_use`.

**Correction.** One appendix listing every reason code with its owning section and its fixed-literal validator message. Section 5's table cites the appendix instead of enumerating a partial set. (The underlying discipline is right — I verified today's `INTERVIEW_FAILURE_REASONS` is a closed literal map at `app.py:3771-3807` and every validator `raise` uses a fixed string.)

## MED-5 — "Release-by-evaluation becomes deterministic" overstates what a file test can do

Section 1 §2.4. The test can assert that `evaluation_runs` is non-empty and that `sha8` recomputes. Whether a run is *accepted* is a human judgment recorded in JSON — the test cannot verify the judgment, only its presence.

**Correction.** "makes recording an accepted evaluation run a mechanical precondition of activation; acceptance itself remains a human decision." This is still a real and valuable control — just not a deterministic quality gate.

## MED-6 — The session-free invariant is addressed by no section, and two live fields look like the object it forbids

Frozen direction: "the product is session-free with no Interview Session object". The live History record carries `sessionId`, `sessionContextId`, and `contextIdentity` (verified at `static/js/interview-studio.js:3186-3191`). No section states the invariant, and none dispositions those fields. Section 3's import maps only the fields it names, so they would be silently dropped — plausibly the right answer, but unstated. Section 2 §5.1 meanwhile leans on `sessionId` as part of today's implicit linkage ("loosely linked by question text + `sessionId` + `attemptNumber`").

**Correction.** Section 3 §4.4 states the disposition explicitly: browser `sessionId`/`sessionContextId`/`contextIdentity` are not imported as identity; the question digest plus record key replace them; no server-side Interview Session object is created. Section 2 stops describing `sessionId` as linkage the version model relies on.

## MED-7 — Section 2's "nothing the member typed is ever overwritten without a preserved copy" is defeated by Section 3's save refusal

Section 2 §5.4 makes the snapshot-before-replacement rule absolute, and R5 requires it be atomic enough that "a crash between snapshot and replacement loses nothing (write snapshot first, then replace)". Section 3 §2.4 makes the save procedure refuse in two of three modes:

> `usp_SaveInterviewHistoryRecordForOwner` refuses unless the request is an explicit member save action, or `saving_mode = 'save_to_account'` **and** `disclosure_acknowledged_at_utc` is set.

A refused snapshot mid-Apply leaves the composer replaced with nothing preserved.

**Correction.** Section 2 states that the snapshot is written to whichever store is active for this member (browser store under `undecided`/`session_only`), and that Apply **fails closed** — no replacement if the snapshot write returns false. Today's client already returns real write outcomes for exactly this reason (`addHistoryRecord`/`updateHistoryRecord` return the write result, `static/js/interview-studio.js:1980-1995`, with the deliberate comment about not claiming a save that did not happen). Build on that; do not lose it.

## MED-8 — Section 3 attributes a general untrusted-content envelope to Section 1, which scopes it to role context only

Section 3 §3.3: the prior answer is placed in the prompt "inside Section 1's shared untrusted-content envelope". Section 1 uses `_untrusted_opportunity_block` for `role_context` only (§3.2 row 2, §1.4) and never defines an envelope for `answer` or `history_selection`. Section 5 guardian 4(1) does define the general rule ("untrusted classes … appear only in user-turn envelope blocks, never in the system instruction… becomes a builder invariant with a test").

**Correction.** Section 5 owns the generalization; Section 3 cites Section 5; Section 1 adds one line saying the envelope it inherits is role-context-scoped and the general rule is Section 5's.

---

# Low findings

## LOW-1 — Section 1 declares a binding interface change that Section 2 neither accepts nor refuses

Section 1 §3.7: "**`competency` specifically:** … it stops being interpolated into downstream system prompts… This closes a small untracked injection surface as a side effect and is **a binding interface change for Section 2**." Section 2's coach manifest (§2.2) does not list `competency` at all — not as accepted, not as rejected. One line needed either way. (The current interpolation is real: `competency` is a free ≤80-char member string dropped straight into the review system prompt at `app.py:3929-3930`.)

## LOW-2 — Section 4's reconciliation items are one-directional and must be treated as requests

Section 4 §9: "**The other consolidated sections (1, 2, 3, 5) were not readable from this worktree at writing time**; spine adherence here is by specification". Honest and correctly labelled — but it means every "consumed requirement" Section 4 places on Sections 1/2/3/5 is unagreed. The consolidation should walk that list explicitly rather than assume the other authors saw it.

## LOW-3 — The stated reason for moving `provider_failure` from 500 to 502 is wrong

Section 5 §5.0: "Partial — today an unexpected exception returns 500; moving to 502 keeps the client's announced single retry working (`interview-studio.js:1872` retries 500/502/503)". I read it: `postReviewWithOneRetry` already accepts **500**, 502, and 503 (`static/js/interview-studio.js:1870-1878`), so the retry works unchanged either way. The move may still be right — 502 is more truthful for an upstream failure — but the justification given is false, and Section 2 §2.8 keeps 500. Pick one and give the real reason.

## LOW-4 — A second, smaller instance of the collapse Section 4 warns about

Section 3 §3.3 and §7 use `insufficient_evidence` for "text-free record selected". Under Section 4's rule that state means the source was consulted and cannot carry the question; an empty record was never consultable. It may also be unreachable — Section 3's step-1 response already carries `"selectable": false` for text-free records — in which case say so and delete the state from that row.

---

# What is genuinely good and must survive consolidation

These are not consolation prizes. Several of them are better than what I expected to find, and a merge that damages them makes the package worse.

1. **The code citations are accurate.** I spot-checked roughly twenty-five line references across all five sections against this worktree and every one was correct or within a line or two: owner-only evidence (`app.py:1972-1985`), the base64 envelope (`:3356`), field-set equality (`:3422`), score rejection (`:3411-3412`, `:3472-3473`), the three evidence allowlists (`:3529`, `:3580-3581`, `:3688-3689`), the marker pattern and its P2-1/P2-2 comment (`:3661-3672`), the `attempt >= 2` review gate (`:3889-3900`), the server-side follow-up refusal (`:4249-4250`), `_log_interview_failure`'s `detail=%s` hole (`:3834`), the three 60–120s literals (`:4067`, `:4309`, `:4324`), `records.slice(0, 100)` (`interview-studio.js:1983`), the merge mutator (`:1986-1995`), `removeHistoryRecord` (`:1997`), the scoped bulk clear (`:5140-5157`), the announced single retry (`:1870-1878`), `bindingStillCurrent` (`:2089-2096`), the opaque storage scope (`app.py:2009-2011`), the Ask Pete bounded client (`provider.py:174-192`), `anthropic==0.112.0`, exactly 306 test functions, and `response.usage` read nowhere in `app.py`. For five documents written in parallel without provider access, that is unusually disciplined. Do not "tidy" these citations.

2. **The errata is respected everywhere, including E4.** No section designs deletion from nothing. Section 3 §2.1 integrates with the existing affordances, Section 2 §5.4 does, and Section 5 §5.5 makes it a standing rule. The live evidence confirms both affordances work (per-record "Delete this browser record" with its confirm, and bulk "Clear local History"). If consolidation reintroduces "deletion must be built", it has regressed.

3. **Section 3's two-step nudge boundary is the strongest privacy design in the package.** Provider-free candidate search returning a precomputed ≤280-unit excerpt; a server-minted, single-use, expiring, purpose-bound selection row; consumption re-reading the *authoritative* record rather than trusting the projection; and — the best single idea in the five documents — **P4**, the set-equality row check that turns a future widening of the step-1 result set into a loud production failure rather than a silent over-disclosure. Also keep "the request body cannot carry History content at all… The browser is a keyring here, never a courier."

4. **Section 4's evidence contract.** One access function, the owner fixture expressed *inside* the contract, and the explicit rule "**No `is_owner` branch may exist anywhere downstream of this function**" — that is the correct lesson from the current code, where the branch is the only thing standing between a member and Pete's fixture. Capability derived from the retrieval result rather than a stored flag is right for the same reason. So is refusing to issue a `contextToken` on a non-answer.

5. **Section 4's compare-isolation elevation.** Turning `app.py:4359-4369`'s comment into a named guardian with a construction test, and the reasoning for why it is needed: "the map guards the citation channel, and only strict input separation guards the prose channel." I verified the control is real and correct in code. This is the one leak the empty evidence map genuinely cannot catch.

6. **Section 5's `planning_hints` interim identifier.** "This prevents any metric or run record from ever claiming specialist 4 exists before it does." The live evidence confirms the nudge is generic — hints contained no trace of the member's immediately prior answer — so this is exactly right, and it is the kind of honesty that is easy to lose in a merge.

7. **Section 5's E3 closure.** The bounded summary formatter that never calls `str(error)`, the allowlisted `detail` keyed to the closed literal set, and the sentinel tests. The hole is real in code (`detail=%s` formats the raw exception at `app.py:3834`) and this is the correct shape of fix, including the rejection of denylist scrubbing.

8. **Every section labels the E2 injection limit honestly.** Not one claims the base64 envelope is a deterministic anti-injection guarantee. Section 5's reframing — injection cannot be prevented, so make a successful injection worthless — is the right posture, and its four legs are the right four.

9. **Nobody invented a launch threshold.** Five authors, and all five held the line: Section 5 §5.4 reserves every threshold for Pete on a decision sheet, Section 1 §3.8, Section 2 §2.9, Section 3 §8, and Section 4 all say measures-not-thresholds. That discipline survived parallel authorship and should be protected in the merge.

10. **Section 2's treatment of the bracket-marker contract.** Keeping it verbatim, naming its four coupled sites as one versioned contract (`marker-contract/1`), and specifying a round-trip drift test that fails if any of the four drifts. The existing control is narrow *by construction* and the comment at `app.py:3661-3672` explains why; Section 2 read that and built on it instead of redesigning it. That is the right instinct throughout this package.

---

*End of independent review. Section files 10–14 were not modified. No branch, commit, or PR was created. No provider call was made under this review.*
