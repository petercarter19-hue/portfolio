# PS-SETTINGS-ACCOUNT-EXPORT-MEDIA-TRANSCRIPT-READER-001 review evidence

Runtime-inert review-tail record for the first decision-spawned reader
package of the accepted 2026-08-30 seven-export-decisions ruling
(Paper 1: voice/photo facts and the member's own transcripts). Paired
receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-MEDIA-TRANSCRIPT-READER-001.json`.

- **Boundary:** Protected, independent review, repository authority
  through merge, production authority withheld. Five read-only readers
  over `voice_media_sources`, `voice_transcription_attempts`,
  `voice_capture_links`, `capture_media_sources`,
  `capture_media_links`; `provider_transcript` INCLUDED as member
  content; every blob locator/name, content digest, etag,
  vendor/provider identifier, actor id, and machinery column excluded
  with category tags; deleted-state (payload-nulled) rows filtered and
  fixture-proven absent. Nothing wired beyond `DOMAINS` (the closed
  integration package's worker reads it dynamically); no live claim.
- **Delivered candidate:** `1618374bd4d6ad18da82d819542e797d8c01d729`
  on `work/2026-08-30-settings-account-export-media-transcript-reader-001`,
  base `5e091544` (this package's own activation merge). Custody: six
  writer commits (agent:claude-code/settings-mt-reader-writer, Sonnet,
  final `84bdf5e3`), one governed append-only extend-surfaces
  transition (PR 757 → both cross-package test files, writer task
  context), the manager's extension-carry merge `806f18df` and tripwire
  repoint `122be84f`
  (`test_voice_photo_is_included_by_the_media_transcript_package`),
  the manager's gate-lockstep commit `d615dc43`, the review-directed
  prose-correction commit `1618374b`, and the review-round records
  commit.
- **Gate proof (two runs; the program's first gate CATCH):** run 1 on
  disposable `ps-migration-path-20260830-mt` FAILED at verification —
  the two deleted-state photo fixture rows omitted `scan_result`, whose
  column DEFAULT `N'unknown'` fired where
  `CK_capture_media_sources_original_payload`'s deleted branch demands
  `NULL`; an engine-only defect class no static trace can see, and
  exactly what the disposable-database gate exists to catch.
  Fixture-only fix (explicit `NULL` on both INSERTs); the forward file
  never changed. Run 2 on fresh `ps-migration-path-20260830-mt2`
  passed in full (`verified = 1`, rollback rehearsed) and sealed digest
  `14d21bd2f4e1d88829d75cedb76b3c39ad63d80e104468c159dff3e1222c35a5`
  (`gated_at_utc 2026-08-30T07:49:34Z`) — identical to the writer's
  authoring-time computation. Registry + replaced pin test + CR6 Gate
  state moved in the one lockstep commit.
- **Independent review (fresh Opus, read-only, no-fetch brief with
  supplied release state):** `d615dc43` → CONDITIONAL with ZERO
  executable findings: allowlists audited column-by-column against the
  DDL (complete, exact, included ⊎ excluded = every column); the
  transcript judgment re-derived and confirmed airtight (the CHECK puts
  every non-NULL transcript on a succeeded row, and finalized deletions
  hard-DELETE attempts, so `state IN ('succeeded','failed')` exports
  every transcript that exists); the gate story independently
  reproduced including a five-table sweep proving `scan_result` is the
  only DEFAULT-vs-required-NULL collision in scope; exactly 27 program
  readers sharing exactly one identity-header variant; scope exact;
  THROW ranges collision-free; 10/10 mutation probes as expected.
  Findings were prose-only: F1 a false "member can already correlate a
  source to its Capture via EXPORT-004" claim (the two domains' outputs
  share no field — all three passages now state the identity is
  DEFERRED, recording the correction openly), F2 an over-absolute
  "never the same string" (now "a different fact, even when the
  characters coincide"), F3 a 2-vs-3 allowlist heading. `1618374b` →
  **CONFIRMED, verdict upgraded to PASS at that SHA**: the reviewer
  extracted the migration from both commits and proved the executable
  body byte-identical (same length, same SHA-256, both hunks inside the
  header comment), verified every other surface byte-identical to the
  reviewed candidate, swept for surviving instances of the corrected
  phrases (none), and reproduced the figures.
- **Figures:** nine-file battery `396 passed, 2889 subtests`, exit 0
  (pytest) and `Ran 396 tests ... OK`, exit 0 (unittest), both
  including the sealed-gate recomputation pin.
- **Standing forward notes:** (a) the cross-domain source-to-Capture
  identity is deferred — a future package wanting it must add an
  explicit reviewed cross-domain identity (no existing export field
  suffices); (b) the DEFAULT-vs-NULL fixture class is now a named brief
  item for future writers: an omitted column with a DEFAULT is not
  NULL; (c) grants remain paper-only until C4.
