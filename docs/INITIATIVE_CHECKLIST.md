# PeerSlate initiative / pull-request checklist (PS-RULES-001)

Answer every line in the initiative's `10-handoff.md` (or the PR
description for small changes). "N/A" is a valid answer when explained.

1. **Canonical object affected** — which canonical record(s) does this
   touch (Journal entry, Project, Goal, Role, Achievement, Promotion,
   Resume version, Interview session, Feed projection, Note…)? Does it
   create a second source of truth? (It must not.)
2. **Owner and audience** — who owns each record read/written, and which
   viewer modes (owner, connection, signed-in member, logged-out) can see
   it? How is that enforced server-side?
3. **Private/public behavior** — is everything new private by default?
   What is the explicit publication step?
4. **AI vs deterministic responsibility** — what does a model decide vs
   application code? (Auth, visibility, publication, deletion, scores,
   durations, retention are never model-controlled.)
5. **Source/provenance behavior** — are source relationships kept
   internally even where the UI uses simpler language?
6. **Accessibility** — keyboard, focus, screen reader, reduced motion,
   200% zoom, touch targets, long content, missing media.
7. **Tests** — unit/integration for the accepted scope; guardrail suite
   (`tests/test_site_rules.py`) still green.
8. **Export/delete behavior** — can the member inspect, correct, export,
   archive, and delete affected records?
9. **Status truthfulness** — nothing mocked, disabled, or unimplemented
   is presented as working; previews are labeled.
10. **Language rules** — no user-facing "Evidence/evidence-backed/proof"
    labels, no job surfaces, no filler polls/quotes/challenges, no
    engagement-pressure mechanics.
