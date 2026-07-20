# PS-CAPTURE-MEDIA-001 - Experience and Accessibility

## Visual authority

Photo is a new state of the real protected Capture product, not a standalone
uploader. Its binding minimums are:

1. the accepted production `/app/capture` Speak/Type hierarchy and review
   composition implemented by PS-VOICE-001;
2. the owner-approved Capture promise in
   `docs/governance/approved_owner_visual_baseline/02_capturing_moments_with_peerslate.png`,
   particularly private-by-default, review-before-canonical, and attach-photo;
3. Deep Navy Gold, light-first owner-shell rules in `AGENTS.md`; and
4. `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`.

The older dark storyboard supplies interaction intent, not current theme tokens
or permission claims. The accepted real protected product is upstream. A
photo-specific V1 storyboard/state set must receive Pete plus designated-
manager visual acceptance before Claude Code changes the runtime UI.

## Required state set

The V1 design and final evidence must show, at minimum:

1. Capture opening with Type, Speak, and Photo understandable at first glance.
2. Take-photo and choose-photo entry, including unsupported device/browser.
3. Local selection preview labeled `Not saved yet`.
4. Upload progress/cancel and interrupted upload.
5. Private scan pending with Type/Voice escape path.
6. Scan delay/error/cap reached and retry/delete/replace actions.
7. Unsafe or unsupported file rejection with no preview.
8. Safe derivative review, required note, privacy/provenance explanation, and
   one dominant **Save private Capture** action.
9. Long note, validation error, stale row version, and unavailable storage.
10. Confirmed private Capture in the recent list with source indicator,
    authorized preview/download/export, correction, archive/restore, and delete.
11. Deletion pending/retry and deletion complete.
12. No-JavaScript document flow and text fallback.

Future photo controls may be visible only when disabled and truth-labeled. Do
not show fabricated AI captions, OCR, tags, audience, publication, destination,
or matching results.

## Interaction rules

- File selection uses a visible label and native input; a drop zone may be an
  enhancement but is never the only control.
- Camera capture is optional. Keyboard and choose-file paths perform the same
  task.
- Focus moves deliberately to the current status/review heading after a state
  change and returns to the invoking control when a dialog closes.
- Cancel during client upload stops the request where possible and never claims
  the server draft is deleted. Once accepted server-side, use explicit draft
  deletion.
- Status is concise live-region text. Do not announce progress on every byte or
  animate indefinitely without reduced-motion handling.
- The local preview's alternative text is `Selected photo, not saved yet`.
  Server review uses the owner's current note when present and otherwise a
  neutral `Private photo awaiting your description` label.
- Do not expose the client filename as visible identity or accessible name.

## Responsive requirements

### Desktop

- One dominant Capture object in the opening viewport.
- Photo review uses a deliberate image-and-note composition, not a generic
  dashboard grid.
- Primary save remains visible without covering the preview, text, errors, or
  browser controls.

### Mobile

- Take photo is an obvious first-class action; choose-file remains available.
- Review uses readable document flow or a purpose-built full-screen/bottom-
  sheet state, not a shrunk desktop card.
- Safe areas, virtual keyboard, portrait/landscape, long validation text, and
  44-by-44 CSS-pixel touch targets are verified.
- The save action remains reachable and unobscured; the floating Ask Pete AI
  control may not overlap it.

### 200% zoom and reflow

- No horizontal page scroll at the required narrow reflow viewport except
  within the photo itself when an explicit zoom control is provided.
- Instructions, status, privacy truth, note, and actions remain in semantic
  order and are not clipped by fixed overlays.

## Screen reader and keyboard

- Native file input remains in the accessibility tree.
- All controls have visible text or precise accessible names and visible focus.
- State is not conveyed by color, thumbnail, or animation alone.
- Preview dimensions/format may be summarized as bounded metadata; do not read
  opaque IDs, digests, or provider codes.
- Every dialog traps focus only while genuinely modal, supports Escape where
  safe, restores focus, and has a normal document-flow/no-JavaScript fallback.
- Delete confirmation states exactly whether it deletes an unconfirmed photo
  draft or the photo Capture/source aggregate.

## Reduced motion and media sensitivity

- Use opacity/transform only for optional transitions and remove nonessential
  movement under `prefers-reduced-motion: reduce`.
- Upload/scan indicators have a static equivalent and do not use a flashing or
  continuously sweeping effect.
- No automatic image zoom, pan, parallax, carousel, or animated crop.

## Truthful labels

Required language concepts:

- `Private photo draft`
- `Not saved yet`
- `Scanning your private photo`
- `Safe preview; embedded metadata removed`
- `Original retained privately with this Capture until you delete it`
- `Save private Capture`
- `Nothing is shared or published`

Do not say `safe`, `scanned`, `saved`, `deleted`, or `private` until the relevant
backend state enforces that exact statement.

## Homepage parity

The logged-out homepage already projects Voice/Capture and presents photo as
`Coming later`. When protected Photo becomes real, that projection is stale.
`PS-HOME-CAPTURE-PHOTO-PARITY-001` must either update the homepage in the same
release wave or remain an explicit blocking downstream package. It must show a
truthful distilled photo experience and may not imply public upload, AI caption,
publication, or cross-room use.
