# Grounded Ask Pete backend contract and visual handoff

## Release truth

This document describes a backend candidate on
`work/2026-08-06-grounded-ask-pete-backend-v1`. Until Azure PR merge evidence
exists, it is not on `main`. Even after merge, it remains dormant while
`PEERSLATE_ASK_PETE_GROUNDED_ENABLED` is false. It is not deployed, enabled, or
live merely because tests pass or a PR merges.

No template, stylesheet, client script, image, resume layout, color, rail,
card, sheet, or other material visual surface is changed in this slice.
ChatGPT remains the sole creator of materially revised production visual
direction under the Owner Visual Integrity Standard.

## The product interaction this backend supports

The flagship interaction is deliberately small:

1. A recruiter selects **Give me the 60-second recruiter brief**.
2. The assistant returns a 100-140 word professional through-line.
3. At least three consequential claims are backed by exact approved source
   spans.
4. A meaningful boundary is labelled **Not established in approved public
   information**.
5. Exactly two evidence-derived interview questions are proposed.
6. Every citation can open the existing resume at the supporting record.
7. A human handoff is available without pretending that a message was sent or
   that a private reply changes AI knowledge.

The backend also supports three bounded jobs: evidence finding, interview
preparation, and a specific public-profile answer. It does not support job
description matching, fit scores, hiring decisions, private Slate retrieval,
uploads, voice, OCR, saved conversations, messaging persistence, automatic
knowledge updates, or publication.

## Request contract

The existing endpoint remains `POST /api/chat`.

```json
{
  "message": "Show evidence of Pete's MBSE work.",
  "action": "evidence_finder",
  "context_key": "skill:mbse"
}
```

- `message` remains required and bounded to 1,000 characters.
- `action` is an optional quick-action hint, not an authorization value. The
  server maps only `recruiter_brief`, `evidence_finder`, and
  `interview_preparation`; unknown values fall back to server classification.
- `context_key` is optional. It must match one explicit public manifest record,
  such as `skill:mbse` or `career_role:dod`, or the request fails before the
  provider call.
- Context orders the selected source first. It never expands the source set.
- Existing same-origin and rate-limit controls still apply before AI work.

## Response contract

The enabled structured path returns
`schema_version: ask-pete-public-answer.v1` with these stable visual inputs:

- `answer_id`
- `purpose`
- `state`
- `support_label`
- `summary`
- `claims[]`
- `follow_up_questions[]`
- `handoff`
- `sources_used[]`
- `source_summary`
- `context`
- `response`, which mirrors `summary` for legacy rendering compatibility

Each claim contains:

- `claim_id`
- `text`
- `kind`: `evidence`, `interpretation`, or `boundary`
- `state`: `supported`, `partially_supported`, `not_established`, or
  `ambiguous`
- a plain-language `support_label`
- optional `limitation`
- zero or more citations

Each citation contains the exact approved `excerpt`, its server-derived
character `start` and `end`, immutable source keys and title, and this locator:

```json
{
  "section": "skills",
  "anchor": "r2-skill-panel-mbse",
  "record_kind": "skill",
  "record_id": "mbse",
  "highlight_key": "skill:mbse",
  "href": "/petec/resume#r2-skill-panel-mbse"
}
```

`sources_used` is a de-duplicated list in first-citation order. The response
also supplies a ready label such as **Used in this answer: 4 public records**
and whether **Show all on resume** is meaningful.

## Required visual states

The visual authority must cover all of these states before implementation:

1. **Empty / capability preview**: visibly demonstrate one example source
   chip, its open behavior, and the support vocabulary before asking the
   recruiter to trust the system.
2. **Context selected**: show a readable label such as **Skills -> MBSE** and
   that only approved public records are in scope. Let the recruiter edit the
   prefilled question; never submit automatically.
3. **Loading**: keep the resume interactive; describe bounded work without a
   fake countdown.
4. **Supported**: answer first, followed by clearly associated claims and
   inspectable evidence.
5. **Partially supported**: visually separate what is supported from the exact
   limitation. One label must never cover mixed claims ambiguously.
6. **Not established**: state that absence of approved public evidence is not
   a no; show related public paths only when relevant.
7. **Ambiguous**: ask the recruiter to choose or rewrite the intended meaning
   before producing a blended answer.
8. **Unavailable**: keep the public resume, PDF, and current contact options
   usable; do not invent a cause or repeatedly demand refresh.
9. **Source open**: scroll the center to the locator anchor, reveal the exact
   record, apply a restrained temporary highlight, and preserve conversation
   state.
10. **Multiple sources**: **Show all on resume** may highlight every used
    record without turning the resume into a permanent heat map.
11. **Contact handoff**: current release copy must say that nothing is sent
    automatically and on-platform private messaging is not live.
12. **Failure / validation error**: never render malformed or ungrounded model
    output as a normal answer.

## Rail and center coordination

The backend does not choose the final container, but it is ready for the
persistent recruiter-evidence rail Pete prefers:

- `context.context_key` identifies what the recruiter was viewing.
- every citation has a center-page anchor and highlight key;
- source de-duplication supports **Used in this answer** and **Show all on
  resume**;
- the API returns one stable answer identifier for future conversation-state
  work; and
- the existing legacy `response` field allows a staged visual transition.

ChatGPT should compare the persistent rail with a strengthened opening card
and responsive side/bottom sheet. A rail is justified when it preserves
conversation and context across resume scrolling; it is wrong if it narrows
the resume, creates confusing dual scrolling, or makes recruiters remember the
chatbot instead of the candidate.

## Warm resume visual direction awaiting ChatGPT

Pete has accepted a warmer visual exploration and dislikes the current cold
blue treatment. ChatGPT should create and compare warm, accessible schemes,
including restrained green-and-neutral directions, while preserving the
existing resume information structure. No palette has been production-locked
by this backend work.

The visual round must include the idle citation preview, right-rail answer,
source highlight in the center, partial/unknown states, loading, unavailable,
contact handoff, standard laptop width, narrow desktop, mobile bottom sheet,
dark-theme-paused behavior, and high-contrast focus treatment.

## Accessibility and visual-debug acceptance

Implementation may begin only after visual authority, then must verify:

- visible keyboard focus for the input, quick actions, source chips, close
  control, and center evidence targets;
- Escape closes a rail or sheet and restores focus to its invoker;
- source navigation does not hide the focused target under a fixed layer;
- no clipped content, unintended horizontal scrolling, or competing scroll
  traps at 200% zoom;
- logical reading order and status announcements for loading and new answers;
- support is never communicated by color alone;
- reduced-motion behavior for scrolling and temporary highlights;
- text and interactive contrast at WCAG 2.2 AA thresholds;
- center alignment, spacing, hit target, truncation, focus-ring, sticky-boundary,
  and viewport checks at every supported breakpoint; and
- screenshots plus keyboard and automated browser evidence for every required
  state, not only the happy path.

## Backend diagnostic contract

Every grounded request can emit a payload-free trace containing only request
identifier, product, purpose, audience, source counts and character counts,
outcome, answer state, claim and citation counts, provider-called status,
duration, and a bounded error category. Questions, prompts, source bodies,
citation excerpts, generated answer text, email addresses, and private member
content have no trace field.

The tests cover manifest drift, unauthorized purpose, missing records, source
ordering, prompt/source separation, strict JSON, provider failure, citation
span validation, unknown evidence, recruiter-brief quality, contact-handoff
truth, same-origin protection, default-off compatibility, and payload-free
diagnostics.

## Later human-response architecture, not implemented here

The desired future loop remains:

1. Ask [Name] cannot establish an answer from approved public information.
2. The recruiter chooses to send a private question.
3. The member replies privately.
4. Only after replying does the member receive a separate, optional knowledge
   review decision.
5. Private reply, AI-use approval, and public publication remain independent
   permissions.

This slice deliberately stops at the honest contact path. There is no inbox,
notification, reply persistence, knowledge proposal, automatic save, or public
update.

## Next gate

After backend PR integration and clean closeout, provide this contract plus the
current resume capture to ChatGPT for the material visual round. Visual
acceptance authorizes implementation of the chosen presentation; it does not
automatically authorize provider enablement, deployment, or production launch.
