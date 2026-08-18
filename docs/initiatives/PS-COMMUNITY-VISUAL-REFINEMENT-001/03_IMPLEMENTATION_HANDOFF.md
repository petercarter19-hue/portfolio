# Community visual implementation handoff

## 1. Outcome and boundary

Implement the locked Community composition and authoring system without
inventing product truth. The visual target is the exact authority set in
`02_VISUAL_AUTHORITY_MANIFEST.md`; the functional target remains private by
default, deliberate about audience and publication, resilient to failure, and
accessible at supported widths and input modes.

This handoff is architecture, not permission to start runtime work. A dedicated
Protected implementation package must first reserve the writer and files,
reconcile current live Community behavior, adopt exact identity/audience/data
contracts, and define tests and release gates.

## 2. Page and component architecture

```text
CommunityPage
├── GlobalHeader
├── CommunityShell
│   ├── MineRail
│   ├── OursFeed
│   │   ├── ComposerLauncher
│   │   └── PostThreadList
│   └── BeyondRail
├── CommunityComposerLayer
│   ├── ComposerHeader
│   ├── IdentityAudienceStatus
│   ├── GrowingEditor
│   ├── VoiceStatus
│   ├── AttachmentTray
│   ├── AuthoringTools
│   ├── AiActionPopover
│   ├── DraftRecoveryNotice
│   └── PublicationAction
└── FeedbackLayer
    ├── ConfirmationPopover
    └── StatusToast
```

The composer is one stateful component family, not separate unrelated dialogs
for text, Voice, files, AI, and publication. Transient controls overlay or fit
within its natural geometry; they must not create the rejected oversized
workspace.

## 3. Required state model

| State | Required visible truth | Primary action |
| --- | --- | --- |
| Closed | Community page and compact launcher | Start a post |
| Empty | Placeholder, `Not saved yet`, colored icon row, disabled Post | None until content exists |
| Drafting | Growing text at caret, explicit audience, `Saved privately` once persisted | Post |
| Audience open | Compact overlay; no modal resize or text reflow | Select audience |
| Voice listening | Teal microphone/waveform, elapsed time, `Listening`, compact Stop; words enter at caret | Stop |
| Attachment ready | Compact removable thumbnail/file chip | Post |
| Attachment failed | Preserved draft and attachment context, `Upload failed · Retry` | Retry/remove |
| AI menu | Small violet popover: `Make clearer`, `Make shorter`, `Ask a better question`; original unchanged | Choose proposal action |
| Draft sync failed | `Couldn't sync. Your draft is safe.` and Retry; content preserved locally | Retry |
| Public confirmation | `Publish publicly? Anyone with the link can view this post.` | Publish or Cancel |
| Publishing | Disable duplicate submission while preserving visible content | Wait/cancel only if supported |
| Posted | `Posted · Undo` for the bounded undo window | Undo |
| Publish failed | Preserve the complete draft and audience; explain failure neutrally | Retry |

Closing an empty composer closes it. Closing a nonempty composer preserves a
private draft. Discard must be a separate deliberate action.

## 4. Identity, audience, privacy, and publication

- Derive member identity server-side. Never trust a client-supplied author ID.
- Draft content and attachment state are private/no-store and authorized before
  retrieval or mutation.
- The visual lock shows `Private`, `Connections`, `Community`, and `Public`.
  Their presence is not runtime authorization. The implementation package must
  define membership, relationship, revocation, block/mute, visibility, direct
  link, and count behavior for every enabled audience.
- Current shared public-pilot authority previously deferred some non-Public
  audiences. That trust/product conflict must be explicitly reconciled before
  an implementation exposes those choices as enabled controls.
- Opening the composer does not publish or widen an audience. Public requires
  the pictured confirmation. Changing audience after publication requires its
  own approved contract; do not infer it from the menu.
- A save is private to the member. `Save privately` never changes the post's
  audience or creates a public count.
- Publication, function, visual acceptance, merge, deployment, and live proof
  remain separate states.

## 5. Voice, attachments, and optional AI

### Voice

- Dictation is transient input into the same editor at the caret; it is not a
  public audio attachment.
- Permission denial, unavailable input, interruption, and retry must preserve
  existing text.
- Recording status must have text/icon meaning in addition to teal color.

### Attachments

- Photo, video, and file controls use the approved icon mapping and compact
  tray/chip treatment.
- Upload progress, validation, scan/processing, failure, retry, and removal must
  not discard the draft.
- The runtime package must define allowed types, size/quota, storage ownership,
  scanning, derivative generation, revocation, cleanup, and authorized open.

### AI

- AI is optional, small, and invoked deliberately through the violet sparkle.
- The original remains unchanged while a proposal is generated.
- A proposal is editable and becomes draft text only after an explicit member
  choice.
- AI may not invent facts, silently save, change audience, attach media,
  publish, delete, or make any Community statement canonical.
- AI-unavailable behavior leaves ordinary authoring fully usable.

## 6. Layout and responsive behavior

### Wide desktop

- Preserve the Mine / Ours / Beyond three-column hierarchy.
- Keep Ours dominant and both rails purposeful rather than decorative.
- Use a centered, natural-height composer with a practical maximum width near
  the locked compact geometry; do not scale it with the full viewport.

### Landscape tablet

- Preserve three columns while their content minimums remain usable.
- Reduce gaps and rail widths before shrinking type or touch targets.
- Keep the composer a centered contained dialog, approximately the locked
  540–570 px family, with touch targets near 44 × 44 px.

### Phone portrait

- Replace desktop rails with the `Mine | Ours | Beyond` switcher; Ours is the
  ordinary feed default shown in the lock.
- Use a bottom sheet for the ordinary composer, approximately 65–72% of the
  available viewport when its content fits.
- A full-height sheet is permitted only when keyboard, long content, large
  text, errors, or supported attachments require it.
- Respect safe-area insets and keep the Post action reachable. When the software
  keyboard appears, scroll/reflow content rather than hiding the action or
  shrinking touch targets.

Breakpoints should follow content minimums rather than device names. The exact
locked desktop, iPad landscape, and phone captures are the comparison anchors.

## 7. Visual and token implementation

Use the semantic roles in
`01_COLOR_LANGUAGE_AND_COMPONENT_ARCHITECTURE.md`. Do not sample and scatter
one-off colors across selectors.

- white composer and content surfaces;
- cloud-neutral page canvas;
- ink/navy body text;
- deep green reserved for brand identity and the primary Post action;
- Photo blue, Video coral, File amber, Voice teal, and AI violet;
- restrained colored rail medallions rather than saturated cards; and
- explicit success, warning, error, information, focus, and disabled roles.

Files 02–04 in the manifest are geometry-only. Applying their older palette is
a fidelity failure. The later whole-site color review is deferred and does not
block this implementation direction.

## 8. Published posts and replies

- Render published attachments compactly beneath the post body.
- Keep response actions low-pressure and without public popularity totals.
- `Save privately` remains a private member action.
- The reply composer inherits the visible audience truth and includes Voice as
  an input aid only.
- Replies remain compact, readable, and subtly separated; nested author replies
  use indentation and an understated `Author` badge.
- Long replies, additional replies, deletion/moderation/permission states, and
  direct links require truthful replacement or continuation behavior; do not
  collapse them into invented counts or infinite scrolling.

## 9. Accessibility contract

Implement and verify the behavior in file 10:

- logical focus order and focus restoration after modal/popover close;
- strong visible focus with no layout shift;
- accessible names for every icon-only control and discoverable tooltips where
  appropriate;
- 200% zoom and 320 CSS-pixel reflow without horizontal clipping;
- forced-colors boundaries, selection, and focus that survive custom-color
  removal;
- normal and large-text contrast meeting WCAG 2.2 AA expectations;
- touch targets approximately 44 × 44 px where the device is touch-first;
- no color-only audience, saved, listening, selected, success, warning, or
  failure meaning;
- reduced motion with no required confetti, bounce, or animated disclosure;
  and
- `Posted · Undo` announced without stealing focus unnecessarily.

## 10. Implementation order

1. Reconcile the current Community implementation, route, flags, APIs, and
   active ownership against fresh `origin/main`.
2. Create a dedicated Protected runtime package and reserve one writer/surface.
3. Resolve the exact audience and publication contract before enabling the
   pictured menu.
4. Build the semantic token layer and shared composer shell.
5. Implement empty, drafting, close/preserve, audience-overlay, and save states.
6. Add Voice, attachments, AI proposal isolation, recovery, confirmation, and
   publication states behind their truthful backend capabilities.
7. Implement the published post/reply composition and authorized interactions.
8. Implement desktop, iPad, phone, zoom, large-text, forced-colors, keyboard,
   safe-area, and reduced-motion behavior.
9. Compare representative browser captures side by side with the exact locked
   files and correct visible drift.
10. Run the package's authorization, privacy, failure, accessibility,
    responsive, pipeline, rollback, and live-smoke gates before making any live
    claim.

## 11. Required comparison evidence

At minimum capture and compare:

- desktop closed/published page;
- desktop empty, active, audience-open, and Voice states;
- attachment failure/retry, AI menu, draft sync failure, public confirmation,
  and posted/Undo states;
- iPad landscape composer;
- phone portrait ordinary composer;
- keyboard focus, 200% zoom/narrow reflow, forced colors, large text/touch, and
  reduced motion; and
- long content plus every actual permission, unavailable, and failure state the
  implementation can produce.

## 12. Explicit exclusions and open gates

- Spark remains excluded.
- No runtime implementation, migration, feature enablement, deployment, or
  live-product claim is authorized by this documentation branch.
- Exact audience semantics, moderation, notifications, edit/delete, attachment
  limits/retention, AI provider/data flow, and operational ownership remain
  runtime-package decisions.
- Homepage work is required only if the released homepage makes a materially
  affected Community capability or visual claim.
- The later whole-site color-refinement review may adjust shared palette values;
  it is not a reason to delay the completed Community visual lock.
