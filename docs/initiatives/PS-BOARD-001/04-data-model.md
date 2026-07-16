# 04 — Data and Trust Contract

## Experience-baseline contract

PS-BOARD-001 may use fixtures and browser-local state to verify interaction and
visual behavior. The UI must label those limitations accurately. It must not
claim server save, file upload, speech transcription, AI execution, invitation,
real-time collaboration, multi-user privacy, or publication unless a tested
backend performs that action.

New captures and proposal fixtures default to private. “Share,” “invite,” and
“publish” are distinct concepts; a proposed person relationship is not an
invitation.

## Planned canonical contract

| Concern | Required rule |
| --- | --- |
| Identity | Resolve the authenticated user server-side; never accept a browser-supplied owner ID as authority. |
| Ownership | Every board, section, placement, drawing, connector, transcript, proposal, and media reference is owner-scoped. |
| Canonical content | Goal, Project, Milestone, Entry/Reflection, Evidence, and Update content is stored once. |
| Placement | Board-only data references a canonical record and stores section, order/position, rotation, and view metadata. |
| Visibility | Private is default; selected-person, connections, and public are explicit transitions validated by the server. |
| Publication | A public projection is deliberate and revocable; unpublish removes projection without deleting the private source. |
| AI | AI returns candidate proposals only. Deterministic application code validates and commits approved changes. |
| Voice | Transcript → structured proposal → source/visibility review → explicit approval → save; publishing is separate. |
| Concurrency | Mutations require version/conflict handling and idempotency so retries do not duplicate records. |
| Audit | Sensitive state transitions record actor, action, object, audience, time, and provenance without leaking private content. |
| Retention | Preserve source wording/provenance; discard raw audio after success by default unless the member explicitly keeps it. |

## Minimum future entities

- Board and ordered Section.
- Placement referencing one canonical record.
- Connector/Relationship with a plain-language label.
- Per-user BoardViewState.
- Private CaptureSource/Transcript.
- AI Proposal and ProposalItem with source, destination, visibility, and status.
- Share/Invitation/Publication records only after their permission services exist.

No production schema or migration belongs in this visual baseline. It requires a
separate approved `PS-BOARD-DATA-001` package with forward/rollback design and
two-user isolation tests.
