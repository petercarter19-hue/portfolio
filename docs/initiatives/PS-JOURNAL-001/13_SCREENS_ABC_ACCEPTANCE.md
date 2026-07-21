# PS-JOURNAL-001 — Screens A/B/C Acceptance (empty, detail, manage)

**Accepted by:** Peter Carter (owner), 2026-07-21 ("Accepted. Now let's move
forward"), designated manager (Fable) concurring.
**Accepted asset:** `visual-authority/accepted/journal-v1-abc-empty-detail-manage.png`
**Scope:** Empty Journal (first visit), Moment detail (voice), and Manage view
as working visual direction, under the same translation rules as docs 10/11
(placeholder nav chrome/fonts/fixture copy replaced at build; build from docs +
images together). This substantially closes the Round-3 operating-view coverage
of the screen matrix; remaining edge/failure states are validated from the
built product's screenshots at owner acceptance.

## Binding

- **A — Empty Journal:** the gold open-book illustration, "Your story starts
  here.", one dominant gold **Capture a Moment**, "Private to you", and the
  quote block "The pages are yours. The story is yours. The impact is yours."
  **Owner ruling on the signature:** the image's "— Pete" attribution is a
  fixture accident and is **dropped in the build** — the quote renders
  unattributed, as product voice, in every member's Journal. (A deliberate
  founder's-note feature would be its own future product decision.)
- **B — Moment detail:** date numeral; the accepted member text as the hero;
  supporting context line; playable waveform + duration; attached media;
  **visible version history** ("1 version · Created … · View history");
  lifecycle row Edit / Archive / Export / Delete; the truth line "Private to
  you · Only you can see this Moment."; Back to timeline.
- **C — Manage view:** "Manage — view and organize all of your Moments";
  search field; All kinds / All time / Archived filters; dense calm table
  (date+time, kind with icon, moment with inline waveform/thumbnail where
  applicable, duration, Private status, per-row overflow menu); total count
  ("68 Moments"); footer truth line "You own your Moments. Only you can see
  them."

## Truth staging

- The Manage search field wires to the J1.1 server-side search when it lands;
  until then the build labels any interim behavior honestly (e.g., "Filter
  loaded moments") — no fake full-history search.
- All privacy lines remain literal truths of the flag-off/private-only J1.
