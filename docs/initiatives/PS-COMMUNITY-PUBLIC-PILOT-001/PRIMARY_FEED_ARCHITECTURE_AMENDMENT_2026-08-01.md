# Community primary Feed architecture amendment

**Package:** `PS-COMMUNITY-PUBLIC-PILOT-001`  
**Checkpoint:** primary `/the-slate` Feed page only  
**Delivery path:** Protected package; bounded local visual implementation  
**Authority:** the Pete-locked 2026-08-01 Voice-first boards and manifest

## Slice boundary

This amendment does not replace the protected package or create a second
Community architecture. It records the minimum mapping needed to implement the
default, closed primary Feed page and identifies the still-missing
Community-to-Voice seams. This checkpoint changes no identity, audience,
publication, attachment, Voice, schema, migration, service, feature-flag, or
release behavior.

The page purpose is to let a reader scan one calm, newest-first public
conversation card. The dominant object is the post and its large media; the
dominant owner action is the closed `Respond` trigger. The first review render
uses Pete-only fixture content and is visibly local/fixture-only. Pete remains
content, never shared product logic.

## Locked UI to existing component map

| Locked UI responsibility | Existing authority/component | Checkpoint use |
| --- | --- | --- |
| `/the-slate` selection and default-off boundary | `app.py:the_slate`, `PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED` | Preserve; no new route or flag. |
| Viewer identity and owner capability | `community_routes.viewer_context`, `get_optional_identity`, `is_owner` | Preserve server-derived identity; no browser owner claim. |
| Finite newest-first Feed | `community_api.feed`, `CommunityFeedService.feed_page` | Preserve the existing public projection and opaque finite cursor. |
| Canonical post/card data | `CommunityFeedService._post` | Render the same body, author, audience, attachment, count, permalink, and owner-viewer response fields; add no presentation column. |
| Primary card and closed actions | `community-v1.js:cardNode`, `community-v1.css` | Apply the locked hierarchy only to the Feed card: derived first-paragraph lead, large media, comment count, unique closed Respond symbol, and owner menu. No visible Save or repetitive Open-post action. |
| Post-local Replies & updates shelf | `CommunityFeedService._post.preview_contributions`, existing shelf pagination, `renderConversationShelf`, and the locked Threadline Signal direction | Render exactly one non-wrapping horizontal shelf on the primary post, with equal-height compact cards, clipped-next-card affordance, attachment ribbons, a persistent `View all Replies & Updates` action, and exact-contribution activation. This reconnects an existing component; it adds no schema, service, audience, member-authoring, or media capability. The local preview uses Pete-only author-update fixtures and does not represent live multi-user activity. |
| Supporting Feed rails | Existing `community_feed.html` catch-up, Spark, pulse, active-question, and caught-up rail markup | Restore the locked desktop information architecture around the owner-corrected 748px primary stage with 234px rails. Rails align with the top composer bar and disappear at compact widths in favor of the existing mobile tools; no new navigation or live aggregation is introduced. Owner-pilot copy remains truthful. |
| Primary response picker | existing `PUT`/`DELETE /api/v1/community/posts/<post_key>/response` commands plus the owner-corrected primary response control | The Feed card opens one compact, anchored rail on hover, focus, or click/touch. Five actual emoji map to the existing intentions (`celebrate`, `support`, `i_relate`, `ask`, `offer_help`). Selection saves immediately and privately; selecting the active emoji removes it. There is no primary-page dialog, card grid, `Done`, or `Remove` footer. The control remains derived from `post.viewer.response`, so Pete is fixture data and the renderer remains reusable for any authorized viewer. |
| Primary comment entry | existing owner-authorized `POST /api/v1/community/posts/<post_key>/contributions` command | Each authorized primary Feed card has one text-only, top-level comment field below Comment/Respond. It starts at one line, grows only as typed text wraps, preserves its unsent text in the viewer-namespaced local draft store, and uses a per-post idempotency record without putting comment content in the command record. Submit remains a separate user action. No attachment, reply-parent, conversation, or member-authorship behavior is added. |
| Comment Voice affordance | locked Voice visual language plus the missing Community dictation seam below | The compact mic control establishes the future cross-site placement beside Send but is explicitly exposed as not yet available. It captures no audio and starts no permission, recording, upload, or transcription state. Typed comment entry remains fully usable. |
| Full-post activation contract | Existing delegated `conversation` action | Title, media, and truthful comment count retain the same activation target. The modal/conversation implementation is inherited and is not revised at this checkpoint. |
| Publication commands | `community_api.publish_post`, `CommunityCommandService.publish_post` | Preserve owner-only authorization, explicit `audience=public`, idempotency, and canonical SQL write. No publication change in this checkpoint. |
| Private draft | owner-derived `community_draft_namespace` plus namespaced browser `localStorage` draft | Preserve local/private-by-default text. Opening a composer creates no server record. |
| Public confirmation | Existing composer selection plus the locked required confirmation step | The candidate already requires explicit Public selection, but its separate pre-publication confirmation remains a missing secondary-state seam and is not implemented here. Send must eventually open that confirmation; only confirmation may call `publish_post`. |
| Attachments | `CommunityMediaService`, `CommunityMediaStorage`, reauthorizing preview/download routes | Preserve current JPEG/PNG/PDF/macro-free-XLSX allowlist and private Blob/scan lifecycle. The primary card consumes only returned safe preview/download URLs. |
| Existing protected Voice primitives | `validate_audio`, `SpeechTranscriptionService`, server-only managed identity, Voice focus/error patterns | Reuse validation, provider isolation, safe errors, and transcript-as-proposal semantics. Do not invoke `VoiceCaptureService.confirm_capture` for Community. |

## Missing Community-to-Voice seams (not implemented at this checkpoint)

Only the following seams are required for the later protected Voice pass:

1. **Owner-only transient transcription command.** Add one package-scoped
   multipart command under `community_api` using the existing same-origin
   checks and `_owner_identity`. It accepts a bounded recording and a validated
   composer context (`post` or `contribution`) only to select the applicable
   text limit; context never grants identity or publication authority.
2. **Community dictation adapter.** Reuse `validate_audio` and
   `SpeechTranscriptionService.transcribe`, but do not create a Voice source,
   Capture, Community post, contribution, attachment, or SQL row. The minimum
   Community flow holds audio only for the active request; server bytes are
   released after the normalized response. The browser may retain the unsaved
   Blob in memory for an explicit retry, but never in `localStorage` or as a
   public attachment.
3. **Composer-local A-H state controller.** Add the locked ready, permission,
   recording, processing, transcript-preview, denied/unavailable, failure, and
   ready-to-send states to the original-post and contribution composers. Typed
   text remains available throughout. Cancel, denial, or failure preserves the
   namespaced local text draft and restores focus safely.
4. **Reviewed insertion only.** The transcript response is an editable
   proposal. `Use transcript` inserts the reviewed text into the current local
   textarea and moves to ready-to-send. Discard/cancel removes the in-memory
   audio/transcript proposal. Neither action saves or publishes.
5. **Separate send boundary.** Original-post Send still requires deliberate
   Public selection and the separate public-confirmation component before the
   existing publish command. Reply/comment Send remains a separate explicit
   command. No Voice state may call either command automatically.
6. **Protected cleanup and evidence.** The later pass must prove no retained
   server audio, no content-bearing logs, owner-only access, size/duration and
   transcript limits, provider failure handling, keyboard/screen-reader focus,
   reduced motion, and text fallback. Public audio and video remain
   unavailable and outside this seam.

The released `VoiceCaptureService` remains authoritative for private Capture,
where original audio is retained and explicit confirmation creates a private
Capture. Community dictation deliberately stops before that convergence point:
its only output is a reviewed local text proposal for Community-native social
speech.

## Primary-page implementation and review boundary

This checkpoint may edit only the package-reserved Community template, card
renderer, route-local CSS, focused frontend contracts, this amendment, and a
non-production preview harness. The preview harness may substitute a labeled
Pete-only in-memory fixture for the Feed read model; it may not seed SQL,
pretend persistence, or change production selection.

Full-post composition, reply branches, composer/Voice states, permission and
failure matrices, publication confirmation, migrations, real Blob/Speech,
retention, Break integration, Candidate, PR, merge, deployment, and flag
activation remain explicitly unopened until Pete approves the real primary
page render.

Pete's 2026-08-01 checkpoint correction supersedes the earlier oversized
primary response panel shown in the rejected review capture. The compact emoji
rail is now the reusable presentation rule for a Respond intention picker.
Applying that rule to the dormant full-conversation response surface remains
secondary-state work and is deliberately not started in this checkpoint.

Pete's subsequent primary-page correction adds the compact type/Voice/Send
pattern only to main Feed posts where the current server-derived viewer is
authorized to comment. This records a reusable placement rule for later
appropriate surfaces; it does not add the control to Motion, the full
conversation surface, or unrelated pages, and it does not authorize the Voice
state matrix.

Pete's final PC correction rejects a second expanded Voice activator beneath
that compact row. In this primary-page slice the compact microphone beside Send
is the sole idle Voice affordance, remains unavailable, and opens no recording
or transcription panel. Any future Voice behavior is separate protected work;
it is not activated by this amendment.

Pete's earlier real-browser reviews progressively reduced the primary Feed
stage from 720 to 640 to 660 and then to a ruler-based 500 CSS-pixel desktop
maximum. Pete's later review of the reconciled page superseded that 500px
intermediate state with a 650px stage, exactly thirty percent wider, and 180px
rails with 16px gaps. Pete's still-later 748px/234px correction below now
controls. Narrow screens remain fluid.

After the PC-to-Mac collision audit, Pete confirmed that the Feed must also
retain the already-approved Threadline Signal composition: one post-local
horizontal `Replies & updates` shelf plus the supporting left and right desktop
rails. He approved a subtle cool blue-gray Motion-card surface and pale rail
tints to separate those regions from the white primary post. This is a
package-local visual correction to existing components, not a competing visual
direction or authorization for full-conversation, Voice, messaging, release,
or data-layer work.

Pete's latest primary-page correction places the compact 40px comment row
immediately after Comment/Respond and before the Motion shelf. The two visible
actions are borderless 36-by-34px controls with 20px icons at rest; the actual
five-emoji hover/focus rail remains 196 by 46px with 36px choices. Motion cards
are 145 by 136px on desktop and separated by 12px; narrow cards are 96 by
132px. Restrained layered gradients and shadows now distinguish the page,
primary post, Motion cards, preview notice, and rails. These are CSS and render
order changes only. They create no new service, schema, audience, authorization,
publication, attachment, or Voice seam.

Pete's following correction replaces the floating `New post` trigger with a
Facebook-familiar top composer bar. Every bar action delegates to the existing
private-draft composer, which still requires explicit Public selection and a
separate publish action; no inline publication command is added. The center
stage is 748px, each rail is 234px, and the three surfaces share the same top
alignment. Motion presentation drops the redundant `Author update` suffix,
retains relative time, and bounds author/body/attachment metadata inside the
equal-height card with two-line ellipsis. The clipped next card remains a
scroller affordance rather than hidden or lost content; activating a card
continues to open the complete contribution.

Pete's medium-width correction keeps `Community activity` on one line without
changing its destination or data. The top composer bar now carries a compact
Voice control matching the post comment row. It is a placement seam only in
this slice: activation reports that Voice is unavailable and leaves the typed
post path usable. The protected microphone/recording/transcription matrix
remains unopened. On narrow screens the media shortcut hides before Voice so
the microphone remains visible.
