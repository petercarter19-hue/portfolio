# Section 2 — Answer Coach and Revision Partner

**Package:** `PS-INTERVIEW-AI-ARCHITECTURE-001`
**Gate:** B, increment 2 of 5 (Answer Coach and Revision Partner).
**Status:** Proposed architecture for Pete and Codex review. Documentation only. No
application, prompt, schema, test, configuration, or live behavior is changed by this
file.
**Evidence base:** source read at the Gate A diagnosed SHA `f7a71739`, which errata E6/D3
confirmed byte-identical to the deployed application SHA `f42e5399` for both Interview
files. Line references below therefore describe production, not a drifted snapshot.
**Reads first:** [`02_GATE_A_ERRATA.md`](02_GATE_A_ERRATA.md) overrides
[`01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md`](01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md)
wherever they disagree; both override any summary in this file.

This section designs two specialists and the answer data model they share:

- **Specialist 2 — `answer-coach`** evolves today's `POST /api/interview/review`
  (`app.py:3838-3985`, validator `app.py:3402-3538`).
- **Specialist 3 — `revision-partner`** evolves today's `POST /api/interview/improve`
  (`app.py:3987-4110`, validator `app.py:3675-3706`, marker pattern `app.py:3661-3672`).
- **The Answer Version Model** — version identity, lineage, apply/compare/discard/
  restore semantics — which both specialists and Section 3's History depend on.

It uses the shared spine exactly as defined for all sections: the six source classes
(`question`, `answer`, `role_context`, `member_evidence`, `history_selection`,
`confirmed_context`), the twelve-guardian taxonomy, the seven failure states, and the
specialist documentation shape (purpose / input manifest / output schema / deterministic
guardians / failure behaviour / evaluation slice / version identity).

---

## 1. What already works and is kept, not replaced

The single most important design statement in this section: **the existing validators
are genuinely strict, and this architecture extends them rather than replacing them.**
Concretely, the following live constructions are preserved as the foundation:

1. **Exact-field-set rejection.** `validate_interview_review` refuses any reply whose
   top-level keys are not exactly the contract (`set(raw) != expected_fields`,
   `app.py:3422`), and the same idiom applies per dimension (`app.py:3474`) and per
   evidence suggestion (`app.py:3514`). This is the real deterministic backstop against
   a manipulated model: even a fully injected model cannot add fields, scores, links,
   or actions and still be rendered. Every schema in this section is enforced the same
   way.
2. **Score prohibition as a validator rule**, not a prompt request (`app.py:3411-3412`,
   `:3472-3473`).
3. **Evidence entitlement as an ID allowlist** — `'review referenced unauthorized
   evidence'` (`app.py:3529-3530`) and `'improvement referenced unauthorized evidence'`
   (`app.py:3688-3689`), with duplicate rejection. This is already the
   `evidence-entitlement` guardian the spine requires.
4. **The never-read `profile_slug` guard** (`app.py:3872-3877`, `:4020-4022`): on the
   authenticated surface the client field is never assigned to a variable. Identity is
   server-derived through `_interview_api_authenticated_identity()` (`app.py:3730`),
   which returns JSON 401 / 503 with `Cache-Control: private, no-store`.
5. **The bracket-marker contract and its server-side guard** — kept in full; section
   3.4 below builds on it and explains why.
6. **Content-free failure logging** — `_log_interview_failure()` (`app.py:3821`) with
   the low-cardinality `INTERVIEW_FAILURE_REASONS` map (`app.py:3771`). Every new
   validator `raise` in this design uses a fixed string literal and adds a mapped
   reason code, preserving that property.
7. **The signed-context pattern** — `interview_context_serializer`
   (`URLSafeTimedSerializer`, `app.py:159`), 30-minute max age
   (`INTERVIEW_CONTEXT_MAX_AGE_SECONDS`, `app.py:155`), digest binding via
   `hmac.compare_digest` (`app.py:4257`). Reused for the two new signed tokens below
   with their own salts.
8. **`_extract_json_object`'s duplicate-JSON-field rejection** (`app.py:3719-3724`),
   `_strip_md` markdown stripping (`app.py:3389`), `_string_list` bounds
   (`app.py:3394`), the untrusted opportunity envelope `_untrusted_opportunity_block`
   (`app.py:3356-3379`, with errata E2's honest limit: it is provenance labelling and
   delimiter protection, not a deterministic anti-injection guarantee), and
   `_cross_site_refusal('interview')`.
9. **Client-side work preservation on failure** — the review error path restores the
   editable answer and announces without clearing anything
   (`static/js/interview-studio.js:3206-3214`); the improve error path announces
   "Your original answer is unchanged" (`:3012`). This behavior becomes a stated
   requirement rather than an incidental property.

What changes is scoped and named: the Router replaces the client-supplied `family` as
the authority for dimensions and length; the review schema is restructured where the
diagnosis (11.9) showed prose blobs; the improve output gains a source-aware change
ledger; the improve prompt loses the 60–120 second literal (errata E6); and the answer
version model makes "preserved original and versions" a data contract instead of a UI
habit.

---

## 2. Specialist 2 — `answer-coach`

### 2.1 Purpose

Review the member's submitted answer against the actual question. Name what the answer
actually said, what worked, what is missing or contradictory, how well the length fits
this question's obligations, and **one proportionate priority improvement**. It proposes
coaching; it never rewrites the answer (that is `revision-partner`'s job, and the coach
schema deterministically has no field a rewrite could travel in), never scores, and
never saves anything as canonical truth.

### 2.2 Input manifest

| Input | Source class | Provenance | Authorization state | Deterministic bound |
|---|---|---|---|---|
| `question` | `question` | Client-typed or Studio question bank | Member-authored this request | Required, ≤300 chars (`MAX_INTERVIEW_QUESTION_LENGTH`, `app.py:143`) |
| `answer` | `answer` | The exact submitted answer version (see version model, section 5) | Member-authored this request | Required, ≤5,000 chars (`app.py:142`); marker gate on revisions (section 3.4) |
| `router_token` | system artifact (server-authored) | Signed RouterResult issued by Section 1's Diagnostician/Router | Server-signed; verified signature + age + question digest | itsdangerous signature, 30-min age, `question_digest` must equal SHA-256 of the submitted normalized question; `dimension_keys` must be a subset of the server dimension registry |
| `family` | UI hint (non-authoritative) | Client | Untrusted hint only | Normalized to closed enum by `_normalize_interview_family` (`app.py:3329`); used only in the fallback path of 2.3 |
| `level` | UI hint | Client | Untrusted hint | Closed enum (`entry/experienced/management/leadership/mixed`, `app.py:3901`) |
| `attempt` | UX truth | Client | Advisory (comment at `app.py:3863-3871` preserved verbatim) | Bounded int 1–1000, defaults to 1 — failure can only widen, never narrow |
| `role_context` | `role_context` | PS-INTERVIEW-ROLE-CONTEXT-001 confirmed context when it exists; today `opportunity_context` | Member explicitly attached; untrusted content | ≤4,000 chars (`_bounded_opportunity_context`), base64 envelope (`_untrusted_opportunity_block`), digest-bindable |
| member evidence | `member_evidence` | Server-derived from identity via `_interview_identity_evidence_context()` (`app.py:1972`) — never client-supplied | Authorized by identity; empty for non-owners today (G2) | Allowlist by ID enforced in validator; nothing client-supplied is read |
| identity | — | `get_current_identity()` server-side | Required on the authenticated surface | JSON 401/503 refusal before any other work (`app.py:3730-3753`) |

**Strict request manifest (new):** the endpoint rejects unknown top-level request keys
with HTTP 400 `'unexpected interview request fields'`. Today extras are silently
ignored; rejecting them is a cheap `source-allowlist` guardian that catches contract
drift and stops fields being smuggled toward future prompt construction.

`history_selection` and `confirmed_context` are **not** in the coach's allowlist. A
prior answer or extra member fact reaches coaching only by the member putting it in the
answer itself, or through `revision-partner`'s `confirmed_context` input. This is the
accepted specialist-2 boundary ("only the small source projection explicitly authorized
for the review").

### 2.3 From client `family` to Router classification

Today `INTERVIEW_FAMILY_DIMENSIONS` (`app.py:3317-3324`) is a fixed six-family map keyed
off the client-normalized `family`, and the prompt tells the model to use exactly those
keys (`app.py:3923`, `:3947`). The client is therefore the authority for which
dimensions the member is coached on. With Section 1's Router classifying the real
question, authority moves server-side:

1. **The dimension vocabulary stays a closed server-side registry.** The existing
   family map's 24 distinct keys become the seed of `INTERVIEW_DIMENSION_REGISTRY`, a
   superset registry of allowed dimension keys with member-facing labels. The Router
   **selects** 3–6 keys from the registry for the actual question; it can never mint a
   key. `validate_interview_review`'s signature changes from `(raw, family, ...)` to
   `(raw, dimension_keys, ...)`: the same membership, uniqueness, completeness, and
   ordering enforcement (`app.py:3460-3502`) now runs against the Router-selected
   tuple instead of the family tuple. The validator's logic is unchanged; only the
   source of the allowed tuple changes.
2. **The RouterResult arrives as a server-signed token** (`router_token`), issued when
   the Router ran, carried by the client, and verified deterministically at review
   time: signature, 30-minute age, `question_digest` equal to the submitted question's
   SHA-256, `dimension_keys ⊆ registry`, `length_band` in the closed band enum. A
   client cannot alter, forge, or replay it against a different question. This reuses
   the proven `_sign_interview_model_context` / `_load_interview_model_context`
   construction (`app.py:3590-3646`) with salt
   `peerslate-interview-router-result-v1`.
3. **Deterministic fallback, truthfully labelled.** When no valid `router_token` is
   presented (Router not yet shipped, token expired, or Router output was rejected by
   its own validator), the coach falls back to today's behavior: normalized `family`
   hint → fixed family map. The response then carries
   `basis.dimensionBasis: "family_fallback"` instead of `"router"`, and no
   `lengthBand`. This keeps coaching useful when the Router is unavailable (the
   AI-unavailable-behavior invariant) without pretending a classification happened.
   The fallback is deterministic — no second provider call.

The `basis` object (see 2.4) is **server-assembled after validation from the verified
token**, exactly as the server injects `reviewVersion` and `family` today
(`app.py:3448-3450`). The model never emits it, so a manipulated model cannot claim a
Router basis it did not have.

### 2.4 Output schema — `reviewVersion: "v3"`

The model must emit exactly this object (field-set equality enforced; all strings pass
`_strip_md`; all caps validated; no other fields render):

```json
{
  "verdict": "<short phrase, max 80 chars>",
  "encouragement": "<1-2 honest sentences, max 300>",
  "whatCameThroughClearly": ["<1-4 observations from the actual answer, max 300 each>"],
  "strengths": ["<0-4 short bullets, max 300 each>"],
  "priorityImprovement": {
    "action": "<the one proportionate improvement, max 200>",
    "why": "<why this one matters most for this question, max 300>",
    "dimensionKey": "<one authorized dimension key, or null>"
  },
  "additionalImprovements": ["<0-3 further concrete improvements, max 240 each>"],
  "missingOrContradictory": [
    {"kind": "missing|contradictory|unclear", "detail": "<what, specifically, max 240>"}
  ],
  "lengthFit": {
    "assessment": "fits|too_thin|too_long|unbalanced",
    "evidence": "<content-based justification, max 240>"
  },
  "strongerApproach": {
    "steps": [{"label": "<max 40>", "guidance": "<max 200>"}],
    "whyThisFits": "<why this structure fits this exact question, max 300>"
  },
  "focusedFollowUp": "<one focused next practice prompt, max 300>",
  "dimensions": [
    {"key": "<authorized key>", "status": "strong|clear|developing|missing",
     "rationale": "<max 400>", "nextAction": "<max 300>"}
  ],
  "evidenceSuggestions": [
    {"opportunity": "<max 400>", "suggestedUse": "<max 400>", "evidenceId": "<allowlisted id>"}
  ]
}
```

Constraints, all validator-enforced: `missingOrContradictory` 0–4 items with `kind` in
the closed three-value enum; `lengthFit.assessment` in the closed four-value enum;
`strongerApproach.steps` 2–5 items; `priorityImprovement.dimensionKey` must be one of
the authorized dimension keys or null; `additionalImprovements` deduplicated against
each other and against `priorityImprovement.action`; `dimensions` exactly one entry per
authorized key in registry order; `evidenceSuggestions` max 2, IDs allowlisted;
score-field prohibition unchanged.

The server injects after validation (never model-emitted): `reviewVersion: "v3"`,
`family` (continuity for the browser record), `specialist:
"answer-coach@<semver>+<prompt-sha8>"`, and

```json
"basis": {
  "dimensionBasis": "router|family_fallback",
  "questionClass": "<router class or null>",
  "lengthBand": "<router band or null>",
  "lengthReasons": ["<router reasons, or empty>"],
  "routerVersion": "<router specialist version or null>"
}
```

`lengthFit` renders alongside `basis.lengthBand` and `basis.lengthReasons`, so the
member sees *which* obligations produced the expectation — "length feedback is justified
by missing or excessive content, not an arbitrary timer" (accepted direction, section
4). Word counts shown in the UI stay client-computed and transparent; any spoken-time
estimate uses a disclosed words-per-minute range and is presentation, not model output.

**What changed from v2 and why:**

- **`improvements` (1–4 flat strings) → `priorityImprovement` + `additionalImprovements`.**
  Today the "one priority" is a positional convention — the client renders
  `improvements[0]` as the priority (`static/js/interview-studio.js:3019-3020`) but no
  contract says index 0 is the priority. The accepted direction makes "one
  proportionate priority improvement" a product promise, and a positional convention
  is invisible to the validator. The explicit object gives it a shape the validator
  enforces (exactly one, with a reason, optionally tied to a dimension). The total
  envelope (1 priority + ≤3 additional = 1–4) matches today's bounds exactly.
- **`missingOrContradictory` is new and observation-only.** The accepted specialist-2
  output includes "missing or contradictory information." It is deliberately *not*
  expressed as bracketed markers: confirmation markers exist only inside
  `revision-partner` drafts, which keeps the marker pattern's meaning unambiguous —
  a marker in an answer is evidence of unresolved improve output, which is exactly
  what the `attempt >= 2` review gate relies on (section 3.4).
- **`lengthFit` is new**, replacing nothing: today review has no length feedback field
  at all, and the improve prompt's 60–120s rule was the only length opinion in the
  system. Length judgment now lives where the accepted direction puts it: the Router
  determines the band with reasons; the coach assesses fit against content.

### 2.5 The 11.9 decision: structure `strongerApproach`, keep `focusedFollowUp` prose

The diagnosis (11.9) flagged `strongerApproach` and `focusedFollowUp` as single prose
blobs inside otherwise structured output. Decision:

- **`strongerApproach` becomes structured** (`steps[]` + `whyThisFits`). Justification:
  at ≤900 free chars it currently does three jobs at once — proposes a structure,
  argues for it, and sequences it — and it is the review field most prone to sliding
  into a rewrite, which is specialist 3's job. Ordered steps with a 200-char guidance
  cap per step keep it about *how to structure*, not *what to say*: the caps are a
  deterministic `content-bounds` guardian that makes a smuggled full rewrite not fit,
  and the accepted composition rule ("separate diagnosis, explanation, suggested next
  step, and proposed member wording") is served by giving the structure proposal its
  own semantic shape the UI can render as a list with a stated rationale.
- **`focusedFollowUp` stays a single prose field** at its existing 300-char cap. It is
  by contract one focused practice prompt — one sentence. Structuring a one-sentence
  field adds schema surface without adding member value, and every added required
  subfield is a new way for a good reply to fail validation (a real cost: each false
  502 throws away a member-visible result).

### 2.6 Not rewriting — the deterministic story

The boundary "does not rewrite unless requested" is assigned to the prompt **and** to
these deterministic controls, per the hard rule that no boundary rests on wording alone:

1. The v3 schema has **no draft field**, and exact-field-set validation rejects any
   reply that adds one — a rewrite has no field to travel in.
2. Every prose field is individually capped (the longest single field is a dimension
   rationale at 400 chars; `strongerApproach` guidance is capped per-step at 200), so
   a full-answer rewrite does not fit anywhere.
3. What the caps cannot catch — a compressed paraphrase inside a 200-char step — is
   named honestly as residual and owned by the evaluation slice (rewrite-leakage
   cases, 2.9), not claimed as deterministic.

### 2.7 Deterministic guardians (taxonomy-complete)

| Guardian | Enforcing construct |
|---|---|
| identity | `_interview_api_authenticated_identity()` first, JSON 401/503, `private, no-store` (`app.py:3730-3753`, `:3843-3846`) — unchanged |
| authorization | Entitlement check (`app.py:3847`); evidence resolved only from server identity (`app.py:3904-3905`); `profile_slug` never read when authenticated |
| source-allowlist | Input manifest of 2.2; new unknown-request-field rejection; `history_selection`/`confirmed_context` structurally absent from this endpoint |
| injection-separation | `_untrusted_opportunity_block` envelope + labelled answer block; honest E2 limit stated; the *deterministic* injection backstop is output-side: field-set equality, closed enums, caps, and the evidence allowlist mean an injected model still cannot emit scores, unauthorized evidence, new fields, links, or actions |
| evidence-entitlement | `'review referenced unauthorized evidence'` allowlist check (`app.py:3529`) — unchanged |
| claim-support | `dimensionKey` membership check; `basis` server-assembled from the verified router token, never model-claimed; evidence suggestions only from allowlisted IDs |
| content-bounds | Every cap in 2.4; `_strip_md`; question/answer/role-context input caps |
| rate-limit | `@limiter.limit('6 per minute')` preserved |
| timeout | New deliberate policy per errata E1: adopt the `_bounded_client()` precedent (`services/ask_pete/provider.py:174`) — explicit ~30s request timeout, 0 SDK retries — replacing the inherited 600s/2-retry SDK default; the exact seconds value is an implementation-package decision with evidence |
| idempotency | The endpoint performs no server-side writes, so a duplicate request duplicates only cost, bounded by the rate limit; when account-backed History arrives (Section 3), version writes carry client-generated version IDs as idempotency keys (section 5.5 requirement R8) |
| malformed-output | `_extract_json_object` (duplicate-field rejection) + extended `validate_interview_review`; rejection → 502, never partial coaching (`app.py:3976-3981`) |
| prohibited-action | No save/publish/send/delete path exists in the endpoint; review output renders only; History writes are member actions in the client; validator field-set equality blocks any "action" field a model might emit |

### 2.8 Failure behaviour

Every failure preserves the member's question, answer, and any prior rendered results
(client evidence at `static/js/interview-studio.js:3206-3214`; now a stated
requirement). Response bodies gain an additive `failureState` field from the shared
enum so the client can render distinct, truthful fallbacks.

| Shared failure state | Trigger | HTTP | Member-facing copy (existing where shown) | Telemetry reason |
|---|---|---|---|---|
| `denied_authorization` | No identity / entitlement off | 401 / 403 | `sign_in_required` / existing copy | none (not a provider event) |
| `rate_limited` | Limiter | 429 | Limiter default + retry guidance | none |
| `unavailable_source` | Identity store outage; expired/invalid `router_token` presented | 503 (+`Retry-After: 5`) / 400 | `workspace_waking`; "That question's analysis expired — review runs with standard coaching dimensions instead." (fallback path taken; a *tampered* token is rejected 400) | `router_token_invalid` (new, fixed literal) |
| `provider_failure` | SDK error, deliberate timeout | 500 | "The coach is unavailable right now. Please try again." (existing) | logged class name only — see G7 note |
| `invalid_output` | Validator rejection | 502 | "The coach returned an unreadable review. Please try again." (existing) | existing `INTERVIEW_FAILURE_REASONS` + new fixed literals: `'priority improvement is incomplete'` → `incomplete_priority_improvement`, `'missing-information entry is invalid'` → `invalid_missing_entry`, `'length fit is invalid'` → `invalid_length_fit`, `'stronger approach is invalid'` → `invalid_stronger_approach` |
| `insufficient_evidence` | Not a failure here: empty member evidence (G2) yields empty `evidenceSuggestions`, honestly | — | — | — |
| `no_history_match` | n/a — this specialist performs no History retrieval | — | — | — |

**G7 closure (deliberate, deterministic):** the generic handler's
`app.logger.error('Interview review API error: %s', e)` (`app.py:3983`) becomes a log of
`type(e).__name__` plus the provider request ID when present — never `str(e)` — so no
SDK exception can carry request/response body content into the log. Same change at the
improve handler (`app.py:4109`). This converts errata E3's open hole into the same
content-free guarantee the deliberate path already has.

**Success telemetry (new, content-free, per accepted section 9):** specialist version,
router basis, band, validation outcome, latency stages, and `response.usage`
input/output tokens (G6). Field inventory here; the pipeline design is Section 5's.

### 2.9 Evaluation slice

Golden and adversarial families (thresholds are selected with evidence in the
implementation package, per the accepted direction — none invented here):

- **Question-class goldens:** factual/preference (short answer must not be told to
  lengthen), behavioral, multi-part (uncovered parts must appear in
  `missingOrContradictory`), technical/case, sensitive-boundary.
- **Length-fit:** thin answer to a scenario question → `too_thin` with content
  evidence; complete concise answer → `fits` (the do-not-reward-length rule);
  rambling answer → `too_long` citing the excess, not a timer.
- **Priority proportionality:** near-strong answers must get a small priority, not a
  rebuild (human-reviewed).
- **No-rewrite leakage:** checks that `strongerApproach.steps[].guidance` and
  `priorityImprovement.action` never contain a proposed full answer (2.6 residual).
- **Adversarial:** injection inside `answer` and `role_context` (embedded instructions,
  fake delimiters, score demands); marker-shaped text in a *first* attempt must pass
  (the P2-1 case — `"[I can share the architecture diagram if useful.]"` style); a
  revision (`attempt >= 2`) with an unresolved marker must be rejected 400.
- **Fairness (accepted section 6):** dialect/non-native phrasing not penalized;
  non-disclosure of sensitive facts not treated as `missing`; no protected-trait
  inference.
- **Failure negatives:** schema-violating replies → 502 with mapped reason; authorization
  negatives; provider-failure copy truthfulness.

Human review is the primary quality decision; automated graders are bounded support.

### 2.10 Version identity

`answer-coach@2.0.0+<prompt-sha8>` — today's live behavior is retroactively designated
the unversioned 1.x; the first versioned release is 2.0.0 because the output schema
(v3) breaks v2 consumers. `<prompt-sha8>` is the first 8 hex chars of the SHA-256 of
the canonical, un-interpolated system-prompt template bytes (UTF-8, exact). The
identity is returned in the response (`specialist`), logged in telemetry, and any
change to prompt template, schema, guardian set, or dimension registry entry produces a
new identity — the rollback unit deliverable 4 requires and G4 says does not exist
today.

---

## 3. Specialist 3 — `revision-partner`

### 3.1 Purpose

Produce an **editable proposed revision** of one preserved answer version, after the
member asks for it, using ONLY: the preserved answer, the member's confirmed additional
context, and member-selected authorized evidence. Every change is accounted for in a
source-aware change ledger. Facts the member must supply are represented by bracketed
confirmation markers, never invented. The proposal never overwrites any answer version
and never submits, saves, or publishes anything by itself.

### 3.2 Input manifest

| Input | Source class | Provenance | Authorization state | Deterministic bound |
|---|---|---|---|---|
| `question` | `question` | As reviewed | Member-authored | ≤300 chars |
| `answer` | `answer` | The exact preserved answer version being revised (`base_version_id` under the version model) | Member-authored; the version is immutable | ≤5,000 chars; digest-bound to `coach_token` when present |
| `coach_token` | system artifact | Server-signed at review time: `{question_digest, answer_digest, priority_action, additional_improvements, coach_version}`, salt `peerslate-interview-coach-findings-v1` | Server-signed; verified signature + 30-min age + both digests match the submitted question and answer | Removes the current tamper vector where coach priorities are client-echoed (`static/js/interview-studio.js:2992` sends `review.improvements` back); fallback below |
| `improvements` (fallback) | UI hint | Client echo — today's mechanism | Untrusted text hints | `_string_list(raw, 4)` (`app.py:4027`); used only when no valid `coach_token`; prompt labels them "member-relayed priorities" — this is prose steering, not a privacy boundary, which is why a fallback is acceptable |
| `evidence_ids` | `member_evidence` | Member-selected from server-derived evidence | Authorized by identity + explicit selection | Existing: ≤2, deduped, membership in server evidence (`app.py:4028`, `:4046-4047`) — unchanged |
| `additional_context` | `confirmed_context` | Member typed it for this revision | Member-authored this request | Existing ≤1,200 chars (`app.py:4035`); becomes the anchor source for `add_from_context` ledger entries |
| `role_context` | `role_context` | As specialist 2 | Untrusted content | Envelope + 4,000-char bound — unchanged |
| `router_token` | system artifact | As specialist 2 | Server-signed, verified | Supplies `length_band` + reasons to the prompt (3.5) |
| identity | — | Server-derived | Required when authenticated | JSON 401/503 (`app.py:3992-3995`) |

`history_selection` is deliberately **not** in this allowlist. The accepted specialist-3
input is "Question, preserved original answer, Router/Coach findings, and
member-selected confirmed evidence." A prior-answer excerpt surfaced by Section 3's
Nudge enters a revision only when the member explicitly places it into
`additional_context` — the member's action converts it to `confirmed_context`, keeping
one door, member-operated, between History and revisions.

Unknown top-level request keys are rejected exactly as in 2.2.

### 3.3 Output schema — `improvementVersion: "v2"`

The model must emit exactly:

```json
{
  "draft": "<the proposed revision, first person, member's voice>",
  "changeLedger": [
    {
      "kind": "restructure|clarify|tighten|remove|add_from_evidence|add_from_context|marker_added",
      "summary": "<what changed, max 200>",
      "basis": "answer|confirmed_context|member_evidence",
      "sourceRef": "<evidence id or null>",
      "anchorExcerpt": "<verbatim excerpt from the claimed source, max 120, or null>"
    }
  ],
  "whyItWorks": ["<1-3 reasons tied to this question's obligations, max 240 each>"],
  "evidenceIds": ["<only selected ids actually used>"]
}
```

Validator rules, all deterministic, extending `validate_interview_improvement`
(`app.py:3675`) without removing anything it does today:

- `draft` non-empty, ≤`MAX_INTERVIEW_ANSWER_LENGTH` — unchanged (`app.py:3678`).
- `evidenceIds` deduped and ⊆ selected evidence — unchanged (`app.py:3686-3689`).
- `confirmations` remain **server-derived** from the draft via
  `_IMPROVEMENT_MARKER_PATTERN.finditer(draft)` (`app.py:3694-3700`), order-preserving
  and deduplicated. The server never trusts the ledger for markers; it reports only
  what the model actually wrote into the draft. Unchanged.
- `changeLedger`: 1–6 entries, `kind` and `basis` in their closed enums, and the
  **source-aware anchor checks** that give the ledger deterministic teeth:
  - `basis: "member_evidence"` requires `kind: "add_from_evidence"` and a `sourceRef`
    present in the selected-evidence allowlist (`'improvement ledger referenced
    unauthorized evidence'` — same reason-code family as today's evidence guard). If
    `anchorExcerpt` is present it must be a verbatim substring of that evidence item's
    `metric`, `label`, or `summary`.
  - `kind: "add_from_context"` requires `basis: "confirmed_context"` and an
    `anchorExcerpt` that is a verbatim substring of the submitted
    `additional_context`.
  - `kind: "marker_added"` requires an `anchorExcerpt` that fullmatches
    `_IMPROVEMENT_MARKER_PATTERN` and appears verbatim in `draft`.
  - `kind` in `restructure|clarify|tighten|remove` requires `basis: "answer"`;
    `anchorExcerpt`, when present, must be a verbatim substring of the submitted
    answer.
  - Any ledger entry claiming evidence used requires that evidence ID to also appear
    in `evidenceIds` (cross-consistency), and vice-versa: every ID in `evidenceIds`
    must have at least one `add_from_evidence` entry — an evidence use the ledger
    cannot account for is rejected (`'improvement ledger does not account for
    evidence use'`).
- Markers ↔ ledger: deliberately **no** hard one-to-one requirement. `confirmations`
  can exceed the 6-entry ledger cap on a sparse answer, and forcing parity would
  convert honest drafts into 502s. The server-derived `confirmations` list is the
  canonical marker truth shown to the member and gating review; `marker_added` entries
  are narrative. (Stated so nobody later "fixes" this into a false coupling.)
- `whyItWorks` 1–3 strings, ≤240, deduplicated.

Server-injected after validation: `improvementVersion: "v2"`, `specialist:
"revision-partner@<semver>+<prompt-sha8>"`, `confirmations` (as today),
`evidenceUsed` (resolved objects, as today, `app.py:3704`), `unresolvedMarkerCount`
(=`len(confirmations)`), and `basis` (router band + reasons echo, as 2.4).

**Why the ledger is trustworthy enough to show:** each `add_*` entry must anchor to a
verbatim substring of an authorized source, checked by the server with plain substring
comparison — an invented "I increased revenue 40%" cannot be ledgered as
`add_from_evidence` unless a selected evidence item actually contains that anchor, and
cannot be ledgered as `add_from_context` unless the member typed it. What remains
non-deterministic — an invented fact placed in the draft but *omitted* from the ledger —
is caught by three layers: the prompt contract, the marker contract (an unsupported
fact must become a marker, and unresolved markers block review), and the evaluation
slice's invention-detection cases. That residual is named, not hidden.

### 3.4 The bracket-marker contract — built on, not redesigned

The existing control is kept **verbatim**, because it is a working end-to-end chain
whose narrowness is by construction (comment at `app.py:3661-3672`): the improve prompt
mandates the imperative-sentence marker shape — capitalized verb, space, text, closing
`.]` (`app.py:4061-4065`); `_IMPROVEMENT_MARKER_PATTERN =
re.compile(r'\[[A-Z][a-zA-Z]*\s[^\[\]]*\.\]')` matches that shape and only that shape
(`[sic]`, `M[1-9]` never match); the server extracts `confirmations` from the draft;
the client gates "Review Revised Answer" on every marker string being gone from the
edited draft, using the server list as canonical (`static/js/interview-studio.js:
2801-2812`, `:2951-2963`); and the server re-validates independently — `authenticated
and attempt >= 2 and _IMPROVEMENT_MARKER_PATTERN.search(answer)` → 400
(`app.py:3889-3900`), scoped so a first attempt's incidental brackets pass (P2-1/P2-2
findings preserved in the comments).

Extensions, none of which alter the pattern or the gate:

1. **The marker contract gets a version name inside the specialist identity.** The
   pattern, the prompt sentence that mandates the shape, the review gate, and the
   client fallback regex are four coupled sites; the architecture names them as one
   contract (`marker-contract/1`) so any future change is a deliberate major-version
   event touching all four together, verified by the round-trip drift test in 3.8.
2. **`marker_added` ledger entries** (3.3) let the member see *why* each marker exists,
   validated against the same pattern.
3. **Version-model integration (section 5):** a proposal records
   `unresolved_marker_count`; applying a proposal as a working draft is allowed with
   unresolved markers (the member keeps editing), but review remains gated exactly as
   today. The `attempt >= 2` condition stays as-is now; when versions become
   server-visible (account-backed History), the same gate can be restated as "the
   submitted version's lineage contains an applied revision" — a strengthening the
   current design leaves room for without changing behavior today.

### 3.5 Length — retiring the 60–120 second rule (errata E6; first implementation slice)

The literal `'"draft":"<60-120 second spoken answer>"'` at `app.py:4067` is a confirmed
production defect against the accepted direction, present in deployed SHA `f42e5399`.
Pete directed that adaptive length lands in the **first implementation slice**. The
design:

- The improve prompt's length instruction becomes: draft to the Router's `length_band`
  with its `lengthReasons` interpolated ("this question obliges: context, personal
  responsibility, action, result — draft to standard_structured length for those
  obligations"), taken from the verified `router_token`.
- When no valid router token exists (interim, or fallback), the instruction is
  "a length that fits this question's actual obligations — no universal time target,"
  and the response carries no band. The universal literal is deleted in the same
  change, not kept as a fallback: the honest interim is *no* stated band, not a wrong
  one.
- Band adherence is **not** a validator rejection. The deterministic bound remains the
  5,000-char cap; a good draft eight words outside a band must not become a 502. Band
  fit is measured in the evaluation slice.
- The band vocabulary (proposed here, owned by Section 1, to be reconciled):
  `brief_direct`, `standard_structured`, `extended_reasoning`, `boundary_first`, plus
  the absent-band state. Bands are size vocabulary; the Router's per-question
  obligations and reasons are the substance — this is what keeps an enum from
  becoming a new universal rule.
- Cross-section flag: the same universal literal exists in the model-answer prompts at
  `app.py:4309` and `:4324`. Those are Section 4's surfaces (Grounded/Generic
  Example); the first slice should carry all three together, but this section only
  owns `:4067`.

### 3.6 Deterministic guardians (taxonomy-complete)

| Guardian | Enforcing construct |
|---|---|
| identity | `_interview_api_authenticated_identity()` first (`app.py:3992-3995`) — unchanged |
| authorization | Entitlement check (`app.py:3996`); evidence from server identity only (`app.py:4039-4040`) |
| source-allowlist | Manifest of 3.2; `history_selection` structurally absent; unknown request keys rejected; selected evidence ≤2 IDs, membership-checked before any prompt is built (`app.py:4046-4047`) |
| injection-separation | Untrusted envelope for role context; answer, confirmed context, and priorities placed in labelled blocks; deterministic backstop is output-side (field-set equality, ledger anchor checks, evidence allowlist, caps) |
| evidence-entitlement | Existing improve checks (`app.py:4046`, `:3688-3689`) + new ledger `sourceRef` allowlist check |
| claim-support | The anchor-substring checks of 3.3 — every `add_*` ledger claim must anchor verbatim to an authorized source; `marker_added` anchors must match the marker pattern and the draft; `evidenceIds` ↔ ledger cross-consistency |
| content-bounds | Draft ≤5,000; ledger 1–6 × capped fields; `whyItWorks` ≤3×240; all inputs capped as today |
| rate-limit | `@limiter.limit('6 per minute')` preserved |
| timeout | Same deliberate bounded-client policy as 2.7 (E1) |
| idempotency | No server-side writes; a duplicated improve call produces a second *proposal*, never a second version — versions are created only by member actions (section 5); future account-backed proposal writes carry `proposal_id` as the idempotency key (R8) |
| malformed-output | `_extract_json_object` + extended `validate_interview_improvement`; rejection → 502, existing copy |
| prohibited-action | The endpoint writes nothing and returns a proposal object only; apply/discard/restore are member actions in the client (and later, member-authenticated History writes); validator field-set equality blocks any model-emitted action field; AI output never triggers save, overwrite, delete, publish, or send |

### 3.7 Failure behaviour

All failures preserve the member's answer, edits, any open proposal text, and prior
results (existing client evidence at `static/js/interview-studio.js:3005-3013`,
`:2841-2844`: a failed context-resubmission leaves the previous draft untouched).

| Shared failure state | Trigger | HTTP | Member-facing copy | Telemetry reason |
|---|---|---|---|---|
| `denied_authorization` | No identity / entitlement / unauthorized `evidence_ids` | 401 / 403 | existing copy; evidence: "One of those evidence suggestions is unavailable." (`app.py:4047`) | — |
| `rate_limited` | Limiter | 429 | limiter default | — |
| `unavailable_source` | Identity store outage; expired `coach_token`/`router_token`; stale role-context digest | 503 / 400 | outage: `workspace_waking`; expired coach token: falls back to member-relayed priorities with truthful labelling, no error; tampered token: 400 | `coach_token_invalid`, `router_token_invalid` |
| `provider_failure` | SDK error / timeout | 500 | "The coach is unavailable right now. Please try again." | class name only (G7 fix) |
| `invalid_output` | Validator rejection incl. ledger anchor failures | 502 | "The coach returned an unreadable draft. Please try again." | new fixed literals mapped: `'improvement ledger is invalid'` → `invalid_change_ledger`, `'improvement ledger anchor is unsupported'` → `unsupported_ledger_anchor`, `'improvement ledger referenced unauthorized evidence'` → `unauthorized_evidence`, `'improvement ledger does not account for evidence use'` → `unaccounted_evidence_use` |
| `insufficient_evidence` | n/a as failure: zero selected evidence is a legitimate mode — the prompt's existing "Use only facts already present in the answer" line (`app.py:4054`) | — | — | — |
| `no_history_match` | n/a — no History retrieval in this specialist | — | — | — |

### 3.8 Evaluation slice

- **Invention detection (primary):** answers with obvious gaps; every unsupported
  metric/employer/outcome in the draft must appear as a marker, not a fact.
  Human-reviewed; automated substring screens as bounded support.
- **Ledger accuracy:** each `add_from_evidence`/`add_from_context` entry traced to its
  anchor (deterministic harness); narrative kinds spot-checked by humans.
- **Marker round-trip drift test:** golden drafts containing each marker shape must
  produce identical `confirmations` from prompt-mandated shape → pattern extraction →
  client gate fallback regex → review-gate rejection; any of the four coupled sites
  drifting fails this test.
- **Voice preservation (accepted section 6):** dialect and non-native phrasing
  preserved, no corporate-speak flattening, no manufactured confidence —
  human-reviewed goldens.
- **Length adherence:** drafts scored against band + reasons; the retired 60–120 rule
  is asserted absent (a literal-string test on the prompt template).
- **Adversarial:** injected instructions inside answer/confirmed context/role context;
  attempts to make the ledger claim unauthorized sources (must 502/403); marker-shape
  forgery in inputs.
- **Failure negatives:** every 3.7 row exercised, including token expiry fallback and
  evidence-allowlist rejection.

### 3.9 Version identity

`revision-partner@2.0.0+<prompt-sha8>`, same construction and rationale as 2.10. The
marker contract (`marker-contract/1`) is part of the versioned surface: a pattern or
shape change is a major version of this specialist and of the coach (whose review gate
shares the pattern).

---

## 4. Cross-specialist interface: review → revision

Today the client echoes `review.improvements` back into improve as "Coach priorities"
(`static/js/interview-studio.js:2992`), so the improve prompt's account of coach
findings is client-tamperable text. The design replaces the echo with the signed
`coach_token` issued alongside each successful review (3.2), binding priorities to the
exact question *and answer* digests. The client-echo path survives only as the labelled
fallback. This is a low-risk integrity hardening using the existing serializer
precedent — not a privacy control, and stated as such: the priorities steer prose; the
privacy and truth boundaries are the evidence allowlist, the ledger anchors, and the
validators.

---

## 5. The Answer Version Model

### 5.1 What is actually there today (verified for this section)

The diagnosis marked the answer-version record shape UNVERIFIED. Read for this section
(`static/js/interview-studio.js`): each *reviewed* attempt is one flattened History
record — id `'attempt-' + Date.now() + '-' + attemptNumber` (or a pre-allocated
video-record id), `attemptNumber`, full answer text, and the review fields inline
(`:3163-3197`); `attemptNumber` advances only on review success (`:3152-3155`,
`:3087`); records are sanitized on read, capped at 100 with silent eviction on write
(`:1980-1984`, G8); `updateHistoryRecord` merges arbitrary field updates into a record
by id (`:1986-1995`); per-record and bulk local deletion exist (errata E4, `:1997`,
`:5140-5157`). The improve draft lives **only in a DOM textarea** (`:2876-2881`) —
"Review Revised Answer" copies it over the composer and submits (`:2930-2938`); "Keep
original answer" removes the section (`:2940-2942`); navigation loses an unapplied
proposal entirely.

So today: reviewed versions are implicitly preserved as separate records (good),
loosely linked by question text + `sessionId` + `attemptNumber` (no lineage pointers),
mutable via merge (no immutability), evictable silently at 100 (destructive), and
proposals are not persisted at all. The model below states its requirements explicitly
rather than assuming this record supports them — it mostly does not.

### 5.2 Objects

**AnswerVersion** — append-only, immutable once created:

```json
{
  "versionId": "<opaque unique id, client-generated, e.g. ULID>",
  "questionRef": {"digest": "<sha256 of normalized question text>", "text": "<question>"},
  "ordinal": 1,
  "parentVersionId": null,
  "origin": "member_typed|member_dictated|applied_revision|restored_edit",
  "fromProposalId": null,
  "createdAt": "<ISO 8601>",
  "text": "<the answer text, ≤5000>",
  "unresolvedMarkerCount": 0,
  "reviewRef": "<review record id or null>"
}
```

**RevisionProposal** — a separate object class; never a member of the version chain:

```json
{
  "proposalId": "<opaque unique id>",
  "baseVersionId": "<the version it revises>",
  "specialist": "revision-partner@<semver>+<sha8>",
  "draftText": "<as returned, then member-edited>",
  "changeLedger": [ ... ],
  "confirmations": [ ... ],
  "unresolvedMarkerCount": 2,
  "status": "proposed|edited|applied|discarded",
  "createdAt": "<ISO 8601>"
}
```

### 5.3 Identity and lineage

- `versionId` is the identity; `ordinal` is display order within a question's chain;
  `attemptNumber` becomes a **derived** display value (count of reviewed versions in
  the chain), no longer identity — which preserves its existing UX meaning and the
  server gate's semantics without change.
- Lineage is the `parentVersionId` chain from the original (`ordinal` 1, parent null)
  through every later version. `origin` says how each version came to exist;
  `fromProposalId` ties an `applied_revision` version to the exact proposal (and
  therefore to its change ledger and specialist version) that produced it.
- **Immutability rule:** no operation may modify the `text` of an existing version.
  New text is a new version. The `updateHistoryRecord`-style field merge may touch
  only presentation metadata, never `text`, `origin`, `parentVersionId`, or
  `createdAt`.

### 5.4 Operations

**Versions are created only at member commitment points** — submit-for-review, apply a
proposal, or an explicit "save this version". AI output never creates a version.

- **Apply as working draft.** Preconditions: none on markers (a draft with unresolved
  markers may be applied and edited further; *review* stays marker-gated exactly as
  today). Effects, in order: (1) if the composer currently holds text differing from
  every saved version in this chain, that text is snapshotted first as a version
  (`origin: "member_typed"`) — **the no-destructive-replacement rule: nothing the
  member typed is ever overwritten without a preserved copy**; (2) a new version is
  appended with `origin: "applied_revision"`, `parentVersionId = baseVersionId`,
  `fromProposalId` set, `text` = the proposal's current (possibly member-edited)
  draft; (3) the proposal's status becomes `applied`; (4) the composer shows the new
  version. Applying does **not** submit for review, save to any server, or publish
  anything. Canonical truth — the member's preserved answers — gains a version and
  loses nothing.
- **Review revised answer** stays as today's compound explicit action (apply + submit),
  with its existing truthful transmit line ("Your revised answer is sent only when you
  click Review Revised Answer", `:2946-2948`) and the marker gate on both client and
  server. It now performs Apply (above) first, so a reviewed revision is always also a
  preserved version even if the review then fails.
- **Compare.** Any proposal against its base version, and any two versions in a chain,
  by id. Two layers, both always shown and labelled: the **computed diff**
  (deterministic client-side word-level diff of the two texts — the literal
  difference) and the **change ledger** (the coach's source-aware account — AI-claimed,
  anchor-validated per 3.3). The ledger never substitutes for the diff.
- **Discard.** Sets proposal `status: "discarded"`. It never touches any version, and
  it is reversible while the practice record exists (see Restore). Today's "Keep
  original answer" removes the DOM node and the proposal is gone; under this model the
  proposal object persists with its record until the member deletes the record.
- **Restore.** Two member paths: (a) **restore a version** — load any prior version's
  text into the composer (with the same snapshot-before-replacement guard); no new
  version is minted by restoring itself — a version appears only at the next
  commitment point, so browsing history does not spam the chain; (b) **restore a
  discarded proposal** — status back to `proposed|edited`, draft and ledger intact.
  When a restored version is edited and then committed (reviewed, revised from, or
  explicitly saved), the new version carries `origin: "restored_edit"` with
  `parentVersionId` pointing at the restored source, so lineage records the true
  ancestry rather than appearing to fork from the latest version.
- **Delete.** Member-owned: deleting a question's practice record deletes its whole
  chain and its proposals. This integrates with the deletion affordances that already
  exist locally (errata E4: `removeHistoryRecord`, bulk clear) and, when
  account-backed History arrives, with Section 3's server-authorized deletion — the
  version model adds no new retention.

### 5.5 Storage requirements — stated, not assumed

The model is a storage-agnostic contract. Whatever stores it — the interim browser
store or Section 3's account-backed History — MUST provide:

- **R1** Per-question version chains with `versionId`, `parentVersionId`, `origin`,
  `fromProposalId`, `createdAt` persisted. *(Today: absent — records are flat.)*
- **R2** Version-text immutability (5.3). *(Today: violated — merge can rewrite
  `answer`.)*
- **R3** Proposal persistence with status transitions. *(Today: absent — DOM-only.)*
- **R4** No silent destruction of any version in a live chain. The current
  `records.slice(0, 100)` silent eviction (G8) violates this; the interim browser
  implementation must at minimum surface the cap and require a member choice before
  anything is evicted, and the account-backed store must not have an eviction cap at
  all.
- **R5** The snapshot-before-replacement guard implementable atomically enough that a
  crash between snapshot and replacement loses nothing (write snapshot first, then
  replace).
- **R6** Namespace isolation exactly as today: member-scoped `:v3` namespace never
  reads, adopts, or deletes anonymous `v1`/`v2` records (owner decision Q-B,
  `static/js/interview-studio.js:352-357`).
- **R7** Deletion of a record removes its chain and proposals; local per-record and
  bulk deletion keep working (E4).
- **R8** When writes become server-side: identity-authorized before every read and
  write, and `versionId`/`proposalId` act as idempotency keys so a retried write
  cannot duplicate a version.
- **R9** Reading a legacy flat record (today's shape) remains possible: it is
  presented as a single-version chain (`ordinal` 1, `origin: "member_typed"`), which
  is exactly what it was. No migration destroys or rewrites legacy records.

Whether existing browser records are *imported* into account-backed History is Pete's
open owner decision 4 from the diagnosis; this model works under either answer.

---

## 6. Rejected alternatives

- **Model-authored dimension keys** (Router mints new dimensions per question) —
  destroys the closed-enum validator that is the system's strongest deterministic
  control.
- **Structuring `focusedFollowUp`** — it is one sentence by contract; added subfields
  add validation failure modes, not member value.
- **Replacing bracket markers with a JSON `placeholders` array** — markers must live
  inside the draft text where the member edits, which is exactly where resolution must
  happen, and the existing regex + server gate already enforces that end-to-end.
- **Validator rejection of drafts outside the length band** — bands are coaching
  judgment; rejecting a good draft for a few words converts quality into member-facing
  502s.
- **Deterministic novel-token diffing to catch invented facts** — unverifiable in
  general and rejects legitimate connective language; markers + anchored ledger +
  evaluation own invention instead.
- **Mutable working-draft version (overwrite text in place)** — violates the
  preserved-versions product contract outright.
- **One combined review-and-revise endpoint/call** — collapses two consent moments and
  two specialists the accepted direction deliberately separates.
- **Requiring a `coach_token` (no fallback) for improve** — would break the working
  flow during rollout for an integrity gain that is not a privacy boundary.
- **Minting a version on every restore/browse** — spams the chain; versions belong at
  commitment points.

---

## 7. Genuine uncertainty, stated plainly

1. **The Router interface is proposed, not settled.** The `router_token` field names,
   the band enum, the obligations shape, and the dimension registry are written here to
   be concrete; Section 1 owns them and reconciliation may rename or reshape them. The
   requirements this section actually depends on are narrower: server-signed, question
   digest-bound, closed dimension keys from a server registry, a closed band enum with
   per-question reasons, and a verifiable absence state.
2. **Orchestration style** (client-carried signed tokens versus a server-side pipeline
   call) is Section 5's decision; this design works under either because the tokens
   are verified server-side regardless of who transports them.
3. **Interim browser storage of the version model** may prove not worth building if
   Section 3's account-backed History lands early; R1–R9 are written so the contract
   survives that sequencing decision.
4. **Whether `strongerApproach.steps` caps (2–5 × 200 chars) are right** is an
   evaluation question; the caps are deliberate first values, expected to be tuned
   with evidence in the implementation package, never removed.
5. **Non-owner evidence remains empty (G2)** — nothing here fixes that; both
   specialists behave honestly with empty evidence (empty suggestions; answer-only
   revisions), and Grounded Example remains blocked as the diagnosis and owner
   decision 1 state.
6. **I have not observed the live authenticated UI** — client behavior statements come
   from source at the byte-identical deployed SHA, consistent with Gate A's evidence
   discipline; the authenticated test batch remains gated on Pete's explicit approval.

---

*End of Section 2. Increment 3 (Private History Nudge and private retrieval) consumes
the version model's `reviewRef`/chain identifiers; increment 4 (Examples) inherits the
band retirement flagged for `app.py:4309`/`:4324`; increment 5 reconciles the token
transport and telemetry field inventory named here.*
