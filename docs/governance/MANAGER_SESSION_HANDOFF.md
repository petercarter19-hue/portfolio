# PeerSlate Manager/Writer Handoff

Use this only when another person or agent will continue an active branch,
take ownership of shared files, or resolve a real cross-lane decision. A
self-managed writer continuing through PR/release needs no handoff. Starting a
new independent package needs only `START_HERE.md`, `CURRENT_BASELINE.yaml`, and
that package.

## Required transfer record

- Package and one-sentence outcome:
- Current delivery path: Routine / Bounded / Protected
- Sender, receiver, and explicit ownership relinquishment:
- Branch, authoritative base SHA, exact pushed handoff SHA:
- Writable and forbidden files/domains:
- Work completed and verification result:
- Open finding or owner decision:
- Release state: local / PR / merged / pipeline / live:
- Single next action:

Add visual authority, migration/rollback, privacy/security, or production
evidence only when it is relevant to the transferred work. Current authority
and active ownership remain in `CURRENT_BASELINE.yaml`; do not copy the entire
site history into this handoff.

Stop if the sender has not pushed the exact SHA, has not relinquished ownership,
or if writable files overlap another active owner. Chat history by itself is
not an ownership transfer.
