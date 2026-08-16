# Gate A — Interview Studio AI current-system diagnosis

**Package:** `PS-INTERVIEW-AI-ARCHITECTURE-001`
**Gate:** A (diagnosis only). Gate B does not begin until Pete and Codex accept this.
**Diagnosed at:** Azure DevOps `origin/main` `f7a71739e7a0d88c184f7deee0b0df0e2444a0dc`
**Live observation:** `https://peerslate.com`, anonymous only, 2026-08-15
**Runtime effect of this document:** none.

## Evidence classification

Every statement below carries one of four labels. Nothing is asserted without one.

| Label | Meaning |
|---|---|
| **CONFIRMED** | Read directly in source at the exact SHA above, with file and line cited. |
| **INFERRED** | Supported by source but depends on a runtime condition I did not execute. |
| **OBSERVED** | Seen live, anonymously, against production. |
| **UNVERIFIED** | Could not be checked without credentials, member data, or a paid call. Stated as unknown. |

No production member answer was used. No paid provider call was made. No sign-in was performed.

---

## 1. Interview AI endpoints and UI callers

**CONFIRMED.** Four live AI endpoints, all in `app.py`, all POST, all rate-limited:

| Endpoint | Line | Rate limit | Job |
|---|---|---|---|
| `/api/interview/review` | `app.py:3838` | 6/min | Answer review |
| `/api/interview/improve` | `app.py:3987` | 6/min | Answer revision |
| `/api/interview/nudge` | `app.py:4113` | 8/min | Planning hints |
| `/api/interview/model-answer` | `app.py:4203` | 6/min | Grounded + generic example |

A fifth, `/api/interview/coach` (`app.py:4421`), is retired and returns HTTP 410 with no provider call.

Page routes: `/interview-studio` (`app.py:2063`), `/interview-studio/history` (`app.py:2068`), and legacy redirects `/interview-me`, `/petec/interview-me`, `/petec/interview-studio` (`app.py:2073-2078`).

The single UI caller is `static/js/interview-studio.js` (5,210 lines). A second file, `static/js/homepage-interview-demo.js`, drives the homepage demo.

**OBSERVED.** All four endpoints are behind the sign-in wall in production. Anonymous `POST /api/interview/review` and `/api/interview/nudge` both return `401 {"error":"sign_in_required"}`. `GET /interview-studio` returns `302` to `/auth/sign-in?return_to=/interview-studio`.

**INFERRED.** That 401 body is emitted only by `_interview_api_authenticated_identity()` (`app.py:3730`), which runs only when `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED` is true. So the flag is **on in production**. The default in source is `false` (`app.py:368`), so this is environment configuration, not code.

**Consequence worth flagging:** every `if not authenticated_studio:` branch — the `profile_slug` client parameter, `RESUME_PROFILE_FILES` lookup, `_interview_page_context()` — is **unreachable in production today**. It is still maintained and tested, and it would become live again if the flag flipped. The architecture should decide deliberately whether to keep or retire it.

## 2. The five specialist jobs as they exist today

**CONFIRMED.** Mapping current code to the six specialists in the accepted direction:

| Accepted specialist | Exists today? | Where |
|---|---|---|
| 1. Diagnostician / Router | **No** | No question-classification step exists. `family` and `competency` arrive from the client. |
| 2. Answer Coach | Yes | `interview_review()`, `app.py:3838` |
| 3. Revision Partner | Yes | `interview_improve()`, `app.py:3987` |
| 4. Private History Nudge | **No** | `interview_nudge()` exists but does **not** search History — see below |
| 5. Grounded Example | Partly | `model-answer` mode `member_history`, `app.py:4302` |
| 6. Generic Example | Yes | `model-answer` mode `best_practice`, `app.py:4315` |

**The nudge is not a History nudge.** Its system prompt (`app.py:4159-4167`) explicitly instructs: *"Do not write an example answer, invent a candidate story, claim a specific outcome, or use profile history."* It is a generic planning-hint generator. The accepted direction's specialist 4 — bounded retrieval over the member's own prior answers, metadata and excerpt first, full content only after selection — **does not exist in any form**. This is new construction, not a modification.

`model-answer` also has a third mode, `compare` (`app.py:4378`), which returns a grounded answer and a generic answer together. It is not named in the accepted six.

## 3. Prompt construction and instruction authority

**CONFIRMED.** All five system prompts are **inline Python string literals inside route functions**, built with `%` interpolation at request time:

- review: `app.py:3924-3949`
- improve: `app.py:4056-4070`
- nudge: `app.py:4159-4167`
- model-answer grounded: `app.py:4302-4314`
- model-answer generic: `app.py:4315-4326`

There is **no prompt version identity, no shared foundation, no diff surface, and no rollback unit**. A prompt change is an `app.py` code change that ships through the normal deploy. Nothing records which prompt version produced a given output. Deliverable 4 of the architecture (versioned prompt authority) has no existing structure to build on.

There is no shared "Interview Constitution" text. Common rules — never invent facts, treat opportunity context as untrusted, no scores — are **restated, in different words, in each of the five prompts**. They have already drifted: the review prompt forbids "a score, percentage, average, hiring prediction, or universal framework"; the generic-example prompt forbids "a score or use a universal framework"; the nudge prompt forbids neither.

## 4. Provider, model, timeout, retry, latency, usage, cost

**CONFIRMED.** One module-level client: `client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)` at `app.py:798`. **No timeout and no retry bound are configured.** All four endpoints call `client.messages.create(...)` with no per-request `timeout`.

**CONFIRMED.** Model is `claude-haiku-4-5-20251001`, hardcoded as a literal at four separate call sites: `app.py:3955`, `:4078`, `:4172`, `:4338`. `max_tokens` is 2400 / 1300 / 500 / 1300 respectively.

**CONFIRMED — no cost or token visibility.** `response.usage`, `input_tokens`, and `output_tokens` appear **nowhere** in `app.py`. No token count, latency measurement, or cost figure is recorded for any Interview AI call. There is currently no way to answer "what does Interview AI cost per member per month."

**Two internal precedents already solve the timeout problem** and should be reused rather than reinvented:

- `services/ask_pete/provider.py:174` `_bounded_client()` — applies `PROVIDER_TIMEOUT_SECONDS = 30.0` and `PROVIDER_MAX_RETRIES = 0` via `with_options`, with a documented note that `messages.create` accepts `timeout` but not `max_retries` in anthropic 0.112.0. It has a dedicated test, `tests/ask_pete/test_provider_timeout.py`.
- `services/opportunity_analysis_service.py:1827` — constructs its client with `timeout=` and `max_retries=` directly.

Interview AI is the **only** provider-backed surface with an unbounded client. **INFERRED:** a slow or hanging provider call currently ties up a worker until the platform's own socket timeout, with no application-level bound. I did not reproduce this.

## 5. Input handling, schemas, validation, failure copy

**CONFIRMED — this is the strongest part of the current system.** Four validators, all in `app.py`, run on every provider reply before anything reaches the member:

- `validate_interview_review` (`app.py:3402`)
- `validate_interview_model_answer` (`app.py:3541`)
- `validate_interview_nudge` (`app.py:3650`)
- `validate_interview_improvement` (`app.py:3675`)

They are strict: they reject non-objects, numeric or universal scoring fields, missing or duplicate list items, invalid dimension keys and statuses, and — critically — **any evidence ID the request did not authorize** (`'review referenced unauthorized evidence'`). Malformed output produces HTTP 502 and honest copy ("The coach returned an unreadable review"), never partial coaching.

Input bounds are enforced server-side: question and answer length caps, opportunity context capped at 4,000 characters, `improvements` capped at 4 items, `evidence_ids` capped at 2 and checked for duplicates and membership (`app.py:4046`), `attempt` bounded to a 1–1000 integer with a deliberately permissive default (`app.py:3869-3871`), and `level` / `family` / `practice_mode` / `mode` all normalized to closed enums.

**This is the part of the system the architecture should preserve and generalize, not replace.** The evidence-entitlement check in particular is already a deterministic guardian of exactly the kind deliverable 6 asks for.

## 6. Identity, authorization, injection separation, rate limits

**CONFIRMED.** Identity is server-derived via `get_current_identity()` inside `_interview_api_authenticated_identity()` (`app.py:3730`). Signed-out callers get JSON `401`, never a redirect or replay. An identity-store outage returns `503` with `Retry-After: 5`. All responses carry `Cache-Control: private, no-store`.

**CONFIRMED.** When the flag is on, the client-supplied `profile_slug` is **never read into a variable** — the `if not authenticated_studio:` guard prevents assignment entirely (`app.py:3876`, `:4021`, `:4141`, `:4225`). This is a stronger construction than reading-then-ignoring, and the comments say so deliberately.

**CONFIRMED — injection boundary.** `_untrusted_opportunity_block()` (`app.py:3356`) **base64-encodes** visitor-supplied text before placing it in the prompt, specifically so a visitor cannot forge a lookalike END delimiter and escape the boundary. The docstring is explicit that base64 is "an envelope, not a trust upgrade." Every prompt separately instructs that this content is role reference and never instructions.

**CONFIRMED.** `_cross_site_refusal('interview')` runs on all four endpoints. Rate limits are per-endpoint as tabled in section 1.

**CONFIRMED — signed follow-up context.** `_sign_interview_model_context` / `_load_interview_model_context` (`app.py:4254`, `:4386`) carry follow-up state in a signed token, and the opportunity-context digest is compared with `hmac.compare_digest` (`app.py:4257`). A mode mismatch between token and request is rejected (`app.py:4269`).

**CONFIRMED — a deliberate server-side refusal worth preserving.** Follow-ups are refused outright on the authenticated surface (`app.py:4249-4250`) because, while `interview_followup_mode_provenance` is open, nothing in the response can state which grounding mode a follow-up came from. The comment notes the client was previously the only thing preventing it and moves the boundary to the server. This is the correct instinct and the architecture should keep it until provenance is designed.

## 7. Source-class boundaries

**CONFIRMED.** Distinct classes and their current provenance:

| Source class | Origin | Trust |
|---|---|---|
| Current question | Client-supplied | Bounded, not verified |
| Current answer | Client-supplied | Bounded, reviewed verbatim |
| Question family / competency / level | Client-supplied | Normalized to closed enums |
| Opportunity context | Client-supplied | Bounded 4,000 chars, base64-enveloped, untrusted |
| Profile evidence | **Server-derived from identity** | Allowlisted by ID, enforced by validator |
| Private History | Browser localStorage | **Never sent to the provider** |
| Role Context | **Does not exist** | Direction recorded, not implemented |

**CONFIRMED — the single most consequential product finding.** `_interview_identity_evidence_context()` (`app.py:1972`) returns the `petec` fixture **only for the owner**, and for every other authenticated member returns `(profile, [])` — an **empty evidence list**.

The docstring is explicit: *"Every other authenticated member gets their own, currently empty, evidence set."*

The consequence: for any member who is not Pete, the Grounded Example specialist has nothing to ground against and can only return `status: "insufficient"`. The evidence-suggestion path in review is likewise always empty. **Interview AI's evidence grounding is, today, an owner-only fixture.** The architecture cannot propose a working Grounded Example specialist for real members until member-owned evidence exists — which is Profile work, outside this package. This belongs in the owner decision register, not buried in a design.

## 8. Persistence, History, answer versions, deletion

**CONFIRMED — there is no server-side Interview History.** A repository-wide search for `InterviewHistory`, `interview_history`, and `InterviewAnswer` across all `.py` and `.sql` files returns **nothing**. No table, no migration, no service.

**CONFIRMED.** History is browser `localStorage` only, in `static/js/interview-studio.js`:
- key `storagePrefix + ':history'` (`:55`), where signed-in members get a member-scoped `:v3` namespace and anonymous visitors a `profileSlug`-based `:v2` namespace (`:52-54`, `:353`)
- a scoped namespace **never reads, adopts, or deletes** the anonymous records (`:352-357`, recorded as owner decision Q-B) — correctly isolated
- an in-code comment states plainly: *"localStorage is not server-validated"* (`:2039`)
- **records are silently capped at 100** — `writeJSON(historyKey, records.slice(0, 100))` (`:1983`). The 101st practice answer silently evicts the oldest, with no member notice.

**Gaps against the accepted direction, all CONFIRMED:** History today is not account-backed, not cross-device, not searchable, not correctable, not archivable, not server-deletable, and not revocable from any index or embedding — because no server-side index or embedding exists. Clearing browser data destroys it. A second device shows an empty History.

This is the largest single gap between current state and accepted direction, and it is a prerequisite for specialist 4. Specialist 4 cannot be built on `localStorage`.

**UNVERIFIED.** Whether answer *versions* are preserved within a browser record — I read the storage and cap logic but did not trace the full record shape through the 5,210-line file. Gate B must confirm before designing the Revision Partner's compare/apply/discard/restore contract.

## 9. Telemetry and log content safety

**CONFIRMED — the deliberate path is content-free.** `_log_interview_failure()` (`app.py:3821`) logs only: a reason code, the exception class name, the provider stop reason, and a **character count**. Its docstring states candidate answers and model text never enter the log line.

**CONFIRMED — the validator errors it logs are safe.** I checked every `raise` in the four validators (`app.py:3402-3720`): all messages are **fixed string literals** (`'review is not an object'`, `'duplicate dimensions'`, `'review referenced unauthorized evidence'`). No member content or model text is interpolated into any of them. So the `detail=%s` field is content-free on the validation path.

**INFERRED — one residual risk.** The generic handler on each endpoint (`app.py:3983`, `:4109`, `:4199`, `:4417`) logs `app.logger.error('... API error: %s', e)` for *any* unexpected exception. If the provider SDK ever raises an error whose string representation embeds request or response body content, that content reaches the log. I did not trigger such an error and cannot confirm the SDK's behavior. Gate B should treat this as a real hole to close deterministically rather than assume it is safe.

**CONFIRMED — no routine success telemetry exists at all.** Nothing is recorded on the success path: no latency, no token count, no cost, no per-specialist volume. Section 4's finding and this one are the same absence seen from two sides.

## 10. Test coverage and gaps

**CONFIRMED.** `tests/test_interview_studio.py` contains **306 test functions** — substantial and the single largest interview asset.

**UNVERIFIED — what those 306 tests actually assert.** I counted them and read the endpoint code they exercise, but did not read all 306 bodies. Gate B must map them to the decision-to-enforcement matrix before claiming any accepted rule is test-covered. I will not assert coverage I have not read.

**CONFIRMED gaps, from absence of the code they would test:**
- no timeout or retry test for Interview (contrast `tests/ask_pete/test_provider_timeout.py`, which exists for Ask Pete)
- no cost/token telemetry test, because no such telemetry exists
- no server-side History test, because no server-side History exists
- no prompt-version or rollback test, because prompts have no version identity

## 11. Discrepancies: code vs live vs accepted direction

Ordered by consequence.

**11.1 — Hardcoded answer length contradicts accepted direction. CONFIRMED.**
The accepted direction states: *"Answer length follows the actual question obligations. There is no universal 45–90 second rule and no automatic three-minute target."*
Three current prompts hardcode a universal band:
- improve: `'"draft":"<60-120 second spoken answer>"'` (`app.py:4067`)
- grounded model answer: `'"answer":"<natural 60-120 second answer>"'` (`app.py:4309`)
- generic model answer: `'"answer":"<natural 60-120 second example>"'` (`app.py:4324`)
This is a direct, live contradiction of accepted direction, in production today.

**11.2 — Specialist 4 does not exist and is mis-implied by the name. CONFIRMED.** The `nudge` endpoint is a generic hint generator that is explicitly instructed *not* to use history (`app.py:4162`). Anyone reading the endpoint list would reasonably assume the History Nudge exists. It does not.

**11.3 — Evidence grounding is owner-only. CONFIRMED.** Section 7. For non-owner members the grounded path can only return "insufficient."

**11.4 — Private History is not private-by-architecture, it is merely local. CONFIRMED.** Section 8. The accepted direction's revocability, searchability, and deletion guarantees cannot be honored by `localStorage`, and the 100-record cap silently destroys member work.

**11.5 — No prompt versioning or rollback. CONFIRMED.** Section 3. The accepted direction's versioned specialist instructions with immutable release identity have no current foundation.

**11.6 — Unbounded provider client. CONFIRMED.** Section 4. Interview is the only AI surface without a timeout, and two internal precedents already exist.

**11.7 — Shared rules have already drifted across five copies. CONFIRMED.** Section 3.

**11.8 — Dead public branch in production. CONFIRMED.** Section 1. Maintained, tested, unreachable.

**11.9 — Structured output is real but partial. CONFIRMED.** Responses are genuinely structured JSON with named fields, satisfying "not one text blob." But `strongerApproach`, `focusedFollowUp`, and `draft` are each single prose blobs within that structure.

## Confirmed gap register

| # | Gap | Severity | Blocks |
|---|---|---|---|
| G1 | No account-backed History | High | Specialist 4; all revocation/deletion guarantees |
| G2 | Member evidence empty for non-owners | High | Specialist 5 for real members |
| G3 | Universal 60–120s length rule live | High | Accepted adaptive-length direction |
| G4 | No prompt version identity or rollback | High | Deliverable 4; any safe prompt change |
| G5 | Unbounded provider client | Medium | Failure matrix; member-visible hangs |
| G6 | No cost/token/latency telemetry | Medium | Provider bake-off; owner cost decisions |
| G7 | Generic exception logs unbounded `%s` | Medium | Content-free telemetry guarantee |
| G8 | History capped at 100, silent eviction | Medium | Member work preservation |
| G9 | Shared rules duplicated and drifted | Medium | Shared constitution |
| G10 | Dead public branch reachable if flag flips | Low | Scope clarity |

## What I did not verify

Stated plainly so nothing here is over-claimed:

1. The bodies of all 306 tests — counted and located, not read.
2. Answer-version record shape inside browser History.
3. Any authenticated live behavior — no sign-in was performed, per the handoff.
4. Real provider latency, token, or cost figures — no paid call was made.
5. Whether the Anthropic SDK's exception strings can carry body content (section 9 residual).
6. `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED`'s literal production value — inferred from live 401 behavior, not read from configuration.

## Owner decisions this diagnosis surfaces

These are for Pete, before or alongside Gate B. They are not design questions.

1. **Grounded Example for real members is blocked by G2.** Member evidence is Profile work, outside this package. Should Gate B design specialist 5 against a future member-evidence contract, or defer specialist 5 entirely to a later slice?
2. **G3 is live and contradicts accepted direction today.** Do you want the 60–120 second rule corrected as a small separate fix now, or held inside the architecture's first implementation slice?
3. **The dead public branch (11.8).** Keep it maintained, or retire it as part of the first slice?
4. **History migration.** When account-backed History is built, is browser-local History imported for existing members, or does History start fresh from that date?

---

*Gate A ends here. No architecture is proposed in this document. Gate B begins only on Pete and Codex acceptance.*
