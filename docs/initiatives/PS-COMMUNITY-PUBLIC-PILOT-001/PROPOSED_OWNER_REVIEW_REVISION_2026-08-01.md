# PS-COMMUNITY-PUBLIC-PILOT-001 — proposed owner-review revision

**Captured:** 2026-08-01
**Owner:** Pete
**Status:** accepted input record — superseded for visual implementation by the exact 2026-08-01 Pete Voice-first lock; not release evidence
**Input reference:** Pete's two real-time Community Feed reviews, two current-build screenshots, and two Facebook post/conversation pattern references supplied in the current Codex task

## Why this record exists

Pete reviewed the current fixture build and requested a materially different
conversation/composer presentation plus broader file and Voice capabilities.
This record preserves those requirements without pretending that the existing
2026-07-31 six-board lock authorizes the revised design or that unbuilt backend
capabilities already work.

The resulting two-board production-intent set is now locked at
`PS-COMMUNITY-FEED-VISUAL-001/visual-authority/2026-08-01-pete-voice-first-lock/`.
Its manifest records the approved truth/accessibility corrections. The
protected runtime package remains controlling for implementation, retention,
verification, and release.

## Second owner review — exact direction to carry into the revised authority

Pete's follow-up review makes the following hierarchy and interaction changes
explicit. These are production requirements for the next exact visual state
set, not authorization to improvise them directly in runtime code:

- Reduce the Community surface's overall type scale and spacing density toward
  the calm, compact readability of established social conversation surfaces.
  The revised authority must specify the Community type ramp at desktop,
  mobile, large text, and 200-percent reflow without changing the shared-site
  typography family or making controls too small to use.
- Treat the post card, post body, and published image as direct ways to open the
  same full-post conversation surface. Opening an image must show the image in
  its post context together with the complete comment thread and composer, not
  a disconnected image-only preview.
- Remove the redundant visible `Open post` action. Preserve one semantic,
  keyboard-operable post link and clear focus behavior without turning every
  nested control into the same click target.
- Remove visible `Save` actions from Feed cards, post conversations, and
  contribution actions. The revised protected package must explicitly decide
  whether V1 private-save procedures remain dormant for future use or are
  removed; a hidden UI action must not imply the capability is released.
- Make Respond and conversation actions compact and icon-led. The five
  purposeful response meanings remain Celebrate, Support, I relate, Ask, and
  Offer help, but the visible trigger/tray should use a refined, immediately
  legible PeerSlate icon family with accessible names and tooltips rather than
  oversized text buttons or copied third-party assets.
- Use one integrated reply/comment composer. The text field occupies the shell;
  file, photo, video, audio/public-media, and Voice controls sit in its lower
  tool row; and submission is a triangular send icon inside the field at the
  lower right. There is no separate large `Reply` button or full-width `Add
  file` row.
- Voice remains visibly primary in that tool row and in the original-post
  composer. A microphone control is present anywhere Community accepts text;
  it cannot be hidden behind the general attachment control.
- The full-post conversation is the primary detailed view: media, post
  context, compact response summary, ordered comments/replies, and the sticky
  integrated composer belong to one responsive surface. Selecting a comment
  may focus that conversation branch without replacing it with a sparse
  selected-reply card.

The supplied Facebook screenshots establish familiar interaction patterns and
information density only. They do not authorize Facebook branding, asset
copying, exact trade dress, reaction vocabulary, ranking, or engagement
mechanics.

## First refinement-pass implementation status

This brief has now driven a bounded local review pass, but it still does not
supersede the exact visual lock:

- the review build uses the established full-width `16:7` Feed image treatment;
- its fixture shows four shelf contributions and a compact visible `View all`
  control with the full accessible name;
- post and contribution menus dismiss on outside click and Escape, and the
  conversation-header post menu is live;
- the gate workbook is present in a fixture owner update for review;
- the command candidate now rejects client-supplied contribution kinds and SQL
  derives `author_update`, `comment`, or `reply` inside the locked transaction;
- strict macro-free XLSX upload/download support is implemented in the local
  runtime and migration candidate; and
- none of those local results is deployment evidence. The real workbook has
  not been published to a live Community post.

The revised Respond popover, icon family, wide Facebook-familiar composer,
conversation/action re-layout, Voice/audio, video, and direct messaging remain
unimplemented. Their visual or protected functional authorities are still
required as described below.

## Owner-directed experience changes

### Feed media

- Make Feed images substantially larger and more visually dominant.
- Use the available Feed-card width and materially more vertical space so
  published work stands out while scanning.
- The revised authority must settle single-image and gallery aspect ratios,
  maximum height, crop/contain behavior, caption treatment, loading/error
  geometry, mobile treatment, and focused-open behavior.
- Activating an image must open the complete post-and-conversation experience,
  with a keyboard-equivalent action and a usable return focus target. Document
  attachments remain authorized downloads rather than fake image previews.

### Replies and updates shelf

- Show a fourth contribution/partial fourth card so horizontal traversal is
  obvious.
- Remove redundant visible `Replies & updates` wording from the shelf header.
- Place the visible `View all` control at the right edge while preserving the
  explicit accessible name `View all Replies & Updates`.
- Preserve one non-wrapping, horizontally traversable row with mouse, touch,
  keyboard, focus restoration, and finite paging truth.

### Respond interaction

- Replace the current large inline expansion with a compact horizontal
  popover/strip aligned to `Respond`.
- Support click/tap and keyboard focus/activation. Pointer hover may reveal the
  tray as an enhancement, but cannot be the only path.
- Outside click, Escape, selection, and a second trigger activation must close
  the tray and return/preserve focus appropriately.
- Replace the current basic glyphs with a refined PeerSlate five-intention icon
  set while preserving the established semantics: Celebrate, Support,
  I relate, Ask, and Offer help.
- The closed trigger is icon-led rather than a large visible `Respond` label.
  Visible labels may appear in the tray, tooltip, or other exact state needed
  for clarity and accessibility.

### Conversation and reply composer

- Make the desktop conversation surface approximately as wide as the Feed and
  give its content more breathing room; mobile remains a true full-screen
  conversation.
- Remove the visible contribution-kind dropdown.
- Use one Facebook-familiar composer shell: multiline text area, bottom-left
  attachment/input icons, and an integrated send control at the right inside
  the shell.
- The send control is a triangular send icon inside the lower-right corner of
  the composer. It replaces the separate large `Reply` button while retaining
  an explicit accessible name.
- The lower tool row uses compact, individually labelled controls for general
  file, photo, video, audio/public media, and microphone/Voice. Controls appear
  only when their real capability or an exact truthful unavailable state is
  authorized; Voice is not grouped under general attachments.
- The send control must retain a clear accessible name, disabled-empty state,
  loading state, recoverable failure, idempotency, and draft/attachment
  preservation.
- If the current post author submits a top-level follow-up, the requested
  default is `author_update`. Reply targeting and contribution type must be
  derived and validated by the server rather than trusted from a hidden client
  field. The protected command contract must define the exact non-owner and
  parent-reply behavior before implementation.

### Contribution presentation and actions

- Keep author-only edit and delete behavior.
- Put a smaller `Reply` action at the lower left.
- Remove the visible contribution `Save` action from this presentation. A
  separate product decision must say whether the underlying contribution-save
  capability is retired or simply absent from this surface.
- Remove the visible post-level `Save` action from Feed and full-conversation
  presentation under the same protected disposition.
- Put the Message affordance at the lower right only when it is truthful. The
  current pilot has no direct-messaging mutation, so the first usable release
  must hide it or show the revised exact unavailable state; it must not fake a
  sent message.
- Make the owner ellipsis visually smaller. Pete requested it at the end of the
  first sentence; the revised authority must settle wrapping, long content,
  touch target, keyboard order, zoom, and mobile behavior before code moves it.
- Fix the concrete current bug so post and contribution menus close after
  outside click, Escape, or a completed action and only one menu remains open.

### File and Voice controls

- The composer icon row should ultimately cover photo, video, audio/voice, and
  file attachments.
- Voice is a primary Community input, not an attachment submenu or a later
  enhancement. It must be front-and-center in the original-post quick/expanded
  composer and every reply, comment, and author-update composer.
- Every Community writing surface must support both typing and speaking, with
  the microphone/voice affordance visible alongside the text entry path rather
  than hidden under `Add file`.
- The exact visual states must cover ready-to-record, permission request,
  recording with a polished waveform and elapsed status, explicit stop,
  processing/transcription, transcript review/edit, retry, cancel, permission
  denied, microphone unavailable, provider failure, and a text-only fallback.
- Dictation audio remains private transient input in the minimum slice. It must
  not automatically become a public audio attachment, insert an unreviewed
  transcript, or publish a post/reply. `Use transcript` and `Publish`/`Reply`
  are separate explicit member decisions.
- A public audio attachment is a separate media action with its own visible
  public-audience, playback, transcript/accessibility, retention, and deletion
  contract; it cannot silently reuse dictation audio.
- Pete's first requested workbook is the Community public-pilot gate tracker,
  attached to an owner `author_update` on the most recent small-win post.

## Current contract conflicts

| Requested capability | Current owner-pilot contract | Required disposition |
| --- | --- | --- |
| XLSX attachment | JPEG, PNG, and PDF only | Protected attachment amendment: OOXML container/signature validation, macro policy, malware scanning, download-only response, retention, revocation, and tests |
| Video attachment | Deferred | Separate safe-video processing/range-delivery contract or truthful deferral |
| Audio attachment | Deferred | Audio allowlist/player/accessibility/retention contract, preferably coordinated with Voice |
| Live dictation | No Community Voice integration | Protected Voice-in-Community contract covering consent, provider use, transcript review, provenance, failure, deletion/export, and text fallback |
| Direct message | No V1 Community mutation | Separate messaging package or truthful unavailable/hidden state |
| Automatic author-update type | Client currently submits explicit type | Protected command amendment with server-derived owner/target semantics |
| New composer/Respond/action hierarchy | Existing six-board lock differs materially | New ChatGPT-created desktop/mobile/critical-state authority and Pete exact lock |

## Required revised visual state set

The revised ChatGPT visual-creation lane should produce enough exact material
to remove runtime guesswork for:

1. desktop and mobile Feed cards with the enlarged single image and gallery,
   compact Community type ramp, icon-led actions, no visible `Open post`, and
   no visible `Save`;
2. desktop and mobile Replies/updates shelf with the fourth/partial-fourth
   traversal cue and simplified `View all` header;
3. Respond closed, hover/focus, opened, selected, replaced, removed, loading,
   failure, and narrow-screen states;
4. wide desktop and full-screen mobile full-post conversation states with
   post media, long/nested contributions, direct image/post activation, branch
   focus, sticky composer, and return-focus behavior;
5. empty, typing, file/photo/video/audio tool row, voice-ready, permission,
   dictation-recording, stop,
   transcription-processing/review, attachment-selected, upload-processing,
   send-loading, and recoverable-failure composer states for both an original
   post and a reply/update, including the integrated triangular send icon;
6. owner versus non-owner contribution actions, including edit/delete menu
   open/dismiss behavior;
7. truthful Message unavailable/hidden treatment for the first pilot; and
8. light, dark, 200-percent reflow, large-text, keyboard/focus, touch, and
   reduced-motion dispositions where the interaction changes.

The Facebook screenshot is a pattern reference for compact comments and the
integrated composer, not a PeerSlate production lock and not permission to copy
Facebook branding or icon assets.

## Fastest truthful path to a usable pilot

1. **Complete:** the revised Feed/conversation/composer/Respond authority,
   including the front-and-center Voice state set, is Pete-locked at the
   2026-08-01 Voice-first authority path.
2. Amend the current package for server-derived owner `author_update` behavior
   and XLSX download-only attachments so Pete can publish the gate workbook.
3. Amend the protected package for reusable Community Voice input, then build
   the complete capture, permission, visible recording, transcription,
   review/edit, explicit `Use transcript`, retry/cancel, failure, cleanup, and
   text-fallback flow. Propagate that proven flow to every Community composer.
   **This is a release blocker for Pete's usable public pilot, not a post-launch
   enhancement.**
4. Finish and release the owner-authored public pilot only after both typed and
   Voice input pass the protected and visual acceptance gates, alongside
   JPEG/PNG/PDF/XLSX.
5. Add video and direct messaging only through their own protected contracts;
   neither should hold the first usable owner pilot unless Pete explicitly
   makes it a launch requirement. Public audio attachments remain distinct from
   Voice dictation and require their own explicit release disposition.

## Stop controls

- Do not implement the new material composition from prose alone.
- Do not treat the current screenshots or third-party pattern references as an
  exact PeerSlate production lock.
- Do not add decorative audio, video, dictation, XLSX, or Message controls that
  lack real backend capability or an exact unavailable state.
- Do not interpret a fixture workbook card as proof that production XLSX upload
  or public download works.
- Do not publish, message, save, transcribe, or change audience without the
  member's explicit action and server authorization.
