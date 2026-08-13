# PS-INTERVIEW-ASK-MY-SLATE-001 - Minimal memory retrieval for Interview practice

**Status:** Planned - not active.
**Authority placement:** Bounded Interview use case of
`PS-ASK-SLATE-AI-001`. `Ask My Slate` is a contextual action within private Ask
Slate, not a new assistant identity.
**Dependencies:** AI Agent Quality Round 2 plus private source, citation,
authorization, retention, and deletion contracts.
**Runtime status:** No retrieval, rail, generation, capture, or save behavior is
authorized.

## Owner outcome

When an interview question makes a member draw a blank, PeerSlate can briefly
jog their memory from their own permitted knowledge without taking over the
answer. The experience must remain intentionally small and quiet.

## Minimal experience contract

- Label: **Ask My Slate**.
- Prompt: `Find a past experience for this question.`
- One primary action: **Jog my memory**.
- Return at most one or two concise, cited possibilities relevant to the
  current standard or custom question.
- Offer **Use as context**, which associates a removable reference with the
  practice session. It does not write into or replace the answer.
- Do not add a persistent chat transcript, long explanation, action wall, or
  automatic model answer.

The retrieval result should identify why the experience may fit while keeping
the member's reviewed answer and coaching dominant. It must clearly distinguish
source truth from AI interpretation.

## Placement

A restrained right rail may be tested on sufficiently wide desktops only after
a new visual lock. On smaller screens use a drawer/sheet or another contextual
reveal. The current Interview authority intentionally has no permanent right
rail, so no writer may add one from this charter alone.

## No-result and capture boundary

If nothing relevant is found, say so. The product may offer **Capture this
experience**, but saving must use the established private Capture/Workshop/
Journal canonical contract, explicit confirmation, provenance, and member
control. Capture is a later bounded slice; no result is silently saved or turned
into resume evidence.

## Acceptance gate

Demonstrate member isolation, server-side authorization before retrieval,
source/version citations, deleted-source behavior, custom-question support,
prompt-injection resistance, no-answer mutation, concise output, responsive
placement, and truthful unavailable/no-result states before release.
