# Community color language and component architecture

## 1. Owner decision and current effect

Pete's 2026-08-16 direction is binding for the active Community visual-creation
round:

- make the Community page more colorful and less green-heavy;
- make action icons meaningfully colorful;
- use white, rather than beige, for the creative-post composer surface; and
- carry the revised language through all new mockups so implementation receives
  one coherent system.

This record changes visual direction only. It does not change live code,
publication behavior, privacy, audience rules, data architecture, or release
state. Exact hues and final raster authority remain open until Pete approves
the revised mockups.

## 2. Page brief

- **Member purpose:** enter Community, understand what changed, participate in
  a finite conversation, and create or respond to a post without visual noise.
- **Dominant object:** the Community conversation/feed, with the compact
  create-post composer as its focused authoring layer.
- **Dominant action:** deliberately publish a member-authored post to the
  selected audience.
- **Truth boundary:** drafts remain private; audience selection is explicit;
  public publication requires confirmation; AI may propose wording but may not
  silently save, change audience, or publish.
- **Must not become:** a green monochrome dashboard, a beige form, a rainbow
  toy, a Facebook visual copy, an infinite engagement feed, or an oversized
  authoring workspace.

## 3. Preserved composition authority

The approved compact composer remains the geometry model:

- centered desktop modal with a shallow title bar;
- one compact identity/audience/save-status row;
- one short, naturally growing writing area;
- one icon-only `Add to your post` row;
- one full-width primary Post action;
- small overlay audience menu that does not resize or reflow the modal; and
- transient Voice, attachment, AI, recovery, and publication states that fit
  within the same efficient component family.

Facebook may remain a structural density reference only. PeerSlate must not
copy Facebook's palette, icon styling, typography, trade dress, or branding.

## 4. Revised color hierarchy

Use a restrained **70 / 20 / 10** balance:

- approximately 70% neutral canvas and white surfaces;
- approximately 20% low-saturation tinted support surfaces and icon wells; and
- approximately 10% stronger brand/action accents.

### Neutral and brand roles

- **Community canvas:** cloud white or a very light warm-neutral gray. Avoid a
  pervasive beige cast.
- **Cards and composer:** clean white. The writing surface should read as open,
  creative, and crisp.
- **Body text:** ink/navy, not green.
- **Deep PeerSlate green:** reserve for the logo/identity anchor, the primary
  Post action, selected brand-critical states, and occasional trust cues. It is
  not the default color for every icon, border, heading, and control.
- **Existing warm navigation accent:** may remain as a small active underline
  or section cue when it supports the shared shell.

### Accent family

The exact hex values are selected in the visual lock, but the role mapping is
stable:

| Role | Direction | Typical use |
| --- | --- | --- |
| Photo/image | cerulean or cobalt blue | photo icon, image attachment cue |
| Video | warm coral | video icon and bounded media cue |
| File/document | amber or ochre | file icon, document attachment cue |
| Voice/dictation | teal | microphone, live waveform, listening state |
| Optional AI | violet or plum | sparkle icon and proposal affordance |
| Community/helpful activity | rotate restrained blue, teal, amber, coral, and plum tints | rail medallions, pulse categories, helpful-response cues |

Do not give a whole card a saturated fill merely because its icon has an
accent. Prefer colored glyphs, pale icon wells, short rules, compact badges,
and small section cues.

### State semantics remain separate

- success/posted: green plus explicit text or icon;
- information: blue plus explicit text or icon;
- warning/confirmation: amber plus explicit text or icon;
- error/destructive: red plus explicit text or icon; and
- disabled: neutral gray with adequate legibility.

Action accents must not make a coral Video control look destructive or an amber
File control look like a warning. Shape, label/tooltip, placement, and state
copy carry meaning alongside color.

## 5. Component rules

### Composer

- Outer surface and editable field are white; boundaries use subtle neutral
  lines and low elevation rather than beige panels.
- The primary Post button remains deep green so there is one unmistakable
  dominant action.
- The five media/action icons use their assigned accent colors in the same
  compact row. Active Voice may use a pale teal well and teal waveform without
  increasing component height.
- Audience and saved-status controls stay visually quieter than the Post action.
  Selection may use a pale brand or blue-tinted surface, not a large green block.
- AI remains a small violet/plum sparkle affordance and never becomes a second
  dominant action.

### Community page and rails

- Preserve the approved Mine / Ours / Beyond composition and editorial
  hierarchy.
- Use color to distinguish meaning in small doses: catch-up types, Pulse,
  questions, My Mix, Explore, The Break, replies, and helpful activity may each
  receive a consistent accent glyph or pale medallion.
- Keep cards primarily white so posts and people remain dominant. Avoid filling
  entire rails with competing colors.
- Keep the page calm at a glance and richer on inspection.

### Responsive behavior

- The accent mapping remains identical on desktop, iPad, and mobile.
- Mobile does not lose color identity, but it also does not gain extra chips,
  labels, or stacked decoration.
- At 200% zoom and narrow widths, color cues must survive reflow without being
  the only way to distinguish an action.

## 6. Token architecture for implementation

The eventual runtime package should implement the approved palette through
scoped semantic tokens rather than one-off element colors. The final exact
values must come from Pete's locked mockups.

Expected roles include:

```text
--community-canvas
--community-surface
--community-surface-subtle
--community-ink
--community-ink-muted
--community-brand
--community-brand-soft
--community-accent-photo
--community-accent-photo-soft
--community-accent-video
--community-accent-video-soft
--community-accent-file
--community-accent-file-soft
--community-accent-voice
--community-accent-voice-soft
--community-accent-ai
--community-accent-ai-soft
--community-info
--community-success
--community-warning
--community-danger
--community-focus
```

Tokens must derive from or coexist cleanly with the shared PeerSlate theme.
They may not globally recolor unrelated rooms. Dark-theme counterparts, if the
supported Community release includes dark mode, require the same semantic roles
with independently verified contrast.

## 7. Accessibility and finish gate

- Normal text meets WCAG 2.2 AA contrast; large text meets its applicable
  threshold.
- Meaningful icons, focus indicators, boundaries, and UI component states meet
  the applicable non-text contrast expectation.
- Color is never the only carrier of audience, save, recording, attachment,
  success, warning, failure, or selected state.
- Every icon-only control has an accessible name and a visible tooltip or other
  discoverable label where appropriate.
- Keyboard focus remains obvious across white and tinted surfaces.
- Forced-colors, reduced-motion, 200% zoom/reflow, long text, and touch targets
  are verified in the later runtime package.

## 8. Visual lock and implementation gate

The visual-creation gate passed on 2026-08-17. The exact files, hashes,
viewports, state roles, and precedence are preserved in
`02_VISUAL_AUTHORITY_MANIFEST.md`.

The remaining gate is runtime-specific. A separately authorized Protected
implementation package must map the locked roles to tokens, resolve the open
audience/privacy and capability contracts, compare representative
desktop/tablet/mobile browser captures, and verify the accessibility
requirements above. The visual lock does not itself authorize code, migration,
enablement, deployment, or a live-product claim.

## 9. Pete's Voice-state acceptance and deferred site-wide refinement

On 2026-08-16 Pete accepted the color-calibrated Voice-listening candidate for
continued use in this Community round. It establishes the working application
of this architecture: white creative surface, compact unchanged geometry,
deep-green primary action, and blue/coral/amber/teal/violet authoring icons.

Pete also judged the overall result to remain somewhat green-heavy. That is a
known visual-refinement observation, not a failure of this package. It is
deferred to a later whole-site color review so Community work can proceed
without inventing a page-local brand correction that might conflict with the
rest of PeerSlate.

The final Community state set and hashes are preserved in
`02_VISUAL_AUTHORITY_MANIFEST.md`. A later whole-site palette revision may
supersede color values through a new material-visual decision; until then, it
must preserve the accepted Community composition, semantic accent roles,
accessibility, and truth model.
