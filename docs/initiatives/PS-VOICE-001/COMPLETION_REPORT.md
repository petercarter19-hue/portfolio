# PeerSlate Completion & Handoff Report

## A. Status

- Package: PS-VOICE-001 - Private Voice Capture
- Status: Complete for technical handoff; user-facing visual status is In Review
- Branch and commit: `work/2026-07-18-voice-001`; this report is part of the final branch commit, whose exact full SHA is supplied in the handoff
- Authoritative base: `origin/main` at `80cff8b5dc06db5a8df74b66ae166be5ccb8793c`; Voice activation `5488819ad13d3f411319d7e184fde3779d62b8d2` is an ancestor
- PR / pipeline / environment: no PR opened and no pipeline requested; real-resource proof used a disposable isolated Azure resource group, now deleted
- Production state: not deployed; no production Azure resource or production SQL change was made; the production Capture experience remains the released text-only slice
- Visual authority and status: homepage Voice walkthrough in `templates/partials/homepage/_voice_hero.html`; implementation comparison is complete and awaits ChatGPT Work/Pete review
- Pete / ChatGPT Work visual acceptance: pending; this report does not claim acceptance

## B. What changed technically

### Application and protected UI

- Added a protected Voice path to `/app/capture` with explicit **Speak** and **Type** modes. Speak is the JavaScript opening path; the server-rendered Type form remains the no-script and failure fallback.
- Added owner-scoped routes for upload/transcription, draft review, retry, explicit confirmation, playback/download, and draft deletion. Existing Capture archive/restore, correction, export, and delete routes now preserve the Voice source contract.
- Added the browser state machine for permission request, recording, three-minute stop, cancel, 20 MB guard, offline/unsupported/denied failures, upload/transcription processing, double-submit prevention, and screen-reader status announcements.
- Matched the selected homepage Voice interaction model with the Deep Navy listening stage, marigold waveform, prompt, timer, and concise controls, while preserving honest protected-product copy.

### Service and privacy architecture

- Added `VoiceCaptureService` orchestration with explicit upload, transcription, review, confirmation, playback, export, and retryable distributed-deletion transitions.
- Added a private Blob adapter that accepts only opaque server-generated names, emits no Blob metadata or URLs, disallows overwrite, and uses `DefaultAzureCredential` only.
- Added an Azure Speech fast-transcription adapter for `en-US`, using the Microsoft Entra token scope and normalized safe error codes. It never logs or returns provider response bodies.
- Enforced accepted MIME/container signatures, finite positive duration, a maximum of 180 seconds, a maximum of 20 MiB, and an 8,000 UTF-16-code-unit transcript boundary on the server independently of browser checks.
- Preserved the immutable provider transcript separately from the member-approved Capture body. A member edit never overwrites provider provenance.
- Extended Capture export to schema version 2 for Voice, distinguishing provider transcript, approved/current text, and an owner-authorized audio export path without any public media locator.

### Data and concurrency

- Added `dbo.voice_media_sources`, `dbo.voice_transcription_attempts`, and `dbo.voice_capture_links` with tenant ownership, explicit states, row-version concurrency, filtered uniqueness, immutable successful provider results, and body-free deletion tombstones.
- Added owner-resolving procedures for every source, attempt, media, confirmation, and deletion operation. Confirmation is idempotent and creates at most one private `capture_type = voice` Capture per source.
- Extended the protected Capture list/get/delete/export contracts without changing the canonical Capture-to-Moment boundary or creating downstream records.
- Added guarded forward, verify, rollback, and reapply support. Rollback refuses when Voice data, later migrations, dependent objects, or protected-procedure drift would make it unsafe.

### Infrastructure automation

- Added an idempotent PowerShell `plan` / `apply` / `verify` script for one private GPv2 Storage account/container, the existing App Service managed identity, `Storage Blob Data Contributor` at container scope, and `Cognitive Services Speech User` at the existing AI Services account scope.
- The script disables public Blob access and shared-key access, writes only nonsecret endpoint/name/limit/locale settings, and stops if the selected AI Services account cannot prove Speech support with managed identity.
- No production mode was run. No queue, worker, VNet, private endpoint, Key Vault secret, second AI account, transcoder, or native media dependency was introduced.

## C. What this means in plain English

The first Voice Capture slice is implemented on this branch. A signed-in member can make a short recording, keep the original audio private, receive an Azure-generated draft transcript, correct it, and explicitly choose to save it as a private Capture. Until that final choice, the transcript is only a private proposal. The original recording stays attached as private source evidence until the member explicitly deletes the Capture.

The application acts as the privacy boundary: it authorizes every audio request and streams the bytes itself. It never gives the browser a public Blob address, reusable SAS link, storage key, or Speech key. If Voice is unsupported or fails, text Capture remains available.

## D. What the website or member can do now

On this branch in a configured isolated or later production environment, an authenticated owner can:

- choose Speak or Type;
- record up to three minutes and 20 MiB in a supported browser;
- review the private original audio and immutable Azure provider transcript;
- correct the proposed text and explicitly save one private Voice Capture;
- correct, archive, restore, export, play/download, and explicitly delete that Capture through the existing lifecycle; and
- safely retry a failed transcription or deletion.

Production members cannot use Voice yet because this branch has not been reviewed, merged, provisioned, migrated, or deployed. Text Capture remains available and unchanged. No Voice action creates a Moment, Placement, Journal entry, résumé/Interview Studio update, share, audience change, or publication.

## E. How this connects to PeerSlate

This implements the Bible v2.4 private Capture entry point without creating a parallel content model. Voice and Type converge on the same canonical private Capture record, and later corrections use the existing PS-CAPTURE-002 revision history. A later, separately approved action may propose or confirm a Moment from an exact Capture version; this package does not do so automatically.

The protected interface uses the approved Deep Navy Gold foundation and treats the homepage Voice walkthrough as the binding production-intent visual minimum. Privacy and member agency remain visible in both the interaction and the enforced backend behavior: AI transcription proposes text, the member reviews it, explicit save creates the private Capture, and publishing remains a separate future action.

## F. Verification and validation

### Automated tests and static checks

- Final Voice/Capture/database/migration focused run: 93 tests passed.
- Governance and Site Rules run: 18 tests passed.
- Complete configured suite: 372 tests passed, 1 skipped. The skip is the existing opt-in real SQL concurrency test, not a Voice failure.
- Python compilation, JavaScript syntax, PowerShell parsing, migration plan selection, `git diff --check`, and static secret/private-content scans passed.
- Focused tests cover owner routing, cross-site rejection, neutral cross-owner outcomes, format/size/duration validation, immutable attempts, retry failures, idempotent confirmation, no-cache media, export shape, deletion retry, state/concurrency contracts, Blob metadata/path constraints, managed-identity configuration, permission timing, unsupported/denied/offline states, screen-reader announcements, mobile layout, focus, and reduced motion.

### Isolated real-resource proof

- SQL: applied the Capture foundation plus PS-CAPTURE-002, PS-MOMENT-001, PS-PLACEMENT-001, and PS-VOICE-001 to disposable Azure SQL; the PS-VOICE-001 verifier passed two-owner denials, stale tokens, immutable provider transcript enforcement, confirmation, lifecycle/export, and outer rollback. Data, definition-drift, and later-migration rollback guards refused as designed. Clean rollback, reapply, and re-verification then passed.
- Blob: with `DefaultAzureCredential`, uploaded, read, and deleted a synthetic file in a disposable private container; Blob metadata was empty, shared-key access and anonymous public access were disabled, and final absence was verified.
- Speech: the existing `peerslate-foundry` AI Services account proved Speech support under Microsoft Entra authentication. One Windows-generated synthetic, non-member audio sample produced a nonempty transcript, provider request ID, and bounded duration without printing the audio or transcript.
- End-to-end isolated application path: exercised review, required confirmation, explicit save, archive, restore, playback/download, versioned export, deletion, and final Blob absence with synthetic data only.
- The disposable resource group `ps-voice-proof-482984` was deleted and `az group exists` returned `false`.

### Visual and accessibility evidence

- Visual authority: homepage Voice walkthrough, specifically its Speak/Type choice, navy listening stage, waveform, prompt, timer, and concise recording controls.
- Desktop opening: `evidence/voice-capture-desktop.png`.
- Mobile/touch review and long-form document flow: `evidence/voice-review-mobile.png`.
- Desktop review: `evidence/voice-review-desktop.png`.
- Viewport-equivalent 200% reflow proxy: `evidence/voice-capture-200-percent-reflow.png` (720 CSS-pixel viewport representing half of a 1440-pixel desktop); no horizontal document overflow was observed.
- Transcription failure/recovery: `evidence/voice-review-failure.png` plus focused retry/deletion tests.
- Real-browser checks observed no horizontal overflow at 1425, 705, and 375 CSS pixels; touch targets were at least 44 pixels; keyboard focus was visible; status/error regions exposed `role=status` or `role=alert`; microphone permission was requested only after Start.
- Reduced motion, unsupported browser, microphone-denied, offline/upload failure, transcription failure, 8,000-character content, and text fallback are covered by focused UI/state tests. The in-app browser could not complete an actual permission-denial prompt or set browser zoom directly, so those two items are not claimed as a real-device/manual acceptance pass.

### Visual parity and intentional deviations

| Visual contract | Result |
|---|---|
| Speak and Type are first-class choices | Matched; Speak opens with JavaScript and Type remains visible and works without JavaScript. |
| Cinematic navy listening object, waveform, prompt, and timer | Matched in the protected Capture frame using the approved design tokens. |
| Clear start/stop/cancel path | Matched and extended with Switch to Type plus truthful status announcements. |
| Demonstration's optimistic downstream cards | Intentionally omitted because PS-VOICE-001 forbids automatic Moments, résumé, Interview Studio, sharing, or publication. |
| Review/correction before persistence | Added as a protected production requirement; the provider transcript is immutable and Save private Capture is explicit. |
| Public marketing composition | Adapted to the existing owner workspace shell rather than copying a public hero into the private application. |

Automated, isolated-resource, and visual-comparison evidence is complete for handoff. Production verification and real-member validation are not complete because production changes were explicitly prohibited. Passing this evidence does not constitute Pete or ChatGPT Work visual acceptance.

## G. Known gaps, risks, and exclusions

- ChatGPT Work must independently review the exact branch SHA, SQL/infrastructure plan, security boundary, and visual parity before any PR or production work.
- Pete and ChatGPT Work visual acceptance is still required before merge. Exact manual 200% browser zoom and an actual microphone-denied prompt should be included in that acceptance pass because the available browser harness could only provide reflow/test evidence for them.
- Production Storage, RBAC, app settings, SQL migration, PR, pipeline, signed-in smoke test, and live deletion proof are intentionally not done.
- The synchronous three-minute Speech request fits the approved first slice, but App Service/provider timeouts remain an operational risk to observe during manager validation. No queue/worker was introduced because that would require a stop and a new package decision.
- Locale expansion, photo/video/document Capture, background processing, downstream Moments/placements, Journal, public projection, sharing/audience controls, résumé, Interview Studio, and publication remain excluded.
- The existing `peerslate-foundry` capability check passed in isolation. If production managed-identity Speech authorization cannot be established with that account, the manager must stop rather than add another AI account or credential.

## H. Clear next step

ChatGPT Work should fetch the exact pushed branch/SHA, rerun the focused/governance/full suites and non-mutating infrastructure `plan`, inspect the completion evidence, and obtain Pete/manager visual acceptance. That review determines merge readiness and unlocks the separately controlled production provision, SQL apply, Azure PR, deployment, and signed-in smoke-test sequence. Interview Studio design work may proceed independently in its assigned lane.

## I. What Pete needs to do or decide

Review the protected Voice Capture visual evidence with ChatGPT Work and either accept it as meeting/exceeding the homepage Voice walkthrough or request specific revisions before merge. No credential or production action is required from Pete at this handoff.
