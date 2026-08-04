# Community Voice propagation protected checkpoint

**Package:** `PS-COMMUNITY-PUBLIC-PILOT-001`  
**Branch:** `codex/2026-08-01-community-primary-feed-sol-ultra`  
**Authoritative base at implementation:**
`d53686abfd68fb1b688b4a56a9976230ab77bea5`  
**Architecture commit:** `bbe7c0e`  
**Implementation commit:** `6ceb0d3b583dbb398cffb057eefed69ed84a5edb`  
**Self-review correction:** `619aacb`
**Final reviewed range:** `bbe7c0e^..54a9d1b`
**State:** local Protected propagation implemented, browser-verified, and
independently reviewed PASS

## Outcome

The reviewed transient Community Voice controller now serves the remaining
approved Community text composers:

- original-post creation/edit composer with `post` context and a 4,000 UTF-16
  unit limit;
- the full-conversation top-level comment/author-update and nested-reply form
  with `contribution` context and a 2,000-unit limit; and
- the top Feed microphone as a delegate to the original-post controller, not a
  separate recorder or draft.

The primary Feed comment remains on the same reusable controller. All surfaces
share one active-recorder/request registry. Feed rerenders dispose only
Feed-scoped controllers; the static post and reply controllers survive. New
cleanup hooks cover composer reset/close/success, edit/create transitions,
reply-target changes, reply success, conversation replacement/close/history,
and `pagehide`.

Complete-diff self-review found that the existing edit-mode attachment toggle
hid the whole post tool strip and therefore hid Voice. The correction moves the
attachment-only marker to File and Photo so Voice remains present while editing
text. It also adds one shared unresolved-Voice submission guard so neither
`Save changes` nor `Review public post` can hide an active recording, request,
or transcript review.

Voice still inserts only a reviewed proposal. It never selects Public, changes
the reply target, derives contribution kind, saves, sends, publishes, or opens
a second command path. Original-post publication still requires explicit
Public selection, `Review public post`, and separate `Publish publicly`.

## Changed runtime and test paths

- `templates/community_feed.html`
- `static/js/community-v1.js`
- `static/css/community-v1.css`
- `tests/test_community_voice.py`
- `tests/test_community_public_pilot.py`
- `tests/test_community_secondary_states.py`

The architecture approval, package status, this checkpoint, and package-scoped
browser evidence are the only documentation changes. No API, service, route
limit, SQL, migration, Blob, provider, retention, flag, navigation, or release
file changed in the implementation commit.

## Verification

The implementation writer recorded:

- 128 focused Community/Voice/Speech tests passed;
- JavaScript syntax passed;
- Python compilation passed; and
- diff whitespace passed.

After the self-review correction, 104 directly affected Community Voice,
public-pilot, and secondary-state tests passed, including 23 subtests, together
with JavaScript syntax and diff-whitespace checks. The broader 128-test set was
not duplicated because the correction changed only template visibility,
client-side pre-submit gating, and its focused contract coverage.

Real-browser proof covered original-post and reply success flows, the unchanged
public-confirmation boundary, reply-target cleanup, permission denial,
transcription failure, focus/status behavior, desktop light/dark, 390px mobile
reflow, 44px review actions, and clean console output. See
`evidence/2026-08-02-community-voice-propagation/BROWSER_BEHAVIORAL_PROOF.md`.

## Release truth and next gate

This is not feature completion, release readiness, deployment, or live Speech
proof. The Community flag remains default-off. No migration, Candidate, flag
activation, PR, push, merge, deployment, retention approval, or public/live
claim occurred.

The independent Protected review passed with no blocking or material findings
on the exact range through `54a9d1b`. The broader package still requires its
remaining migration, attachment, retention, Candidate, release, and live
verification gates before Pete can use the pilot in production.
