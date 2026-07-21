# PS-JOURNAL-001 — J1 Frontend Implementation Brief

**Manager/architect:** Claude Code (Fable). **Implementer:** Sonnet 5.
**Reviewer:** Opus. **Base:** current `origin/main`.
**Route authority:** doc 07 — **APPROVED**: `/app/journal` (owner Journal),
`/app/journal/moments/<moment_key>` (detail), API `/api/journal/moments`.
**Visual authority:** doc 10 + doc 11 + the two accepted PNGs in
`visual-authority/accepted/`. Build from the docs + images together; the
images' nav chrome/fonts/fixture copy are placeholders per doc 10 §2.

## Mission

Build the flag-off owner Journal experience on top of the merged J1 backend:
the `/app/journal` page (bound-book Journal per accepted JOURNAL-01), the
in-context composer (accepted 02/03), and the saved state (accepted 05).
`PEERSLATE_JOURNAL_ENABLED` stays **false**; when false, `/app/journal` and its
sub-routes return the same neutral 404 the API uses. Nothing user-visible
changes in production until the flag flips.

## Read before writing code (in this order)

1. This brief; docs 10 and 11 (translation contracts); the two accepted PNGs.
2. docs 01 (requirements), 02 (experience/state machine), 06 (in-the-moment
   sharing), 07 (approved routes).
3. `docs/governance/OWNER_CONTEXT_RAIL_STANDARD.md` — the Journal ships the
   reference rail; build its markup/styles as a reusable partial
   (`templates/partials/context_rail.html` + `static/css/context-rail.css`)
   consumed by the Journal page.
4. `docs/PEERSLATE_SITE_RULES.md` rules 18–24, 69–71; AGENTS.md Journal section
   and design foundation (Deep Navy Gold tokens, Newsreader/Inter).
5. Existing owner page conventions: `owner_routes.py` (auth + flash patterns),
   `templates/owner_capture.html`, `static/css/owner-app.css`, and the released
   voice capture flow (`static/js/owner-capture-voice.js`, voice endpoints).
6. `services/journal_service.py` + `peerslate_api.py` journal endpoints (the
   engine you are consuming — do not modify them except where this brief says).
7. `docs/initiatives/PS-HOME-FRONTEND-001/README.md` — check its reserved
   files. Select **non-overlapping files only**; if a needed file is reserved
   by that lane, stop and report instead of editing it.

## Deliverables

### 1. Route + page (flag-gated, owner-only)
- `GET /app/journal` in the owner blueprint: identity required (same pattern as
  existing `/app/*` routes); flag off → neutral 404; flag on → the Journal.
- `GET /app/journal/moments/<moment_key>`: Moment detail (accepted version,
  source type, created/occurred dates, version number, lifecycle state,
  privacy). Owner-only; neutral 404 for others/flag-off.
- New files: `templates/journal.html`, `templates/journal_moment.html`,
  `templates/partials/context_rail.html`, `static/css/journal.css`,
  `static/css/context-rail.css`, `static/js/journal.js`. Do not edit existing
  templates except—if unavoidable—minimal additive includes; report any such
  edit.

### 2. The Journal page (accepted JOURNAL-01, translated)
- Bound-book character, light + dark (respect the site's existing theme
  toggle; use central tokens, not per-file palette copies).
- Context rail: chapters Timeline · Voice · Photos · Videos · Milestones ·
  Reflections with subtitles; **local views/filters only** (rail never leaves
  the room); gold `aria-current` active state; scroll-following where
  applicable; mobile = slim chip-row under the title per the standard.
  Chapters whose kinds have no Moments show truthful, warm empty states.
- This-season hero: member display name; season line only when member data
  provides it (no AI-imposed copy); quiet totals from real counts (moments,
  voice notes, milestones) — never streak/points framing.
- Timeline: large date numerals; mixed-media rows — voice rows with playable
  audio (reuse the released owner voice audio endpoint) + duration; text rows
  in the serif treatment with **no decorative imagery**; milestone rows with
  the gold star marker. "Load more moments" drives the API's keyset cursor.
- Manage chapter/view: denser list with archived filter (uses
  `include_archived`), client-side kind filtering of loaded items. **Server
  search is a disclosed deferral** (the list procedure has no search parameter;
  a J1.1 backend addition will add it — do not fake a search box that only
  filters loaded rows unless it truthfully labels itself "Filter loaded
  moments").
- Empty first-visit state: warm, honest, leads to Capture a Moment
  (illustration is a banked direction — a typographic/simple treatment is
  acceptable for J1; do not block on new artwork).

### 3. The composer (accepted 02/03 + doc 11)
- Opens in-context over/beside the Journal (book facing-page character on
  desktop; bottom sheet on mobile). No new route; no navigation away; focus
  restored on close (PS-JRN-CAP-003/014).
- Type and Speak equal tabs. Type: spacious field, the approved placeholder,
  the truth-line, Cancel, one **Save Moment**.
- Speak: reuse the **released voice lifecycle** (record → upload → transcribe →
  member reviews/edits transcript). The member's accepted transcript text is
  submitted through the same single Save Moment action. Keep technical states
  underneath the flow (PS-JRN-CAP-006); if exact voice-source pinning to
  `usp_SaveMomentForOwner` is not achievable without modifying existing
  procedures, route the accepted text through the one-step save and record the
  voice-source linkage gap as a disclosed J1.1 item — do NOT modify existing
  voice/Moment procedures.
- Attachment row ("Add a photo or video") per doc 11: rendered, clearly
  disabled, truthful "Coming later" — no fake pickers.
- Save: POST `/api/journal/moments` with a client-generated idempotency key
  (one per composer session; reused on retry). Implement the doc 02 state
  machine states: open/empty, composing, recording, transcribing, review
  voice, saving (duplicate submit blocked, status announced), saved, save
  failed (truthful error + recoverable draft text kept locally), conflict.
  Enrichment states are N/A in J1 (no enrichment pipeline) — do not fabricate.
- Kind/precision/date fields: minimal and calm — kind defaults sensibly
  ("update"), occurred date defaults to today with precision "exact",
  member-editable; validation errors surface the API's member-safe messages.

### 4. The saved state (accepted 05 + doc 11)
- Exact order: saved-privately confirmation → **Use This Moment** four chips
  (all clearly disabled "Coming later" in J1) → **Who can see it** showing the
  true locked "Only you" + preview reassurance line → **Done** (closes, returns
  to origin, focus restored) and quiet Back to page. "View in Journal" scrolls/
  focuses the new Moment, which must appear in the timeline immediately.

### 5. Accessibility & responsive (hard gate)
Keyboard-complete (composer open/compose/save/close, waveform play, rail);
visible focus; screen-reader announcements for state changes; semantic
chronological order; 390px and 200% zoom reflow; reduced-motion variant;
long-content behavior. The rail renders as a labeled scoped `nav`.

### 6. Tests (all existing green + new)
`tests/test_journal_frontend.py` (or extend `test_owner_journal.py`):
- flag off → `/app/journal` + detail = neutral 404 (unauth and non-owner
  identical); flag on + identity → 200 with the page shell.
- Rendered page contains: rail chapters, timeline container, composer trigger
  labeled "Capture a Moment", truth-line, Save Moment label, disabled
  Use-This-Moment chips with "Coming later", "Only you" audience text.
- No fake enabled controls: assert disabled semantics on chips/attachments.
- Detail route: owner sees fields; guessed keys → 404 via the service error
  path.
- Reuse the established mocked-database patterns; do not require a live DB.

## Hard boundaries
- Flag stays false; no baseline/Bible/Roadmap edits; no navigation additions
  outside the approved routes; no edits to existing procedures, the migration
  SQL, `journal_service.py` logic, or the API contract (additive template/
  static/route/test code only); no Owner-Home reserved files; no changes to
  public pages.

## Definition of done + report
- `ANTHROPIC_API_KEY=test <venv python> -m unittest discover -s tests -q` all
  green (existing + new), run at your pushed SHA.
- Screenshots: desktop light + dark, mobile 390px, 200% zoom, composer open,
  saved state, empty state — saved under
  `artifacts/ps-journal-001-j1-frontend/` and listed in your report.
- Push branch `work/2026-07-21-journal-frontend-j1-impl` (or -2). Report:
  branch + full SHA, files added/changed, exact test command + result line,
  screenshot list, every assumption/deferral (voice-source linkage, search,
  any shell compromise), self-certification Pass/Conditional/Fail. STOP — no
  PR. Opus reviews next; Pete's visual acceptance follows.
