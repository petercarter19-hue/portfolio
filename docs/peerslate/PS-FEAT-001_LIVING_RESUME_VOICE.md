# PS-FEAT-001 - Living Resume Ledger, Career Constellation, and Voice Builder

**Status:** Validated signature concept
**Priority:** Signature product experience
**Foundation:** Direction C - Newsreader plus Inter; indigo, azure, cyan, amber, ink, and cloud white

## Decision summary

PeerSlate provides two synchronized resume experiences generated from the same approved structured career data:

1. **Living Resume Ledger:** a detailed, recruiter-friendly resume with an integrated timeline controlling the displayed content.
2. **Career Constellation:** a cinematic summary beneath the Ledger that connects defining education, experience, credential, and future chapters.

Voice and conversational AI help members create and maintain this information, but members review and approve proposed changes before they become approved data. Publication is separate and explicit.

Pete's Slate is User 001 and a reference implementation, not a hardcoded template.

## Product behavior

- The Ledger supports Career, Education, Credential, Project, Evidence, and Future views.
- Selecting a timeline chapter updates the detailed Ledger within the same dominant frame.
- The Constellation references real timeline events and returns to the related Ledger chapter when selected.
- Skills attach to the chapters where they were demonstrated.
- Approved outcomes remain restrained summaries linked to supporting evidence.
- Missing, short, long, concurrent, overlapping, and incomplete histories must render safely.

## Shared data contract

Ledger and Constellation render from the same structured multi-tenant data. Core entities include Profile, Experience, Education, Credential, Project, Achievement, Skill, EvidenceItem, TimelineEvent, AISuggestion, and VoiceDraft.

Every skill, claim, metric, and evidence item retains:

- profile ownership;
- source entity and source identifier;
- original and AI-proposed wording when applicable;
- visibility and approval state;
- evidence/provenance state; and
- stable identity and timestamps.

No reusable component may hardcode Pete-specific employers, dates, metrics, skills, education, role counts, or evidence. A member's AI accesses only that member's authorized data and evidence approved for the current audience. Never use another member's data or private/unapproved evidence.

## Voice and AI workflow

1. Capture speech and produce an editable transcript.
2. Interpret the transcript into a structured change preview with source assignment, proposed fields, visibility, and affected records.
3. Save the proposal as a draft only.
4. Let the member review, edit, approve, reject, or defer each change.
5. Make approved data available to the appropriate private views.
6. Require a separate, explicit publication action before it appears on a public or recruiter Slate.

AI-extracted content follows the same workflow. It cannot silently overwrite an approved record or publish evidence.

## Mandatory implementation gate

Read this specification before any resume, timeline, evidence-flip, onboarding, or voice-builder work. Verify tenant isolation, ownership, source, visibility, approval status, editable transcript, structured preview, and explicit publication behavior before implementation begins.
