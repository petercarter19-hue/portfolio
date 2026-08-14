# PS-DATA-FOUNDATION-001 — PeerSlate AI, Knowledge, Evidence, and Data Foundation

- Status: completed non-production foundation; merged through Azure PR 311 as
  `779ab5f`. This README preserves the delivered slice and grants no current
  writer, provider, route, schema, deployment, or production authority.
- Owner: Pete
- Implementation branch: work/2026-08-06-ai-foundation-ask-pete-slice-1
- Delivery path: Protected
- Reference product: Ask Pete AI

## Current outcome

Build a reusable foundation for every PeerSlate AI experience while keeping
each product room's purpose, authorization, and canonical records separate.
Ask Pete is the first reference consumer because its public recruiter use case
makes grounding, citations, unknowns, and human handoff plainly testable.

This first slice implements provider-neutral requests and answers, exact
approved source-version scope, authorization before a provider call, evidence
versus interpretation, honest support states, deterministic claim-level
citations, strict provider-output decoding, product-level evaluation checks,
versioned prompt contracts, and privacy-safe traces.

It does not wire a live route, change a model/provider, add schema, read a
private record, change the resume page, deploy, or mutate production.

## Architecture rule

PeerSlate does not need one giant chatbot or one giant AI database. Product
adapters own the job. Domain services own canonical truth. The foundation owns:

authorized retrieval -> provider-neutral request -> candidate structured answer
-> deterministic grounding validation -> product presentation

AI proposes and summarizes. People remain authoritative. Canonical truth,
original sources, AI proposals, public projections, and operational traces
remain distinct.

## Parallel delivery boundary

Pete directed normal branch-based parallel development on 2026-08-06. This
lane uses a separate branch/worktree and only the additive surfaces recorded in
CURRENT_LANES.json. Opportunity Slate and Workshop retain their own files.

## Historical checkpoint

The original database/storage definition remains preserved at
work/2026-08-04-data-foundation-gate-001@9952d6427f57dc5a38679f616158497cb945eec4.
Its review-before-build, repository-owned schema, portability, authorization,
backup/restore, and bounded-migration rules remain applicable when a later
slice proposes persistence or infrastructure. This slice proposes neither.

## Exit evidence

- focused contract and grounding tests pass;
- unauthorized, stale, cross-subject, or mismatched sources fail before use;
- claims labelled supported cannot omit validated exact-span citation links;
- partial support and interpretation expose their limitations;
- unavailable behavior remains useful without fabricated claims;
- malformed, excessive, or unrecognized provider output fails closed;
- product expectations can be evaluated without retaining answer payloads;
- bounded inputs and failures produce payload-free diagnostic categories;
- traces contain no question, source, excerpt, answer, or contact payload; and
- the diff stays inside the activated additive surfaces.
