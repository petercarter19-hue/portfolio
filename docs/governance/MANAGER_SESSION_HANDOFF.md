# PeerSlate Manager/Writer Handoff

Use this only when ownership changes.
Use this only when another task will continue an active branch. A writer
continuing its own package needs no handoff.

## Required transfer record

- Package, status, delivery path, outcome, scope, exclusions, and one next action
- Exact from/to task references, assigned manager/writer/reviewer roles, and
  explicit relinquishment when it is a voluntary transfer
- Receiving platform plus the stable account/organization, project and
  repository identifiers needed to prove access; avoid personal identity when
  durable non-personal identifiers suffice
- Configured model/effort and how the effective setting was verified; state
  unavailable evidence honestly
- Authoritative base, branch, exact pushed checkpoint SHA, changed files,
  tests, review evidence, open findings, and separate PR/pipeline/deployment/live
  states
- Receiver access proof and explicit acceptance before the receiver writes

Never transfer passwords, MFA, tokens, cookies, browser state, private session
files, or session-only authority. Chat history, a created task, or a zero exit
code is not receiver acceptance.

A complete authorized cross-platform transfer lets the accepted receiver manage
the bounded package through architecture within scope, implementation,
verification, review coordination, corrections, Azure PR/merge, evidence and
closeout. It does not require the originating Codex manager to remain active.
Independent review and owner/production gates still apply.

For a voluntary writer transfer, push the checkpoint and use the one-claim
`transfer` transition in `START_HERE.md`. For recovery without relinquishment,
use its fail-closed `owner-reassignment` protocol. Merge the control PR before
the receiver writes; stop on missing acceptance, access, source, custody, or
collision proof.
