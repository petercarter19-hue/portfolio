# PS-CAPTURE-MEDIA-001 - Capture Media Manager Planning

## Assignment

- Owner decision: Pete, 2026-07-19
- Designated session manager: Claude Co-Work
- Current status: Manager/planning active
- Implementation writer: Unassigned
- Manager branch: `work/YYYY-MM-DD-capture-media-manager`
- Entry baseline: current fetched `origin/main`
- Current evidence: no authoritative pushed Capture Media implementation branch
  was observed at activation

## Outcome

Produce the implementation-ready package architecture for private photo, video,
and document sources entering the existing Capture -> proposal/review -> Moment
pipeline. Select one first vertical slice and assign one self-managed writer
branch. Do not bundle all media into an unreviewable release.

PS-VOICE-001 is a released backend with an active visual correction. Voice is
not reimplemented, migrated, or absorbed by this package. The manager may reuse
its owner isolation, private Blob, managed identity, provenance, retention,
export/delete, retry, and explicit-save lessons where the source type requires
them.

## Manager deliverables

Claude Co-Work must return:

1. current-state inventory of Capture, Moment, Placement, private media,
   infrastructure, data rights, and relevant production evidence;
2. explicit photo, video, and document vertical-slice boundaries;
3. recommendation for the first slice with owner value and dependency reason;
4. requirements for source limits/types, upload/capture, private storage,
   preview, extraction/transcoding where applicable, editable proposal,
   provenance, confirmation, retention, export, and deletion;
5. identity/authorization-before-storage-or-retrieval and two-owner denial;
6. lifecycle, idempotency, failure/retry/cancel/recovery, observability, cost,
   provider, and content-safety boundaries;
7. mobile, keyboard, screen-reader, 200% reflow, reduced-motion, long-content,
   unavailable-provider, and text-fallback design states;
8. schema/migration and infrastructure impact, including rollout and guarded
   rollback without touching production during planning;
9. focused, security, data-rights, full-suite, infrastructure, visual, pipeline,
   and live-verification evidence plan; and
10. one implementation writer, clean branch name, writable files, shared zones,
    stop conditions, and exact entry/exit gates.

## Planning-only truth boundary

- No photo, video, or document Capture is implemented, deployed, or live by
  this manager package.
- Do not start Journal, Feed, Story publication, connection/audience, placement
  UI, authenticated Interview Studio, or global navigation/theme work.
- Do not imply upload, transcription, extraction, matching, AI proposal,
  sharing, or publication behavior the backend does not enforce.
- Do not read or expose private member media or credentials during discovery.
- Do not provision infrastructure, apply SQL, or add production dependencies
  until the selected implementation package explains the reason and impact.

## Manager workflow

Follow `START_HERE.md` and `docs/AI_WORKFLOW.md`. If Claude Co-Work already has
local or cloud planning, it must fetch the current Azure authority, reconcile
without overwriting unrelated work, push a clean manager branch, and return its
exact full SHA. The manager may rely on future writers' coherent
self-certification, but Pete and the designated manager retain product/visual
acceptance.

Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`. Only an
approved manager package may activate the first implementation slice.
