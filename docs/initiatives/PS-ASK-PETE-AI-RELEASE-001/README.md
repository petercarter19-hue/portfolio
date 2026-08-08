# PS-ASK-PETE-AI-RELEASE-001 — Ask Pete app-seam corrections and release record

## What this package is

`PS-ASK-PETE-AI-001` merged the grounded Ask Pete path default-off behind
`PEERSLATE_ASK_PETE_GROUNDED_ENABLED`. `PS-ASK-PETE-AI-READINESS-002` fixed
three enablement blockers inside `services/ask_pete/` and recorded one gap it
could not close, because closing it meant editing `app.py` — outside that
package's writable surface.

This package owns `app.py`. It closes that gap, documents the flag in
`.env.example`, and holds the release evidence for the enablement decision.

It then took on a second, separately evidenced slice: the first real-provider
verification failed 502 on every grounded question, and the lane record was
amended on 2026-08-08 to add `services/ask_pete/` and the prompt contract for
exactly that correction. See "The evidenced release-blocker correction" below.

- Status: **Source complete on the package branch; not merged, not deployed,
  not enabled**
- Delivery path: **Bounded** — an established seam, no new trust boundary. See
  "Why this is not Protected" below.
- Runtime effect while `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` is false: one
  deliberate, flag-independent change — a rate-limited caller on any limited
  route now receives JSON instead of HTML. The provider and prompt corrections
  are on the grounded path only, which the flag holds closed, so they change no
  flag-off behavior at all.
- Writable surfaces used: `app.py`, `.env.example`, `tests/ask_pete/`,
  `services/ask_pete/`, `prompts/ask_pete/grounded_public_v1.md`, and this
  directory. `services/ai_foundation/`, `templates/`, `static/`,
  `azure-pipelines.yml`, SQL, and governance files were not modified.

## The correction that landed

### A rate-limited caller now gets JSON and a Retry-After

**Before.** `/api/chat` carries `@limiter.limit('10 per minute')`, and so do
the four Interview AI routes, the Workshop state-changing routes, the
Opportunity Slate routes, and the Community API. `app.py` registered no `429`
error handler, so Flask-Limiter's refusal rendered werkzeug's default HTML
page:

```
HTTP/1.1 429 TOO MANY REQUESTS
Content-Type: text/html; charset=utf-8
(no Retry-After header)

<!doctype html>
<html lang=en>
<title>429 Too Many Requests</title>
<h1>Too Many Requests</h1>
<p>10 per 1 minute</p>
```

The body a JSON client could not parse; the limit string was the only hint it
carried; and nothing said when to try again.

**After.**

```
HTTP/1.1 429 TOO MANY REQUESTS
Content-Type: application/json
Retry-After: 57

{"error": "Too many requests. Please wait a moment and try again."}
```

**Where the Retry-After value comes from.** Flask-Limiter records the breached
limit on the request context *before* it raises, so `limiter.current_limit`
is populated inside the handler and `.reset_at` is the real window reset. The
header is therefore the actual remaining wait and counts down between attempts
(measured: 60, then 57 three seconds later), not a fixed guess. Werkzeug's own
`retry_after` attribute is not usable here — `RateLimitExceeded.__init__` never
passes one to `_RetryAfter`, so it is always `None`. A one-minute fallback
applies only if the extension has nothing to report, so the header is never
omitted and the computation can never fail a response that has already been
decided.

**Why the sentence is static.** The exception's `description` holds the limit
string (`10 per 1 minute`). That is operational detail a visitor does not need
and an abusive caller should not be handed. A test asserts neither it nor the
visitor's question appears in the body.

**Scope, deliberately app-wide.** The handler fires for any `429` raised as an
HTTP exception, which means every rate-limited route in the application gains
the same contract. Two consequences a reviewer should confirm they accept:

1. Routes that build their own `429` payload — Workshop voice's
   `voice-daily-limit`, Opportunity Slate's spent-ceiling card — *return* a
   response rather than raising, so Flask never invokes an error handler for
   them. They are untouched, and their tests still pass unchanged.
2. Routes reached by an ordinary browser form post (Workshop's
   save/update/archive/restore/delete, Opportunity Slate's writes) previously
   showed werkzeug's HTML page when refused and now receive JSON. Both flags
   are default-off, so nothing about this is live, but it is a real change in
   what a refused form post renders. The alternative — negotiating on `Accept`
   or path prefix — was not taken because the brief specified one app-wide JSON
   contract and every one of those surfaces is fetch-driven.

`static/js/chatbot.js` is unaffected either way: it already discards an
unparseable body and shows its own `429` sentence keyed on `response.status`.

## The correction that was stopped

### Manifest failures at `/api/chat` are already classified

The brief specified a second correction: add an `except PublicSourceManifestError`
clause to the grounded branch of `/api/chat`, on the stated premise that
`PublicSourceManifestError` "subclasses `AskPeteError` but NOT
`AIFoundationError`", so a manifest or digest failure fell through to the bare
`except Exception` and returned a generic **500**.

The code contradicts that premise, so the slice was stopped rather than
improvised. Verified against the branch:

```
PublicSourceManifestError -> AskPeteError -> AIFoundationError -> RuntimeError
```

`services/ask_pete/errors.py` declares `class AskPeteError(AIFoundationError)`,
so `issubclass(PublicSourceManifestError, AIFoundationError)` is `True`. The
existing `except AIFoundationError` clause already catches it, ahead of the
bare `except`. Driven end to end with the flag on and the real exception
raised, `/api/chat` today returns:

```
HTTP/1.1 502 BAD GATEWAY
Content-Type: application/json

{"error": "Ask Pete could not verify a grounded answer. Please try again."}
```

with `app.logger.exception('Grounded Ask Pete answer failed validation.')` and
no payload in the log line. The behavior is already fail-closed, already `502`,
already classified, and already payload-free. `PublicSourceManifestError` is
also already imported at `app.py` line 48, for the evidence-companion helper.

What the change would actually have achieved is narrower than the brief
describes: a distinct *sentence* for a source-integrity failure
("Ask Pete's approved sources are unavailable right now") separated from a
grounding-validation failure, at the same status code. That is a reasonable
improvement, but it is a message-differentiation decision rather than the
classification correction the brief authorized, and the clause would have to be
placed before `except AIFoundationError` — not "before the bare except" as
written — to fire at all. It is left for the orchestrator to decide.

## `.env.example`

`PEERSLATE_ASK_PETE_GROUNDED_ENABLED=false` was absent from `.env.example`
even though `app.py` has read it since `PS-ASK-PETE-AI-001`. It is now
documented alongside the other default-off feature flags, in the same style,
with the same keep-off-through-merge-and-deployment instruction, and with the
one thing that makes it different from its neighbours stated plainly: it does
not open a new route, it replaces how an already-public route answers, and
every question it answers is a paid model call.

## The evidenced release-blocker correction

The first real-provider verification (deploy `ee5ee842`, flag briefly enabled)
returned **502 on every grounded question**. Two defects, both in the shape of
the reply rather than in the substance of the answer, captured from the raw
model output:

1. **The model fenced its JSON.** The reply began ` ```json\n{\n  "state": ` —
   a markdown code fence around an otherwise well-formed object. `json.loads`
   refused it and the adapter raised
   `AnswerContractError("provider response is not strict JSON")`.
2. **The reply truncated at the output ceiling.** It ended mid-array at 5,953
   characters, cut off by `max_tokens=1_600`. The truncated text then failed the
   *same* JSON check, so the operator-visible error named the symptom and hid
   the cause.

The flag was returned to off, which also served as the recorded rollback proof.
Three corrections follow, in `services/ask_pete/provider.py` and the prompt
contract.

### 1. One outer code fence is unwrapped before parsing

`_unwrap_single_fence` removes exactly one well-formed outer fence pair: an
opening fence line (` ``` ` or ` ```json `, case-insensitive) as the first line
and a closing fence as the last line. It removes nothing else and repairs
nothing. A preamble before the fence, commentary after it, a second fence, an
unrecognized info string, a closing fence that does not open its own line, an
object embedded in prose, or a malformed interior is returned **unchanged** and
still fails as `provider response is not strict JSON`.

This loosens transport formatting only. The interior faces the full chain it
always did — `services/ai_foundation/codec.py` field/enum/bound decoding, exact
citation location and verification against the approved source, grounding
validation, and product-quality validation. No trust rule moved, and a test
holds the line by proving an embedded-JSON-in-prose reply is still refused
rather than mined.

### 2. Truncation is named as truncation, and given headroom

The adapter now reads `stop_reason` off the SDK response **before** anything
tries to parse the text. Verified empirically against the installed
`anthropic` 0.112.0: `stop_reason` is a top-level field on `Message`, and
`max_tokens` is one of its literal values. On `max_tokens` the adapter raises
`AnswerContractError("provider response was truncated before completion")` — a
distinct, honest category. The visitor still sees the same honest unavailable
answer; the operator now sees the real cause. A test pins the SDK mechanic so
an upgrade that moves or renames it fails loudly instead of silently reverting
the diagnosis.

The default output ceiling moves **1,600 → 3,000** tokens. This does not
license a longer answer: what an acceptable answer may contain is already
bounded by the decoder (at most 12 claims, 600-character excerpts, a
2,000-character summary), so the ceiling only has to clear the largest answer
that contract would already accept. `services/ask_pete/runtime.py` — the single
production construction site — passes no explicit value, so it picks up the new
default.

### 3. Prompt formatting discipline

`prompts/ask_pete/grounded_public_v1.md` now asks for the bare object and
nothing else (no fence, no preamble, no commentary), for excerpts under 300
characters, and for the fewest claims that honestly answer the question —
explicitly without dropping anything the purpose requirements demand. Nothing
else in the prompt moved: the trust rules, the untrusted-evidence framing, the
purpose requirements, the schema, and the server-owned-fields rule are
byte-identical.

**`PROMPT_CONTRACT_VERSION` stays `ask-pete-grounded-public.v1`.** The judgment:
the version identifies the *answer contract* the server will accept — its
fields, enums, citation obligations, and trust rules — and none of those
changed. What changed is formatting discipline about how the same object is
delivered, plus two length preferences already bounded by the decoder. A
stored answer tagged `v1` before this change and one tagged `v1` after it are
alike in every respect the identifier is used to reason about, so bumping it
would assert a difference that does not exist. If a later change alters a
field, an enum, a citation rule, or a trust rule, that one bumps the version.

### 4. Excerpt copying discipline, and one corrective retry

With parsing fixed, the next real-provider run got further and failed
differently: **two of three grounded questions returned
`AnswerContractError("citation excerpt does not occur in its approved
source")`**. The captured mismatches show the model copying real source words
and then *stitching* them — newlines and field labels flattened into a
sentence:

```
model:  "Burdick Special Act Award. U.S. Air Force. 2024. Peer-selected across the program..."
source: "...Special Act Award\nOrganization: U.S. Air Force\nYear: 2024\nPublic detail: Peer-selected across the program..."
```

Elsewhere it joined two bullet lines with `". "` where the source has `"\n- "`.
The words are faithful; the strings are not contiguous substrings, so the
server cannot locate them and refuses the answer. This is a copying mistake,
not a fabrication — the same run's `evidence_finder` question produced **eight
verified citations**, so the model can comply. Two changes follow.

**The prompt now states the discipline.** Rule 4 of
`prompts/ask_pete/grounded_public_v1.md` gains two sentences: every excerpt is
one contiguous passage copied character for character from a single place in
that source, including its punctuation, labels, and any line breaks; never
assembled from separate lines or list items, and never with a label or bullet
removed to make it read as a sentence. Nothing else in the prompt moved — the
trust rules, untrusted-evidence framing, purpose requirements, schema, and
server-owned-fields rule are byte-identical.

**The adapter makes exactly one corrective retry.** When the first attempt
fails with `AnswerContractError` — the model-behavior class: not-strict-JSON,
non-object, truncation, excerpt-not-found, ambiguous-excerpt —
`AnthropicGroundedProvider.answer` re-sends the *same* request document with
one appended user message that (1) quotes the exact contract error, (2) lists
the offending excerpt strings verbatim, and (3) restates the copying discipline
and the bare-JSON requirement. If that attempt also fails, its error
propagates: the adapter fails closed and never makes a third call.

What the retry deliberately does **not** cover:

- **Transport failures are never retried.** A timeout, connection error, or
  HTTP status is `ProviderUnavailableError`; there is no model reply to
  correct, the SDK's own retries are disabled on purpose, and a second call
  would mostly re-buy the same outage. A transport failure on the *retry* is
  equally final.
- **At most two provider calls per question** (`MAXIMUM_PROVIDER_CALLS`),
  enforced structurally by two call sites and pinned by tests whose provider
  double signals an unscripted third call out of band, so it cannot be masked
  as a degradation.
- **`_reject_truncated_response` and `_unwrap_single_fence` are unchanged.**
  The retry wraps the whole parse-and-resolve attempt; it does not loosen what
  a single attempt accepts.

**What the corrective message may carry.** The quoted excerpts are
model-authored strings copied from *approved public* source content, so no
private data crosses this boundary. They are still untrusted text, and the
message treats them as such: it says they are data and never instructions
before quoting any of them, wraps each in a `<refused_excerpt>` tag, refuses to
quote any excerpt that contains that tag name, quotes at most five, and skips
any excerpt longer than the decoder's own 600-character ceiling. Whatever it
withholds it counts, so the retry input is bounded and the message is not
quietly incomplete.

**Accepted limitations, stated rather than assumed away:**

1. **Wall clock.** `PROVIDER_TIMEOUT_SECONDS` (30 s) is a *per-attempt* bound
   and `answer` may now make two attempts, so the worst case is 60 s of
   provider time against `static/js/chatbot.js`'s 45 s abort. Reaching it
   needs a complete-but-refused reply arriving at nearly 30 s — a reply slower
   than that times out and is never retried — so it is unlikely rather than
   impossible. The bound was left per-attempt as specified; a total wall-clock
   budget for the pair is the available mitigation if the owner wants the 45 s
   ceiling guaranteed.
2. **Cost.** A refused question now costs up to two generations instead of
   one, and the retry re-sends the full request document. This is the intended
   trade: a stitched-excerpt answer is worth one correction, and the ceiling is
   two calls rather than a loop.
3. **The trace does not report the attempt count.** `AITrace` in
   `services/ai_foundation/observability.py` has no field for it —
   `provider_called` is a boolean — and `services/ai_foundation/` is outside
   this package's writable surface, so no field was added and none was
   overloaded. An operator reading a trace cannot currently tell a one-call
   answer from a two-call one; `duration_ms` is the only indirect signal. This
   is recorded here as a stated limitation rather than forced into the
   contract.

**`PROMPT_CONTRACT_VERSION` still stays `ask-pete-grounded-public.v1`**, for
the same reason recorded above and re-examined for this change. The version
identifies the *answer contract* the server accepts — fields, enums, citation
obligations, trust rules — and none of those moved. The prompt gained copying
discipline (how to produce the same object), and the adapter gained one retry
(how many times the server asks for it). An answer stored as `v1` before this
change and one stored as `v1` after it are alike in every respect the
identifier is used to reason about. A field, enum, citation rule, or trust rule
change bumps it; this one does not.

### 5. Every number the server enforces is now a number the prompt states

Live verification with corrections 1–4 in place, five real-provider cases:

| Case | Result |
|---|---|
| `evidence_finder` | **Pass** — 9 claims, 9 verified citations |
| general "sustainment" question | **Pass** — 4 claims, 7 citations |
| general-1 | **Fail** — `answer.follow_up_question exceeds 300 characters` |
| `interview_preparation` | **Fail** — same |
| `recruiter_brief` | **Fail** — `summary_below_minimum_words` |

The two passes are the evidence that corrections 1–4 work: the excerpt
discipline held and citations resolved against real approved sources. The three
failures are a different defect with a single shape — **the model was refused
for missing a number it was never told.**

- `MAX_FOLLOW_UP_CHARS = 300` lives in `services/ai_foundation/codec.py` and the
  prompt never mentioned it, so a long multi-part follow-up question was
  refused after generation. The corrective retry fired and failed again,
  correctly: its message quotes the contract error, but no correction can make
  the model comply with a bound it still cannot see.
- The recruiter summary bound *was* stated ("100 to 140 words"), but the
  compactness paragraph added in correction 3 read as permission to go shorter
  and never said which rule wins. The model shortened, and
  `services/ask_pete/quality.py` refused it at `minimum_summary_words=100`.

This correction is **prompt calibration only** — no code changed. Every number
was read out of `codec.py`, `quality.py`, and `evaluation.py` and quoted:

1. **Follow-up shape and ceiling.** A new response-format rule: each
   `follow_up_question` is one question in plain text, at most 300 characters,
   never several questions joined into one string and never a paragraph of
   setup.
2. **The decoder's ceilings, stated once.** A new line naming all eight: 12
   claims, 8 citations per claim, 5 follow-ups, 2000-character summary,
   1000-character claim text, 1000-character limitation, 300-character
   follow-up, 600-character excerpt.
3. **Compactness loses to a purpose requirement.** A new closing paragraph:
   brevity applies to excerpt length and to claim count *above* the stated
   minimum, and never takes an answer below a stated minimum or outside a
   stated word range — with the recruiter summary named explicitly, because
   that is the case that actually failed. The excerpt preference is also
   reworded so 300 reads as a preference inside the real 600 ceiling rather
   than as the limit itself.
4. **The quality contract's numbers, per purpose.** `quality.py` enforces
   floors the prompt had only implied. Now stated: `recruiter_brief` needs
   `partially_supported` and no other state, a 100–140 whitespace-separated
   word summary, at least 4 claims in total including a boundary claim, at
   least 3 citations in total, and at least 2 follow-ups;
   `interview_preparation` needs at least 3 follow-ups and, when supported or
   partially_supported, at least 1 claim carrying at least 1 citation;
   `evidence_finder` needs the same conditional claim and citation;
   `public_profile_answer` is stated to have no minimum at all, so the model
   does not invent one. The word unit is named as whitespace-separated because
   that is literally what `evaluation.py` counts (`summary.split()`).

**The tests check the correspondence, not just the wording.**
`tests/ask_pete/test_prompt_states_the_enforced_numbers.py` builds the exact
recruiter brief the prompt now describes and asserts `validate_product_quality`
accepts it, then goes one step below each stated floor and asserts the matching
refusal identifier — `summary_below_minimum_words`, `claim_count_below_minimum`,
`citation_count_below_minimum`, `follow_up_count_below_minimum`,
`boundary_claim_required`, `private_handoff_required`, `state_not_allowed` — so
a prompt number that stops matching the server fails here rather than in
production. The decoder ceilings are asserted against the imported `codec.py`
constants for the same reason.

**`PROMPT_CONTRACT_VERSION` still stays `ask-pete-grounded-public.v1`.** Every
number added was already enforced by the server before this change; the prompt
now states them instead of leaving the model to guess. No field, enum, citation
obligation, or trust rule moved.

**What this correction does not fix.** The corrective retry still quotes the
contract error generically and adds no purpose-specific coaching. That should
be sufficient once the prompt states the numbers — the *first* attempt is the
one that now has what it needs — but a retry on a length failure remains a
weaker correction than a retry on an excerpt failure. If live verification
shows length failures surviving the retry, teaching the corrective message to
restate the violated bound is the next step; it was not taken here because this
round was scoped to the prompt.

### 6. The last two failures, and where each one could actually be corrected

Live round 3, with corrections 1–5 in place: **3 of 5 pass.** general-1 is fixed
by the stated numbers (summary 114 words); general-2 and `evidence_finder` are
solid. Two remained, and they failed in two different places for one underlying
reason — **each refusal happened somewhere the correction could not reach.**

**`interview_preparation`: `answer.follow_up_question exceeds 300 characters`.**
The retry fired and the model repeated the mistake. Two causes, and only the
first was obvious: the corrective message quoted the error without naming which
field to shorten or to what. The second is structural — **that refusal is
raised by `services/ai_foundation/codec.py`, which `AIFoundationGateway.answer`
runs after `AnthropicGroundedProvider.answer` has already returned.** A decoder
bound could therefore never reach the provider's corrective retry at all, and
teaching `_corrective_message` to restate one would have been dead code on its
own. So the fix has two parts:

- **The adapter decodes its own finished answer** before returning it, calling
  the same `parse_grounded_answer` the gateway calls, on the same object with
  its server-owned metadata already set. Nothing is loosened, repaired, or
  re-classified: the same function raises the same `AnswerContractError` with
  the same message. Only *when* it is raised moves — from after the adapter to
  inside the attempt, where the one corrective retry can address it. An answer
  refused before is still refused, an answer accepted before is still accepted,
  the gateway decodes again and stays the authority, and the adapter still
  returns a mapping because that is what the gateway and every caller expect.
  The cost is one extra pure decode per answer.
- **`_corrective_message` restates the violated bound.** For a length violation
  it appends one sentence naming the field and the limit — *"Rewrite only the
  answer.follow_up_question field so it is at most 300 characters, and leave
  every other part of the answer as it was."* — with both values read out of
  the refusal's own message, so it can never state a limit the decoder is not
  enforcing. The decoder's three count ceilings carry no number in their
  message, so those restate the decoder's own constant. Every other refusal
  keeps the existing generic behavior, and no bound was loosened.

**`recruiter_brief`: `boundary_claim_required`.** A grounded, citation-clean
answer that simply lacked the boundary claim the flagship contract requires.
This one is raised by `services/ask_pete/quality.py` *after* the gateway has
finished, so it is past the provider entirely and the visitor got a 502 for a
recoverable shortfall. `AskPeteService.answer` now takes **exactly one fresh
sample** on `AskPeteResponseError` and re-validates; a second failure
propagates unchanged.

**It is a resample, not a correction, and that is a real limitation.** There is
no feedback channel: `AIRequest` carries a request id, product, purpose,
audience, subject key, question, and context key, and nothing else. Adding a
field would mean changing `services/ai_foundation/`, outside this package's
surface, and writing the complaint into `question` would corrupt the one field
that records what the visitor actually asked. A second sample of the same
request is therefore a bet on sampling variance — a weaker instrument than the
provider's corrective retry, and worth taking once because the alternative for
the flagship brief is a 502.

**What is not resampled**, each pinned by a test:

- A **grounding failure** is a trust boundary, not a usefulness bar. Asking
  again would be asking a model that just broke the rule to break it less.
- An **unavailable provider** degrades to the honest unavailable answer, which
  `validate_product_quality` passes over, so no paid call is spent on a
  provider that just failed.
- A **purpose with no quality contract** cannot raise `AskPeteResponseError` at
  all, so a general question can never trigger a resample.

**The combined ceiling, stated honestly.** The provider makes at most 2 calls
per gateway round and there are at most 2 rounds, so one visitor question can
cost **at most 4 provider calls**. The typical cost is **1** — both bounds are
failure paths, and each of round 3's three passing cases took a single call.
Four bounded Haiku calls is a price worth paying to keep the flagship recruiter
brief available instead of returning a 502, and the ceiling is a fixed small
number rather than a loop.

**Latency, and who gives up first.** Each provider call is bounded at 30 s, so
the worst-case chain runs to about 120 s while `static/js/chatbot.js` aborts at
45 s. In that worst case the visitor sees the browser's own failure before the
server finishes. The server still finishes inside its own bounds — never
unbounded, never the SDK's 600 s default, always a fixed call count — but it
can finish generating an answer nobody is waiting for. Reaching it needs three
refusals in a row, each arriving late; it has not been observed. Stated as an
accepted limitation rather than assumed away. A total wall-clock budget across
the chain remains the available mitigation and remains an owner decision.

**Both rounds are traced.** A resampled question emits two `AITrace` records
with the same `request_id`, and the returned diagnostic describes the round
that was delivered. That is honest — two rounds did happen — and it is the only
signal an operator has that a resample occurred, because `AITrace` still has no
attempt-count field.

### 7. One resample for the whole model-output class

Live round 4: **3 of 5 again** — general-1, general-2 and `evidence_finder`
pass, and have now passed in three consecutive rounds. The two remaining
failures moved to a third layer:

| Case | Failure | Raised by |
|---|---|---|
| `recruiter_brief` | `interpretations must state their inferential boundary` | `citation_validator.py` |
| `interview_preparation` | `a supported answer may contain only supported claims` | `citation_validator.py` |

Both are `GroundingValidationError`, raised inside `AIFoundationGateway.answer`
— **past the provider's corrective retry, and not an `AskPeteResponseError`, so
correction 6's resample did not cover them either.** Four rounds have now
walked the same taxonomy one layer at a time: the excerpt layer, the decoder
layer, the quality layer, and now the grounding layer.

**The resample now covers the whole class.** `RESAMPLED_REFUSALS` is
`AskPeteResponseError`, `GroundingValidationError`, `AnswerContractError` —
every refusal that is a judgment about what the model produced. Deliberately
absent, pinned by tests:

- `ProviderUnavailableError` — transport, already degraded to the honest
  unavailable answer before it could reach the service.
- `SourceAuthorizationError` and `ExecutionLimitError` — deterministic
  functions of the request and the approved sources. Neither changes between
  rounds, so a resample fails identically and pays a call to do it.
- `PublicSourceManifestError` — source integrity, raised while the catalog is
  assembled rather than inside a round. Resampling a model cannot repair a
  changed digest and must not appear to.

**The ceiling does not move.** Still `MAXIMUM_QUALITY_ROUNDS = 2`, still at
most 4 provider calls per question. Widening *which* refusals resample means
more paths can reach that ceiling, not that the ceiling is higher.

**The prompt states the two tripped rules the way it states the numbers.** A
new block after the core rules, read out of `citation_validator.py` and
faithful to it:

- A claim of kind interpretation must carry a limitation stating its
  inferential boundary; a claim of kind boundary must also carry one, and its
  state must be `not_established` or `ambiguous`.
- A supported claim needs at least one citation; a partially_supported claim
  needs a citation and a limitation; a not_established claim carries none.
- The answer's own state must agree with its claims — supported holds only
  supported claims; partially_supported needs at least one claim that is not
  supported *and* at least one that is supported or partially_supported;
  not_established holds only not_established or ambiguous claims; ambiguous
  holds only ambiguous claims. So mixing evidence with an unknown means the
  state is partially_supported.

Rule 7 already mentioned the interpretation limitation as guidance. What was
missing was that the server *refuses the whole answer* over it, and that answer
state and claim states have to agree at all — the prompt described neither.

**The tests pin the rules against the validator, not against the wording.**
`test_prompt_states_the_enforced_numbers.py` now builds an answer violating
each of the eleven grounding rules and asserts the validator refuses it with
that exact message, plus a well-formed mixed answer that is accepted — so a
prompt sentence that stops matching `citation_validator.py` fails there rather
than in production.

### Files in this correction

| File | Change |
|---|---|
| `services/ask_pete/provider.py` | `_unwrap_single_fence`; `_reject_truncated_response`; `DEFAULT_MAXIMUM_OUTPUT_TOKENS` 1,600 → 3,000; `TRUNCATED_STOP_REASON`; then `MAXIMUM_PROVIDER_CALLS`, `RefusedExcerptsError`, `_unresolvable_excerpts`, `_corrective_message`, `_attempt`, and the one corrective retry in `answer`; then `_violated_bound_sentence` and the self-decode at the end of `_attempt`. Unchanged by correction 7 |
| `services/ask_pete/service.py` | `MAXIMUM_QUALITY_ROUNDS`, `_answer_and_validate`, and the one resample in `answer`; then `RESAMPLED_REFUSALS` widening it to the whole model-output class |
| `tests/ask_pete/test_service_quality_resample.py` | New: a recoverable shortfall recovered in two rounds, a persistent one failing closed at two, a first-time pass costing one; then grounding and decoder refusals resampled, the excluded taxonomy pinned, and an execution-limit refusal counted by traces |
| `prompts/ask_pete/grounded_public_v1.md` | Bare-object-only instruction; excerpt and claim-count preferences; the contiguous-copy discipline in rule 4; the enforced numbers — per-purpose quality floors, the eight decoder ceilings, the follow-up shape rule, the compactness-never-overrides paragraph; then the claim-shape and answer-state consistency block. No trust rule or schema field changed |
| `tests/ask_pete/test_prompt_states_the_enforced_numbers.py` | New: the prompt's numbers checked against what `quality.py` and `codec.py` actually enforce, one step below each floor; then its stated grounding rules checked against `citation_validator.py`, one violation per rule |
| `tests/ask_pete/test_provider_response_shape.py` | New: truncation category and call count, output-ceiling headroom, the tolerated/refused fence boundary, installed-SDK `stop_reason` contract. The truncation test now pins the two-call bound instead of a one-call one |
| `tests/ask_pete/test_provider_and_classification.py` | The fenced-object case now succeeds end to end with its citation verified; genuinely malformed cases (prose preamble, double fence) still refused |
| `tests/ask_pete/test_provider_corrective_retry.py` | New: stitched-excerpt recovery, what the corrective message carries and how it frames it, fail-closed after two refusals, no retry for transport, no retry after success, the quoting bounds, and the prompt/version pins; then decoder bounds being correctable inside the attempt and the restated field and limit |

### What this correction does not claim

- **No live call was made from this lane.** Every real-provider result quoted
  above was produced by the orchestrator and reported into it; this writer ran
  tests only. Corrections 1–4 are now partly verified — two of five cases pass
  end to end with real citations resolved — and correction 5 is **not verified
  at all**, because it landed after that run. A fresh five-case run is required
  before any redeploy.
- **Nothing here demonstrates that the corrective retry recovers a real
  stitched excerpt.** The two passing cases resolved their citations on the
  first attempt. The tests prove the adapter asks correctly and stops
  correctly; whether a live retry recovers a live stitching mistake has not yet
  been observed either way.
- The flag stays off. Nothing here proposes enablement.
- Only `max_tokens` is treated as truncation. A `refusal` or `pause_turn` stop
  reason still falls through to the JSON check and reports as an unparseable
  reply. Neither has been observed on this path, and widening the check was not
  in scope for an evidenced-blocker correction.
- Truncation is inside the retryable class, so a reply cut off at the ceiling
  now costs a second generation before it fails. That is a deliberate revision
  of the earlier "no retry of a call that would truncate again" stance: the
  correction asks for an object compact enough to finish, which is a different
  request, and the two-call ceiling bounds what it can cost.

## Why this is not Protected

- **Identity and authorization.** Untouched. The handler derives no identity
  and reads no member data; the rate-limit key function is unchanged.
- **Privacy.** Improved. The refusal body no longer carries the limit string,
  and a test asserts the visitor's question is not echoed.
- **Canonical truth and consequential AI.** The app-seam slice left this
  untouched, and the grounded branch of `/api/chat` is still byte-identical to
  `origin/main`. The release-blocker slice does change the AI path — this is
  the one claim in this section the second slice revises, so it is stated
  plainly rather than left as written. What changed: how a provider reply is
  unwrapped and parsed, how a truncated reply is classified, how many output
  tokens one call may spend, and the prompt's formatting discipline. What did
  not: the answer contract, the source manifest, and every validation rule.
  `services/ai_foundation/` is unmodified, so the codec, citation validator,
  grounding validator, and quality validator still run in full on the same
  interior. AI still proposes and nothing it returns becomes canonical.
  Whether that combination keeps this slice Bounded or admits it to Protected
  is the owner's classification call at review, not one this record makes on
  its own; the lane grant recorded it as an evidenced release-blocker
  correction.
- **Shared infrastructure.** The `Limiter` instance is read, never mutated; no
  limit value, storage backend, or key function changed.
- **Material visual direction.** None. No template, stylesheet, or script.

Enablement of `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` is a separate Protected
release decision under `PS-OPS-001`. This package does not make it, recommend a
date for it, or claim any live behavior.

## Files (app-seam slice)

The release-blocker slice's files are listed in its own section above.

| File | Change |
|---|---|
| `app.py` | `import time`; `_rate_limit_retry_after_seconds()`; `@app.errorhandler(429)` returning JSON with `Retry-After` |
| `tests/ask_pete/test_app_compatibility.py` | Readiness-002's HTML characterization test replaced by the new JSON + `Retry-After` contract |
| `.env.example` | `PEERSLATE_ASK_PETE_GROUNDED_ENABLED=false` documented |
| `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/README.md` | New: this record |
| `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/COMPLETION_REPORT.md` | New: implementation completion record |

---

# RELEASE EVIDENCE

Skeleton only. Every field below is filled by the orchestrator at merge and
deploy time from observed facts, not predicted ones. An unfilled field is an
unmet condition, not an omission. Leave `Not Assessed` where a check genuinely
did not apply and say why.

`PS-ASK-PETE-AI-READINESS-002`'s closeout addendum recorded an open deployment
finding this package inherits: no automatic `batchedCI` run had fired for any
`main` merge since pipeline 610 (2026-08-07 21:31 UTC, source `1806d20c`),
although the merge messages carry no skip marker, and live `/healthz` still
reported release `a00f609a`. **Resolve the trigger state before claiming any
deploy.** Do not queue a manual production run before inspecting the automatic
run state for the exact SHA, per `PS-OPS-001` "Azure production release
reliability".

## Merge facts

- Reviewed implementation candidate SHA:
- Final PR head SHA:
- Azure PR number and target branch:
- Required pipeline validation run and result:
- Squash-merge `main` SHA (exact 40 characters):
- Merged tree verified identical to PR head tree (yes/no):
- `[skip ci]` present in the final squash message (yes/no, and why):

## Deployment facts

- Automatic run for the merged SHA (id, trigger, start time, result):
- If no automatic run fired: the trigger state found, and the action taken:
- Deployed release identity from live `/healthz` (release id + source SHA):
- Live smoke of the affected contract — a refused `/api/chat` request returns
  JSON with `Retry-After` (observed status, content type, header value):
- Real-provider verification of the grounded path, run before any redeploy and
  outside this lane (observed `stop_reason`, whether the reply arrived fenced,
  the resulting answer state, and the question asked):
- Excerpt-discipline verification, same run (for each question: whether every
  citation resolved on the first attempt, whether a corrective retry was made,
  and whether the retry recovered the answer):
- Purpose-contract verification, same run, one line per purpose — the run that
  produced 2/5 predates correction 5, so this needs repeating (for
  `recruiter_brief`: observed summary word count, claim count, citation count,
  follow-up count, boundary claim present, handoff present; for
  `interview_preparation` and general questions: longest `follow_up_question`
  in characters):

## Candidate record — `PS-OPS-001` minimum

Complete this section only if the enablement of
`PEERSLATE_ASK_PETE_GROUNDED_ENABLED` (a consequential-AI transition) is being
admitted. The app-seam correction in this package is Bounded and uses the
normal PR/pipeline/smoke path instead.

- **Exact source SHA:**
- **Immutable artifact (build id / package identity):**
- **Target environment and configuration:**
- **Audience and flag state** (every environment where the flag is set, and its
  value in each):
- **Security, privacy, authorization results:**
- **Migration results:** (expected `Not Assessed` — no schema change)
- **Dependency results:**
- **Accessibility results:**
- **Performance results:**
- **Failure-path results** (provider timeout degradation, manifest/digest
  failure, rate-limit refusal, AI-unavailable state):
- **Newly load-bearing production settings, verified against the actual
  target:** `PEERSLATE_ASK_PETE_GROUNDED_ENABLED`, `ANTHROPIC_API_KEY`
  (observed value state, not the secret)
- **Stop/rollback action and named operator:**
- **Accepted limitation or bounded exception (owner, reason, expiry, blast
  radius, compensating control):**
- **Verdict:** `Pass` / `Conditional` / `Fail` / `Not Assessed`

## Owner decision

- Enablement decision, owner, and date:
- Observation window and who watches it:

Completion record: `COMPLETION_REPORT.md`.
