# Pete-locked Community Feed Voice-first visual authority

## Owner decision

Pete approved this exact two-board set on 2026-08-01, including the documented
manifest corrections below, with the instruction to hand implementation to a
new Sol Ultra session.

This lock supersedes the 2026-07-31 public-pilot visual lock for Community Feed,
full-conversation, composer, and Voice presentation. It authorizes
implementation; it is not evidence that the revised runtime is built, merged,
deployed, enabled, or live.

## Exact files

| File | Authority | Raster size | SHA-256 |
| --- | --- | ---: | --- |
| `01-feed-and-conversation.png` | Feed card, full-post conversation modal, mobile conversation, density, and interaction hierarchy | 1536 × 1024 | `d92beeca76556fbe18ce02723405fa624014c3d0fbf80f7956723e441bd5a156` |
| `02-composer-and-voice.png` | Original-post and reply composer, attachment tools, send behavior, Voice states, focus order, and protected truth | 1448 × 1086 | `0feddceebd2868c6a0922fba90b18d54acd6e9fb05a01a82acc81ae52652aa7b` |
| `REFERENCE-workshop-type-and-color.png` | Typography weight/scale and restrained color-language reference only; not layout or navigation authority | 1448 × 1086 | `e0f0c4283e321da10a6ee423b26b7b31231314741819a436d84487b3233e5d8b` |

## Binding hierarchy and manifest corrections

The two controlling boards remain exact except for these owner-approved,
non-material truth/accessibility corrections. These corrections control over
conflicting raster labels or annotation marks:

1. The closed `Respond` trigger is a unique multi-intention symbol: two linked
   conversation-bubble outlines with a small four-point spark, cobalt 2 px
   stroke, inside a 44 px circular target. Its accessible name is `Respond`.
   It must not resemble Save, Celebrate, or Ask. The question-mark icon remains
   exclusive to the `Ask` intention.
2. The five intentions are exactly `Celebrate`, `Support`, `I relate`, `Ask`,
   and `Offer help`. Any raster label resembling `I-initiate` is an image-text
   artifact and is non-authoritative.
3. Blue numbered bubbles on the composer board are editorial callouts, not UI.
   The controlling keyboard/focus order is: 1 Text area, 2 File, 3 Photo,
   4 Voice, 5 Video unavailable, 6 Public audio unavailable, 7 Send.
4. The controlling Voice state identifiers are A Voice ready, B Permission
   request, C Recording, D Processing, E Transcript preview, F Microphone
   denied/unavailable, G Transcription failure, and H Ready to send. The
   successful flow is A → B → C → D → E → explicit Use transcript → H → Send;
   B/F/G provide retry, cancel, or typed fallback.
5. Original-post Send opens the existing explicit public-confirmation
   component after the owner deliberately selects Public. It never publishes
   directly. Reply/comment Send submits directly. Cancel preserves the private
   local draft.
6. V1 attachments are JPEG, PNG, PDF, and macro-free XLSX only, maximum 10 MiB
   each and maximum four per post or contribution. Video and public audio are
   visibly unavailable. Voice is active private dictation, not a public audio
   attachment.
7. The microphone permission dialog is illustrative and operating-system
   controlled. Dictation audio is processed privately for transcription, is
   never published as audio, and is deleted under the protected Voice cleanup
   policy. Transcript insertion and Publish/Reply remain separate explicit
   actions.

## Typography and color interpretation

`REFERENCE-workshop-type-and-color.png` controls only the following shared
visual language:

- normal copy uses near-black/deep navy rather than pervasive blue;
- cobalt is reserved for primary actions, active navigation, selection, focus,
  and occasional links;
- the established PeerSlate serif/sans pairing remains, with selective bold
  hierarchy and compact readable body sizing;
- white/off-white surfaces, pale neutral canvas, restrained borders, and soft
  elevation provide the base; and
- green, amber, and red remain semantic status/destructive colors rather than
  decoration.

The reference does not authorize its Workshop layout, navigation, routes,
information architecture, controls, content, or capabilities on Community.

## First-pilot truth

- Pete is fixture content and the sole initial owner/interactor; product logic
  remains reusable and server-derived.
- Signed-out visitors are read-only. No broader member writing, public
  reactions, ranking, pinning, featuring, direct messaging, or public Voice
  attachment is implied.
- Visible `Open post` and Save actions are absent. Post title, photo, and the
  truthful comment count open the same full-post conversation.
- Voice is visible anywhere Community accepts text; typed input remains
  available through permission, processing, and failure states.

No other candidate or third-party screenshot is part of this exact lock.

## Post-lock primary-Feed owner corrections

Pete inspected the real primary `/the-slate` page after this board set was
locked and approved the following exact corrections on 2026-08-01. They
control only the primary Feed card; the full-conversation and Voice-state
boards remain unchanged.

1. The primary Respond expansion is a compact 196-by-46-pixel floating rail
   using five actual emoji controls in this order: Celebrate, Support,
   I relate, Ask, and Offer help. The visible option controls are 36 by 36
   pixels with 22-pixel emoji. This is an owner-approved exception to the
   board's general 44-pixel touch-target target for this compact rail; WCAG
   target size, spacing, keyboard, focus, touch, and zoom evidence remains
   required before release.
2. Selecting an option saves the existing private response immediately;
   selecting the active option removes it. There is no heading, explanatory
   block, close button, card grid, Remove footer, or Done footer on the primary
   Feed card.
3. An authorized primary Feed card includes one compact, initially one-line
   `Write a comment…` field below Comment and Respond. It grows only as text
   wraps, preserves an unsent viewer-namespaced local draft, and submits a
   top-level text contribution only through a separate Send action.
4. The compact microphone control establishes the later Voice placement beside
   Send but is truthfully unavailable. It requests no permission, captures no
   audio, and performs no transcription until the protected Community Voice
   pass is implemented and accepted.
5. Pete's PC review rejected a second expanded Voice activator beneath the
   compact comment row. The idle primary Feed card has one Voice affordance:
   the compact microphone beside Send. No additional Voice panel is rendered
   below the row in this primary-page slice.
6. Pete's next real-browser inspection found the 720-pixel desktop Feed stage
   oversized. The controlling desktop primary Feed stage is now a compact
   640 CSS pixels maximum, with the card, media, preview notice, access notice,
   and policy line sharing that center-column width. Narrow/mobile reflow still
   uses the available viewport rather than a fixed width.
7. Pete then set the final density target at approximately ten percent larger
   than a familiar 600-pixel social-feed card. The controlling desktop maximum
   is therefore 660 CSS pixels. The established proportions remain intact:
   16-pixel card inset, full inner-width landscape media, compact 44-pixel
   action targets, and a 48-pixel comment field. This final correction
   supersedes the 640-pixel intermediate review width in item 6.
8. Pete rejected the 660-pixel result after direct inspection because it still
   appeared materially oversized. The final ruler-based desktop primary Feed
   maximum is 500 CSS pixels, matching Meta's concrete 500-pixel desktop
   embedded-post example. The 16-pixel inset and locked type/action/comment
   scale remain unchanged; narrow/mobile screens remain fluid. This 500-pixel
   correction supersedes both intermediate width decisions above.
9. In the continuation review Pete directed the existing post-local horizontal
   `Replies & updates` Motion shelf to remain visible on primary Feed posts and
   approved a slightly different card surface so it does not blend into the
   white post. Motion cards use a restrained cool blue-gray surface
   (`#F3F6FA`), a quiet blue-gray border (`#D8E1EE`), and a slightly bluer
   hover/focus surface (`#EDF3FF`). Cobalt remains reserved for actions,
   links, focus, selection, and occasional semantic emphasis. Pete also
   approved very pale warm/cool tints for the supporting desktop rails and
   caught-up state to reduce the page's otherwise continuous white field;
   primary post cards remain white.
10. Pete's direct review of the reconciled Mac page supersedes item 8's
    500-pixel density and item 9's flat-white primary surface. The desktop
    primary Feed maximum is 650 CSS pixels, exactly thirty percent wider than
    the rejected 500-pixel render, with 180-pixel supporting rails and 16-pixel
    rail gaps. Comment and Respond use borderless 36-by-34-pixel visible action
    areas with 20-pixel icons; their idle state has no surrounding circle or
    pill, while hover and focus retain a quiet blue treatment. The 40-pixel
    `Write a comment…` row sits immediately below those actions, before the
    Motion shelf, and keeps 30-pixel Voice and Send controls. Desktop Motion
    cards are 145 by 136 pixels with 12 pixels between cards; narrow cards are
    96 by 132 pixels. The page background, near-white primary post, Motion
    cards, preview notice, and supporting rails use restrained tonal gradients,
    borders, and layered shadows for separation without turning cobalt into a
    decorative fill. This owner correction changes no navigation, behavior,
    data boundary, full-conversation state, or Voice runtime.
11. Pete's next direct review increases the controlling center stage by about
    fifteen percent, from 650 to 748 CSS pixels, and increases each supporting
    rail by thirty percent, from 180 to 234 CSS pixels. The grid maximum is
    1,248px with the existing 16px gaps. A Facebook-familiar composer bar now
    replaces the floating `New post` button at the top of the center stage;
    its prompt and compact post-type controls open the existing private-draft
    composer and do not publish directly. Both rails align to the top edge of
    that bar. In Motion cards, `Author update` is removed as redundant while
    the relative timestamp remains. Card author/body type is 0.82rem with
    bounded two-line ellipsis, compact attachment ribbons, and no text spill
    outside the equal-height card. The intentionally clipped next card remains
    the horizontal-scroll cue. This correction changes no publication,
    authorization, identity, attachment, conversation, or Voice contract.
12. Pete's medium-width review requires `Community activity` to remain on one
    line. The compact tool row uses 46px controls, 0.84rem non-wrapping labels,
    and 0.69rem single-line supporting copy with ellipsis when space is tight;
    the existing activity panel is unchanged. Pete also requires the top
    composer bar to retain the site's Voice-first language. Its question
    shortcut is replaced by the same compact microphone treatment used beside
    the primary post comment field. In this primary-page checkpoint both
    microphones share the same truthful unavailable boundary: activating the
    top microphone gives an unavailable/type-now message and starts no
    permission, recording, upload, or transcription state. At narrow widths
    the media shortcut yields its place to the microphone so Voice remains
    visible.

The exact implementation and evidence are recorded in
`PS-COMMUNITY-PUBLIC-PILOT-001/PRIMARY_FEED_REVIEW_CHECKPOINT_2026-08-01.md`
and its Mac continuation checkpoint.
