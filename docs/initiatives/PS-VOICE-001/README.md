# PS-VOICE-001 - Private Voice Capture

## Assignment

- Original backend writer: ChatGPT Codex; released through Azure PR 75 / pipeline 105
- Current corrective frontend writer: Claude Code, self-managed
- Task manager / visual authority / final acceptance: Pete and the package-designated session manager (ChatGPT Work/Codex or Claude Co-Work)
- Corrective branch: `work/2026-07-19-voice-visual-parity-001`
- Entry gate: PS-VOICE-CAPTURE-MANAGER-001 is squash-merged, its Azure pipeline is green, and the branch starts from the resulting current `origin/main`.
- Depends on: PS-AUTH-001, PS-CAPTURE-001/002, PS-MOMENT-001, and the existing App Service managed identity.

## Outcome

Implement the first complete owner-scoped Voice Capture path:

**record short audio -> store original privately -> transcribe -> member reviews or corrects -> explicit Save private Capture -> existing Capture lifecycle**

Voice and text converge at the existing private Capture boundary. The original audio is preserved as private source evidence until the member explicitly deletes the Capture. The transcript is a proposal until the member approves it. No later product object is created automatically.

## Current release and corrective status - 2026-07-19

The backend, production infrastructure, SQL migration, Azure merge/deploy, and
signed-in functional workflow are real. Pete confirmed that Voice works, then
withdrew visual acceptance because the protected desktop/mobile UI does not
match the approved homepage/feed walkthrough. Read and follow
[06_VISUAL_PARITY_CORRECTION.md](06_VISUAL_PARITY_CORRECTION.md) for the current
Claude assignment. The earlier implementation documents remain authoritative
for backend behavior and must not be reopened by the visual correction.

The corrective branch exists at planning checkpoint
`0158daf22d26e7c38be494e2b32e6b51fdaca0fb`. That checkpoint adds design
instructions only; it is not implementation, review, acceptance, deployment,
or closeout evidence. Claude must synchronize the branch with current
`origin/main` after this governance package lands.

## Owner-visible first slice

1. A signed-in member can choose Voice on `/app/capture` and see a clear microphone/privacy explanation before recording.
2. The browser records up to 3 minutes and enforces a 20 MB upload maximum. The server independently enforces duration when verifiable, byte size, accepted MIME/container formats, and authenticated ownership.
3. The interface clearly shows recording, uploading, transcribing, needs review, failed, and ready-to-save states. It preserves the member's work across recoverable failures.
4. The transcript is editable. Nothing is saved to `dbo.captures` until the member selects **Save private Capture**.
5. Saving creates one `capture_type = voice` Capture through an owner-resolving database contract, links it to the immutable original audio source and original provider transcript, and keeps visibility private.
6. Text Capture stays available before, during, and after voice failures.
7. A voice Capture can be corrected, archived/restored, exported, and explicitly deleted. Archive retains its private source. Delete removes the private blob and transcript content and leaves only the minimum body-free audit/lifecycle tombstone.
8. An authenticated owner may play or download their own original audio through a server-authorized response. The application never exposes a public container, public blob URL, reusable SAS URL, storage credential, or provider secret.

## First-slice decisions

- Language: `en-US` only, visibly labeled. Language expansion is later.
- Raw-audio retention: retain privately with the Capture to preserve original input; remove on explicit Capture deletion.
- Recording limit: 3 minutes and 20 MB. Both client and server limits are required.
- Transcription: Azure Speech/AI Services, server-side, using Microsoft Entra managed identity. No browser provider call.
- Failure behavior: speech failure never blocks or damages text Capture. Failed voice drafts remain private and may be retried or deleted.
- Automatic behavior: none. No automatic Moment proposal, confirmation, placement, publication, Journal entry, resume update, sharing, or public projection.

## Acceptance criteria

1. All voice draft, source, transcript, and final Capture reads/writes resolve the signed-in user on the server and fail closed for another owner.
2. Original audio is stored in a non-public Blob container under an opaque server-generated blob name. Member names, email addresses, public profile slugs, transcript text, and Capture text do not appear in paths, metadata, logs, or audit payloads.
3. App Service uses its managed identity with least-privilege Blob and Speech roles. Shared storage keys and Speech keys are disabled or unused by the application. Only nonsecret endpoints, account names, container names, limits, and locale are app settings.
4. Upload and transcription operations use explicit states: `uploading`, `queued`, `processing`, `needs_review`, `confirmed`, `failed`, `deletion_pending`, and `deleted`. Retry and stale-row behavior are deterministic and version protected.
5. The raw provider transcript is preserved privately as provenance. Member edits do not overwrite it. The approved transcript becomes the immutable original body of one voice Capture; later Capture corrections continue to use PS-CAPTURE-002 revisions.
6. Save is explicit, idempotent, owner-scoped, and creates at most one Capture for one voice source. Replayed, concurrent, stale, oversized, unsupported, empty, cross-owner, and already-deleted requests fail safely.
7. Audio playback/download is owner-authorized on every request, uses safe content headers, prevents cache leakage, and returns no storage locator or credential.
8. Export extends the existing versioned Capture export with source-media metadata and an owner-authorized audio export path without embedding a public URL. It distinguishes the provider transcript from the member-approved Capture body.
9. Delete is an explicit, retryable distributed workflow. Database state records deletion pending before Blob deletion; successful finalization removes audio and transcript content. Failed Blob deletion never reports success and remains safely retryable without exposing data.
10. Archive/restore retains the private source and never changes visibility. Existing text Capture, Moment, Placement, public resume, and public Interview Studio tests remain green.
11. Versioned SQL apply, verify, guarded rollback, and reapply are proven on isolated real SQL Server. Rollback refuses after real voice data, later migrations, or protected-procedure drift would cause data loss or contract reversal.
12. Desktop, touch mobile, keyboard, visible focus, 200% zoom, reduced motion, denied microphone, unsupported browser, offline/upload failure, transcription failure, long transcript, and screen-reader status behavior are proved.

## Writable files

- `owner_routes.py` - Voice Capture endpoints and voice-aware lifecycle orchestration only
- `templates/owner_capture.html` - protected Capture UI only
- `static/css/owner-app.css` - Capture-scoped styles only
- `static/js/owner-capture-voice.js` - new protected Voice Capture client
- `services/database_service.py` - Voice stored-procedure allowlist only
- `services/voice_capture_service.py` - new validation/orchestration module
- `services/media_storage_service.py` - new private Blob adapter
- `services/speech_transcription_service.py` - new Azure Speech adapter
- `requirements.txt` - reviewed Azure identity/storage and HTTP dependencies only
- `SQL FIles/Migrations/proposed/PS-VOICE-001_voice_capture.sql`
- `SQL FIles/Migrations/proposed/PS-VOICE-001_voice_capture_rollback.sql`
- `SQL FIles/Verification/PS-VOICE-001_owner_isolation_verify.sql`
- `scripts/apply_sql_migrations.py` - Voice migration registration/verification only
- `scripts/provision_voice_capture_azure.ps1` - new idempotent plan/apply/verify infrastructure script; never prints credentials
- focused Voice/Capture/database/migration tests and this initiative directory

If implementation requires another shared file, stop and ask the designated session manager to reserve it before editing.

## Read-only and forbidden domains

- Do not edit public resume or Interview Studio templates, CSS, JavaScript, tests, routes, datasets, or visual packages.
- Do not change global navigation, theme tokens, external identity architecture, public routes, or unrelated deployment behavior.
- Do not add Moment, Placement, Journal, Story, Work, Project, resume, Feed, sharing, audience, or publication behavior.
- Do not feed transcript text to a generative model, polish it automatically, or claim speaker analytics, sentiment, confidence, emotion, or accuracy that the provider does not enforce.
- Do not place private payloads in application logs, audit metadata, exception messages, analytics, blob metadata, request IDs, file names, or infrastructure outputs.
- Do not provision production Azure resources, apply production SQL, open a PR, merge, deploy, or start the next package. Return the tested branch to the designated session manager.

## Required reading

Follow `START_HERE.md`, then read the current baseline/state/initiatives, Document Control, Bible/Roadmap/Sync Standard, PS-CAPTURE-001/002, PS-MOMENT-001, this README, [architecture](01_ARCHITECTURE.md), [security/privacy](02_SECURITY_PRIVACY.md), [infrastructure](03_INFRASTRUCTURE.md), [test/release plan](04_TEST_RELEASE_PLAN.md), and [implementation sequence](05_IMPLEMENTATION_PLAN.md).

For the current correction, also read `06_VISUAL_PARITY_CORRECTION.md`. Close
with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`, a `Pass`,
`Conditional`, or `Fail` self-certification, and the exact branch plus full
commit SHA. After Pete/designated-session-manager acceptance, the same writer may complete
the Azure PR, pipeline, production verification, and package closeout.
