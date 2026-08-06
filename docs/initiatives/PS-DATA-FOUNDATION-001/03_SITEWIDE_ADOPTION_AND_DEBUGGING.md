# Sitewide AI adoption and debugging plan

## One foundation, separate product authority

This package is intended to support every PeerSlate AI experience without
turning them into one assistant or one undifferentiated database. Each product
retains its own purpose, audience, source authority, prompt, evaluation cases,
presentation, and mutation boundary. The shared foundation provides the
request, source-version, citation, support-state, decoding, limit, trace, and
evaluation contracts those adapters must satisfy.

| Product adapter | Typical audience | Foundation responsibility | Product responsibility |
|---|---|---|---|
| Ask Pete / Ask Member | Public | Public-purpose source scope, structured answers, exact citation links, unknowns, private handoff proposal | Public retrieval authorization, recruiter presentation, source opening, contact workflow |
| Ask Slate | Owner | Owner-purpose request, bounded private source versions, grounded proposal | Private workspace retrieval, member intent, save/publish decisions |
| Workshop | Owner | Proposal/evidence separation, source versions, evaluation and traces | Knowledge-improvement workflow, confirmation, archive/delete governance |
| Opportunity Slate | Owner | Bounded analysis contract, evidence links, uncertainty | Opportunity records, member decisions, qualification presentation |
| Interview Studio | Product-specific | Structured coaching output and evaluation seam | Session contract, coaching UX, retention and member controls |

The currently implemented `Purpose` values cover the Ask Pete reference slice
and a generic private-coaching seam. A later product adapter must add an
explicit purpose and tests; it must not reuse a nearby purpose merely to gain
access to sources approved for a different job.

## Adapter readiness checklist

Before any runtime product adopts this foundation, its separately authorized
slice must establish:

1. the exact audience and purpose;
2. server-derived subject and caller authorization;
3. the authoritative domain source and immutable source-version mapping;
4. retrieval limits and a stricter product budget when warranted;
5. a versioned prompt and strict output contract;
6. deterministic negative-path and curated semantic evaluation cases;
7. useful unavailable, ambiguous, partial, and not-established presentation;
8. what a citation opens and how the original source remains authoritative;
9. a payload-free trace sink, retention policy, and operational owner; and
10. explicit human confirmation for any later save, send, publish, delete, or
    canonical-truth change.

## Debugging layers

### Contract and authorization

Automated tests must exercise wrong audience, wrong subject, wrong purpose,
stale digest, duplicate source version, excessive request/source size,
malformed provider output, unknown fields, invalid answer states, and exact
citation mismatch. These failures must occur before presentation; source-scope
and limit failures occur before a provider call.

### Payload-free operational diagnosis

The trace contract records request identifier, product, purpose, audience,
counts, elapsed time, provider-called status, outcome, answer state, and a
bounded error category. It has no field for questions, prompts, source text,
citations, answer text, uploads, email addresses, or private member content.
Trace identifiers reject control characters to prevent forged diagnostic
lines. Sink failure cannot change the product result or replace its real error.

### Semantic quality

Exact-span validation proves that a citation points to supplied approved text;
it does not prove that the text entails the claim. Each product therefore needs
a curated evaluation set for correctness, relevance, unsupported inference,
prompt injection inside source text, ambiguity, absence handling, and useful
human follow-up before runtime acceptance.

### User-interface and accessibility diagnosis

UI work is excluded from this slice, but its later acceptance must include:

- keyboard-visible focus indication on the input, Ask action, source controls,
  rail/sheet close action, and contextual Ask controls;
- focus restoration, Escape behavior, reading order, and no covered focused
  element;
- source-click scrolling, exact temporary highlight, conversation persistence,
  and correct current-context display;
- alignment, centering, overflow, nested scrolling, zoom, reflow, standard
  laptop widths, mobile sheet behavior, reduced motion, and contrast checks;
- supported, partial, unknown, ambiguous, slow, unavailable, and handoff states;
  and
- proof that the resume remains understandable when AI is unused or
  unavailable.

Visual polish defects such as an incorrect focus ring, off-center controls, or
a source highlight obscured by a sticky element are release defects even when
the API contract is correct. They belong to the later authorized UI slice and
must be captured with reproducible viewport, browser, state, and interaction
evidence.

## Current stop line

This document establishes adoption and debugging requirements only. It does
not authorize or implement another product adapter, runtime route, retrieval
path, database, telemetry service, provider, UI, pipeline, deployment, or
production action.
