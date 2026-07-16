# PS-FEAT-002 — Retired colorful Community board

Status: Retired by product-owner direction, 2026-07-16.

The corkboard-style Community surface, its duplicate page, fixture store,
client renderer, and API were removed. The decision replaces it with one
canonical Community page at `/the-slate` containing only:

- `Feed` for member updates.
- `News Feed` as a same-page mode, intentionally empty until a trusted news
  source, licensing, attribution, moderation, freshness, and failure contract
  are approved.

Compatibility policy:

- `/the-slate/people-interests` redirects once to `/the-slate`.
- Former People API endpoints are no longer registered.
- The old colorful implementation must not be restored as a second post store
  or a public fixture-backed Community surface.

This retirement also closes a security issue found during the July 16 audit:
the old fixture service could return records marked private to an anonymous
reader. Removing the API prevents that exposure while canonical server-side
audience authorization is designed.
