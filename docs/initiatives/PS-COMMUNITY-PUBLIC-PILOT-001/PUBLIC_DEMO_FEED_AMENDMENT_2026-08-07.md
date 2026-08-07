# Community public-demo Feed amendment

**Package:** `PS-COMMUNITY-PUBLIC-PILOT-001`

**Delivery path:** Protected — public truth and publication boundaries

**Visual authority:** unchanged Pete-locked Voice-first Feed and conversation boards

## Release gap being corrected

The approved Community post and Replies & updates content existed only in the
non-persistent local preview harness. Production correctly prohibited fixture
rows in the canonical Community schema, but no separate public-demo projection
was carried into the release. With the pilot flag enabled and no owner-published
rows, `/the-slate` therefore rendered an empty Feed that could not demonstrate
the approved experience.

## Smallest safe seam

- Keep Azure SQL as the only canonical Community store. The demo writes no SQL,
  Blob, audit, outbox, response, save, draft, or attachment record.
- When the first real Feed window contains no public posts, return the locked
  Pete-only example through a dedicated read-only demo projection. A real public
  post replaces the fallback automatically; demo and canonical rows are never
  blended.
- Mark every demo post, contribution, and non-downloadable file ribbon as
  illustrative. The page and card identify the state as a public demo based on
  the owner-approved mockups, not live member activity.
- Keep the owner composer, private local draft, explicit Public selection,
  confirmation, Voice transcript review, and separate publish action unchanged.
  Add a visibly labelled hands-on sandbox beside it only while the demo
  projection is active. The sandbox has text, local attachment selection, and
  Voice controls, but deliberately has no Send, Review, or Publish action.
- A signed-out visitor's sandbox text, attachment metadata/preview, Respond
  choice, and comment text exist only in the current browser tab. Signed-out
  Voice exercises permission, recording, duration, stop, re-record, and discard
  locally; its audio is never uploaded or transcribed. A signed-in owner may
  exercise the already-authorized transient Speech transcription and reviewed
  transcript insertion inside the same no-publish sandbox. In both cases the
  recording is discarded and cannot become public content.
- Demo post and Motion-card deep links open the existing conversation surface.
  Demo Feed cards expose Respond and a compact text/Voice comment field as
  local interaction previews, never as mutation commands. Demo content still
  exposes no reply publication, Save, edit, delete, or upload command. Direct
  write attempts continue through the real owner-authorized commands and find
  no canonical demo row.
- Dependency failures remain failures. The demo is used only after a successful
  empty database read; it never masks SQL, identity, media, or provider outages.
- The retired multi-author People & Interests fixtures remain retired. No fake
  member network, broader authorship, audience, ranking, messaging, navigation,
  schema, migration, service dependency, or feature flag is introduced.

## Verification boundary

Focused contracts must prove stable labelled demo projection, zero persistence,
read-only deep links, local-only demo interaction, absence of demo submit
controls, real-row precedence, signed-out readability, and unchanged owner-only
write authorization. Browser review must compare populated desktop and narrow
views with the locked boards and exercise the Motion shelf, full conversation,
no-publish composer, local signed-out Voice boundary, signed-in transcription,
and signed-out mutation denial before release.
