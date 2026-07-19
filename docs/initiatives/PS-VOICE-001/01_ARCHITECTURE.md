# PS-VOICE-001 Architecture Contract

## Canonical flow

```text
authenticated owner
  -> browser microphone recording
  -> owner-scoped media draft row
  -> private Blob source
  -> owner-scoped transcription job
  -> immutable provider transcript
  -> editable review in the browser
  -> explicit Save private Capture
  -> dbo.captures(capture_type = voice, body = approved transcript)
  -> stable source-to-Capture link
```

The existing Capture is the convergence point. Voice does not create a second Capture model and does not change the Capture-to-Moment contract.

## Persistence model

The migration may choose precise table and procedure names, but must preserve these roles:

- **Media source:** owner ID, opaque public-safe key, opaque Blob name, media type, verified content type/container, byte length, SHA-256 digest, locale, lifecycle state, timestamps, actors, and row version. It contains no transcript or member identity in storage paths/metadata.
- **Transcription job/result:** owner-bound media source, attempt number, explicit state, provider identifier, nonsecret provider request correlation, timestamps, safe error code, immutable raw transcript, and row version. Raw transcript text is never audit metadata.
- **Capture link:** exactly one media source to at most one voice Capture. Confirmation pins the exact successful transcript result and is idempotent.

The database remains the authority for ownership and lifecycle. Blob Storage is the authority for original audio bytes. Neither can infer authorization from a browser-supplied owner identifier.

## Service boundaries

- `media_storage_service` accepts only opaque server-generated blob names and validated bytes. It never accepts an arbitrary container, account, URL, path, or credential from a request.
- `speech_transcription_service` accepts validated audio from the server and returns a normalized transcript result. It obtains an Entra token server-side.
- `voice_capture_service` coordinates state transitions and converts technical failures into safe product states. It contains no SQL strings and no Flask response logic.
- `owner_routes` authenticates, validates same-origin mutations, maps HTTP requests to services, and renders owner-safe responses.

## State transitions

```text
new -> uploading -> queued -> processing -> needs_review -> confirmed
                    |            |              |
                    +----------> failed <-------+

any non-deleted state -> deletion_pending -> deleted
```

- Only the server advances state.
- Retry creates a new transcription attempt; it does not overwrite a prior raw result.
- `confirmed` requires an explicit member action and one linked voice Capture.
- A stale row-version token or invalid transition returns a neutral conflict without protected data.
- Cleanup may retry `deletion_pending`; it never silently marks missing work successful without proving the Blob is absent.

## Recording and review contract

- Feature-detect `MediaRecorder` and MIME support before showing Record.
- Explain microphone use before requesting permission.
- Keep Stop, Cancel, Retry, Use text instead, and Delete draft available in the appropriate states.
- The transcription result is labeled as a draft for review.
- Save is disabled until the reviewed transcript contains meaningful text and the media source is in `needs_review`.
- Long transcripts use readable document flow; the UI does not shrink them into a fixed panel.

## Deletion ordering

Deletion spans SQL and Blob Storage and therefore cannot be one database transaction:

1. An owner-resolving procedure validates the Capture/source version and records `deletion_pending`, returning only the opaque blob locator needed by the trusted server.
2. The server deletes the Blob or proves it is already absent.
3. A final owner-resolving procedure deletes transcript and approved Capture content according to PS-CAPTURE-002, clears storage locators/digests, and leaves only a body-free tombstone.
4. Any failure remains `deletion_pending`, is reported honestly, and is retryable.

The implementation must not call the existing text-only delete path first and leave an untracked private audio orphan.
