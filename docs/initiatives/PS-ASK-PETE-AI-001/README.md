# PS-ASK-PETE-AI-001 - Ask Pete AI discovery and multimodal expansion

## Package status

- Status: **Planned - not active**
- Roadmap placement: Phase 11, Next Chapter and Qualification Alignment
- Working product name: **Ask Pete AI**
- Designated session manager for docket registration: ChatGPT Work/Codex
  manager session
- Future discovery manager: Unassigned
- Implementation writer: Unassigned
- Branch owner for docket registration: Codex on
  `work/2026-07-19-ask-pete-ai-roadmap`
- Base: `origin/main` at
  `296711d001c7dd0d0bc66001a29c42595a938bdb`
- Migration owner: Not applicable; this package authorizes no schema,
  infrastructure, dependency, route, or runtime change
- Visual authority: Not applicable to this governance-only registration;
  future product visual authority is Not Started
- Release boundary: documentation and governance only

## Owner decision

Pete directed PeerSlate to preserve a future phase for a much deeper Ask Pete
AI experience. The current assistant is useful, but the concept must be explored
beyond a short typed question. The future discussion must include voice,
document upload, and screenshots of job postings, then define the complete role,
experience, trust boundary, architecture, and implementation sequence before a
writer starts.

The phrase **Ask Pete AI** is intentional. This package does not use or define
"PAI." The multi-user platform naming relationship among Ask Pete AI,
Ask [Name] AI, and private Owner AI remains a discovery decision; no live label
is renamed here.

## Honest current production baseline

Today, Ask Pete AI is a logged-out public-profile assistant:

- the browser sends one text message to `POST /api/chat`;
- input is limited to 1,000 characters and there is no attachment control;
- the server selects approved Markdown knowledge files and sends that bounded
  public context to the configured model;
- answers are short, public-profile responses for visitors and recruiters;
- there is no voice input, OCR, document processing, conversation workspace,
  private owner-history retrieval, or saved uploaded source; and
- no uploaded job posting, screenshot, private analysis, or Qualification
  Alignment experience is implemented, deployed, or live.

That current public assistant remains real and reusable. It must not be silently
expanded to private owner data or treated as proof that the future package
already exists.

## Product purpose

Explore Ask Pete AI as one trusted intelligence with specialized, contextual
workflows rather than a generic chatbot. The first candidate vertical slice is
a private, source-grounded role or opportunity conversation in which a signed-
in member may describe a goal by typing or voice and provide a job posting or
other target material by paste, document, or screenshot.

The system should help the member understand what the source says, how it
relates to confirmed Slate history, what is directly supported, what transfers,
what is genuinely unknown or missing, and what truthful next action is worth
considering. It must not become a job board, fit oracle, automatic application
tool, or unreviewed editor of the member's Slate.

## Candidate first-class inputs for discovery

- Type a question or paste text.
- Speak a question, goal, constraint, or context.
- Attach PDF, DOCX, or TXT source material.
- Attach one or more PNG/JPEG screenshots, including multi-image job postings,
  for OCR and ordered review.
- Select explicitly permitted confirmed Slate records for private grounding.

URL ingestion, email forwarding, cloud-drive sources, additional media types,
conversation retention, and reusable saved targets are ideas to evaluate, not
approved first-slice commitments.

## Required trust boundary

1. Public Ask Pete AI and private owner analysis are visibly separate
   permission contexts. A user is never moved into private retrieval silently.
2. Public Ask Pete AI uses only public-approved profile sources.
3. Private files, screenshots, OCR text, voice, prompts, extracted requirements,
   and derived answers are owner-scoped and session-private by default.
4. The member reviews extracted text and source spans before they become the
   basis for a consequential comparison.
5. Uploaded content is treated as untrusted source material, never as system or
   developer instruction. Prompt injection, malicious files, MIME mismatch,
   OCR errors, and source poisoning require explicit controls and tests.
6. The member can inspect, correct, remove, export when applicable, and delete
   supplied sources and derived outputs. Explicit save is separate from upload.
7. AI outputs are proposals. Ask Pete AI may not apply, contact an employer,
   publish, share, change audience, or modify canonical Slate records without a
   separate explicit member action and authorized workflow.

## Relationship to current authority

- Bible v2.5 authorizes private-first multimodal sources, transparent AI, and
  Qualification Alignment without opaque fit scoring.
- Roadmap v2.4 Phase 11 already reserves Next Chapter and Qualification
  Alignment for a member-supplied role, standard, or need. This package expands
  the discovery agenda to include voice and screenshot/OCR input while
  preserving that phase's privacy, correction, deletion, and no-marketplace
  gates.
- `docs/PEERSLATE_SITE_RULES.md` rules 35-42 remain useful subordinate detail:
  job descriptions are private analysis sources, never public job listings.
- Released PS-VOICE-001 and future PS-CAPTURE-MEDIA-001 may provide reusable
  speech and private-media infrastructure, but this package may not rebuild or
  silently repurpose them.
- Any logged-out homepage section that presents or links Ask Pete AI must follow
  the cross-product homepage projection parity contract in
  `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`.

## Docket phases

### Phase A - Owner discovery and role definition

Hold the product discussion, name the public/private modes, rank member jobs to
be done, choose the first scenario, decide which inputs and outputs belong in
the first release, and define success without prescribing implementation.

### Phase B - Experience and visual authority

Create a complete production-intent prototype for Type, Speak, and Attach;
document/screenshot processing and OCR review; grounded answers with inspectable
sources; privacy, retention and deletion; mobile, keyboard, 200-percent zoom,
reduced motion, long content, processing, error, retry, and recovery states.
Pete and the designated manager must approve the visual authority.

### Phase C - Architecture, privacy, and AI assurance

Define owner-scoped source and session models, storage/retention, OCR and file
processing, authorization-before-retrieval, provider boundaries, citations,
prompt-injection defenses, lifecycle propagation, telemetry, cost/latency,
rollout, rollback, and evaluation cases. Record requirements and traceability.

### Phase D - First vertical slice implementation

After the prior gates pass, assign one writer and fresh branch for a bounded
private role/opportunity workflow. The accepted slice must keep Type, Speak,
and Attach first class and include document plus screenshot/OCR review; any
smaller implementation requires a new explicit owner decision.

### Phase E - Validation and expansion decision

Validate with real member tasks, including a job posting screenshot and a
document upload. Measure comprehension, extraction correction, source trust,
usefulness, privacy control, and whether the experience identifies a truthful
next action. Only then choose broader Ask Pete AI workflows.

## Entry gate before implementation

Implementation remains blocked until all of the following are durable:

- one approved primary member scenario and explicit out-of-scope list;
- a resolved public Ask Pete AI versus private Owner AI permission model;
- approved Type, Speak, document, and screenshot/OCR interaction states;
- named visual authority and V0/V1 evidence;
- requirements and architecture for ownership, storage, processing, retrieval,
  correction, retention, deletion, AI safety, evaluation, rollout, and rollback;
- reuse boundaries with PS-VOICE-001 and PS-CAPTURE-MEDIA-001;
- homepage-impact assessment and any required parity package;
- assigned designated manager, implementation writer, branch, and files; and
- Pete's explicit authorization to start implementation.

## Reserved files for this docket-registration slice

- `docs/initiatives/PS-ASK-PETE-AI-001/**`
- `docs/peerslate/PeerSlate_Product_Backlog.md`
- `docs/governance/CURRENT_BASELINE.yaml`
- `docs/governance/CURRENT_STATE.md`
- `docs/governance/ACTIVE_INITIATIVES.md`
- `docs/governance/DECISIONS.md`
- `docs/governance/DOCUMENT_CONTROL.md`
- `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`
- `docs/governance/MANAGER_SESSION_HANDOFF.md`
- `docs/AI_WORKFLOW.md`
- `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`
- `AGENTS.md`, `CLAUDE.md`, and focused governance guardrails

No product route, template, JavaScript, stylesheet, data file, knowledge source,
SQL, infrastructure, dependency, or live AI behavior is reserved or changed.

## Next action

When Pete is ready, schedule the Phase A product discussion using
`01_DISCOVERY_AGENDA.md`. Do not assign an implementation writer before that
discussion and the later experience/architecture gates are complete.
