# Community Voice composer propagation architecture amendment

**Package:** `PS-COMMUNITY-PUBLIC-PILOT-001`  
**Path:** Protected  
**Authority:** Pete-locked `2026-08-01-pete-voice-first-lock` A-H states  
**Approval:** Pete approved the reviewed primary-comment slice on 2026-08-02
and instructed this task to keep going.  
**Scope:** propagate the reviewed transient Voice controller to the remaining
approved Community text composers; default-off local implementation and review
only.

## Reuse map

Keep the existing request-only endpoint and `CommunityVoiceService` unchanged.
Parameterize the existing `CommunityVoiceController` rather than adding a
second implementation:

| Surface | Existing form and input | Context | Limit | Existing send boundary |
| --- | --- | --- | ---: | --- |
| Primary Feed comment | dynamic `[data-primary-comment]` | `contribution` | 2,000 | comment Send |
| Original post | `[data-composer-form]` and `textarea[name="body"]` | `post` | 4,000 | Review public post, then explicit public confirmation |
| Full conversation comment, author update, or nested reply | `[data-reply-form]` and `#cv1-reply-body` | `contribution` | 2,000 | reply Send |

The top composer-bar microphone opens the existing private original-post
composer and delegates to its one Voice controller. It does not create a
second recorder, panel, draft, or publication path. The conversation form
continues to derive comment, author-update, and reply semantics server-side
from the authenticated owner, post, and validated `state.replyParentKey`.
Voice sends none of those identity or target claims to transcription.

## Controller seams and lifecycle

The reusable controller accepts its context, UTF-16 limit, accessible noun,
panel host, resize callback, and lifetime. Controller IDs are unique and do not
depend on a Feed post key.

Feed-card controllers remain Feed-scoped and are disposed when Feed/search
content is replaced. Original-post and conversation controllers are
page-scoped so a Feed refresh cannot disable their microphones. All surfaces
still share one page-wide active-recorder/request registry.

In addition to the reviewed cleanup paths, clear transient audio, proposal,
tracks, timers, and requests when:

- the original composer is reset, cancelled, closed, changes between create
  and edit, or completes a post mutation;
- the reply target changes, a reply succeeds, or the conversation closes or
  is replaced by history navigation; and
- the page emits `pagehide`.

Typed viewer-namespaced drafts remain local. Cleanup never changes typed text.
An unresolved Voice preview or active operation must be used, discarded, or
cancelled before its composer is hidden behind a confirmation or closure.

## Decision boundaries

`Use transcript` inserts reviewed proposal text at the current selection only
when the combined text fits the surface limit. It never overwrites, truncates,
saves, sends, selects Public, or publishes. The original-post path remains:

`Use transcript -> private typed draft -> Review public post -> explicit
Publish publicly`.

Reply/comment Send remains separate and direct. Existing server-derived
identity, authorization, audience, idempotency, attachment, and contribution
contracts are unchanged.

## Files and proof

Implementation is limited to the package README, this amendment and checkpoint,
`templates/community_feed.html`, `static/js/community-v1.js`,
`static/css/community-v1.css`, focused Community Voice/public-pilot tests, and
package-scoped browser evidence. No API, service, route-limit, SQL, migration,
Blob, provider, retention, flag, navigation, or release change is required.

Prove context/limits, insertion without replacement or truncation, no automatic
send/publish, public-confirm isolation, reply-target draft separation,
cross-surface single-recorder ownership, scoped rerender survival, cleanup,
keyboard/focus, permission/provider failure, desktop/mobile/dark/reflow, and
the unchanged text-only paths. Then complete one Protected independent review
and stop before migration, Candidate, flag activation, PR, merge, deployment,
or any live/public claim.
