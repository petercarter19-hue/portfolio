# Journal J1 playback decision

Date: 2026-07-22

Package: `PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001`

Decision owner: Pete

Status: Binding package-local amendment for this milestone

## Decision

Pete explicitly decided on 2026-07-22 to **defer Journal voice playback** from
this milestone. This amendment narrowly supersedes, for J1 only, the earlier
Journal requirements that describe a playable Timeline or Detail voice row or
waveform. It does not change the approved static composition, duration label,
waveform appearance, or any later Journal goal.

The J1 implementation must continue to render voice media honestly as disabled
with the visible label `Coming later`. Pete's approval of the static Journal
screens proves their visual composition only; it does not prove, imply, or
authorize working audio playback.

No fake playback, timer simulation, decorative control presented as active, or
client-only Blob URL playback may be added to satisfy the superseded wording.
This milestone adds no playback service, route, media lookup, or source key.

## Required future package

Playback requires a separate owner-only media-read/playback package. Before
implementation, that package must define and verify:

- an authorized mapping from the requesting owner's confirmed Moment to its
  retained voice source;
- a server-mediated read path that does not expose or leak storage Blob URLs;
- fail-closed behavior for revoked, deleted, missing, quarantined, or otherwise
  unavailable retained media;
- deterministic keyboard behavior and accessible control names, status, and
  error announcements;
- audio lifecycle behavior for play, pause, completion, interruption,
  navigation, repeated activation, and concurrent players; and
- privacy, authorization, cache, range-request, content-type, audit, abuse,
  and browser-security evidence appropriate to private owner media.

That future package requires its own architecture, implementation, review,
evidence, feature boundary, and activation gate. This amendment changes no
shared governance file and authorizes no SQL, deployment, flag change, or live
verification.
