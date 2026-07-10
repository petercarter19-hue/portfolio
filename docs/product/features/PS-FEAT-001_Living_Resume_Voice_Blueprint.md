# PS-FEAT-001 — Living Résumé, Career Constellation, and Voice Builder

**Status:** Validated signature concept — design and architecture discovery  
**Priority:** Signature product experience  
**Decision date:** July 9, 2026  
**Product:** PeerSlate  
**Design system:** Direction C — Newsreader + Inter; indigo, azure, cyan, amber, ink, and cloud white  
**Target:** A credible first Slate within 20 minutes, followed by progressive enrichment over time

## 1. Decision Summary

PeerSlate will provide two synchronized résumé experiences generated from the same approved structured career data:

1. **Living Résumé Ledger** — the detailed, recruiter-friendly résumé with an integrated timeline controlling the content displayed inside the résumé.
2. **Career Constellation** — a cinematic visual summary that materializes beneath the Ledger as the visitor scrolls and shows the member's defining education, experience, credential, and future chapters.

Voice and conversational AI will be primary methods for creating and maintaining this information. Members enter or approve information once; the Ledger, Constellation, public Slate, Ask AI grounding, skill evidence, and related experiences update from the same source.

Pete's Slate is User 001 and the reference implementation, not a hardcoded template. The system must work for every member profile.

## 2. Product Promise

> Capture who I am → connect it to proof → turn it into stories → practice explaining it → publish what I choose → get discovered or understood better.

The feature succeeds when a member can move from an existing résumé or spoken career history to a credible, editable, evidence-connected Slate without months of manual design work.

## 3. The Two Synchronized Views

### Living Résumé Ledger

- Appears first.
- Uses an integrated chronological timeline as the résumé's navigation and structural spine.
- Supports Career, Education, Credential, Project, Evidence, and Future views.
- Selecting a chapter updates the detailed résumé content inside the same dominant frame.
- Displays the selected chapter's overview, featured accomplishments, skills, metrics, evidence, and approved AI actions.
- May show all timeline events, using internal scrolling, grouping, or filtering when necessary.
- Clearly distinguishes selected-role impact from career-wide highlights.

### Career Constellation

- Materializes below the Ledger during the public résumé scroll experience.
- Shows approximately four to six defining chapters by default.
- May include education, major career transitions, credentials, and future development.
- Uses a connected path to communicate progression rather than a row of unrelated cards.
- Skills attach to the chapters where they were demonstrated.
- Major approved outcomes appear as a restrained summary, not an exhaustive metric wall.
- Selecting a constellation node may return the visitor to the associated Ledger chapter.
- Additional history remains available through grouping, expansion, or a “View complete timeline” action.

## 4. Multi-Tenant Product Rules

- Every profile-owned record includes `profile_id` or the platform's equivalent tenant-safe ownership key.
- No visual component contains Pete-specific assumptions about role count, dates, employers, education, metrics, or skills.
- Each member's AI may access only that member's authorized data and the evidence approved for the current audience.
- Shared templates control quality. Members may choose supported variations but may not inject arbitrary CSS or modify system templates.
- All layout logic must support missing, short, long, concurrent, overlapping, and incomplete histories.
- Every content item has a stable identifier so both résumé views reference the same record.

## 5. Conceptual Data Model

This is an architecture contract, not final SQL.

### Core entities

- `Profile`
- `Experience`
- `Education`
- `Credential`
- `Project`
- `Achievement`
- `Skill`
- `EvidenceItem`
- `TimelineEvent`
- `AISuggestion`
- `VoiceDraft`

### Required relationships

- An experience, education item, credential, or project may create one or more timeline events.
- An achievement belongs to a source chapter such as an experience, project, education item, or credential.
- A skill connects to achievements and evidence through explicit link records.
- An evidence item connects to its originating member source and may support multiple approved claims.
- A featured résumé bullet is a member-approved achievement presentation, not a free-floating AI statement.
- A constellation node references a real timeline event.
- A voice draft records the transcript, interpreted intent, proposed structured change, source assignment, visibility, and approval status.

### Required metadata

- Owner/profile
- Source entity and source identifier
- Original member wording
- AI-proposed wording, when applicable
- Start and end dates or date precision
- Visibility: draft, private, published, or configured audience
- Evidence/provenance state
- Featured state and display order
- Approval status and approving member
- Created and updated timestamps

## 6. Variable-Content Rendering Rules

| Member profile | Ledger behavior | Constellation behavior |
| --- | --- | --- |
| Student or no full-time history | Education, projects, credentials, internships, and future goals become the timeline | Learning and project path |
| Early career, one to two roles | Show every chapter | Show every meaningful chapter |
| Mid-career, three to six roles | Show complete timeline with selected detail | Show four to six defining chapters |
| Senior career, seven or more roles | Group earlier history, support filters and internal timeline scrolling | Show defining chapters plus an earlier-career group or expansion |
| Career changer | Preserve both paths and highlight the transition | Treat the transition as a defining chapter |
| Freelancer or consultant | Group by period, engagement, or client according to member choice | Show defining engagements or capability eras |
| Concurrent work and education | Render parallel or clearly associated dates without implying a false sequence | Use grouped or parallel chapter treatment |

### Stress-test profiles

Before approval, the system must be tested with:

1. Student with education and projects but no full-time role.
2. Early-career member with two roles.
3. Mid-career member with three to five roles.
4. Career changer with two distinct professional paths.
5. Freelancer with overlapping engagements.
6. Senior member with eight or more roles.

## 7. Featured Accomplishment Selection

The complete career record may contain many accomplishments. An open Ledger chapter normally shows three to five featured accomplishments.

AI may rank candidates using:

- Measurable outcome
- Specificity
- Leadership or responsibility scope
- Technical depth
- Relevance to the selected chapter
- Evidence strength
- Recency
- Relevance to a member-selected target role
- Diversity of demonstrated capability

The member may accept recommendations, select different items, edit wording, or tailor the featured set. AI must preserve the original source and may not invent scope, metrics, tools, or outcomes.

## 8. Skill-to-Evidence Flip

This is a signature PeerSlate interaction.

### Front state

- Compact skill name
- Evidence count or evidence-state indicator
- Optional connection to the selected timeline chapter

### Back state

- The two or three strongest approved proof points
- Originating role, project, education item, or credential
- Evidence state
- “Inspect evidence” action

### Rules

- Skill controls remain visually small enough that the résumé and timeline remain dominant.
- Essential evidence is available without requiring a 3D flip.
- Keyboard, screen-reader, touch, reduced-motion, and high-contrast alternatives are required.
- Skills without approved support are not publicly presented as evidence-backed.
- AI may recommend skill links, but the member approves each relationship.

## 9. AI-Assisted Onboarding

### Target first-run flow

1. Upload a PDF or Word résumé, or paste existing résumé content.
2. Extract employers, titles, dates, education, credentials, accomplishments, metrics, skills, projects, and possible evidence references.
3. Show the proposed timeline for correction before generating public views.
4. Let the member correct dates, merge duplicate roles, resolve overlaps, and add missing chapters.
5. Recommend the strongest accomplishments and skill relationships.
6. Show original wording beside AI-proposed wording.
7. Let the member approve, edit, reject, regenerate, change visibility, or postpone each item.
8. Generate the Ledger and Constellation from approved structured data.
9. Show a public-preview mode before publication.

The initial experience should optimize for a credible first Slate within 20 minutes. Deeper evidence, projects, stories, and refinements may be added progressively.

## 10. Voice-First Conversational Builder

Voice is a primary creation and update channel across the signed-in product.

### Representative commands

- “Add this accomplishment to my L3Harris chapter, connect it to MBSE, and keep it private for now.”
- “Update my Ph.D. start date to January 2027.”
- “Turn what I just said into a stronger résumé bullet, but keep the original.”
- “This evidence belongs to the Air Force role, not my current role.”
- “Which skills still need evidence?”
- “Use my strongest three leadership examples for this chapter.”
- “Show me how the public résumé will look before publishing.”

### Voice change lifecycle

1. **Listening** — obvious microphone state and stop control.
2. **Transcribing** — live, editable transcript.
3. **Interpreting** — convert speech into a structured proposed action.
4. **Clarifying** — ask one focused question when role, date, source, claim, or visibility is ambiguous.
5. **Previewing** — show affected records, before/after wording, source assignment, skill links, and visibility.
6. **Approving** — member confirms, edits, or cancels.
7. **Committing** — save the approved structured change.
8. **Publishing** — separate explicit action when the change affects public content.

### Voice safety and trust rules

- Voice drafts are private by default.
- No voice command automatically publishes content.
- The member can edit the transcript before interpretation and the structured proposal before save.
- AI must not guess the employer, date, metric, evidence source, or visibility when ambiguous.
- The original transcript and original member wording remain traceable to the approved result according to the final retention policy.
- Visitor-facing Ask AI and owner-facing editing AI use separate permissions and prompts.
- Voice must have an equivalent text workflow.
- Listening must stop visibly and predictably.
- Raw audio retention requires explicit disclosure and member choice. Preferred default: retain the approved transcript and structured change, not raw audio, unless the member intentionally saves a recording.

## 11. Privacy, Approval, and Evidence Provenance

- AI-extracted and voice-created claims remain drafts until approved.
- Every published claim identifies its originating member record and evidence relationship.
- Visibility is set per item or through an explicit bulk action with preview.
- Public AI grounding uses only approved data for the public audience.
- Private evidence metadata must not leak through public counts, labels, AI answers, URLs, or error messages.
- Evidence states must distinguish self-reported, document-supported, public-artifact, reference-confirmed, verified credential, and employer-verified where supported by policy.
- “Verified” is used only when the defined verification process is satisfied.

## 12. Responsive and Accessible Behavior

- Desktop: Ledger may use an integrated left timeline rail and main chapter panel; Constellation may use a wide connected path.
- Tablet: Ledger becomes two columns when readable; Constellation simplifies labels and may use a shorter connected path.
- Mobile: both experiences become a vertical timeline with expandable chapters. No horizontal shrinking of the full desktop visualization.
- Reduced motion: Constellation appears through staged fades and normal document flow; skill flips become accessible reveal panels.
- All timeline chapters, skill evidence, voice controls, previews, approvals, and visibility controls are keyboard and screen-reader accessible.
- Long employer names, long titles, unknown dates, approximate dates, missing logos, missing evidence, and translated text must be tested.

## 13. Reusable Component Contract

- `ResumeLedger`
- `ResumeTimelineRail`
- `ResumeChapterPanel`
- `TimelineEventNode`
- `CareerConstellation`
- `SkillEvidenceCard`
- `SkillEvidenceFlip`
- `EvidenceDrawer`
- `VoiceCaptureControl`
- `ListeningIndicator`
- `LiveTranscript`
- `ClarificationPrompt`
- `StructuredChangePreview`
- `SourceAssignmentControl`
- `VisibilityConfirmation`
- `PublicPreview`

All components must use generic structured props or server-rendered view models. Pete-specific values belong in seed/demo data only.

## 14. Recommended Delivery Sequence

1. Lock Foundation C tokens and component preview.
2. Approve the combined Ledger-above/Constellation-below visual architecture.
3. Define the conceptual data contract and variable-content rules.
4. Create Storybook or internal-preview states using the six stress-test profiles.
5. Build résumé ingestion and timeline correction flow.
6. Build the Ledger with manually approved structured demo data.
7. Build compact Skill Evidence Flip and evidence inspection.
8. Build the Career Constellation from the same data.
9. Prototype text-based conversational editing and structured change preview.
10. Add voice capture to the same proposal-and-approval pipeline.
11. Validate privacy, accessibility, mobile behavior, performance, and tenant isolation.
12. Apply the approved system to Pete's Slate as User 001, then test with a small group of diverse profiles.

## 15. Acceptance Criteria

- A new member can produce a credible first Slate within the 20-minute onboarding target using résumé ingestion, conversational help, and approval screens.
- Ledger and Constellation render from the same source records.
- Updating one approved timeline event updates both views without duplicate entry.
- The system renders useful results for all six stress-test profiles.
- No implementation component requires Pete's employers, dates, metrics, education, or role count.
- Every accomplishment and skill-evidence relationship retains source and visibility metadata.
- Career-wide metrics cannot be misrepresented as selected-role achievements.
- Voice changes cannot be committed without a reviewable proposal and cannot be published without explicit approval.
- A member can correct a misassigned role or evidence item by voice or text.
- Skill evidence is accessible without hover or motion.
- Public AI never uses another member's data or private/unapproved content.

## 16. Return Point

Use the stable identifier **PS-FEAT-001** in future planning, prompts, issues, commits, and documentation.

When work resumes, the first instruction should be:

> Open PS-FEAT-001. Confirm Foundation C is locked. Then prototype the Résumé Ledger with the student, early-career, mid-career, career-changer, freelancer, and senior-career fixture profiles before applying it to the live résumé page.

This feature should move from **Validated** to **Ready** only when the visual architecture, data contract, variable-content behavior, voice proposal flow, and privacy rules are approved.
