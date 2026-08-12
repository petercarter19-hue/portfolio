# Mobile, App Runway, Accessibility, and Performance

## Responsive-web and app direction

Profile v1 is responsive web designed with a PWA/native runway. It is not a
WebView wrapper, native rewrite, offline-first product, or installable PWA
claim. Canonical HTTPS routes, opaque object keys, authorization contracts,
and transport-neutral services must remain usable by later iOS/Android clients.

Desktop may lead visual composition, but every implementation slice includes
phone composition and source/reading order. Mobile is not a late reskin.

## Responsive composition

- At 1280/1440, the dominant Profile plane owns the page; any rail remains
  contextual or clearly secondary.
- At 768/1024, supporting regions recompose without squeezing the main object
  into an unreadable center strip.
- At 390 and 320 pixels, navigation and owner tools become labeled sheets;
  the dominant content appears before secondary context.
- At 200% zoom and 320 CSS pixels (equivalent 400% reflow target), no
  two-dimensional horizontal scrolling is required except intrinsically
  spatial media where an accessible alternative exists.
- Device safe areas, browser chrome, orientation change, virtual keyboard, and
  text expansion are accounted for.
- Left/right rails never become a long stack of equal cards on mobile.

The shared base-template touch-tablet viewport override that forces many iPads
to 1280 pixels must be retired through a separately authorized shared-shell
implementation before it can distort Profile.

## Mobile state continuity

- Destination -> selected object -> Back restores query, filter, scroll, and
  selection when authorized.
- Contextual sheet close returns focus to its invoking control.
- Unsaved edits survive ordinary reflow/navigation and are never silently
  discarded.
- Session expiry obscures private content and preserves only a safe GET return
  path. POST is never replayed.
- Media/Voice recording reserves permission denied, interrupted, backgrounded,
  cancelled, unsupported, upload retry, and processing states.
- Temporary local recordings and upload parts are cleaned after completion,
  cancellation, logout, or bounded expiry.

## WCAG 2.2 AA acceptance

Required evidence includes:

- semantic landmarks, headings, lists, navigation, forms, buttons, dialogs,
  and real audio/video controls;
- complete keyboard paths, logical focus order, visible focus, focus trap only
  in a true modal, and reliable focus return;
- screen-reader names, descriptions, current/expanded/selected state, form
  errors, status/live-region announcements, and no color-only meaning;
- text contrast, non-text contrast, forced-colors support, reduced motion, and
  no motion/autoplay dependency;
- 44-by-44 CSS-pixel touch targets or documented spacing exception;
- resize text, text spacing, 320-pixel reflow, long names/titles/transcripts,
  bidi/RTL-safe layout, and no clipped controls;
- alt text/caption workflow, prerecorded audio transcript, video captions or
  equivalent, and nonvisual access to album counts/order;
- accessible reorder alternatives, confirmation/destructive actions, errors,
  conflict resolution, loading, empty, unavailable, and retry states; and
- Windows High Contrast, browser zoom, iOS VoiceOver/Safari, Android
  TalkBack/Chrome, desktop screen-reader, and keyboard-only checks.

Target is WCAG 2.2 AA; public claims wait for evidence and remediation contact.

## Performance budgets

At representative production-like data and a mid-tier mobile device/network:

| Measure | Target |
|---|---|
| LCP | <= 2.5 seconds at 75th percentile |
| INP | <= 200 milliseconds at 75th percentile |
| CLS | <= 0.10 at 75th percentile |
| Initial HTML TTFB | <= 800 milliseconds at 75th percentile |
| Profile-only CSS | <= 45 KiB gzip |
| Profile-only initial JS | <= 80 KiB gzip |
| Mobile LCP image | <= 200 KiB optimized derivative |
| Desktop LCP image | <= 350 KiB optimized derivative |

No giant shared payload or all-destination preload. Use dimensions/aspect ratio,
responsive sources, lazy-loading below the fold, poster frames, font-display
discipline, and progressive continuation without layout shift.

## Pagination and scale

- Posts: 10 initial, cursor continuation.
- Media: 20-24 authorized objects or an equivalent justified album slice.
- Voice: 20-25 compact rows; create an audio element for the selected item,
  not every row.
- Projects: editorial feature plus compact continuation.
- Home: finite manifest, never paginated chronology.

Cursors bind profile, audience/publication revision, filter/sort, and last
stable key. A revision change invalidates the cursor honestly; it never mixes
audiences or old/new revisions.

## App-facing service constraints

New mutable commands use versioned JSON contracts, stable opaque IDs,
idempotency keys, expected versions, and typed error envelopes. Media upload is
resumable only when its integrity and cleanup contract exists. Native identity
later needs a protected OIDC/token adapter while preserving issuer+subject as
the canonical identity; browser Easy Auth cookies/headers are not assumed in
the domain service.

Safely deferred: service worker/install manifest, offline database/sync,
push notifications, native framework, Keychain/Keystore code, store listing,
haptics, and exhaustive device lab. Deferral does not permit page-local storage
to become canonical app truth.
