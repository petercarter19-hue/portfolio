# PS-ASK-PETE-AI-RELEASE-001 — Ask Pete app-seam corrections and release record

## What this package is

`PS-ASK-PETE-AI-001` merged the grounded Ask Pete path default-off behind
`PEERSLATE_ASK_PETE_GROUNDED_ENABLED`. `PS-ASK-PETE-AI-READINESS-002` fixed
three enablement blockers inside `services/ask_pete/` and recorded one gap it
could not close, because closing it meant editing `app.py` — outside that
package's writable surface.

This package owns `app.py`. It closes that gap, documents the flag in
`.env.example`, and holds the release evidence for the enablement decision.

- Status: **Source complete on the package branch; not merged, not deployed,
  not enabled**
- Delivery path: **Bounded** — an established seam, no new trust boundary. See
  "Why this is not Protected" below.
- Runtime effect while `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` is false: one
  deliberate, flag-independent change — a rate-limited caller on any limited
  route now receives JSON instead of HTML. Nothing else about the flag-off path
  moves.
- Writable surfaces used: `app.py`, `.env.example`, `tests/ask_pete/`, this
  directory. `services/`, `prompts/`, `templates/`, `static/`,
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

## Why this is not Protected

- **Identity and authorization.** Untouched. The handler derives no identity
  and reads no member data; the rate-limit key function is unchanged.
- **Privacy.** Improved. The refusal body no longer carries the limit string,
  and a test asserts the visitor's question is not echoed.
- **Canonical truth and consequential AI.** Untouched. No AI path, prompt,
  source manifest, or validation rule changed. The grounded branch of
  `/api/chat` is byte-identical to `origin/main`.
- **Shared infrastructure.** The `Limiter` instance is read, never mutated; no
  limit value, storage backend, or key function changed.
- **Material visual direction.** None. No template, stylesheet, or script.

Enablement of `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` is a separate Protected
release decision under `PS-OPS-001`. This package does not make it, recommend a
date for it, or claim any live behavior.

## Files

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
