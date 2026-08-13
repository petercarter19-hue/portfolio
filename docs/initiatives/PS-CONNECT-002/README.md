# PS-CONNECT-002 — Profile relationship foundation

Status: active, non-production implementation candidate; disposable SQL gate
passed on `ps-connect-002-gate-202608131840` at `2026-08-13T18:29:53Z`.

This bounded extension preserves `PS-PLAT-004` as the source of truth for
existing directed requests, active/ended member connections, and directional
blocks. It adds a pair-scoped lifecycle state, append-only event evidence,
monotonic relationship and block epochs, idempotent command receipts, and one
actor-scoped relationship snapshot contract for a later Profile audience
integration.

The candidate deliberately does not register procedures in the shared database
service, add a route, alter Profile behavior, apply SQL to production, open a
PR, release, or enable any audience. The governed disposable-database gate
passed with forward apply, no-op reapply, relationship-isolation verification,
an executed reciprocal-pending-request acceptance, malformed-key refusal,
guarded rollback rehearsal, and reapply; its exact executable digest is recorded in
`SQL FIles/Migrations/registry.json`. The disposable database was deleted after
the proof. A later authorized integration
must wire the provider, and a separate production-schema decision remains
required before any apply.

## Contract boundary

- Actor identity is derived only from `identity.PeerSlateIdentity`; service
  callers cannot provide an actor key.
- Commands are pair-scoped and explicitly limited to request, accept, decline,
  cancel, expire, disconnect, block, unblock, and reconnect.
- The initial request or block can establish a pair; each later transition
  carries the exact opaque relationship-version compare-and-swap token.
- Replays are scoped to actor plus idempotency key and return the stored winner
  only when command, target, digest, and expected version agree exactly.
- Snapshot and command reads are actor-scoped, binary exact, and return neutral
  absence for missing, self, invalid, or cross-owner data.
- No Profile route or public projection consumes this provider in this package.
