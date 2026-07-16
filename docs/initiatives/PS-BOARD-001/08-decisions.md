# 08 — Decisions and Deferred Backend Work

## Locked decisions

### D1 — Photo 1 wins visual conflicts

Peter's latest attached Photo 1 is the desktop visual authority. The selected
original image3 is equivalent supporting evidence. Later revised storyboards
define interaction purpose only and must not steer the resting page toward a
flat blue board, generic cards, or a dashboard.

### D2 — Real shell, Photo 1 workspace

Keep the repository's shared PeerSlate header instead of hardcoding the mockup
header. Recreate the whiteboard workspace directly below it with the photo's
proportions and physical materials.

### D3 — Approved information labels override mockup labels

Use Short Term, Projects, Long Term, and Work in the Now/Next/Ideas/Blockers
positions. This preserves Peter's approved organization while retaining Photo
1's composition.

### D4 — Semantic DOM over a painted screenshot

Text, controls, notes, and list content remain semantic and selectable. CSS/SVG
may create the frame and marker lines. This is the only acceptable deviation
from literal screenshot reproduction because it preserves accessibility,
responsiveness, data binding, and interaction.

### D5 — Honest baseline over simulated production

Fixture and browser-local states may demonstrate the complete experience, but
labels must not imply authenticated persistence, recording, AI, upload,
invitation, presence, sharing, or publication.

## Deferred work packages

- Authenticated owner workspace and route policy.
- Public read-only projection with explicit publication and unpublish.
- Canonical Goal/Project/Milestone/Entry/Evidence/Update models.
- Board/section/placement/connector/view-state schema and migrations.
- Owner-scoped CRUD, optimistic concurrency, idempotency, archive/delete, and
  audit events.
- Cross-user share, invitation, permission, revoke, and notification flows.
- Real media upload and private Blob authorization.
- Shared Capture/Speech pipeline, transcription recovery, and retention.
- AI proposal service with deterministic approval transaction and provenance.
- Visibility-aware matching; never auto-connect users.
- Performance qualification for dense boards and connector rendering.
- Telemetry/monitoring with private-content redaction and cost controls.

These require separately approved packages, data/privacy review, migrations and
rollback where applicable, and two-user isolation tests. Visual completion of
PS-BOARD-001 does not close them.
