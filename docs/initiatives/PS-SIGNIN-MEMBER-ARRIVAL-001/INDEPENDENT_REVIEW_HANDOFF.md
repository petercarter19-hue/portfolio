# Independent Review Handoff — PS-SIGNIN-MEMBER-ARRIVAL-001 follow-up

**Prepared by:** Claude Code desktop session `acd9f218-d287-490f-b2d5-a185c5bceb27` (Opus 5), sole writer for this lane.
**Date:** 2026-08-21.
**Requested by:** Pete, 2026-08-21. **Reviewer:** Grok, independent.
**Review type:** independent Protected review of an exact frozen candidate SHA.
**Base:** `origin/main` `196fd502a8425e7ee35eaec15efff30f58e2bab0`
**Branch:** `work/2026-08-21-signin-member-arrival-followup`

The exact frozen candidate SHA is not written into this file, because this file
is itself part of the candidate and could not then name its own commit. It is
recorded in `FOLLOWUP_COMPLETION_REPORT.md` and in the review request that
accompanies this document; it is the branch tip, and §3 shows how to confirm
it.

Nothing is merged. Nothing is deployed. No production behaviour has changed.

---

## 1. What you are being asked to do

Review the candidate above and return one of:

- `ACCEPTED_FOR_OWNER_RELEASE_DECISION`
- `ACCEPTED_WITH_NAMED_CONDITIONS`
- `REJECTED_WITH_NAMED_DEFECTS`

You are **not** asked to implement, merge, deploy, or change the lane record.
If you want a change made, name it and hand back — I am still the writer.

If you disagree with the core design decision in §4, say so plainly. It is the
one call in this change that a reasonable reviewer could go the other way on,
and I would rather be told now than after it ships.

---

## 2. Lane authority

Registered on `origin/main` at `068e4bcd` via PR 568.

| Field | Value |
|---|---|
| Package | `PS-SIGNIN-MEMBER-ARRIVAL-001` |
| Lane class | `implementation` (3 of 4 active) |
| `production_capable` | `false` |
| Delivery path | Protected |
| Exclusive domains | `product:signin-cross-tab-reconciliation`, `evidence:signin-package-release-record-truth` |

`delivery_preflight --intent activate` passed with 0 errors / 0 warnings on the
activation branch; `--intent write` passed on the implementation branch.

**Writable surfaces claimed** (the diff touches these and nothing else):

```
templates/base.html
static/js/auth-state.js
tests/auth_state.test.js
tests/test_auth.py                      (claimed, ultimately unmodified)
tests/test_owner_home.py
tests/test_signin_member_arrival.py
docs/initiatives/PS-SIGNIN-MEMBER-ARRIVAL-001/
docs/initiatives/PS-SIGNIN-EXPERIENCE-001/COMPLETION.md
docs/initiatives/PS-AUTH-CALLBACK-001/COMPLETION_REPORT.md
```

**Deliberately excluded, and why it matters to you:**
`tests/test_operational_readiness.py` and the `CURRENT_BASELINE.yaml`
release-truth block are writable surfaces of the active
`PS-INTERVIEW-AI-EXTRACT-001` lane, owned by another writer. See §7 — there is
a real, proven correction there that this lane may not apply.

---

## 3. How to get the code

```bash
git fetch origin
git log -1 --format=%H origin/work/2026-08-21-signin-member-arrival-followup
```

That SHA must equal the one in the review request. Review from a clean worktree
of it; do not reuse or modify mine.

```bash
git diff --name-only 196fd502a8425e7ee35eaec15efff30f58e2bab0..FETCH_HEAD
git diff --shortstat 196fd502a8425e7ee35eaec15efff30f58e2bab0..FETCH_HEAD
```

Expect exactly these 10 paths and nothing else:

```
docs/initiatives/PS-AUTH-CALLBACK-001/COMPLETION_REPORT.md
docs/initiatives/PS-SIGNIN-EXPERIENCE-001/COMPLETION.md
docs/initiatives/PS-SIGNIN-MEMBER-ARRIVAL-001/INDEPENDENT_REVIEW_HANDOFF.md
docs/initiatives/PS-SIGNIN-MEMBER-ARRIVAL-001/FOLLOWUP_COMPLETION_REPORT.md
static/js/auth-state.js
templates/base.html
tests/auth_state.test.js
tests/test_owner_home.py
tests/test_signin_member_arrival.py
```

Nine files. `tests/test_auth.py` is a claimed surface that was ultimately not
modified — its absence is expected, not an omission.

---

## 4. The change, and the judgement call to challenge

### The defect

A member who signed out in one tab kept a fully usable private workspace in
another until they navigated.

### Why the previously recorded fix was wrong

The first round's completion report attributed this to `templates/base.html`
not loading `auth-state.js` on `/app`, implying that loading it there was the
fix. **It is not.** `templates/base.html:291` withholds
`data-ps-auth-controls` from the owner workspace, and `:357` renders a separate
legacy branch of account controls with no `data-ps-auth-control` attribute.
Every element `auth-state.js` toggles lives in the `not is_owner_app_path`
branch. Loading the script there as described would have found nothing to
toggle — green tests, no fix.

Please verify this claim independently. It is the premise for everything else,
and if I have misread the template the rest of the change is misdirected.

### What I did instead — and this is the call to challenge

`auth-state.js` now detects a private document and, when `/auth/session`
answers `signed_out`, calls `location.reload()` instead of touching controls.
The server then answers `/app` with `302 → /auth/sign-in?return_to=/app`.

**The argument for it:** repainting the header to "Sign In" while a private
workspace stays on screen underneath trades one untruthful state for another.
Only the server can decide what a signed-out member may see, and reloading is
how you ask it. It mirrors `easy-auth-callback.js`, which already reloads a
private document restored from bfcache.

**The arguments against it, which I want you to weigh:**

1. **Unsaved work.** A reload discards in-progress input on `/app` — a
   half-typed capture, an unsaved draft. My reasoning: the session has already
   ended, so a save would be rejected anyway, and leaving the member typing into
   a dead page is worse. But this destroys client state without asking, and
   that is a real cost. If you think it needs a confirm step or a save-first
   path, say so.
2. ~~**A new request on the busiest private page.**~~ **Resolved in §4a.**
   The first revision fetched `/auth/session` on every private page load. It no
   longer does: private documents reconcile only on tab focus (throttled to
   15s). Raised here because it was a real cost, and because the fix was forced
   by a test failure rather than foreseen.
3. **Only `signed_out` reloads.** `invalid_session` deliberately falls through
   to the existing control swap. My reasoning: an unmapped principal that
   reloads `/app` could bounce through `/auth/complete` and loop, whereas
   `signed_out` lands cleanly on the sign-in page. Check that reasoning — I may
   be leaving a real broken-session case unhandled.
4. **`/auth/` is excluded**, so a member sitting on a sign-in page after
   signing out elsewhere still sees the last server render. Reloading there is
   the loop the exclusion exists to prevent. Confirm the exclusion is exactly
   `startswith('/auth/')` and that no protected route lives under it.
5. **One attempt per document**, held in a `WeakSet` keyed on the window — no
   browser storage, and a genuinely new document may try again. Consider
   whether once is right if the session endpoint flaps.

## 4a. A defect I introduced, found, and fixed — read this first

The first revision of this candidate **broke 16 tests** and I nearly handed it
to you claiming the suite was clean. The baseline-vs-candidate comparison is
the only reason I caught it, and my first explanation of it was wrong.

**What happened.** The first revision reconciled on `pageshow` as well as on
tab focus. On a private document that put a `/auth/session` request on every
page load. `tests/test_journal_frontend.JournalBrowserBehaviorTests` navigates
`/app/journal` with `wait_until="networkidle"`, and all 16 of its browser tests
began timing out at 30s where they had taken 5s.

**What it was not.** I chased two wrong theories before measuring: an infinite
reload loop (there is none — `/auth/session` answers `auth_unavailable`/503 in
that fixture and the 503 branch preserves the UI and never reloads), and a
single-threaded fixture server (forcing `threaded=True` changed nothing). The
endpoint itself answers in 60ms. I record this because the wrong theories are
plausible and you may reach for them too.

**The fix, which is better design regardless.** A private document no longer
reconciles on load. The server authorized that very render, so asking again
immediately is redundant — and it was not free. `easy-auth-callback.js` already
reloads a private document restored from bfcache, and the case this feature
exists for is *returning to an already-open tab (a `visibilitychange` to visible, not a `focus` event)*, which `visibilitychange`
covers. Public documents are unchanged: their header is the only thing that can
be stale on arrival, and `testPublicReconciliationUsesOnlyTheFixedSameOriginEndpoint`
still asserts the `pageshow` fetch there.

This also removes concern (2) I raise below about new load on the busiest
private page. All 53 Journal tests now pass in 43s.

**What I want from you here:** confirm that dropping the load-time check on
private documents leaves no real gap. My argument is that the server just
authorized the render, so there is nothing to reconcile until something
changes — and the only thing that can change while the tab sits there is
answered by `visibilitychange`. If you can name a case that falls between
those, it is a defect.

## 4b. A second defect, found by self-review rather than by a test

Reading the diff back before submitting it, I found that the reload was
conditional on the wrong thing.

`PRIVATE_PREFIXES` names four namespaces, but three of them are behind sign-in
by **configuration**, not by nature. With the gate off, the same path serves an
ordinary public page to a signed-out visitor. Verified directly: with
`PEERSLATE_TRUST_EASYAUTH_HEADERS=True` and no principal, `/interview-studio`
returns **200** and renders `data-ps-auth-state="signed_out"`, while
`/auth/session` returns `signed_out`.

The first version would have reloaded that page — and since the one-attempt flag
is keyed on the window, a reload produces a new document and a fresh flag, so
the visitor would have been reloaded **every time they returned to the tab**.
Not an infinite spin, but a page that throws itself away whenever you look at it.

Production has Interview Studio's gate on today (`/interview-studio` returns 302
live), so no existing test would have caught this. A single flag flip would have
shipped it.

**The guard I first wrote was itself defective** — see §4c. It reloaded when
the state container was absent, treating absence as proof of privacy. That held
on `/app` and failed on `/app/workshop`.

**Independent review answered the question I raised here:** the markup coupling
was unsound, and the governance reason I gave for avoiding a server-side mark
did not hold — this lane already recaptures `tests/test_owner_home.py`, and no
Workshop test is owned by another active lane. §4c is the repair.

## 4c. DEFECT-1 — the third defect, found by independent review

The review rejected frozen candidate `ee6b86f0` and was correct.

`/app/workshop` is a **deliberately public preview** (owner decision
2026-08-02). Verified live, signed out: `/app/workshop`, `/app/workshop/add`
and `/app/workshop/work` all return **200**, while `/app` returns 302. Live
Workshop HTML carries `easy-auth-callback.js` and **no** `auth-state.js` and
**no** `data-ps-auth-*` marker at all.

`templates/base.html` sets `is_owner_app_path` for `/app` **and** `/app/…`, so
Workshop renders on the owner shell — no controls container. The 7b guard read
that absence as "private", so after deploy a signed-out visitor on Workshop
would have been reloaded on every tab return. Not after a flag flip: **today**.

It also falsifies my own challenge-2 reasoning. "The session has ended so a save
would be rejected anyway" is untrue here — the visitor is *meant* to be signed
out, and the reload would discard composer state with no session having ended.

**The repair.** `templates/base.html` now emits `data-ps-auth-state` on **both**
shell branches, so every document declares what it is rather than being inferred
from a missing node. The client reloads only when that declaration reads
`authenticated`. `signed_out`, `auth_unavailable`, `account_issue` and an
undeclared document are all left alone — failing to reload is inert, reloading a
correct page is not. The public branch is emitted byte-identically, so no other
page's baseline moved; Interview Studio's 306 tests confirm it.

**DEFECT-2, the tests that encoded the bug**, is repaired too.
`testTheOwnerWorkspaceReloadsEvenThoughItRendersNoAuthState` asserted
"null container ⇒ reload" — the defect written down as an invariant. It is
replaced by `testAnUndeclaredDocumentIsNeverReloaded` and
`testTheOwnerShellIsJudgedByItsDeclaredStateNotByMissingControls`, which drive
both Workshop documents. Two server-side tests assert that a signed-out Workshop
render declares `signed_out` and a signed-in owner-shell render declares
`authenticated`. Negative-tested: removing the shell declaration fails three
tests.

**Also from the review: the side-by-side gap is closed, not documented away.**
The matrix said "focus"; the code listened only to `visibilitychange`, which
does not fire between two windows that are both visible. Rather than restate the
claim more narrowly, a `focus` listener now shares the existing 15-second
throttle — so returning to a tab costs at most one session check however you got
there — and a focus event on a hidden window is ignored. Three new checks cover
the trigger, the shared throttle, and the hidden-window case.

This is the only behavioural change beyond the two named defects. It is offered
for your judgement: if you would rather ship the narrower claim and take this
separately, say so and I will revert it.

### Also in the change

**A Python/JavaScript parity test.** The private-namespace list existed three
times — `safe_return.py`, `auth-state.js`, `easy-auth-callback.js` — with
nothing checking they agreed. That is the same producer/consumer mismatch that
dropped Opportunity Slate members on `/app`, reappearing across the language
boundary. `PrivateNamespaceParityTests` now fails on drift; I negative-tested
it by removing a namespace and confirming the failure, then restoring it.

Please check the regex is not brittle in a way that could make it pass
vacuously. I added `test_the_registered_set_is_not_accidentally_empty` for
exactly that risk, but a second pair of eyes is worth more than my own guard.

**Two stale release records corrected** — see §7.

---

## 5. Verification, and how to reproduce it

### Full suite, run twice for comparison

Baseline, clean `origin/main` `196fd502`:

```
Ran 3898 tests in 222s — FAILED (failures=2, errors=2, skipped=7)
```

All four are pre-existing local-environment reds in Community maintenance / SQL
infrastructure, unrelated to this change:

```
ERROR tests.test_community_maintenance_off_request_path.ScheduledRunnerTests.test_failure_is_content_free_and_returns_failed_status
ERROR tests.test_community_maintenance_off_request_path.ScheduledRunnerTests.test_hard_deadline_interrupts_a_running_sweep
FAIL  tests.test_community_disposable_sql_proof.CommunityDisposableSqlProofTests.test_private_environment_file_has_owner_only_permissions
FAIL  tests.test_community_maintenance_off_request_path.ScheduledRunnerTests.test_success_runs_each_bounded_sweep_once
```

Candidate result: `Ran 3910 tests in 250s — FAILED (failures=2, errors=2, skipped=7)`. The failure set is **identical to the clean baseline**: the same four pre-existing local-environment reds in Community maintenance / SQL infrastructure, and no new red. Of the twelve tests above the 3898 measured at `068e4bcd`, **eight are this change's own**; the other four arrived on `main` with the two Interview Extract control commits this branch was rebased onto.

Expect `3910` tests — eight of the twelve above the 3898 baseline are this change's new
Python tests. The two extra JavaScript checks live in `tests/auth_state.test.js`,
which unittest does not collect; run it with `node` as shown below.

```bash
python -m unittest discover -s tests -t .
```

**Do not trust my numbers — run the baseline yourself.** An earlier revision of
this handoff said an 18-error run was probably machine contention. That was
wrong, and §4a records what it actually was.

### JavaScript behaviour

```bash
node tests/auth_state.test.js     # 17 behavioural checks (was 4)
```

New coverage: a private document does not reconcile on load but does on tab
focus; every registered private namespace and a path beneath one reloads
exactly once; `/auth/sign-in`, `/auth/complete` and public paths never reload;
`/appointments` proves segment matching rather than a bare `/app` string
prefix; a 503, an unrecognised state, unparseable JSON and a rejected fetch each
preserve the server-rendered UI and never reload.

### Byte lock

`/app` moved **15777 → 15846** bytes. The delta is exactly the 69-byte tag
`<script src="/static/js/auth-state.js?v=21716f20541f" defer></script>`,
appearing once. Stripping it reproduces the previous locked baseline byte for
byte (`e6a4cfc7…` unchanged), and that step is now the first link of the
recapture chain in `tests/test_owner_home.py`, so any other disturbed byte
fails there.

`.gitattributes` pins the repository to `eol=lf`, so the content token is
identical on Windows and on the Linux agent. **Please confirm that**, since the
locked SHA depends on it.

Interview Studio's baselines normalize every versioned asset token via
`_INTERVIEW_JS_VERSION_TOKEN`, so the moved `auth-state.js` token does not
disturb them. Confirm that too — those pages already loaded the script, so
their token moved even though their markup did not.

### Live probes, unauthenticated

No credential, token, cookie, principal, or session state was requested, held,
inspected, or stored.

| Probe | Result |
|---|---|
| `GET /auth/session` | `{"state":"signed_out"}`, HTTP 200 — the exact payload that triggers the reload |
| `GET /app` signed out | `302 → /auth/sign-in?return_to=/app` |
| Safe-return matrix, 12 targets | 4 registered destinations round trip; scheme, host, protocol-relative, backslash, dot-segment, NUL, unregistered and `/auth/` targets fall back to `/app` |
| `GET /static/js/easy-auth-callback.js` | HTTP 200, `?v=bfd4097e46c7` |

`origin/main`'s `auth-state.js` hashes to `70ef068d4d73` — exactly the token
production serves, confirming live matches source for the file this changes.

---

## 4d. C1 — the condition that failed, and why it mattered

Round-2 review accepted the candidate `ACCEPTED_WITH_NAMED_CONDITIONS`, and
condition C1 was: confirm production `PEERSLATE_OWNER_HOME_ENABLED` is false; if
it is true, do not ship, and put the declaration on `body.owner-home-shell`
first.

**The flag is `true` in production.** Azure app settings for `peerslate-pete`:
`PEERSLATE_OWNER_HOME_ENABLED=true`, alongside `PEERSLATE_WORKSHOP_ENABLED=true`.
The review had reasoned from the source default and from `auth_routes.py`; the
deployed setting overrides both.

That turned a documented residual into the most important finding of the round.
Flag-on `/app` renders the standalone Owner Home shell, which skips the global
header and therefore carried no declaration. The client would never have
reloaded it. **On production's real configuration, the package's central
outcome would have been inert on the exact page it was built for** — and every
flag-off test would still have passed.

`<body class="owner-home-shell">` now carries
`data-ps-auth-state="{{ auth_navigation_state }}"`. Both shells verified;
negative-tested; the flag-off byte lock is untouched because the change lives
inside the standalone branch. `test_both_owner_shells_declare_their_state`
covers both flag states and asserts the shell each one renders.

C2 is therefore **closed rather than deferred**: enabling Owner Home no longer
re-opens cross-tab sign-out, because the standalone shell declares its state.

## 6. Not in scope, deliberately

- No change to `safe_return.py`, `auth_routes.py`, `community_routes.py`,
  `workshop_routes.py`, or `opportunity_slate_v2_routes.py`. The released
  safe-return behaviour is correct; the live matrix above re-proves it.
- No schema, migration, dependency, pipeline, App Service configuration,
  session duration, cookie policy, provider, tenant, callback, DNS, TLS,
  secret, or RBAC change.
- No material visual change. One `<script>` tag in `<head>`; no new page,
  component, composition, hierarchy, dominant action, typography, colour
  language, or responsive interaction model.
- No merge, deployment, release, or production mutation.

---

## 7. A correction this lane may not apply

`CURRENT_BASELINE.yaml` records production as commit `aa4a4ec6` / pipeline 722.
That is wrong and has been for some time.

**Production is** commit `9f742614949b2a84811c7f6f20e7fbe203e09df2`, Azure
build **1303** (`20260819.44`), active on the production slot since
**2026-08-19T15:14:16Z**.

Proof, not assertion:

```python
release_id_for_build('9f742614949b2a84811c7f6f20e7fbe203e09df2', '1303')
# -> '2edbd8819968a72e74a933e5'   == live /healthz
release_id_for_build('aa4a4ec6a12d334805298f81041fee49c6fdc51a', '722')
# -> '689d0be742c2c8d02c585827'   == live nowhere
```

I could not correct it. `tests/test_operational_readiness.py:1480-1493`
hard-pins the stale strings, the test and the baseline move in enforced
lockstep (`test_baseline_and_lane_ledger_pin_the_same_production_release`), and
that file is a writable surface of the active `PS-INTERVIEW-AI-EXTRACT-001`
lane. Writing it would have been writing another writer's surface.

Three records must change in one commit: `CURRENT_BASELINE.yaml` `authority`,
`CURRENT_LANES.json` `release_truth`, and the pinned strings in
`test_operational_readiness.py`.

**Also note:** `CURRENT_BASELINE.yaml` is at **896 words against a hard <900
cap** (`tests/test_governance_pointers.py:83`). There are four words of
headroom. I tried to trim the `authority` note for room and the activation
validator correctly refused — activation may not change that section. Whoever
edits it next should trim while they are in there, or a legal edit will turn
`main` red.

---

## 8. Honest limitations

- **Not proven in a real browser across two real tabs.** That needs two
  signed-in members — `GAP-SYNTHETIC-MULTI-MEMBER-QA`, an S00 row owned by
  `PS-SYNTHETIC-MULTI-MEMBER-QA-001`. The node tests drive the real module and
  the live probes prove both server halves; the join between them is reasoned,
  not observed. **This is the weakest evidence in the change.**
- **The reload is client behaviour.** With JavaScript unavailable the member
  keeps the stale page until they navigate, exactly as before. The server-side
  guarantee is unchanged and unconditional.
- **Session expiry** is now measured (`FixedTime 08:00:00`, 72h token refresh,
  5min validated nonce) but remains App Service configuration that no source
  test can assert.
- **Accessibility** was not separately re-evaluated: the change adds no visible
  element and alters no focus order, so I judged the existing coverage
  sufficient. Challenge that if you disagree.

---

## 9. Contact and next step

Return one of the three verdicts in §1, naming any defect precisely enough to
act on. The candidate returns to me for correction; I will produce a new exact
frozen SHA and hand it back if anything material changes.

Pete has authorized me to carry this package through PR, merge, deployment, live
verification, and package exit once you accept the exact candidate. Please do
not merge, deploy, or alter the lane record yourself.
