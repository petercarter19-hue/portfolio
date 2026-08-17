# PS-SIGNIN-MEMBER-ARRIVAL-001 — Completion Report

**Outcome:** a member is returned to the page they asked for after signing in.
**Delivery path:** Protected (redirect boundary, identity-adjacent).
**Owner decision:** Pete, 2026-08-16 — diagnosis accepted, then "fix everything".
**Audit stage:** S01 — Sign-in, member arrival, Settings and My Data.

## What was wrong

A signed-out member who asked for the Opportunity Slate room signed in
successfully and landed on `/app` instead, with no explanation and no trace of
where they were going.

The cause was a disagreement between two halves of one journey. Four modules
held four different implementations of the return-path rule:

| Module | Allowlist | State |
|---|---|---|
| `auth_routes.py` | yes — the only one | the consumer |
| `workshop_routes.py` | no | docstring claimed it mirrored `auth_routes` "exactly" |
| `opportunity_slate_v2_routes.py` | no | did not parse the URL at all |
| `community_routes.py` | none at all | built the target straight from the request |

Producers were permissive; the single consumer was strict and silent. A
namespace never added to the consumer's allowlist was accepted by its own room
and discarded on arrival.

Opportunity Slate shipped in exactly that state.
`PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED` is `true` in production, so this was
live and member-facing, not latent.

**Proven live, 2026-08-16**, owner-assisted with a real authenticated session —
two requests to the same endpoint, seconds apart:

| Request | Landed on |
|---|---|
| `/auth/complete?return_to=/opportunity-slate` | `/app` — destination discarded |
| `/auth/complete?return_to=/the-slate` | `/the-slate` — correct |

The room itself was healthy when reached directly. Only the return journey was
broken.

The tests could not see it: `tests/test_opportunity_slate_v2.py:137-148`
registers a **stub** auth blueprint, so the four assertions that read as proof
of the round trip only ever verified the string the room emitted, never the
half that decides where the member lands.

## What changed

**`safe_return.py` (new)** — one parser, one allowlist, one place to register a
protected destination. Destinations declare their prefix and the flag that must
be on for them to be reachable, so a member is never returned to a route that
would answer 404. All four modules now delegate to it; the duplicates are gone.
An unregistered destination now fails a test rather than a member's journey.

**Dot-segment traversal closed.** `urlsplit` does not remove RFC 3986 dot
segments, so `/app/../.auth/logout` previously satisfied every guard — it
starts with an allowlisted prefix and carries no scheme, host, fragment,
backslash or `//` — then resolved in the browser to exactly the provider path
the exclusions exist to keep out. Rejected outright now.

**The header no longer discards context.** `shared_authentication_state`
hardcoded `return_to=/app` for both the Sign In control and the recovery retry
link, so the most-clicked sign-in entry point on the site threw away the
member's page on every load — undoing what every per-route redirect does to
preserve it. It now offers the current page. Public and unrecognised paths
still resolve to `/app` through the same validator.

Deliberately path-only: the query string is caller-controlled and this value is
rendered into every page's header. An earlier revision included it and was
caught by `tests/test_workshop_checkpoint.py`, which proved it reflected
`?user_key=someone-else` into the page. Per-route redirects still preserve
their own query strings where that matters.

**Community's database-wake is honest.** An identity-storage failure on
`/the-slate` fell through to Werkzeug's unbranded 503. Community is a
first-class place to land straight after signing in and Azure SQL serverless
auto-pauses, so this was the most likely first-arrival failure. It now returns
the same truthful "waking up" surface `/app` already used.

**The bfcache guard covers the private namespaces.** It was written when
`/app` was the only private one and never extended as Community, Interview
Studio and the Opportunity Slate room moved behind sign-in — so those pages
could restore a signed-in body under a signed-out header after Back.

**Recovery tells the truth about three different situations.** One sentence
served all of them because the surface was never told which it was in. A
member whose sign-in simply did not complete was told their account needed
checking, which reads as something being wrong with them.

## Verification

Full suite: **3809 passed, 4 skipped** (`tests/`, 283s).

New: `tests/test_signin_member_arrival.py` — 21 tests, 63 subtests. Round trip
through the real endpoints for every registered destination; dot-segment
traversal; `/app` prefix confusion (`/the-slate` and `/interview-studio` had
these negatives, `/app` did not); the full control-character class (only NUL
was covered); exact length boundary; the hostile matrix against
`/auth/complete`, which is the actual open-redirect sink and had never been
given one; and a structural test that fails if any producer stops delegating.

### Changed expectations, and why

Four, each deliberate:

1. **`test_completion_is_principal_only_and_non_looping_when_missing`** — copy
   only. Returning from the provider without a principal means the sign-in did
   not complete; it is not evidence the member's account needs checking. The
   property the test exists for — never re-entering the provider automatically
   — is unchanged and still asserted.
2. **`test_mapping_failure_uses_generic_private_recovery`** — copy only. No
   claim detail, no provider re-entry, private and unstorable, one `<main>`:
   all unchanged and still asserted.
3. **Interview Studio byte baselines** — `+26` bytes on the room and `+42` on
   history: exactly the two header controls now returning to
   `/interview-studio` (17 chars) and `/interview-studio/history` (25) instead
   of `/app` (4), twice each. That is the fix working. Its asset-token
   normalization was also widened from two named files to any versioned static
   asset, so an unrelated shared script can no longer break an Interview Studio
   HTML baseline.
4. **Owner Home flag-off byte baseline** — byte length unchanged; the only
   delta is the `easy-auth-callback.js` content fingerprint. Proven by
   rendering the exact request before and after: the diff is one `?v=` token
   and nothing else. The chain intermediates moved for the same single reason.
   **`FLAG_OFF_APP_RENDER_PREVIOUS_SHA256` is deliberately not recaptured** —
   it is the terminal step, taken after the token is normalized back, and it
   still matches the historically locked render byte for byte. If any owner
   workspace byte had moved, that assertion would have failed.

## Visual authority

No material visual change. Under
`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md:14-26, 33-40` this is
truthful state wiring and copy on existing components: no new page, no new
component, no change to composition, hierarchy, dominant action, typography,
colour language, or responsive interaction model.

A new first-arrival cue inside `/app` **would** be material. It was diagnosed
and deliberately excluded: a designed, accepted, content-aware empty arrival
already exists in Owner Home, and Pete enabled it on 2026-08-16 rather than
commissioning new design.

## Honest limitations

- **Cross-tab sign-out on `/app` is still not reconciled.** `auth-state.js`
  already reconciles on tab focus, but `templates/base.html:18` does not load
  it on `/app` or `/auth/`. Extending it means editing the shell, which
  `PS-SHELL-001` reserves and states requires fresh activation. Left alone
  deliberately. The bfcache guard covers the Back-navigation case everywhere.
- **Session expiry and re-authentication remain unproven.** The governing
  lifetime is an App Service setting with no representation in this
  repository, so it cannot be verified or regression-tested from source.
- **Two synthetic members remain unproven end-to-end** — covered at unit and
  SQL-transaction level only. That is `GAP-SYNTHETIC-MULTI-MEMBER-QA`, an S00
  row.
- **The Opportunity Slate flag cannot be exercised per-test**, because
  `app.py:806-809` chooses the blueprint at import time. The round-trip test
  drives the gate's own return-target builder instead — the half that was
  disagreeing.
- **Package-record drift found and not fixed here** (outside this scope):
  `PS-SIGNIN-EXPERIENCE-001/COMPLETION.md:179-182` still reads "Not deployed,
  not pushed" two weeks after it shipped, and
  `PS-AUTH-CALLBACK-001/COMPLETION_REPORT.md:91-95` still shows its release
  gates Pending.

## S00 note

S00 is not closed: `PS-PORTABLE-SESSION-MANAGER-002` closeout,
`GAP-SYNTHETIC-MULTI-MEMBER-QA`, and `GAP-LEGAL-L0-OPERATIONS` remain open.
This package proceeded on Pete's explicit 2026-08-16 instruction, which the
portable packet's own authority order places first. Recorded here rather than
implied.
