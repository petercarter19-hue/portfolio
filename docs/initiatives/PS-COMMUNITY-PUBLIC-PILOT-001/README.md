# PS-COMMUNITY-PUBLIC-PILOT-001 — Real owner-authored public Community V1

## Assignment

- **Owner and release authority:** Pete
- **Designated manager and sole writer:** current Codex task
- **Delivery path:** Protected — identity, public publication, schema,
  attachments, deletion, and material visual implementation
- **Branch:** `codex/2026-08-01-community-primary-feed-sol-ultra`
- **Authoritative base:** Azure DevOps `origin/main` at
  `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`
- **Runtime flag:** `PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED`, default `false`
- **Route authority:** Feed remains `/the-slate`; The Break remains
  `/the-slate/break`; post and contribution URLs are subordinate deep links
- **Exact visual authority:**
  `PS-COMMUNITY-FEED-VISUAL-001/visual-authority/2026-08-01-pete-voice-first-lock/`
- **Retention decision:** `APPROVED_RETENTION_AND_DELETION_DECISION.md` —
  **approved by Pete 2026-08-03 exactly as proposed, live for this release
  wave; not yet implemented.** Pete committed to readdressing the schedule
  when Community moves behind the sign-in experience. The deletion jobs and
  their evidence must still pass before production collects content.
- **Community Voice status:** **P0 usable-release requirement; exact visual
  authority locked; the primary-comment slice and its propagation to the
  remaining approved composers passed local Protected review.**
- **Status:** Pete approved the real local primary Feed on 2026-08-02 and
  authorized continuation into the remaining package work. Full conversation,
  reply, and protected Community Voice implementation are now the active local
  tranche. The broader pilot remains default-off and is not usable or
  releasable while the Voice and other release gates below remain open.

## PC-to-Mac continuation

Pete accepted the compact primary Feed correction, then froze the PC lane and
transferred sole active-writer ownership back to this Mac task on 2026-08-01.
The exact continuation ZIP, its verified SHA-256, the 17-file overlay matrix,
and final per-file actions are recorded in
`PC_TO_MAC_COLLISION_MATRIX_2026-08-01.md`. The collision audit found no
Mac-newer or unresolved Community file. The PC lane remains frozen.

Pete's 2026-08-02 approval closes the primary-page inspection stop and opens
the package-local secondary-state and protected Voice continuation. It does not
silently approve the proposed retention durations, authorize production data
collection, change Azure infrastructure or configuration, enable the
default-off feature flag, or replace the protected release gates below.

Pete rejected a second expanded Voice activator that had appeared below the
compact comment row. The controlling primary-card rule is explicit: the
compact microphone beside Send is the only visible Voice affordance in the
idle row and no second idle Voice panel appears below it. Pete's subsequent
2026-08-02 instruction to keep moving after approving the revised Feed adopted
`COMMUNITY_VOICE_VERTICAL_SLICE_ARCHITECTURE_AMENDMENT_2026-08-01.md` for the
first protected primary-Feed comment-composer slice. That slice passed focused
validation and independent Protected review at
`85219407b492c1374d9bc95fa20c4277edefaae1`. Pete then approved the rendered
result and instructed this task to keep going, authorizing local propagation to
the original-post and full-conversation contribution composers under
`COMMUNITY_VOICE_PROPAGATION_ARCHITECTURE_AMENDMENT_2026-08-02.md`. The
transient request-only audio boundary controls over the earlier persistence
wording for these Community dictation surfaces. That propagation passed
focused validation, real-browser fixture review, and independent Protected
review through `54a9d1b`; it does not close the migration, retention,
Candidate, release, deployment, or live-provider gates.

Pete also reconfirmed the existing Threadline Signal direction: the primary
post includes one horizontal `Replies & updates` Motion shelf, supported by
the approved catch-up and activity rails on desktop. His later color correction
uses subtle cool blue-gray Motion cards and pale rail tints while leaving the
primary post white and reserving cobalt for interaction and emphasis.

Pete approved the exact revised boards and instructed: “Build and deploy it.”
That authorizes the protected implementation, reviewed migration, Candidate,
Azure squash merge, production deployment, owner-pilot enablement, and live
verification defined here. It does not authorize broader member authoring,
signed-out interaction, direct messaging, AI publishing, or automatic
Journal/Slate creation.

## Member outcome

The production pilot is useful with one author only when:

- the configured site owner signs in and can compose a Community-native post
  by typing or speaking;
- opening the composer creates no server record and the local draft is private;
- `Public` must be selected for each publish command and is never inferred;
- a successful publish persists one canonical Community post in Azure SQL;
- the owner can edit or remove a post, add/edit/remove replies and author
  updates, choose/replace/remove one Respond intention, save/unsave, search,
  and attach supported clean files;
- signed-out visitors can read published-public posts and attachments through
  reauthorizing application routes, but cannot mutate anything; and
- Feed pagination is finite and ends in a truthful caught-up state.

## Exact first-pilot contracts

### Identity and audience

- Authoring and every interaction require trusted server identity plus the
  existing configured site-owner allowlist. Empty or nonmatching allowlists
  fail closed.
- Signed-in non-owners and signed-out visitors are read-only.
- Persisted V1 rows are created only by an explicit publish transaction with
  `audience=public`; there is no durable server draft or alternate audience.
- Published content is `noindex, nofollow` during the narrow owner pilot. This
  keeps the route publicly viewable without representing a broad launch.
- Browser-supplied owner, user, role, audience capability, or moderation values
  are ignored.

### Content and lifecycle

- Community-native creation only; no Slate projection creation.
- Post intents: `post`, `question`, `small_win`.
- Response posture is display-only: `open_feedback`, `questions_welcome`,
  `sharing_only`, `help_welcome`.
- Plain text only; post body maximum 4,000 UTF-16 code units; contribution body
  maximum 2,000.
- Contributions are `comment`, `reply`, or `author_update`; maximum stored
  parent depth is eight and visual indentation is clamped responsively.
- Contribution kind is server-derived and cannot be supplied by the browser.
  A top-level follow-up from the post author becomes `author_update`; a
  top-level contribution from another future eligible member becomes `comment`;
  and a contribution with a validated same-post parent becomes `reply`. The
  server derives the post-author relationship and parent semantics without
  trusting a client claim to broaden author capability.
- Owner edits use an exact integer revision precondition. There is no edit
  window. The current revision is public and prior revisions remain protected
  audit history, not public projections.
- Delete is a soft, immediately public-revoking action. It never claims that
  audit/legal-hold history vanished. Unattached uploads expire after 24 hours;
  attached media becomes inaccessible immediately when its source is removed.
- Every publish/reply command uses an author-scoped idempotency key. Responses
  and saves use deterministic PUT/DELETE commands, never toggles.

### Community Voice — required before a usable release

- Voice is a prominent peer to typing in the original-post composer and every
  comment, reply, and author-update composer. It is not an attachment hidden
  behind Add file. Exact placement, iconography, responsive behavior, and
  interaction states are controlled by the 2026-08-01 Pete lock.
- Reuse the protected `PS-VOICE-001` capture, private media, and transcription
  architecture rather than creating a second speech truth store. Community
  integration still requires an amended protected contract and its own
  authorization, limits, cleanup, accessibility, and release evidence.
- The minimum safe flow is explicit Start recording, browser permission,
  visible recording waveform and elapsed time, explicit Stop, protected upload
  and transcription, an editable transcript proposal, explicit Use transcript,
  and a separate explicit Publish or Reply command. Voice never starts,
  inserts, attaches, saves, or publishes automatically.
- The typed path remains available throughout. Permission denial,
  unavailable-device, timeout, transcription failure, cancellation, and retry
  states must preserve the user's local draft and return focus safely.
- Dictation audio is private and transient in the minimum Community slice. It
  is not a public attachment and is deleted under the approved Voice cleanup
  contract. Publishing an audio recording as Feed content is a distinct
  requested capability and is not part of the current JPEG/PNG/PDF/XLSX
  attachment allowlist.
- The first Community Voice runtime is limited to the protected, transient
  primary-Feed comment-composer vertical slice. The feature flag must remain
  off, and the pilot must not be described as usable, until that slice passes
  protected review and the same approved behavior is later propagated and
  verified in the remaining required composers.

### Respond, saves, search, and finite Feed

- Respond vocabulary is exactly `celebrate`, `support`, `i_relate`, `ask`, and
  `offer_help`; one current value per member/post; no public aggregate count.
- Saves are private references and cannot preserve inaccessible content.
- Search covers currently published-public post and contribution plain text,
  authorizes before returning content, is bounded to 20 results, and never logs
  raw query text.
- The owner pilot uses one newest-first Feed with an opaque keyset cursor and a
  fixed request watermark. Page size is 12, maximum 120 cards per explicit
  session, no engagement ranking, no automatic refill, and a real end state.
- `Following`, `Recent`, separate `Questions`, Pulse aggregation, and broad
  catch-up activity are deferred. The locked Community activity sheet may show
  only truthful owner-pilot availability/empty states.

### Attachments

- Accepted V1 types: JPEG, PNG, PDF, and macro-free XLSX; maximum 10 MiB each; maximum four
  ready attachments per post or contribution.
- Bytes enter through a route-specific bounded multipart request into an
  opaque private Blob object. Declared type, signatures, exact byte length, and
  SHA-256 are checked before upload.
- Azure Defender Blob tags control scan progression. Only a clean scan can
  create `ready`. Images are decoded with bounded dimensions, orientation is
  normalized, metadata is stripped, and a safe derivative is generated. PDFs
  and XLSX workbooks are download-only and never embedded as active content.
  XLSX packages receive bounded OOXML structure validation before upload and
  again after the clean scan; encrypted entries, macros, ActiveX/OLE or embedded
  packages, external relationships, unsafe paths, duplicate entries, and ZIP
  bombs are rejected. The service does not parse cells, evaluate formulas,
  render previews, or index workbook content. Original workbook contents and
  document properties remain in the public download, so the owner must review
  them before publishing.
- Storage exposes no public Blob URL or SAS. Every preview/download rechecks
  current SQL publication, lifecycle, moderation, owner, and media state.
- Failed, rejected, abandoned, removed, and expired objects remain unavailable;
  cleanup uses SQL lease tokens plus idempotent Blob deletion and can be
  retried. A bounded cleanup batch runs at most hourly on the production App
  Service Always On request cadence, with targeted best-effort cleanup after
  owner removal and terminal scan outcomes.

### Moderation, public-content readiness, and AI

- The owner can edit or remove only their own pilot content through the
  ordinary author lifecycle; no hold/restore control or general moderator
  console is introduced. Reserved moderation states are server-only and do
  not imply a released pilot control.
- Public readers receive a visible report/takedown/contact link on the page.
  Broader registration and third-party authoring remain blocked pending a
  separate legal, moderation, support, and Gate Launch decision.
- The pilot page links a dated plain-language pilot policy covering ownership,
  confidentiality, prohibited uploads, public visibility, reporting, removal,
  age position, retention limits, and no-AI-processing truth.
- No Community content is sent to a generative model, used for AI ordering, or
  automatically saved, published, messaged, or converted into Slate truth.

## Data and procedure ownership

The migration owns only Community-prefixed tables, procedures, indexes,
constraints, triggers, and its migration ledger row. It uses existing
`dbo.app_users` only for server-derived identity foreign keys.

Required data classes:

- canonical posts plus protected post revisions;
- canonical contributions plus protected revisions;
- one purposeful response and private save per member/post;
- uploader-owned attachment reservations and post/contribution bindings;
- content-free audit and outbox rows; and
- no fixture rows, copied Journal/Moment facts, raw search logs, or presentation
  fields.

The forward migration is idempotent and transactional. The rollback refuses
to remove a populated Community domain. Production rollback disables the flag
first and preserves member content; destructive schema rollback is not the
normal release response.

## Reserved files

- `app.py`
- `community_routes.py`, `community_api.py`
- `services/community_*.py`
- `services/database_service.py`
- `templates/community_*.html` and
  `templates/partials/community_v1/**`
- `static/css/community-v1.css`, `static/js/community-v1.js`
- `SQL FIles/Migrations/proposed/PS-COMMUNITY-PUBLIC-PILOT-001*`
- `SQL FIles/Verification/PS-COMMUNITY-PUBLIC-PILOT-001*`
- `scripts/apply_sql_migrations.py`
- focused Community runtime tests/evidence and this package
- `docs/governance/CURRENT_BASELINE.yaml`

The package does not edit Home/profile, Journal, Story, Projects, Studio,
Interview, homepage, Break content, global navigation, deployment credentials,
or unrelated active-package files. The legacy mutable
`people_interests_api.py` is unregistered while this flag is enabled and
returns neutral 404 for its retired route family; its fixture files remain
rollback history and never mix with real data.

## Verification and release gates

Before merge:

1. migration/rollback static validation and an outer-transaction two-owner SQL
   verifier pass without printing member content;
2. API/service tests prove owner-only writes, anonymous public reads,
   non-owner denial, private draft/no-default-public behavior, cross-origin
   denial, neutral missing objects, idempotency, revisions, deletion,
   deterministic response/save, search minimization, finite cursors, and media
   revocation;
3. the complete protected Community Voice flow passes contract, authorization,
   privacy, cleanup, keyboard, screen-reader, permission/error, reduced-motion,
   and browser evidence in the original-post and every contribution composer;
4. exact locked-state desktop/mobile browser comparison, keyboard/focus,
   200% reflow, large text, dark theme, reduced motion, long content, empty,
   error, permission, upload-processing, and caught-up evidence pass;
5. Break, redirects, homepage, shared shell, fixture API retirement, full suite,
   dependency, secret, and compile checks pass;
6. complete-diff self-review and Protected independent review pass; and
7. exact source SHA passes package-specific Candidate Build/Deploy/Smoke/Stop;
   and
8. Pete approves the exact Community retention schedule required by
   `PS-LEGAL-020` and `PS-LEGAL-022`, and its deletion job is implemented and
   verified before production collects Community content.

Release sequence:

1. apply and verify the backward-compatible migration through the approved
   secure connection while the flag remains off;
2. squash-merge through Azure and verify the exact production pipeline with
   the flag still off;
3. enable `PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=true` for `peerslate-pete`
   only after the Community Voice gate and every other gate above passes;
4. verify signed-out public-read/no-write behavior, signed-in Pete authoring,
   public attachment delivery, edit/remove revocation, and exact live build;
5. leave broader member authoring and public interaction disabled; and
6. record a Conditional—not broad-launch—Gate Launch result unless qualified
   legal/security review has independently passed.

## Completion record

Use `OWNER_TECHNICAL_COMPLETION_REPORT.md` for exact SHAs, changed paths,
tests, Candidate, migration, pipeline, production configuration, live evidence,
limits, rollback, and the final answer to whether Pete can actually use it.
