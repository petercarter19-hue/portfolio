# Gaps, dependencies, and prioritized plan (v1.2 reconciliation)

## Gap list (v1.2 requirement → current state)

| # | v1.2 requirement | Current state | Package |
|---|------------------|---------------|---------|
| 1 | Rules/CLAUDE.md/Bible discoverable in repo | Not tracked | PS-RULES-001 |
| 2 | Iris Foundry tokens + room accents | Foundation C blues everywhere | PS-BRAND-NAV-001 |
| 3 | Evidence out of nav + language migration | Evidence tab + ~30 user-facing uses | PS-BRAND-NAV-001 |
| 4 | About PeerSlate out of top nav; Why PeerSlate page | In header nav; recruiter-led About copy | PS-BRAND-NAV-001 |
| 5 | Interview mode control + copy + missing-history ask | No mode control; "Proof/evidence" copy | PS-INTERVIEW-002 |
| 6 | Respond system (Celebrate/Support/I relate/Ask/Offer help) | Encourage (preview) + Applaud/Inspired/Rooting (board) | PS-FEED-002 |
| 7 | Community right rail = one Note card only; no polls/quotes/challenges | Poll, quote, challenge, fake join-count present | PS-FEED-002 (removal now), Note card with PS-JOURNAL-002 |
| 8 | No Ask Pete AI inside Community | Global launcher shows on Community | PS-FEED-002 |
| 9 | Journal center + Note + check-in | Does not exist | **PS-JOURNAL-002 — HELD by owner** |
| 10 | Qualification Alignment | No upload/auth/private storage | PS-QUALIFY-001 — **auth-gated** |
| 11 | Resume Creator + PDF/DOCX | Static PDF only | PS-RESUME-001 — **auth-gated** |
| 12 | Constellation projects/achievements/promotions | Roles only | PS-CONSTELLATION-001 — after auth phase |
| 13 | Auth/owner isolation/private storage | Easy Auth scaffolding only | v1.1 prerequisite program (next phase per owner) |

## Dependency map
- 10, 11 depend on 13 (auth + private storage + ownership) and partially 9.
- 9 (Journal) depends on 13 for real member-owned records — owner has
  deliberately deferred it together with the Note card.
- 6, 7, 8 are safe now (public fixtures; removal + relabeling only).
- 2, 3, 4, 5 are safe now (visual/copy/UI on existing surfaces).

## Prioritized recommendation (this program)
1. **PS-RULES-001** — land governance artifacts + automated guardrails.
2. **PS-BRAND-NAV-001** — Iris Foundry, nav cleanup, Why PeerSlate,
   site-wide language migration (largest visible change).
3. **PS-INTERVIEW-002 (public-safe slice)** — mode control wired to the
   existing model-answer/coach endpoints, v1.2 feedback structure and
   copy; session persistence and history capture marked deferred until
   auth (per rule 83, nothing mocked as real).
4. **PS-FEED-002 (public-safe slice)** — banned rail modules removed
   (rail recenters; Note card arrives with the held Journal package),
   Respond system replaces Encourage/Applaud vocabulary in both the
   corkboard and the Feed preview, Ask Pete AI suppressed on Community
   routes, "Original transcript" → "Transcript".
5. Report and stop before PS-JOURNAL-002 / PS-QUALIFY-001 /
   PS-RESUME-001 / PS-CONSTELLATION-001 (owner hold + auth phase).

## Conflicts to flag (rule 85)
- v1.2 CLAUDE.md's logged-out marketing nav recommends "How It Works /
  Community / Interview Studio / Explore a Slate / Create My Slate".
  Only some of these destinations exist today ("How It Works" exists as
  an anchor on /peerslate; "Create My Slate" has no flow before auth).
  Decision: keep the existing real destinations (Pete's Slate, Community,
  Interview Studio) and move About to the footer now; adopt the full
  marketing nav when the auth phase makes Create My Slate real. Recorded
  in PS-BRAND-NAV-001/08-decisions.md.
- Rule 70 public-member nav includes "Journal" — held with the Journal
  package; the public sub-header keeps Story/Board/Work/Resume for now.
