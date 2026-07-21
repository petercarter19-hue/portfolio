# PS-ASK-SLATE-AI-001 — Signed-In Member Intelligence

**Status:** Architecture committed; discovery/implementation not active

**Owner naming decision:** July 20, 2026

**Runtime writer:** Unassigned

**Dependency:** Trusted identity, one-Journal authorization, source/version
provenance, deletion/retention, and safe AI proposal architecture

**Runtime truth:** No signed-in Ask Slate AI product is claimed live.

## Coherent naming model

- **Ask Slate AI** — signed-in intelligence umbrella across the member's
  permitted private Slate.
- **Ask My Slate** — owner-facing action/CTA within Ask Slate AI, not a second
  assistant.
- **Ask [Name] AI** — reusable viewer-authorized public/profile pattern.
- **Ask Pete AI** — existing public Pete-specific instance using approved
  public Pete sources only.
- **Interview AI, Board AI Help, Moment Lab, Next Chapter, Qualification
  Alignment, résumé/Story assistance** — specialist workflows powered by the
  same governed intelligence, not separate bot identities.
- **Slate Mirror, What PeerSlate Noticed, Replay** — proactive capabilities and
  experiences, not chat personas.

Ashley AI is retired as a transcription error. Owner AI remains an internal
authorization term. AI Coach, AI Profile/Career Assistant, and Interview You
are retired/merged rather than maintained as competing products.

## Product role

Ask Slate helps a signed-in member ask questions of their own permitted history,
prepare, compare, find, reflect, and create reviewable drafts. It should be
available contextually and may also have a global surface, but normal product
tasks shall not be forced through chat.

## Boundary with Ask Pete AI

Ask Pete AI remains public. Its existing typed behavior does not prove private
retrieval, voice, uploads, OCR, or member analysis. Future private document/
job-posting analysis belongs to Ask Slate's Qualification Alignment workflow.
Public Ask Pete and private Ask Slate may eventually share infrastructure, but
they must use separate authorization, source scopes, prompts, logging, and
release evidence.

## Detailed architecture

See `01_ARCHITECTURE.md`. A product branch requires a bounded first scenario,
production-intent visuals, exact source/retention policy, evaluation set, and
one manager/writer assignment.
