# Community authoring runtime architecture

## 1. Decision

Implement one responsive Community page and one stateful composer family over
the existing authenticated Community services. Replace the superseded blue
card/inline-composer presentation with the locked Mine / Ours / Beyond page,
white compact composer, semantic accent icons, centered desktop/tablet dialog,
and ordinary mobile bottom sheet.

This candidate does not expand author eligibility. It keeps the current
owner-authoring pilot and signed-in member read boundary while replacing the
page and composer architecture. It does not reinterpret the current database
token, expose anonymous content, or claim that every pictured audience or tool
is enabled.

## 2. Runtime boundary

```text
GET /the-slate
  -> require signed-in identity
  -> derive current owner-authoring authorization server-side
  -> render CommunityPage
       MineRail | OursFeed | BeyondRail
       ComposerLauncher
       CommunityComposerLayer

/api/v1/community/*
  -> require signed-in identity before body/dependency work
  -> require server-derived author capability for mutations
  -> existing command/feed/media/Voice services
  -> existing signed-in Community data contract
```

The browser never supplies an author identity. This candidate leaves the
current owner-authoring pilot intact: other signed-in members receive the
read-only Community surface. Existing draft namespaces and mutations continue
to use the resolved member key rather than Pete-specific shared logic. A future
member-authoring package must add per-item viewer authorization to the feed
projection and owner controls before it widens author eligibility; this
visual-runtime package does not imply that policy.

## 3. Audience reconciliation

The current stored `public` token is transitional schema debt that the signed-
in Community wall already presents truthfully as **Community — signed-in
PeerSlate members**. This package keeps that exact behavior and does not add a
migration merely to restate it.

The locked audience menu is implemented as a compact non-reflow popover with
four visible rows:

| Visual row | Candidate behavior |
| --- | --- |
| Private | Draft-only explanation; not a publication target |
| Connections | Disabled with `Not available yet`; no relationship inference |
| Community | Enabled; maps to the existing transitional stored token |
| Public | Disabled with `Not available yet`; no anonymous read route |

Only Community enters the publication path, so the existing deliberate
Community confirmation remains the truthful confirmation. Public confirmation
is not enabled because anonymous visibility, attachment access, blocking,
revocation, counts, cache behavior, and direct-link authorization are not
currently implemented. Connections remains disabled for the same reason; the
dormant relationship foundation is not silently promoted into a read policy.

## 4. Composer state machine

```text
closed
  -> empty
  -> drafting <-> audience_open
               <-> voice_listening/review
               <-> attachment_uploading/ready/failed
               <-> ai_unavailable
  -> confirm_community
  -> publishing
  -> posted | publish_failed
```

- Empty content reports `Not saved yet` and disables Post.
- Nonempty content is retained in the existing per-member, signed namespace
  local draft envelope and reports `Saved privately`.
- Closing never publishes or widens visibility. Voice and attachment failure
  preserve text.
- The editor grows with content to a bounded height; it does not create an
  oversized fixed workspace.
- Publication remains idempotent and requires the existing explicit
  confirmation step.
- `Posted · Undo` is not claimed: current deletion is a separate destructive
  contract, not a bounded undo transaction. The candidate uses the existing
  honest posted status and dismiss action.

## 5. Tools

- **Photo and File:** use the existing upload, validation, processing, retry,
  removal, authorized preview/download, and cleanup services.
- **Voice:** uses the existing transient Speech proposal flow and inserts only
  after member review. It is not a public audio attachment.
- **Video:** icon is present but disabled and explicitly named unavailable.
- **AI:** the violet action opens the approved small menu, but actions are
  disabled with an explanatory unavailable state. This package will not fake
  AI or send member-authored Community text to a provider without an approved
  data-flow, spend, prompt, validation, and policy contract. Ordinary writing
  remains fully usable.
- **Spark:** absent. It is explicitly excluded by visual authority.

## 6. Published stream and replies

- Published Photo and File attachments use compact thumbnail/metadata chips
  beneath the post rather than a full-width media takeover.
- Response controls remain low-pressure and their aggregate count is not shown
  as a popularity signal. The authorized private-response contract is
  unchanged.
- `Save privately` uses the existing owner-authorized save endpoint and viewer
  state. It does not change audience or publish a count.
- The feed shows at most three compact, avatar-led reply/update previews. The
  exact contribution total and `View all` continuation open the existing
  authorized conversation surface; additional replies are not invented or
  silently discarded.

## 7. Responsive and accessibility architecture

- Wide layouts retain the three-column page with Ours dominant.
- Rail widths and gaps reduce before content collapses.
- At the content minimum, phone layout exposes Mine / Ours / Beyond as a
  switcher and shows one region at a time; Ours is the default.
- Desktop/tablet use a natural-height modal near the locked compact family.
- Phone uses a bottom sheet with safe-area padding and a reachable Post action;
  content may grow/scroll for keyboard, errors, attachments, or large text.
- Icon-only controls have accessible names and native/discoverable titles.
- Popovers restore focus, Escape closes the active overlay, and modal close
  restores the launcher.
- Focus, forced colors, reduced motion, 200% zoom, 320 CSS-pixel reflow, large
  text, and touch target behavior are verified as explicit candidate gates.

## 8. Token boundary

Community owns scoped semantic tokens only. White and cloud neutrals dominate;
ink/navy carries copy; PeerSlate green is reserved for identity and the primary
Post action; Photo, Video, File, Voice, and AI use blue, coral, amber, teal, and
violet roles. No selector in this package recolors another room.

## 9. Persistence and migration decision

No schema change is required for this candidate. Existing Community posts,
replies, saves, attachments, Voice proposals, idempotency, retention, and
signed-in reads remain on their current contracts. The activation's reserved
migration surfaces remain unused. A future audience-expansion package must use
a new additive migration ID and its own disposable proof before it can enable
Connections or anonymous Public visibility.

## 10. Review boundary

Completion means a clean, tested, browser-compared source candidate with an
exact SHA and honest limitations. It does not mean merged, deployed, enabled,
launched, or live. A different reviewer must inspect that frozen candidate
before any later integration decision.
