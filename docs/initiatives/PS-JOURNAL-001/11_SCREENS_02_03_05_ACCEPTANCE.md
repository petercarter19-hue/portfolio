# PS-JOURNAL-001 — Screens 02/03/05 Acceptance (composer + saved state)

**Accepted by:** Peter Carter (owner), 2026-07-21 ("Agreed with your thoughts
and approved"), designated manager (Claude Code / Fable) concurring.
**Accepted asset:** `visual-authority/accepted/journal-v1-02-03-05-composer-and-saved.png`
**Scope:** Screens 02 (composer desktop), 03 (composer mobile), and 05
(moment saved with Use This Moment options) as the working visual direction for
the J1 frontend, under the same translation rules as doc 10 (build from this
document + doc 10 + the accepted images, never from images alone). Round 2–4
state coverage (doc 03 matrix) remains open and required before the frontend
passes its final visual gate.

## Binding from the accepted sheet

- **02 — composer as the facing page of the book.** The composer opens as the
  book's opposite page (desktop) with the Journal still visible: origin
  preserved, no separate route. Type and Speak equal tabs; the truth-line
  "Private to you — only you can see this until you choose to share"; quiet
  Cancel; one dominant gold **Save Moment**; no destination choices while
  composing.
- **03 — mobile bottom sheet.** Purpose-built 390px sheet over the Journal;
  same labels; large touch targets; not a shrunken desktop.
- **05 — saved state.** Order is binding: (1) "Moment saved privately — It is
  now in your Journal." with lock cue (automatic, already done); (2) **Use This
  Moment** — four equal, clearly optional chips: Share to Feed · Add to My
  Story · Use in Work · Add to Résumé; (3) **Who can see it** selector showing
  "Only you" + the line "You will preview what is shared before anything
  posts."; (4) dominant **Done**, quiet Back to page. Nothing pre-selected,
  toggled on, or auto-applied.

## Owner-directed addition (accepted 2026-07-21, ahead of its regenerated image)

**Attachment row on 02/03:** beneath the writing area, in both Type and Speak
modes, a quiet "Add a photo or video" row (camera + film icons). Attachments
are **context for the same single Save Moment** — not new tabs, not a separate
flow (per `PS-JRN-CAP-010`: photo/video/document inputs use the same ownership,
privacy, source, processing, Save Moment, and failure architecture; presence in
design is not runtime enablement). A regenerated 02/03 image with this row
refines the reference when produced; this record already makes the row part of
the accepted direction.

## Runtime staging (truth labels required)

| Capability | J1 runtime | Presentation in J1 |
|---|---|---|
| Type + Speak capture → Save Moment | Live (flag-gated) | Fully working |
| Photo attachment | Not enabled (Photo remains flag-off under PS-CAPTURE-MEDIA-001 gates) | Clearly disabled "Coming later" affordance permitted by this acceptance |
| Video attachment | No backend yet | Clearly disabled "Coming later" |
| Use This Moment chips (Feed/Story/Work/Résumé) | Destinations not wired until J2 | Chips render clearly disabled "Coming later" (permitted per `PS-JRN-USE-015`); Done/Back fully work |
| Who can see it | Audience changes are J3 | Shows "Only you" as the true, locked state; no fake selector behavior |

No disabled element may imply it works; every label stays truthful.
