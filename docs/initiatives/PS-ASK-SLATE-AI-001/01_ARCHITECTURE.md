# PS-ASK-SLATE-AI-001 — Requirements and Architecture

## Normative requirements

- **PS-ASK-001:** Ask Slate AI shall use trusted signed-in identity and an
  explicit purpose/context for every request.
- **PS-ASK-002:** Application authorization shall constrain retrieval before a
  model receives records. A model shall never decide which private records the
  caller may access.
- **PS-ASK-003:** Ask My Slate shall operate over owner-permitted private
  records; Ask [Name] AI shall operate only over records independently
  authorized for the actual viewer.
- **PS-ASK-004:** Ask Pete AI shall remain a public Pete-specific instance and
  shall never inherit owner-private retrieval by naming or shared-session
  accident.
- **PS-ASK-005:** Public and private assistants shall use separate retrieval
  policies, source manifests, system instructions, caches, telemetry scopes,
  and tests even if they share lower-level code.
- **PS-ASK-006:** A public Journal/Story/Work item may be used only when its
  current exact version and audience permit the viewer; route visibility alone
  is not authorization.
- **PS-ASK-007:** Private multimodal job-description or qualification analysis
  shall live in Ask Slate/Qualification Alignment, not private Ask Pete AI.
- **PS-ASK-008:** Every substantive answer grounded in the member's Slate shall
  show the relevant sources/versions in member-comprehensible language.
- **PS-ASK-009:** The product shall distinguish source fact, model inference,
  missing context, uncertainty, and suggested wording/action.
- **PS-ASK-010:** When no permitted evidence supports an answer, Ask Slate shall
  say so and may ask one focused question; it shall not invent a history.
- **PS-ASK-011:** AI output is a proposal. It shall not create/edit a Moment,
  change audience, publish, delete, retain, place, send a message, apply to a
  job, or change a résumé/Story/Project automatically.
- **PS-ASK-012:** A proposed save or downstream use shall display content,
  source set, destination, audience, and material uncertainty, then require the
  domain's explicit action.
- **PS-ASK-013:** Ask Slate shall preserve the member's natural voice and shall
  not default to corporate performance language or invented certainty.
- **PS-ASK-014:** Type is required. Speak may be added through the same private
  source/transcription/review contract. Voice availability shall not remove
  Type.
- **PS-ASK-015:** PDF, DOCX, TXT, PNG, JPEG, and other inputs require a bounded
  later multimodal package with type/size limits, malware/content checks,
  extraction/OCR state, source spans, member review, retention, and deletion.
- **PS-ASK-016:** Extracted/OCR text shall be visibly distinguishable from the
  original file and reviewable before consequential analysis.
- **PS-ASK-017:** External documents shall be session-private by default and
  shall not enter canonical Journal history, model training, public grounding,
  or long-term retention without an explicit member action/policy.
- **PS-ASK-018:** Sensitive questions and private-source retrieval shall not be
  exposed in public URLs, client logs, analytics, notifications, or support
  traces.
- **PS-ASK-019:** Conversation/history retention shall be explicit, configurable
  where applicable, exportable, and deletable. Deleting a source shall
  invalidate dependent grounding/citations under policy.
- **PS-ASK-020:** The service shall defend against prompt injection in uploads,
  sources, OCR, web content, and retrieved text. Source instructions are data,
  not system authority.
- **PS-ASK-021:** Tool calls shall be allowlisted by workflow and purpose;
  read-only retrieval is the default. Side effects require deterministic
  validation and explicit member approval outside model text.
- **PS-ASK-022:** AI shall never send a message or invite, publish a projection,
  connect members, or change access on the member's behalf.
- **PS-ASK-023:** Models/providers, prompts, source manifests, output state,
  feedback, and material tool actions shall be auditably versioned without
  logging private content unnecessarily.
- **PS-ASK-024:** Provider failure shall leave Journal/source inspection and
  deterministic product tasks usable and shall not replace results with fixture
  content.
- **PS-ASK-025:** Rate limits, quotas, timeouts, cancellation, retry, long
  context, partial extraction, unsupported file, stale source, and deleted
  source shall have truthful states.
- **PS-ASK-026:** The UI shall support keyboard, screen reader, mobile, touch,
  200% zoom, reduced motion, long answers/sources, copy/export, and focus-safe
  streaming/error recovery.
- **PS-ASK-027:** Ask Slate shall measure answer support, task usefulness,
  correction, missing-context honesty, source inspection, and harmful/privacy
  failures—not conversation length or dependence.
- **PS-ASK-028:** Public Ask [Name] AI requires abuse/rate-limit, impersonation,
  moderation/contact, exact-source, and owner-disable controls.
- **PS-ASK-029:** Ask Slate naming does not create a required top-level route;
  exact global/contextual surfaces remain a design and navigation decision.
- **PS-ASK-030:** The first implementation shall be one bounded scenario with a
  fixed source class and evaluation set, not every specialist workflow and
  upload type at once.

## Logical request flow

```text
trusted viewer + owner + purpose + room context
        ↓ deterministic authorization
minimum permitted source/version handles
        ↓ retrieval and injection/content controls
bounded evidence packet + source manifest
        ↓ model/specialist workflow
answer proposal + citations + uncertainty + optional next action
        ↓ deterministic output/tool validation
member review
        ↓ explicit domain action, if chosen
Save Moment | projection draft | practice | compare | dismiss | nothing
```

## Specialist workflow allocation

| Workflow | Purpose | Extra boundary |
|---|---|---|
| Ask My Slate | Find/explain/reflect across owner-permitted history | Private owner only |
| Ask [Name] AI / Ask Pete AI | Answer viewer questions from approved public/audience sources | No owner-private data or hidden counts |
| Interview AI / Moment Lab | Practice/example/coaching using chosen mode and permitted history | Generic examples never imply member experience |
| Board AI Help | Propose planning questions/milestones/resources | Never saves or connects automatically |
| Qualification Alignment | Compare member-supplied external criteria with trusted member-saved history | Not a hiring probability, job feed, or auto-application |
| Résumé/Story assistance | Propose selection/wording/layout | Exact source links; no invented facts or auto-publication |
| Next Chapter | Identify transfer, gaps, and small experiments from member-chosen direction and trusted member-saved history | No opaque destiny/fit score |

## First-slice recommendation

After the private Journal exists, start with owner-only typed **Ask My Slate:
find and explain relevant history** over member-saved canonical text Moments. Require exact
citations, no writes/tools, correction feedback, no-results honesty, two-owner
isolation, and private deletion. Voice, uploads/OCR, global navigation, public
Ask [Name], and specialist side effects follow separate gates.
