# PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001

Protected implementation lane. Put the real Interview Studio behind sign-in and
recompose it to the 19 hash-locked warm-material visual states, per the accepted
architecture.

## Authority chain

1. `Interview Studio Claude Architecture Handoff 2026-08-11` (iCloud, 44/44
   files SHA-256 verified) — owner decisions, locked visuals, trust constraints.
2. `Interview Studio Claude Architecture Deliverable 2026-08-11` (iCloud) —
   the accepted architecture, including `OWNER_ACCEPTANCE_2026-08-11.md`
   (Pete's acceptance, Q-A/Q-B/Q-C answers, model routing, and the
   "all the way until it's almost live" boundary).
3. The activation record in `docs/governance/CURRENT_LANES.json`.

## Delivery shape

- One flag, `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED`, default off, gates the
  two HTML routes and all four interview APIs as a unit. Everything merges and
  deploys dark; flag-off anonymous behavior stays byte-comparable.
- **Enablement is excluded from this lane.** Setting the flag true is Pete's
  separate recorded decision after his browser acceptance.
- Routing: Sonnet (max) sole implementation writer; Fable orchestrates and
  reviews slices; fresh Fable (extra-high) independent review of the exact
  candidate SHA before the PR.

## Slice log

| Slice | Scope | Status |
|---|---|---|
| 1 | Access boundary (flag, identity gates, safe return, headers, robots/sitemap, rate keys, same-origin) | — |
| 2 | Storage isolation (member scope, v3 namespace, no legacy adoption, forged-slug hardening) | — |
| 3 | Authenticated shell (left rail, mobile control row, warm tokens, truth copy) | — |
| 4 | Interview Me consequence stack (append-only, immutability, markers, binding) | — |
| 5 | Interview AI / Video / Session Complete / History to the locks | — |
| 6 | Responsive/accessibility/failure finish + 19-visual comparison | — |

## Enabling fixture note

The state-coupled bootstrap replay test (added by the 2026-08-10 three-lane
repair) failed every activation candidate's CI. Owner-approved test-only repair
merged as main `f85df24` before this lane's activation; all assertions were
preserved. Recorded here because it was a prerequisite this lane surfaced and
fixed for every queued activation (including PR 370's failed build 777).

## Rewritten public-contract tests

Maintained in `SLICE_NOTES.md` — every superseded public-layout/copy pin that
the authenticated composition deliberately rewrites, with rationale.
