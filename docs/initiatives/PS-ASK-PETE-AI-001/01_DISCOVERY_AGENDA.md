# Ask Pete AI discovery agenda

This agenda preserves the ideas already raised without prematurely deciding the
product. It is for the future Phase A discussion under `PS-ASK-PETE-AI-001`.

## 1. Decide the role

- What should Ask Pete AI be uniquely excellent at for a visitor?
- What should the signed-in private version do for Pete or another member?
- Which tasks should stay contextual inside Resume, Studio, Work, Story, or
  Next Chapter instead of being forced through one chat window?
- What should the assistant refuse, redirect, or hand off?
- How should Ask Pete AI, Ask [Name] AI, and Owner AI be named so the permission
  boundary is obvious?

## 2. Rank the first real scenarios

Candidate scenarios to compare:

1. Upload or screenshot a job posting, review the extracted requirements, and
   ask how they align with confirmed Slate history.
2. Ask for interview preparation grounded in a selected posting and approved
   history, with a handoff to Interview Studio rather than duplicate coaching.
3. Ask how to tailor a resume draft for a purpose while preserving one
   canonical career dataset and requiring review before any change.
4. Upload a promotion standard, certification rubric, project need, or other
   professional document and identify direct experience, transferability,
   missing information, and genuine gaps.
5. Use voice to explain personal goals, constraints, or overlooked context that
   the document alone cannot show.

The discussion should choose one primary scenario and one secondary scenario.
Everything else remains later.

## 3. Explore input paths

### Type

- short question;
- long pasted source;
- pasted job posting with headings and lists; and
- follow-up correction or clarification.

### Speak

- voice question;
- goal or constraint;
- explanation of missing experience; and
- correction of an OCR or extracted requirement.

### Attach

- PDF, DOCX, and TXT;
- one screenshot or a multi-image posting in page order;
- PNG and JPEG at minimum for the screenshot use case; and
- clear validation, progress, cancel, failure, retry, delete, and retention
  states.

Open questions include maximum size/pages/images, image order, OCR provider,
tables and multi-column layouts, duplicate sources, password-protected files,
handwritten text, unsupported formats, and whether URL capture belongs later.

## 4. Define the answer anatomy

A candidate grounded answer may include:

- the direct answer first;
- the exact supplied source section or image region used;
- confirmed Slate records used;
- a clear separation among direct match, transferable experience, missing
  information, and genuine gap;
- uncertainty, conflict, or OCR warning;
- one focused question when the record is insufficient; and
- one member-controlled next action, such as open Interview Studio, draft a
  resume proposal, capture missing context privately, or dismiss the result.

The discussion must decide when scores help and when they create false
authority. No score may be represented as hiring probability.

## 5. Set privacy and lifecycle expectations

- Is the default source session-only, and what explicit action saves it?
- How long do source bytes, OCR text, transcripts, and derived answers persist?
- Can a saved target be reused, renamed, exported, archived, or deleted?
- What happens to derived analysis when the source is corrected or deleted?
- How are private owner sources prevented from entering public Ask Pete AI?
- What provider receives which minimum data, and what is never logged?
- How does the user cancel a processing job and confirm deletion?

## 6. Design the complete experience

Prototype at least:

- opening with Type, Speak, and Attach as first-class choices;
- attachment validation and upload;
- OCR/extraction processing;
- extracted-text and source-span review/correction;
- grounded answer with inspectable sources;
- missing-information question;
- long document and multi-screenshot flow;
- microphone denied, file rejected, OCR low confidence, provider unavailable,
  interrupted upload, timeout, retry, cancel, and delete;
- public/private mode explanation;
- desktop, touch mobile, landscape, keyboard focus, 200-percent reflow, screen
  reader order, and reduced motion; and
- any logged-out homepage section that presents Ask Pete AI, compared with the
  accepted real product under the homepage parity contract.

## 7. Prove the architecture before build

The implementation plan must answer:

- trusted identity and owner scope;
- source/session/target/analysis data boundaries;
- private Blob and metadata storage;
- file validation and malware strategy;
- OCR and document extraction lifecycle;
- authorization-before-retrieval and public/private source filters;
- source citations and correction propagation;
- prompt injection and source poisoning controls;
- provider fallback, latency, cost, queues, retry, observability, and deletion;
- reuse of Voice and Capture Media without merging their distinct product
  purposes; and
- rollout, rollback, evaluation dataset, and real-member validation.

## 8. Discussion output

The Phase A meeting closes only when the repository records:

- the chosen primary scenario;
- canonical product and mode names;
- first-release inputs and outputs;
- explicit exclusions;
- success measures;
- unresolved decisions and owner choices;
- the next design package; and
- whether any implementation work is authorized. The default answer remains
  **no implementation yet**.
