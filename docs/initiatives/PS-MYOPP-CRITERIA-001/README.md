# PS-MYOPP-CRITERIA-001 — C3 owner-scoped criteria foundation

This Protected child implements the accepted My Opportunities criteria state
machine without opening a route or running a search. A bounded interpretation
port may propose structured criteria and one clarification; deterministic
service code alone validates and persists the visible draft, rotates its opaque
version token, freezes an immutable applied snapshot, and returns an immutable
terminal receipt. An interpretation is never silently applied.

The complete command set is present: manual `create_draft`, natural-language
`interpret`, atomic `edit_draft`, `answer_clarification`,
`dismiss_clarification`, structured `refine_from_results`,
`keep_current_criteria`, `discard_draft`, and explicit `apply`. Idempotency is
owner-scoped and evaluated before live/terminal token state, so exact retries
return their original result while mismatched keys, terminal drafts, and stale
live tokens fail in the required order without mutation. Provider unavailability
returns the same fully usable manual draft surface.

Every member read and command takes the server-derived `user_key` first.
Cross-owner direct-key access has the same not-found result as an absent key.
Apply allocates an `execution_key` for the later C4 boundary, but C3 creates no
`search_execution`, retrieves nothing, and performs no search.

`PS-MYOPP-002` adds only owner-scoped criteria drafts, immutable draft versions
and applied snapshots, plus TTL-bounded content-free idempotency receipts. Its
forward migration, rollback, verifier, and registry entry are repository
candidate artifacts only. Pete authorized the bounded disposable Azure SQL
proof, and attempt `ps-myopp-c3-gate-20260829-a1` passed the governed forward,
idempotent reapply, verifier, rollback, and forward-after-rollback sequence. The
database was deleted and an exact lookup returned `ResourceNotFound`. Merge
will not apply schema, deploy, enable, contact a provider, or change production.

## Current state

The implementation, P-1 fixture/contract evidence, and disposable P-2 migration
proof are prepared on `work/2026-08-29-myopp-criteria-001`. The required fresh
exact-SHA independent review remains pending. The package is not merged,
deployed, schema-applied, enabled, or live.
