# PS-ASK-PETE-DIRECT-001 — registration leg specification

**Status: DONE, 2026-08-08.** PS-INTERVIEW-STUDIO-FUNCTIONAL-V1-001 closed and
released `app.py`, the lane recorded the surface, and all four edits below were
applied exactly as written. The checklist ran green — including the byte-identity
item: `/petec/resume` with the flag off renders **identically** to the
pre-registration bytes in both the legacy (172,930 B, sha256 `3ef02bd6…`) and
companion (176,373 B, sha256 `0f228364…`) modes.

**The feature is registered and OFF.** Enablement remains a separate owner
decision and still needs the production schema apply
([`SCHEMA_GATE_RUNBOOK.md`](SCHEMA_GATE_RUNBOOK.md) Part 4) and
`PEERSLATE_OWNER_USER_KEYS` naming exactly one key.

The edits are kept below as written rather than rewritten in the past tense:
they are the record of what was applied, and the checklist stays the right
thing to re-run after any future change to `app.py`.

Four edits to one file, all additive, none touching an existing line. Nothing
else in the repository changes: the blueprint, the service, the templates, the
CSS, the JS, and the migration are already merged and already correct. This
leg only connects them.

Anchors below are line numbers as of `app.py` at `origin/main` `4551b80`.
Re-locate by the quoted neighbouring text rather than by number if the
Interview lane has moved things.

> **The rehearsal already exists.** `tests/ask_pete_direct/run_direct_preview.py`
> registers the blueprint on the real application object with exactly the line
> in edit 3 below, boots it, and exercises both surfaces. Run
> `run_direct_preview.py --check` before and after this leg — it is the
> cheapest proof that the registration composes.

---

## Edit 1 — the config flag

**Where:** the `app.config.update(...)` flag block, immediately after the
`PEERSLATE_ASK_PETE_GROUNDED_ENABLED` entry (`app.py:311-313`).

```python
    # PS-ASK-PETE-DIRECT-001: the private recruiter-question path — the
    # consent-first form inside Ask Pete's handoff card, POST
    # /api/ask-pete/direct-question, and the owner-only inbox at
    # /owner/ask-pete-inbox. Off by default. The blueprint reads this with
    # `is True`, so only a real boolean opens it; when it is false every
    # route in that blueprint answers a neutral 404 and the companion partial
    # renders byte-for-byte what it renders today.
    #
    # Enablement additionally requires PEERSLATE_OWNER_USER_KEYS to name
    # EXACTLY ONE key — that key is both the member questions are addressed
    # to and the identity that opens the inbox — and the
    # PS-ASK-PETE-DIRECT-001 migration to be gated and applied. Zero keys,
    # more than one, or an email-only owner allowlist leaves the path
    # honestly unavailable (every send answers 503) rather than guessing a
    # recipient. Enablement is Pete's decision, not a config change.
    PEERSLATE_ASK_PETE_DIRECT_ENABLED=(
        os.environ.get('PEERSLATE_ASK_PETE_DIRECT_ENABLED', 'false').lower() == 'true'
    ),
```

`.env.example` already carries the entry and its prerequisites; nothing to add
there.

---

## Edit 2 — the import

**Where:** the blueprint import block, after
`from opportunity_slate_routes import opportunity_slate` (`app.py:37`).

```python
from ask_pete_direct_routes import ask_pete_direct
```

The blueprint imports nothing from `app` — asserted by
`tests/ask_pete_direct/test_darkness.py::test_the_blueprint_imports_nothing_from_app`
— so there is no import cycle and no ordering constraint beyond the usual one.

---

## Edit 3 — the registration

**Where:** the registration run at `app.py:684-693`, after
`app.register_blueprint(opportunity_slate)` and **before** the
`if not app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED']:` line.

```python
app.register_blueprint(ask_pete_direct)
```

Register it unconditionally, exactly like every other blueprint here. The gate
belongs in the blueprint's own `before_request`, not in the registration —
which is what makes "flag off" mean *404 from a route that exists* rather than
*no route at all*, and is why the flag can be flipped without a redeploy.

**This deletes a tripwire on purpose.**
`tests/ask_pete_direct/test_darkness.py::test_the_blueprint_is_not_registered_by_any_production_module`
and `::test_app_py_is_untouched_by_this_package` will fail the moment this line
lands. That is their entire job: they exist so registration cannot happen
quietly. Update both in the same commit — do not delete them. Replace the
assertion with the honest successor: that the blueprint IS registered exactly
once, and that the flag still defaults off. Suggested replacement:

```python
    def test_the_blueprint_is_registered_exactly_once(self):
        import app as app_module

        self.assertIn("ask_pete_direct", app_module.app.blueprints)
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("app.register_blueprint(ask_pete_direct)"), 1)

    def test_registration_did_not_also_enable_the_flag(self):
        import app as app_module

        self.assertIs(
            app_module.app.config["PEERSLATE_ASK_PETE_DIRECT_ENABLED"], False
        )
```

---

## Edit 4 — the rate limits

**Where:** after the Community post-registration wrapper loop ends
(`app.py:786-788`), in the same run of wrapper blocks.

The blueprint cannot do this itself: `app.py` owns the `Limiter`, and the
house idiom is to wrap the already-registered view function afterwards so a
reusable blueprint never imports this module back. The budgets are declared in
`ask_pete_direct_routes.PLANNED_RATE_LIMITS`, and a test asserts that mapping
covers every state-changing endpoint in the blueprint — so a route added later
without a budget fails the suite rather than shipping unbounded.

```python
# PS-ASK-PETE-DIRECT-001: the same post-registration wrapper idiom for the
# private recruiter-question path. The blueprint declares these budgets in
# PLANNED_RATE_LIMITS precisely because it cannot apply them itself; reading
# them from there rather than restating them keeps the declaration and the
# application from drifting.
#
# 30/hour on the public write is the house floor for a state-changing
# endpoint (community_api.publish_post and its neighbours). It is the only
# anti-abuse ceiling this path has — there is no CAPTCHA, by decision — so it
# is the number to revisit if abuse ever appears, not one to relax.
# 60/hour on the owner's own read/archive action is roomier because a member
# working through a backlog legitimately presses it many times in a row.
for _direct_endpoint, _direct_limit in ask_pete_direct.PLANNED_RATE_LIMITS.items():
    app.view_functions[_direct_endpoint] = limiter.limit(_direct_limit)(
        app.view_functions[_direct_endpoint]
    )
```

`PLANNED_RATE_LIMITS` is a `MappingProxyType` on the module, not the blueprint
object — import it explicitly if the reference above does not resolve:

```python
from ask_pete_direct_routes import PLANNED_RATE_LIMITS, ask_pete_direct
...
for _direct_endpoint, _direct_limit in PLANNED_RATE_LIMITS.items():
```

Current contents:

| Endpoint | Budget |
|---|---|
| `ask_pete_direct.submit_direct_question` | `30 per hour` |
| `ask_pete_direct.set_question_status` | `60 per hour` |

The blueprint already registers its own `RateLimitExceeded` handler, so a 429
answers in this blueprint's JSON shape rather than the application's HTML
default. That handler is dead code until this edit lands.

---

## Verification checklist

Run in this order. Steps 1–4 need no credentials and no database.

### 1. Flag OFF is byte-identical

```
PEERSLATE_ASK_PETE_DIRECT_ENABLED=false \
  venv/bin/python -m pytest tests/ask_pete_direct/ tests/ask_pete/ -q
```

Expect green, including
`test_flag_off_renders_byte_identically_to_the_template_without_the_block`.
Then confirm the deployed-shaped render directly:

```
venv/bin/python - <<'PY'
import os; os.environ.setdefault("ANTHROPIC_API_KEY", "check")
import app as app_module
app_module.app.config.update(TESTING=True, PEERSLATE_ASK_PETE_GROUNDED_ENABLED=True)
html = app_module.app.test_client().get("/petec/resume").get_data(as_text=True)
assert "ask-pete-direct" not in html, "the private path leaked with the flag off"
print("flag-off resume carries no trace of the private path")
PY
```

Compare the same page against `origin/main` before the leg if you want a
literal byte diff; the template block is wholly inside its conditional, so the
two renders are identical strings.

### 2. Routes are 404-neutral with the flag off

With the flag false, all three must answer 404 — and the API one must answer
the *same* 404 to a cross-site caller as to a same-origin caller, so the
surface never confirms its own existence:

| Request | Expect |
|---|---|
| `POST /api/ask-pete/direct-question` (valid, same-origin) | `404 {"success": false, "message": "Not found."}` |
| `POST /api/ask-pete/direct-question` (`Sec-Fetch-Site: cross-site`) | byte-identical 404 to the above |
| `GET /owner/ask-pete-inbox` (as the owner) | bare `404` |
| `POST /owner/ask-pete-inbox/<key>/status` (as the owner) | bare `404` |

Covered by `tests/ask_pete_direct/test_endpoint.py::FlagGateTests` and
`test_inbox.py::AuthorizationTests`; re-run them against the registered app.

### 3. The limiter is actually attached

```
venv/bin/python - <<'PY'
import os; os.environ.setdefault("ANTHROPIC_API_KEY", "check")
import app as app_module
from ask_pete_direct_routes import PLANNED_RATE_LIMITS
for endpoint in PLANNED_RATE_LIMITS:
    view = app_module.app.view_functions[endpoint]
    assert getattr(view, "__wrapped__", None) is not None, f"{endpoint} is unwrapped"
    print(f"{endpoint}: wrapped")
PY
```

### 4. The 429 shape

With the flag on locally, send 31 requests to the write endpoint in one hour
window. The 31st must be:

```json
{"success": false, "code": "rate_limited",
 "message": "Too many questions from this connection. Try again later."}
```

with status `429` — this blueprint's handler, not the application's HTML
default. The companion renders that as the honest "Not sent - too many
questions from this connection just now" state.

### 5. The preview harness, before and after

```
venv/bin/python tests/ask_pete_direct/run_direct_preview.py --check
```

All checks pass both before and after this leg — before, because the harness
registers the blueprint itself; after, because `configure_preview_app` skips
re-registration when `app.py` has already done it.

### 6. Whole suite

```
venv/bin/python -m pytest tests/ -q
```

Expect green with the two darkness tests replaced per edit 3.

---

## What this leg does NOT do

* It does not turn the flag on. Registration and enablement are separate acts;
  after this leg the routes exist and answer 404.
* It does not apply the migration. See `SCHEMA_GATE_RUNBOOK.md`. Until the
  schema is applied, a send with the flag on answers an honest 503 rather than
  a false success — but do not rely on that as a plan: apply the schema first.
* It does not add outbound notification. There is still no channel, and the
  inbox is still pull-based.
