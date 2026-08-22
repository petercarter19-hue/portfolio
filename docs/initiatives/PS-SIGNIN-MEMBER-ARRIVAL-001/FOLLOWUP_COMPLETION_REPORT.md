# PS-SIGNIN-MEMBER-ARRIVAL-001 — Follow-up Completion Report

**Outcome:** signing out in one tab now ends the session everywhere, and three
release records stop claiming work is unshipped that members have been using
for weeks.
**Delivery path:** Protected (shared shell, session-state boundary).
**Owner decision:** Pete, 2026-08-21 — "I want you to do everything".
**Round:** second. The first round's report is
`OWNER_TECHNICAL_COMPLETION_REPORT.md`; this closes two limitations it named.

## What was wrong

The first round closed the sign-in return journey and listed what it had
deliberately left open. Two of those were still open, and its own diagnosis of
the first one was wrong in a way that mattered.

**1. Cross-tab sign-out.** A member signed out in one tab kept a fully usable
private workspace in another until they navigated. The first report attributed
this to `templates/base.html` not loading `auth-state.js` on `/app`, and
implied that loading it there was the fix.

It is not. `templates/base.html:291` withholds `data-ps-auth-controls` from the
owner workspace, and `:357` renders a separate legacy branch of account
controls that carry no `data-ps-auth-control` attribute at all. Every element
`auth-state.js` toggles lives in the `not is_owner_app_path` branch. Loading
the script on `/app` as described would have found nothing to toggle: a change
that reads correctly, tests green, and fixes nothing.

Swapping a header is also the wrong ambition. Turning the control into
"Sign In" while a private workspace stays on screen underneath trades one
untruthful state for another.

**2. Session expiry.** Recorded as unverifiable because the governing lifetime
is App Service configuration with no representation in this repository. The
second half of that is true. The first half was not: the policy is readable.

**3. Three stale release records.** `PS-SIGNIN-EXPERIENCE-001/COMPLETION.md`
still read "Not deployed, not pushed" nineteen days after PR 229 merged.
`PS-AUTH-CALLBACK-001/COMPLETION_REPORT.md` showed four release gates Pending
four weeks after PR 165 merged. `CURRENT_BASELINE.yaml` — the file every
session reads first — still named a 9 August build as production.

## What changed

**Reload, don't repaint.** `auth-state.js` now recognises a private document
and, when the session check answers `signed_out`, reloads it instead of
touching controls. The server then does what it always does: `/app` answers
`302` to `/auth/sign-in?return_to=/app`. The private content leaves the screen,
and the destination is preserved by the first round's safe-return work, so
signing back in returns the member to where they were.

This follows the pattern `easy-auth-callback.js` already uses for a private
document restored from bfcache. The two predicates are deliberately different:
that one treats `/auth/` as private so it can clear a callback fragment; this
one must treat `/auth/` as **not** private, because reloading a sign-in page on
a signed-out session is a loop. Both files say so.

The one-attempt flag lives in a `WeakSet` keyed on the window. It never touches
browser storage, and a genuinely new document may try again.

**A private document reconciles on tab focus, not on load.** The first revision
of this change also reconciled on `pageshow`, which put a `/auth/session`
request on every private page load. That broke all 16
`JournalBrowserBehaviorTests`, which navigate `/app/journal` with
`wait_until="networkidle"`: they went from 5s to a 30s timeout. It was caught
only by running the suite against clean `origin/main` and diffing the failure
sets, and two plausible explanations — an infinite reload loop, and a
single-threaded fixture server — were both measured and disproved before the
real cause was found.

Dropping the load-time check is the better design regardless. The server
authorized that very render, so asking again immediately is redundant;
`easy-auth-callback.js` already covers a private document restored from
bfcache; and the case this exists for is returning to an already-open tab (a `visibilitychange` to visible, not a `focus` event),
which `visibilitychange` covers. Public documents are unchanged.

**A private prefix is not always a private page.** Three of the four registered
namespaces are gated by configuration, not by nature. With the gate off, the
same path serves an ordinary public page to a signed-out visitor — and that
render is truthful, not stale: it already carries
`data-ps-auth-state="signed_out"`. The first version of this change would have
reloaded it, so a signed-out visitor on a public Interview Studio would have
been reloaded every time they returned to the tab.

The reload is therefore conditional on the server having rendered the document
for a signed-**in** member: state `authenticated`, or no state container at all,
which is the owner workspace and the one unconditionally private namespace.
Found by reading the diff back rather than by a failing test — production has
that gate on today, so nothing would have caught it before a flag flip.

**The shell declares what it rendered.** Independent review rejected the first
frozen candidate on this, and it was right. `/app/workshop` is a deliberately
public preview — owner decision 2026-08-02 — and returns **200 to a signed-out
visitor in production today**, while `/app` returns 302. It renders on the
*owner* shell, which carries no account controls at all. The previous revision
inferred "this document is private" from that absence, so after deploy a
signed-out visitor on Workshop would have been reloaded every time they
returned to the tab. The `WeakSet` does not bound that: a reload makes a new
document with a fresh flag.

That reasoning was wrong in a way worth naming. The guard asked "is there no
controls container?" when the question is "did the server render this for a
signed-in member?" Those coincided on `/app` and diverged on `/app/workshop`.

`templates/base.html` now emits `data-ps-auth-state` on **both** shell
branches, so every document states what it is. The client reloads only when
that declaration reads `authenticated`; `signed_out`, `auth_unavailable`,
`account_issue` and an undeclared document are all left alone. Failing to
reload is inert. Reloading a page that is behaving correctly is not.

The public branch is left byte-identical, so no other page's baseline moved —
Interview Studio's 306 tests confirm it.

**Two windows side by side now reconcile too.** `visibilitychange` does not
fire when you click between two windows that are both visible, so the headline
claim — signing out in one place reaches the other — was false for that
arrangement. Independent review named it as a gap in the claim rather than a
ship-blocker; it is closed rather than documented away. A `focus` listener
shares the existing 15-second throttle, so returning to a tab still costs at
most one session check however you got there, and a focus event on a hidden
window is ignored.

**Both owner shells declare, not just one.** `/app` renders through two
different shells. Flag-off uses the global header, whose `platform-actions`
carries the declaration. Flag-on uses the standalone Owner Home shell, where
`{% if not standalone_owner_shell %}` skips that header entirely — so the
declaration was absent there and the client could never reload it.

Independent review found this and made shipping conditional on
`PEERSLATE_OWNER_HOME_ENABLED` being false in production. **It is not.** Azure
app settings for `peerslate-pete` record `PEERSLATE_OWNER_HOME_ENABLED=true`.
So the condition failed, and the hole was not theoretical: on production's
actual configuration this package's whole purpose — reloading the owner
workspace after sign-out elsewhere — would have been inert on `/app`, while
every flag-off test stayed green.

The declaration now also sits on `<body class="owner-home-shell">`. Verified
both ways: flag-off renders the legacy shell and declares `authenticated`,
flag-on renders the standalone shell and declares `authenticated`.
Negative-tested: removing the body declaration fails the flag-on case only.
The flag-off byte lock is untouched, because the change lives inside the
standalone branch.

**`templates/base.html`** drops `/app` from the exclusion and keeps `/auth/`.

**A parity test across the language boundary.** The list of private namespaces
existed three times — `safe_return.py`, `auth-state.js`,
`easy-auth-callback.js` — and nothing checked that they agreed. That is exactly
the producer/consumer mismatch that dropped Opportunity Slate members on
`/app`, reappearing where no test was watching: register a destination on the
server, forget a script, and it breaks quietly in a member's browser.
`PrivateNamespaceParityTests` now fails instead. It was negative-tested by
removing one namespace and confirming the failure, then restoring it.

**The two stale package records** now state their actual released state with
commit, PR, build, deployment time, and the derived live release identity. The
one gate that is genuinely still open — a fresh owner sign-in and callback
check — is left open and marked as needing Pete.

## Verification

Full suite: `Ran 3910 tests in 250s — FAILED (failures=2, errors=2, skipped=7)`. The failure set is **identical to the clean baseline**: the same four pre-existing local-environment reds in Community maintenance / SQL infrastructure, and no new red. Of the twelve tests above the 3898 measured at `068e4bcd`, **eight are this change's own**; the other four arrived on `main` with the two Interview Extract control commits this branch was rebased onto.

`tests/auth_state.test.js`: 17 behavioural checks (was 4). New coverage — a
private document does not reconcile on load but does on tab focus; every
registered private namespace and a path beneath one reloads exactly once;
`/auth/sign-in`, `/auth/complete` and public paths never reload;
`/appointments` proves the match is a path-segment match and not a bare `/app`
string prefix; a 503, an unrecognised state, unparseable JSON and a rejected
fetch each preserve the server-rendered UI and never reload.

Live, against production as it stands today (unauthenticated, no credentials
requested, held, or inspected):

| Probe | Result |
|---|---|
| `GET /auth/session` | `{"state":"signed_out"}`, HTTP 200 — the exact payload that triggers the reload |
| `GET /app` signed out | `302` to `/auth/sign-in?return_to=/app` — where the reload lands, destination preserved |
| `GET /static/js/easy-auth-callback.js` | HTTP 200, `?v=bfd4097e46c7` — closes a PS-AUTH-CALLBACK-001 gate |
| Safe-return matrix, 12 targets | 4 registered destinations round trip; scheme, host, protocol-relative, backslash, dot-segment, NUL, unregistered and `/auth/` targets all fall back to `/app` |

`origin/main`'s `auth-state.js` hashes to `70ef068d4d73`, exactly the token
production serves — independent confirmation that live matches source for the
file this round changes.

### Changed expectations, and why

One, and it is the point of the change.

**`/app` byte lock: 15777 to 15881 bytes.** Two deltas, 104 bytes: the
69-byte script tag and the 35-byte declared state. The chain strips each in
turn and only then reproduces the locked baseline. The tag is exactly
`<script src="/static/js/auth-state.js?v=21716f20541f" defer></script>`,
appearing exactly once. Proven by the documented method — stripping that tag
from the new render reproduces the previously locked baseline byte for byte,
SHA `e6a4cfc7...` unchanged — and that step is now the first link of the
recapture chain, so if loading the script had disturbed any other owner
workspace byte it would fail there. `.gitattributes` pins the repository to
LF, so the content token is identical on Windows and on the Linux agent.

Nothing else was recaptured and no test was relaxed.

## Session policy, measured

Read from App Service `authsettingsV2` (read-only; nothing was changed):

| Setting | Value |
|---|---|
| Cookie expiration | `FixedTime`, `08:00:00` |
| Token refresh extension | 72 hours |
| Nonce | 5 minutes, validated |

This is configuration evidence, not a source contract. No test in this
repository can assert it and none pretends to. Recording it converts the first
round's "unverifiable" into "verified, and outside source control" — which is
the honest description.

## Visual authority

No material visual change. One `<script>` tag in `<head>`. No new page,
component, composition, hierarchy, dominant action, typography, colour
language, or responsive interaction model.
`OWNER_VISUAL_INTEGRITY_STANDARD.md` is not triggered.

## Honest limitations

- **Not merged and not deployed.** This is a reviewed candidate. It changes
  behaviour on every signed-in page, so release is Pete's decision.
- **The production truth record is still wrong, and this lane may not fix it.**
  `CURRENT_BASELINE.yaml` names commit `aa4a4ec6` / pipeline 722. Production is
  commit `9f742614949b2a84811c7f6f20e7fbe203e09df2`, Azure build 1303
  (`20260819.44`), active on the production slot since 2026-08-19T15:14:16Z.
  Proof: `release_id_for_build('9f742614...', '1303')` returns
  `2edbd8819968a72e74a933e5`, which is exactly what live `/healthz` serves,
  while the recorded pair derives `689d0be742c2c8d02c585827`, which is live
  nowhere. The correction is blocked, not unknown:
  `tests/test_operational_readiness.py:1480-1493` hard-pins the stale strings
  and moves in enforced lockstep with the baseline, and that file is a
  writable surface of the active `PS-INTERVIEW-AI-EXTRACT-001` lane. Writing it
  would be writing another writer's surface. **Whoever holds that file can
  apply all three values in one commit.**
- **The reload is a client behaviour.** With JavaScript unavailable the member
  keeps the stale page until they navigate, exactly as before. The server-side
  guarantee is unchanged and unconditional: every protected route re-authorizes
  on the next request.
- **The reload's cost to unsaved work is unmitigated.** A reload discards
  in-progress input on a private page. The session has already ended so a save
  would be rejected anyway, but this destroys client state without asking. It is
  named for review rather than solved.
- **Not proven in a real browser across two real tabs.** That needs two
  signed-in members and is `GAP-SYNTHETIC-MULTI-MEMBER-QA`, an S00 row owned by
  `PS-SYNTHETIC-MULTI-MEMBER-QA-001`. The node tests drive the real module and
  the live probes prove both server halves; the join between them is reasoned,
  not observed.
- **`/auth/` surfaces are unchanged by design**, so a member sitting on a
  sign-in page after signing out elsewhere still sees whatever the server last
  rendered. Reloading there is the loop this exclusion exists to prevent.

## Target reconciliation

`origin/main` moved during this round, from `068e4bcd` to `196fd502` — one
commit, "Activate Interview Extract merge-control child", touching only
`docs/governance/CURRENT_BASELINE.yaml` and `docs/governance/CURRENT_LANES.json`.
Zero overlap with this candidate's nine paths, so reconciliation required **no
implementation change**. The branch was rebased onto `196fd502`, this lane
remains registered and active (now 4 of 4 writer slots), and the full governance
set was re-run green against the new ledger.

## Next action

Pete decides whether to release. If yes: PR, required pipeline, then confirm
`/app` serves the new tag and `/auth/sign-in` still does not. If no, the
candidate stays frozen and no member-facing behaviour changes.

Separately, and independently of this lane: the production truth record above
needs one commit from the `PS-INTERVIEW-AI-EXTRACT-001` writer.
