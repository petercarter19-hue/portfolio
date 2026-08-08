# PS-ASK-PETE-AI-READINESS-002 — Grounded Ask Pete enablement readiness

## What this package is

`PS-ASK-PETE-AI-001` merged the grounded Ask Pete path in source and left it
default-off behind `PEERSLATE_ASK_PETE_GROUNDED_ENABLED`. A readiness audit of
that dormant path found three things that would only become visible once the
flag is turned on, when they would be visitor-facing and billable. This package
fixes them in `services/ask_pete/` and `tests/ask_pete/` before any enablement
decision. It changes no route, no template, no flag default, and no visual
authority.

- Status: **Source complete on the package branch; not merged, not deployed,
  not enabled**
- Delivery path: **Bounded** — approved package, established architecture, no
  new trust boundary. Escalation to Protected was considered and not taken;
  see "Why this is not a Protected change" below.
- Runtime effect while `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` is false: **none**.
  Every changed line is inside `services/ask_pete/`, which is only reached from
  the flag-on branch of `/api/chat`.
- Writable surfaces used: `services/ask_pete/`, `tests/ask_pete/`, this
  directory. `app.py`, templates, static assets, `services/ai_foundation/`,
  the source manifest, and resume data were not modified.

## The three fixes

### 1. The paid provider call had no bound

**Before.** `AnthropicGroundedProvider.answer` called `messages.create` with no
`timeout` and no retry bound, so the anthropic SDK defaults applied: a 600 s
read timeout and two retries. `static/js/chatbot.js` aborts the visitor's fetch
after 45 s. A hung or slow call therefore held a gunicorn worker — and kept
paying for a generation nobody could still see — for up to ten minutes after
the visitor had already been told the question failed. The bound could not be
supplied by the caller either: `app.py` builds the shared Anthropic client bare,
and that client is used by other AI surfaces.

**After.** The call carries an explicit 30 s per-request `timeout` and runs on a
`with_options(timeout=..., max_retries=0)` copy of the injected client. The copy
shares the underlying HTTP connection pool and leaves the application's client
untouched, so no other caller's settings change. A client that does not offer
`with_options` still receives the per-request timeout.

**Why both.** In anthropic 0.112.0, `timeout` is a `messages.create` keyword and
`max_retries` is not, so the retry bound has to come from client options. The
retry bound matters on its own: the SDK retries `APITimeoutError`, so three
bounded 30 s attempts would put the total back past the browser's abort.

**Failure contract unchanged.** A timeout is still converted to
`ProviderUnavailableError`, which the foundation gateway degrades into the
honest `state: "unavailable"` answer with a `degraded` trace outcome. Nothing
plausible is invented, and no transport detail reaches the visitor.

### 2. A visitor's wording could select a stricter contract than their surface

**Before.** `classify_public_purpose` escalated on keywords found in the
visitor's own question. `static/js/chatbot.js` posts only `{"message": ...}` —
no `action`, no `context_key` — so a visitor who typed "60-second recruiter
brief", "first interview", or "how has Pete…" was moved into a stricter product
quality contract than that surface can satisfy. The recruiter brief is the sharp
case: `services/ask_pete/quality.py` requires `partially_supported` state, four
claims, three citations, a 100–140 word summary, a boundary and a handoff. A
shortfall raised `AskPeteResponseError`, and `/api/chat` returned **502** — so
the visitor lost an answer the model had already produced and been paid for.

**After.** A purpose is a server-side decision about which quality contract an
answer must meet, so it now comes only from an explicit, recognized `action`.
No action, an unrecognized action, or merely suggestive wording all answer under
the general `public_profile_answer` purpose. Unknown values are still ignored
rather than rejected, and every function signature and response field is
unchanged.

**The resume companion does not move.** `static/js/ask-pete-evidence-companion.js`
always sends an action and falls back to `evidence_finder` for anything outside
its own allowlist, so the flagship recruiter and evidence experiences behave
exactly as before.

**This is not an authorization change.** Every record in
`data/ai_sources/ask_pete_public_v1.json` allows all four public purposes, so
the four purposes offer an identical approved source set. Moving a question
between purposes changes which quality contract applies, not what the model is
allowed to read. A test pins that equality so a future manifest edit cannot make
this fix quietly widen or narrow source access.

**Consequence for the code.** Keyword matching was removed rather than left
unreachable: all three keyword-reachable purposes were strict purposes, so the
block could no longer fire. `question` stays in the signature because
classification remains the server's decision about the request and no caller's
seam changes.

### 3. Two spend-relevant behaviors had no test

**Rate limit.** `/api/chat` carries `@limiter.limit('10 per minute')` and that
limit is the ceiling on anonymous AI spend, but every existing app-compatibility
test disables the limiter. A new test class enables it and proves the eleventh
request from one client in a minute is refused with 429 and costs nothing — no
grounded work and no legacy provider call.

**Flag-on legacy seam.** A test now drives the full grounded path the way
`chatbot.js` drives it: flag on, `{"message": ...}` with no action, only the
model itself stubbed. Classification, the quality gate, serialization, and the
provider bound all run for real. It asserts 200 with a populated flat
`response` key, which is the only field a legacy client reads. Against the
pre-fix classification this same test fails with the production 502.

## Open findings recorded, not fixed here

### The 429 body is HTML on an otherwise-JSON route

`app.py` registers no 429 error handler, so a rate-limited `/api/chat` request
returns Flask-Limiter's default HTML page with `Content-Type: text/html`, not
the JSON error shape every other `/api/chat` failure uses. There is no
`Retry-After` header.

No visitor sees a broken state today: `static/js/chatbot.js` falls back to `{}`
when a body will not parse and shows its own 429 sentence. But a JSON client
that trusts the content type does not get the shape it expects. Closing this
means an `app.py` error handler, which is outside this package's writable
surface. The behavior is pinned by
`test_the_refused_request_body_is_flask_limiters_html_default` so the gap stays
visible and the test fails loudly when it is closed.

### Flag-off `/api/chat` is not byte-identical for malformed bodies

`PS-ASK-PETE-AI-001` states that the flag-off path preserves legacy `/api/chat`
behavior exactly. That is true for well-formed requests and no longer exactly
true for malformed ones, because of the body hardening merged in Azure PR 320 —
before this package, and independent of it.

Before PR 320, `chat()` called `request.get_json()` without `silent=True` and
then `data['message'].strip()`. A `text/plain` body raised Flask's unsupported
media type (415), a malformed JSON body raised Flask's bad request (400), both
rendered as HTML, and a non-string `message` raised `AttributeError` and became
a 500. Today all of those return a JSON 400. That is an improvement and it is
covered by
`test_non_json_and_malformed_json_bodies_are_json_400_before_provider_work`.
It is recorded here because the earlier package's "byte-identical" claim is now
narrower than it reads, not because anything is wrong with the current
behavior. Nothing in this package changed it.

## Why this is not a Protected change

The trust boundaries the lean workflow names as Protected triggers were checked
and none is crossed:

- **Identity and authorization.** Untouched. No identity is derived, and source
  authorization still runs in `services/ai_foundation/` before any model call.
- **Canonical truth.** Untouched. AI output is still a proposal validated
  against approved source spans; nothing is made canonical.
- **Privacy.** Improved slightly and not otherwise changed: the bounded-call
  tests assert that transport detail does not reach the visitor, and the 429
  test asserts the refusal body does not echo the question.
- **Consequential AI.** The change narrows what visitor text can influence and
  shortens how long a paid call may run. Both reduce exposure.
- **Shared infrastructure.** The application's Anthropic client is read but
  never mutated; bounds are applied to a per-request copy.
- **Materially revised visual direction.** None. No template, stylesheet, or
  script changed.

Enablement of `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` remains a separate
Protected release decision under `PS-OPS-001`. This package does not make it,
recommend a date for it, or claim any live behavior.

## Files

| File | Change |
|---|---|
| `services/ask_pete/provider.py` | Bounded timeout and retry constants; `_bounded_client`; bounded create call |
| `services/ask_pete/classification.py` | Strict purposes selectable only from an explicit recognized action |
| `tests/ask_pete/test_provider_timeout.py` | New: call bounds, timeout degradation, installed-SDK contract |
| `tests/ask_pete/test_provider_and_classification.py` | Classification expectations updated to the new contract; wording, unknown-action, and normalization coverage added |
| `tests/ask_pete/test_service.py` | Strict-contract tests name the action a real client sends; new regression test that the same answer is delivered without one; source-parity test |
| `tests/ask_pete/test_public_eval_catalog.py` | New invariant: a strict-purpose or context-bearing case must name its action |
| `tests/ask_pete/public_eval_cases.json` | Two cases carried a `context_key` with no action, a shape no client sends; they now name `evidence_finder` |
| `tests/ask_pete/test_app_compatibility.py` | New: rate-limit refusal class, 429 body characterization, flag-on legacy-seam test |

Completion record: `COMPLETION_REPORT.md`.
