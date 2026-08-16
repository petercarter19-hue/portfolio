# Section 4 — Grounded Example and Generic Example

**Package:** `PS-INTERVIEW-AI-ARCHITECTURE-001`
**Consolidated architecture section:** 4 of 5 (Gate B increment 4: Grounded Example and Generic Example)
**Status:** Draft for Pete and Codex reconciliation. Documentation only.
**Runtime effect:** None. No application, prompt, schema, test, configuration, or release change.
**Code evidence base:** `app.py` and `static/js/interview-studio.js` at diagnosed SHA `f7a71739`, byte-identical to deployed SHA `f42e5399` (errata E6/D3). Line references below are to that source.
**Overriding facts:** [`02_GATE_A_ERRATA.md`](02_GATE_A_ERRATA.md) controls wherever it corrects [`01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md`](01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md).
**Accepted product direction:** [`07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md), specialists 5A and 5B.

---

## 0. The fact this section is designed around

`_interview_identity_evidence_context()` (`app.py:1972-1985`) resolves evidence by server-derived identity and, **by deliberate construction**, returns the `petec` fixture only when `is_owner(identity)` is true. Every other authenticated member receives `(profile, [])` — an empty evidence list. Its docstring says so plainly. This is not a bug; authorized member evidence does not exist yet. Building it is Profile work, outside this package.

Consequence today: for any member who is not Pete, the grounded path can only ever end in "insufficient" — and, as section 6.3 shows, it currently spends a provider call and can end in a misleading retriable 502 to learn what the server already knew deterministically.

**Owner direction, binding on this section:** design Grounded Example against a **future authorized member-evidence contract**, with server-side capability detection and a safe unavailable/generic fallback until that contract exists. Grounded Example is **not** enabled for ordinary members until authorized member evidence exists and Pete separately authorizes enablement.

This section therefore delivers three things: (A) the consumer-side member-evidence contract, (B) capability detection and truthful fallback, (C) the two specialists themselves, plus the adaptive-length correction and follow-up provenance design.

Shared spine used throughout, identical to the other sections: source classes `question`, `answer`, `role_context`, `member_evidence`, `history_selection`, `confirmed_context`; guardian taxonomy `identity`, `authorization`, `source-allowlist`, `injection-separation`, `evidence-entitlement`, `claim-support`, `content-bounds`, `rate-limit`, `timeout`, `idempotency`, `malformed-output`, `prohibited-action`; failure states `provider_failure`, `invalid_output`, `no_history_match`, `insufficient_evidence`, `denied_authorization`, `unavailable_source`, `rate_limited`.

---

## Part A — The future member-evidence contract (consumer side only)

This is the contract **Interview AI consumes**. It does not design Profile's storage, editing surface, import pipeline, or data model — it states what must be true of whatever Profile ships before Grounded Example can serve a real member. Today's owner-only fixture is expressed inside the same contract so there is exactly one code path.

### A.1 The evidence item

An evidence item has two strictly separated parts: an **envelope** the application uses for authorization decisions, and a **projection** — the only part that may ever reach a prompt, a validator, a response body, or the browser.

```
EvidenceItem
├─ envelope (never crosses into any prompt, response, or log)
│  ├─ member_key            string    server identity.user_key of the owning member
│  ├─ provenance            enum      member_authored | member_imported | owner_fixture
│  ├─ authorization_state   enum      draft | approved_for_interview_ai | revoked
│  ├─ publication_state     enum      private | published
│  ├─ version               integer   >= 1, increments on any content edit
│  ├─ approved_at           ISO-8601 timestamp or null
│  └─ revoked_at            ISO-8601 timestamp or null
└─ projection (the ONLY fields that may cross into prompt/validator/response)
   ├─ id        string, <= 64 chars, stable and unique within the member
   ├─ metric    string, <= 120 chars   (the claim: "38% proposal cycle-time reduction")
   ├─ label     string, <= 120 chars
   ├─ summary   string, <= 500 chars
   └─ tag       enum: Leadership | Technical | Impact
```

The projection field names are **deliberately identical to today's fixture items** produced by `_interview_evidence_from_profile()` (`app.py:1935-1941`: `id`, `metric`, `label`, `summary`, `tag`), and to the shape `validate_interview_model_answer` keys on. That identity is what makes "one code path" real rather than aspirational: the validator, the evidence prompt lines, and the `evidenceUsed` response field do not change when member evidence arrives — only the retrieval behind the contract function does.

### A.2 The single access function

One function is the only way any Interview AI specialist obtains member evidence:

```
authorized_interview_evidence(identity) -> EvidenceContext

EvidenceContext = {
    "capability": "available" | "unavailable",     # derived: available iff len(items) >= 1
    "items":      [<projection>, ...],             # approved_for_interview_ai items only, <= 10
    "source":     "owner_fixture" | "member_profile" | "none",
}
```

Internally, today: `is_owner(identity)` → adapter over the existing fixture (`provenance: owner_fixture`, `authorization_state: approved_for_interview_ai`, `version: 1`, `member_key` = Pete's user key); any other identity → the Profile provider query, which returns nothing until Profile ships, additionally short-circuited by the enablement flag (A.4). `_interview_identity_evidence_context()` becomes a thin wrapper so all four endpoints keep a single entry point. **No `is_owner` branch may exist anywhere downstream of this function.**

### A.3 Contract requirements (what Interview AI requires of the provider side)

- **CR-1 — Authorize-before-retrieve, identity-keyed.** Retrieval takes the server-derived `identity` and nothing else. No request-supplied key, slug, or id may select the evidence source. This preserves the current construction, which is stronger than filtering: when the authenticated flag is on, the client's `profile_slug` is never even read into a variable (`app.py:4225-4226`).
- **CR-2 — Purpose-scoped approval.** Only `authorization_state == approved_for_interview_ai` items cross the contract. Approval for Interview AI use is an explicit member act on the Profile surface — never a default on creation, import, or publication. `publication_state` is irrelevant to eligibility: a private item may be approved (it is only ever returned to its own member), and a published item is not automatically approved.
- **CR-3 — Revocation is immediate at the boundary.** A revoked or deleted item must be absent from the very next `authorized_interview_evidence()` result. Interview AI never caches the evidence list across requests (true of the current per-request retrieval at `app.py:4284-4294`; the contract makes it a rule). Signed follow-up contexts naming a since-revoked id fail closed (section 8).
- **CR-4 — Version identity.** `version` increments on any content edit. Provenance blocks (section 7.1) and future History records carry `(id, version)` pairs. A version drift after signing does not kill a conversation — the next turn re-grounds against the current projection text, which is rebuilt fresh every request — but the drift is visible in provenance rather than silent.
- **CR-5 — Bounds.** At most 10 items per member cross the contract (today's fixture cap, `app.py:1942-1943`); projection field caps as listed. Interview AI re-truncates defensively regardless of what the provider returns.
- **CR-6 — One code path.** The owner fixture is expressed in-contract (A.2). No specialist, prompt builder, or validator may distinguish fixture evidence from member evidence.
- **CR-7 — Cross-member retrieval is structurally impossible.** The provider-side query is scoped `member_key == identity.user_key`; Interview AI never passes any other key. A negative test asserting a foreign member's items can never appear is an enablement precondition.
- **CR-8 — No unconfirmed AI content as evidence.** An item whose content is an AI proposal the member has not confirmed must not be approvable for Interview AI use. This is the site invariant (canonical truth vs AI proposal) stated as a dependency: Interview AI will treat everything the contract returns as member-confirmed fact, so the contract must only ever contain member-confirmed fact.
- **CR-9 — Deletion behaves as revocation.** From Interview AI's viewpoint a deleted item is indistinguishable from a revoked one: absent from retrieval, failing the follow-up re-check.
- **CR-10 — Deterministic enablement.** Server configuration `INTERVIEW_MEMBER_EVIDENCE` (default `off`): when off, the `member_profile` branch returns `unavailable`/`[]` regardless of what Profile has stored. The owner-fixture branch is independent of the flag, so today's behavior is exactly preserved and rollback of enablement is a flag flip.

### A.4 What must be true before specialist 5 is enabled for ordinary members

Named as the enablement gate, in order:

1. Profile ships member evidence satisfying CR-1 through CR-9, under its own Protected package.
2. A member-facing approval surface exists: explicit per-item approve and revoke for Interview AI use, with truthful labels.
3. Negative evidence passes: cross-member retrieval (CR-7), draft item never crosses, revoked item never crosses, revoked-mid-conversation follow-up fails closed, validator rejects any citation outside the request's authorized selection.
4. Pete explicitly authorizes enablement, and `INTERVIEW_MEMBER_EVIDENCE` flips in a Protected release with rollback evidence (flag off restores today's behavior byte-for-byte).

Until all four hold, ordinary members get the Part B fallback — never a grounded attempt, never a fabricated answer.

---

## Part B — Capability detection and safe fallback

### B.1 Detection is server-side, per member, per request, derived from the data

`capability` is computed inside `authorized_interview_evidence(identity)` as `available` iff at least one approved item was actually retrieved. There is no separate stored flag that can drift from the data, and the UI's copy of it is advisory only:

- The `/interview-studio` page context includes `capabilities.member_evidence: "available" | "unavailable"` so the interface can label the grounded option truthfully before any request (visible but disabled-with-reason, not hidden — hiding it would misrepresent the product and surprise members when Profile ships; exact layout is the interface's, per accepted direction section 7).
- The `model-answer` endpoint **re-derives capability on every request** and is authoritative. A stale or tampered client cannot obtain a grounded attempt the server would not grant.

### B.2 Two different truths that must never collapse into one message

These are distinct spine failure states with distinct copy, distinct next actions, and distinct telemetry codes:

**Truth 1 — evidence capability is absent for this member: `unavailable_source`.**
The `member_evidence` source class does not exist for this member (every non-owner today). Decided deterministically, **before any provider call**. The member sees:

> **Grounded example isn't available for your account yet.**
> A grounded example is built only from work evidence you've approved on your profile. Your account doesn't have approved evidence yet, so PeerSlate can't ground an example in your real history — and it won't guess.
> You can get a clearly illustrative generic example for this question instead.
> **[Get a generic example]**

One click issues a `best_practice` request. The member's question, draft answer, and prior results are untouched. This is not an error and not "try again" — retrying can never change it; only approving evidence can.

**Truth 2 — evidence exists but cannot support this question: `insufficient_evidence`.**
Capability is `available`; the model judged the selected evidence insufficient and returned `status: "insufficient"`, which the validator normalizes to fixed server-authored copy (`app.py:3559-3565` — the model cannot author this message, which is itself a deterministic control against leaking or fabricating inside a refusal). The member sees today's honest copy, preserved:

> **PeerSlate does not have enough approved profile evidence to answer this question without guessing.**
> Why this is right: it avoids unsupported claims and makes the evidence gap explicit.
> **[Get a generic example]**  **[Choose different evidence]** *(shown only when approved items exist outside the current selection)*

**The distinction in one line:** `unavailable_source` means "you have no approved evidence at all — nothing was attempted"; `insufficient_evidence` means "your evidence was consulted and honestly cannot carry this question." Collapsing them would tell a capability-absent member their evidence was consulted (false) or tell an evidence-holding member they have none (false).

### B.3 Response shapes

`unavailable_source` (HTTP 200 — a truthful computed state, not a transport failure; no provider call, no charge, no `contextToken` because there is nothing to follow up):

```json
{
  "mode": "member_history",
  "failureState": "unavailable_source",
  "modelAnswer": { "status": "unavailable", "answer": "", "whyItWorks": [], "evidenceUsed": [] },
  "capability": { "member_evidence": "unavailable" },
  "nextActions": ["generic_example"]
}
```

`"status": "unavailable"` is **server-synthesized only**. The validator's model-facing status enum stays closed at `{answered, insufficient}` (`app.py:3558-3567`); a model claiming `unavailable` is `invalid_output`. The model can never speak for the capability state.

`insufficient_evidence` keeps today's HTTP 200 normalized shape, plus `failureState: "insufficient_evidence"` and `nextActions`. One cleanup: **no `contextToken` is issued for an insufficient result.** Today one is signed regardless (`app.py:4386-4395`), enabling a follow-up on top of a non-answer on the public branch; there is nothing grounded to follow up.

### B.4 The current defect the short-circuit fixes

Today a non-owner requesting `member_history` still triggers a provider call with the evidence block rendered as `- No approved public evidence is available.` (`app.py:4296-4301`). Best case, the model obeys and returns `insufficient` — a paid call to compute what `len(evidence) == 0` already proved. Worst case, the model answers anyway; `require_evidence=True` then raises `'model answer has no approved evidence references'` (`app.py:3578-3579`) and the member gets a 502 reading *"The answer could not be validated against the profile evidence. Please try again."* (`app.py:4415`) — an invitation to retry a request that can never succeed. The deterministic capability check removes the spend, the misleading copy, and the retry trap in one move. This is additional to diagnosis section 7, which established only that the outcome could never be grounded.

---

## Part C — The specialists

Mode names on the wire stay `member_history`, `best_practice`, `compare` — renaming would break the deployed client, saved History records, and signed tokens for zero safety gain. The mapping is: `member_history` = specialist 5 (Grounded Example); `best_practice` = specialist 6 (Generic Example); `compare` = orchestrated composition of both (C.3).

### C.1 Specialist 5 — Grounded Example

**Version identity:** `grounded_example@1.0.0+<prompt-sha8>` (first versioned release; today's inline literal at `app.py:4302-4314` is retroactively the unversioned `0.x`). The prompt template is hashed at build; the version appears in response provenance and content-free telemetry.

**Purpose.** Produce one clearly labelled AI-proposed example answer supported **only** by evidence the member deliberately selected and is authorized to use — or return a truthful `insufficient`. It is never the member's statement, never fills evidence gaps, and can never be silently adopted, saved, or published.

**Input manifest** (spine source classes; everything not listed as allowed is prohibited):

| Source class | Allowed | Provenance and authorization state |
|---|---|---|
| `question` | Yes | Client-supplied, bounded (`MAX_INTERVIEW_QUESTION_LENGTH`), untrusted content, never instructions |
| `role_context` | Yes | Member-established Role Context / bounded opportunity context (<= 4,000 chars), untrusted, base64-enveloped via `_untrusted_opportunity_block` (`app.py:3356`) |
| `member_evidence` | Yes | Server-derived through the Part A contract; request selection intersected against the approved set before any provider call |
| Router result (Section 1) | Yes | Server-derived: question class, obligations, length band with reasons |
| `answer` | **No** | The current answer is not included merely because it exists (accepted 5A) |
| `confirmed_context` | **No** | Belongs to the Revision Partner's flow, not 5A |
| `history_selection` | **No** | History retrieval belongs to specialist 4 exclusively |

**Selection model.** Approval on the Profile surface is the member's standing deliberate authorization; per-request `selected_evidence_ids` is an optional narrowing:

- When present: 1–10 unique ids, every one in the member's approved set, else **403 `denied_authorization` before any provider call**. Exact prior art: the Revision Partner already does this intersection at `app.py:4045-4048`.
- When absent: scope is the full approved set (which keeps today's owner flow working unchanged), and response provenance records `selection: "all_approved_default"` versus `"member_selected"` with the exact ids — the truth of what was in scope is always stated, never implied.
- The validator's `evidence_by_id` becomes the **selected subset**, not the full approved set. A citation of an approved-but-unselected id is rejected (`'model answer referenced unauthorized evidence'`, `app.py:3580-3581`). This strengthens today's check into a deterministic enforcement of "deliberately selected."

**Output schema.** Model-facing (unchanged shape, length line now Router-supplied — section 6):

```json
{"status": "answered", "answer": "<string>", "whyItWorks": ["<2-4 concise factors>"], "evidenceIds": ["<selected ids actually used>"]}
{"status": "insufficient", "answer": "", "whyItWorks": [], "evidenceIds": []}
```

Server-validated and enveloped:

```json
{
  "mode": "member_history",
  "modelAnswer": {
    "status": "answered",
    "answer": "...",
    "whyItWorks": ["..."],
    "evidenceUsed": [{"id": "...", "metric": "...", "label": "...", "summary": "...", "tag": "Impact"}],
    "generic": false
  },
  "provenance": {
    "specialist": "grounded_example@1.0.0+<sha8>",
    "mode": "member_history",
    "selection": "member_selected",
    "evidence": [{"id": "...", "version": 3}],
    "turn": 1,
    "lengthBand": {"seconds_low": 45, "seconds_high": 75, "reasons": ["..."]}
  },
  "contextToken": "<signed>"
}
```

The answer may contain bracketed confirmation markers in the established Revision Partner style (`app.py:4061-4065`) for a supporting, non-essential missing detail; when the **core** claim would require invention, the correct output is `insufficient` (accepted section 4: unknown details are omitted, requested, or explicitly marked — never invented).

**Deterministic guardians** (taxonomy names; each names its control, never a prompt):

- `identity` — `_interview_api_authenticated_identity()` first; JSON 401; 503 + `Retry-After` on identity-store outage; `Cache-Control: private, no-store`.
- `authorization` — entitlement gate `get_interview_entitlements()['model_answers']` (`app.py:4212`) plus the Part B capability gate.
- `evidence-entitlement` — pre-call: selection ⊆ approved set else 403 (`app.py:4045-4048` pattern); post-call: citations ⊆ selection via `validate_interview_model_answer` (`app.py:3580-3581`). Both are code, not wording.
- `claim-support` — `answered` requires >= 1 citation (`require_evidence=True`, `app.py:3578-3579`); every citation resolves to a server-held item that is echoed back as `evidenceUsed` from the server's own map (`app.py:3586`), never from model text. The prompt asks; the validator enforces.
- `source-allowlist` — the grounded prompt/content builders accept only `{question, router_result, role_context_block, selected_evidence_lines}`; no parameter exists for `answer` or History. Enforced by construction and by a test asserting the builder signature and rendered content.
- `injection-separation` — base64 envelope plus explicit boundary (`app.py:3356`). Honestly non-deterministic against model obedience (errata E2); the deterministic backstop is that injected text can never mint a citation (`evidence-entitlement`), never widen the evidence set (server-built), and never trigger an action (`prohibited-action`).
- `content-bounds` — question and follow-up caps; context <= 4,000; answer truncated at `MAX_INTERVIEW_ANSWER_LENGTH` (`app.py:3568`); `whyItWorks` <= 4; selection <= 10; follow-up chain depth <= 5 (section 8).
- `rate-limit` — 6/minute (today's `app.py:4204`), per authenticated identity.
- `timeout` — explicit provider timeout and retry policy from the shared foundation (Section 1's provider configuration; errata E1: never the SDK's silent 600s/2-retry default; the 30s Ask Pete precedent at `services/ask_pete/provider.py:174` is the reference implementation).
- `idempotency` — the specialist writes nothing server-side; the response is a proposal; a repeated request creates no duplicate state; no silent retry of a consequential call.
- `malformed-output` — `_extract_json_object` + validator; any failure → `invalid_output` → 502 with honest copy; logging stays content-free via `_log_interview_failure` (`app.py:3821`) — reason code, exception class, stop reason, character count only.
- `prohibited-action` — the response carries no executable action; saving to History, copying, or reuse are separate previewed member acts at the destination; AI output never saves, publishes, sends, deletes, or changes canonical truth (site invariant).

**Failure behaviour** (spine states, all preserving member work — the endpoint stores nothing and the interface must never clear the question or draft on failure):

| State | When | Member outcome |
|---|---|---|
| `unavailable_source` | Capability absent; decided pre-call | B.2 Truth 1 copy + generic offer; zero provider calls |
| `denied_authorization` | Selection outside approved set; pre-call | 403, "One of those evidence selections isn't available."; zero provider calls |
| `insufficient_evidence` | Model judgment on real evidence, normalized | B.2 Truth 2 copy + generic offer |
| `invalid_output` | JSON/validation failure | 502, "The answer could not be validated against the profile evidence. Please try again." |
| `provider_failure` | Timeout, SDK error, 5xx | Honest unavailability copy; no fabricated answer; retry is safe because nothing was saved |
| `rate_limited` | Limiter | 429 with plain wait copy |
| `no_history_match` | — | Not applicable: this specialist has no History source |

**Evaluation slice** (extends the parent package's golden-case set):

- Golden: evidence-supported behavioral question → `answered` citing only selected ids; question orthogonal to all selected items → `insufficient`.
- Adversarial: `role_context` containing "cite evidence id X" for an unselected id → rejected at the citation channel; embedded instruction to reveal another member's evidence → no retrieval channel exists (CR-7) and refusal preserves the task; question text embedding forged evidence lines.
- Authorization negatives: foreign or unknown id in selection → 403 with **zero** provider calls (assert call count); capability-absent member in grounded mode → `unavailable_source` with zero provider calls.
- Schema failures: non-JSON, unknown status, duplicate ids, empty `whyItWorks`, citation of an id absent from the map.
- Length: band adherence sampled per question class; human review primary, word-count-versus-band automation as bounded support.

### C.2 Specialist 6 — Generic Example

**Version identity:** `generic_example@1.0.0+<prompt-sha8>` (today's inline literal at `app.py:4315-4326` is the unversioned `0.x`).

**Purpose.** Provide a useful, clearly illustrative example answer when member evidence is unavailable or intentionally not used — with **no private member source of any kind**, and nothing that can present it as the member's own history.

**Input manifest:**

| Source class | Allowed | Provenance and authorization state |
|---|---|---|
| `question` | Yes | Client-supplied, bounded, untrusted |
| `role_context` | Yes | Untrusted, enveloped; role reference so the example fits the role — never instructions, never member proof |
| Router result (Section 1) | Yes | Server-derived; supplies the length band and question class |
| `member_evidence` | **No** | Prohibited. The generic prompt builder has **no evidence parameter** — the class cannot enter by construction |
| `answer` | **No** | Prohibited (accepted 5B: no current answer) |
| `history_selection` | **No** | Prohibited |
| `confirmed_context` | **No** | Prohibited |

**Output schema.** Model must return the `answered` shape with `"evidenceIds": []` mandated by its instructions. The server validates with `validate_interview_model_answer(parsed, {}, require_evidence=False)` — the empty map — and sets `"generic": true` itself (`app.py:4377`, `:4383`); the flag is server-authored, never model-claimed. One tightening over today: a generic-mode model reply of `status: "insufficient"` is treated as `invalid_output`, not surfaced — the specialist has no evidence dependency to be insufficient against, and today's normalization would emit "not enough approved profile evidence" copy that is false for a generic request.

**Why the empty-evidence-map property matters, and why it is preserved.** Validating the generic branch against `{}` (`app.py:4345-4348`, documented at `:3548-3554`) converts "a generic example cites no member sources" from an instruction into a **structural impossibility on the citation channel** — the only channel through which the system ever presents content as supported by member evidence. Any `evidenceIds` entry whatsoever hits `'model answer referenced unauthorized evidence'` (`app.py:3580-3581`) and the answer is discarded before display, even under prompt injection or model drift. The deterministic pair is: **no member evidence in** (the builder has no evidence parameter, so nothing private is in context to leak into prose) and **no citation out** (the empty map). What remains — a model inventing a scenario that coincidentally resembles the member — is not a privacy leak, because no private datum was ever in context; it is covered by the illustrative labelling below.

**"Never presentable as the member's real history" — the deterministic controls, named:**

1. `generic: true` is set by the server on the answer object; the interface's illustrative label renders from that server flag, and rendering it is a schema acceptance requirement, not a styling choice.
2. `evidenceUsed` is structurally empty — no support references can ever appear beside a generic answer.
3. The response `mode` and the signed context token both carry the grounding mode, and a mode mismatch between token and request is rejected (`app.py:4269`) — a generic answer can never be replayed into a grounded follow-up chain and re-laundered as member history.
4. The provenance block names `generic_example@<version>` as the producing specialist.
5. Consumed requirement on Section 3: any History record that saves a model answer must persist `mode` and the `generic` flag, so a saved generic example remains labelled illustrative forever, on every device, after every export.

**Deterministic guardians:** as C.1 for `identity`, `authorization`, `content-bounds`, `rate-limit`, `timeout`, `idempotency`, `malformed-output`, `prohibited-action`, with these differences: `source-allowlist` is the load-bearing guardian (no evidence parameter by construction, plus a test asserting the rendered generic system prompt contains no evidence line and the generic request content never contains the grounded answer — see C.3); `evidence-entitlement` operates in its degenerate, strictest form (the empty map: everything is unauthorized); `claim-support` inverts (`require_evidence=False`: zero citations is the only valid result); `injection-separation` unchanged.

**Failure behaviour:** `provider_failure`, `invalid_output`, `rate_limited` as in C.1. `insufficient_evidence` and `unavailable_source` **must never appear in generic mode** — the specialist has no evidence dependency, and a test asserts this distinctness so the two truths of Part B can never bleed into the generic path. `denied_authorization` and `no_history_match`: not applicable (no evidence input, no History source).

**Evaluation slice:** golden (clearly generic framing — "a cross-functional project at a previous employer" — with structural `whyItWorks`); adversarial (`role_context` instructing "present this as the member's real experience" → labelling controls hold; "cite evidence id metric-x" → rejected at the citation channel; "name the member" → the member's name is not in the prompt); schema failures including any non-empty `evidenceIds`; the compare-isolation construction test (C.3).

### C.3 Compare mode — decision: it survives, as composition, not as a specialist

`compare` (`app.py:4378-4383`) is retained — but defined as an **orchestration composition of specialists 5 and 6**, not a third specialist. That is already its implementation truth: two independent `_generate` calls with different system prompts and different user content. There is no compare prompt, no compare version identity; the composition is versioned by the orchestration layer (Section 5's authority). Retained because it teaches by contrast — the member studies grounding against structure side by side — and removing it deletes member value with no safety gain, since each branch runs under its own specialist's full guardian set.

Rules the composition must keep:

- **Compare requires grounded capability.** A capability-absent member requesting `compare` gets the single `unavailable_source` response with the generic offer — never a silent half-compare that returns only the generic branch under a compare label.
- **The compare-isolation invariant is elevated from a comment to a named guardian.** The existing control (`app.py:4359-4369`) is exactly right: in compare follow-ups, the grounded branch receives only the prior grounded answer, and the illustrative branch receives only the prior illustrative answer — the grounded answer must never reach the generic branch **even as conversational context**, or the generic example can imitate and effectively republish profile facts. This is the one leak the empty evidence map cannot catch, because prose is not citations: the map guards the citation channel, and only strict input separation guards the prose channel. Enforcement: separate content builders (`grounded_user_content` / `illustrative_user_content`, `app.py:4352-4369`) plus a construction test asserting the grounded answer string and every evidence projection string are absent from the illustrative request content. Guardian classification: an instance of `source-allowlist`, named `compare-isolation` in tests and telemetry.
- The signed token continues to carry the two answers in separate fields (`answer`, `illustrative_answer`, `app.py:3596-3611`), and `_load_interview_model_context` continues to require the illustrative half in compare mode (`app.py:3645-3646`).
- Cost truth: compare is two provider calls; telemetry records both under one request id.

---

## 6. Adaptive length — closing live defect G3/E6

The 60–120 second literals at `app.py:4309` (grounded) and `:4324` (generic) are **confirmed present in the deployed artifact at SHA `f42e5399`** (errata E6) and directly contradict the accepted direction's adaptive-length rule. The same defect class exists in the Revision Partner at `app.py:4067`, owned by Section 2.

**Design:** length comes from the Router's band, with reasons, or not at all.

- Section 1's Diagnostician/Router emits (field names proposed here, to be reconciled as Section 1's authority):

```json
"length_band": {"seconds_low": 30, "seconds_high": 60, "class": "factual", "reasons": ["factual question needs a direct response", "single-part"]}
```

- Both specialist prompts render a **server-built** length line from that band — e.g. `Length: aim for about 30-60 seconds spoken (factual question needs a direct response); shorter is fine when every obligation is met.` — replacing the literal in the schema line. The band and reasons are echoed in response provenance so the interface can present any speaking-time figure as a disclosed estimate, never a score (accepted section 4).
- **Deterministic no-regression guardrail:** a unit test asserts no Interview specialist prompt template contains a hardcoded seconds range (regex `\d+\s*[-–]\s*\d+\s*second`). The defect class cannot silently return in any specialist, including Section 2's.
- Length enforcement stays **guidance, not a hard reject**: the accepted direction ties length feedback to missing or excessive content, not a timer; the only hard bound remains `MAX_INTERVIEW_ANSWER_LENGTH` (`content-bounds`).
- **Slice placement, owner-directed:** adaptive length is in the **first implementation slice**. Dependency stated plainly: it requires exactly one Router capability — the band with reasons — and nothing else of the Router. Sequencing authority is Section 5's; this section records the owner direction and the minimal dependency.

---

## 7. Follow-ups — the provenance that would make them safe, and why the refusal stays today

### 7.1 Current state, endorsed

Follow-ups are refused server-side on the authenticated surface (`app.py:4249-4250`). The comment's reasoning is correct and is adopted here: nothing in the response can state which grounding mode a follow-up answer came from, the client was previously the only thing preventing that path, and the boundary belongs on the server. **The refusal stays until every element below is implemented and negatively tested. Re-opening it is that future package's decision, not any caller's.**

### 7.2 The provenance design that would permit re-enabling

Four elements, all deterministic:

1. **Identity-bound context token, v2.** Today's signed token (`_sign_interview_model_context`, `app.py:3590-3612`) carries mode, question, answers, evidence ids, and the opportunity digest — but **not the member's identity**. A token minted in member A's session would load in member B's authenticated session; both surface checks would pass. Currently moot (authenticated follow-ups are refused; the public branch has no identity), but it must be closed before re-enablement. Token v2 adds: `token_version: 2`, `member_digest` (HMAC of `identity.user_key` under the existing serializer secret), `specialist_version`, `evidence: [{id, version}]` (replacing bare ids), `turn`, `issued_at`. Load-time check: `member_digest` must match the current identity via `hmac.compare_digest`, else the token is invalid — the `identity` guardian applied to conversation state.
2. **Per-turn response provenance.** Every model answer already carries the C.1 provenance block; follow-up turns increment `turn` and add `parent_answer_digest` (SHA-256 of the prior answer text). The interface renders the grounding-mode label on **every** turn from server data. This supplies exactly the missing fact the refusal comment names: which grounding mode this follow-up answer came from.
3. **Follow-up entry re-checks**, in order, all pre-provider: identity match (new, element 1); mode match between token and request (**exists**, `app.py:4269`); opportunity-context digest match via `hmac.compare_digest` (**exists**, `app.py:4257`); **evidence re-intersection** (new): every token evidence id must still be in the member's current approved set, else `denied_authorization` with copy "This conversation used evidence you've since removed. Start a fresh example." — this is how CR-3 revocation reaches an in-flight conversation, since the replayed prior answer embeds evidence facts even though the evidence list itself is rebuilt fresh each turn; chain depth `turn <= 5` (`content-bounds`).
4. **Compare isolation per turn** (**exists**, `app.py:4363-4369`): each branch receives only its own prior answer, preserved verbatim in the v2 design.

Elements 3-partial and 4 already exist; elements 1, 2, and the re-intersection are new. Until all four are live with authorization negatives (foreign-member token replay, revoked-evidence continuation, mode-swap replay), the server refusal at `app.py:4249-4250` stands unchanged.

---

## 8. Rejected alternatives

- **Defer specialist 5 entirely until Profile ships** — rejected: the owner directed designing against the future contract now, and the owner fixture keeps the single grounded code path continuously exercised and testable.
- **Two code paths (owner fixture vs member evidence)** — rejected: divergence is where authorization bugs breed; the fixture is expressed inside the contract instead (CR-6).
- **Auto-substituting a generic answer when grounded is unavailable** — rejected: it blurs the grounded/generic line the direction requires visible; the member chooses the fallback with one explicit click.
- **Hiding the grounded option for capability-absent members** — rejected: it misrepresents the product and makes Profile's arrival a surprise; disabled-with-reason is truthful.
- **A third `compare` specialist with its own prompt** — rejected: compare is two specialists composed; a merged prompt would destroy the isolation invariant that keeps the generic branch member-free.
- **Retiring compare mode** — rejected: it exists, the UI uses it, its isolation control is sound, and contrast teaching is real member value.
- **Renaming wire modes to `grounded`/`generic`** — rejected: breaks the deployed client, saved records, and signed tokens for cosmetic gain.
- **Hard server-side rejection of answers outside the length band** — rejected: the accepted direction makes length a content-justified judgment, not a timer; truncation or rejection would destroy answer integrity.
- **A stored per-member capability flag** — rejected: any stored flag can drift from the data; capability is derived from the retrieval result itself, with `INTERVIEW_MEMBER_EVIDENCE` as the only deliberate override, default off.
- **Prompt-instruction-only enforcement that generic answers look generic** — rejected by standing rule: the deterministic controls are the empty evidence map, the no-evidence-parameter builder, the server-set `generic` flag, and mode-bound tokens.

## 9. Genuine uncertainties, labelled

- **Router band schema field names** (`seconds_low`/`seconds_high`/`class`/`reasons`) are proposed here but are Section 1's authority; reconciliation required. This section's only hard requirement is band-plus-reasons.
- **Whether Profile will express evidence as today's resume metrics or a new object** — unknown and deliberately out of scope; the projection adapter absorbs either, and the contract is consumer-side only.
- **Whether `level` and `family` remain client-supplied hints or become Router outputs** — if Section 1 makes the Router authoritative for question class, these prompts consume the Router's class and the client values demote to non-authoritative hints; flagged for reconciliation rather than assumed.
- **The other consolidated sections (1, 2, 3, 5) were not readable from this worktree at writing time**; spine adherence here is by specification, and the consumed requirements this section places on them are listed explicitly (Section 1: length band; Section 2: `app.py:4067` literal and the shared no-literal test; Section 3: History records persist `mode` + `generic` flag + evidence `(id, version)`; Section 5: compare-composition versioning, capability flag naming, slice sequencing).
- **SDK exception strings possibly carrying body content** (`app.py:4417`, gap G7) is real and adjacent but owned by the shared observability section; this section's specialists rely on `_log_interview_failure` for every deliberate path.

---

*End of Section 4. No runtime change is proposed for immediate execution; every element above enters implementation only through its owning slice's Protected package after Pete and Codex reconciliation.*
