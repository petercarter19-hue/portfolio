# Ask Pete Recruiter Evidence Companion — visual/runtime architecture

## 1. Decision and release truth

This is the implementation contract for the Pete-approved **Concept H V2
Recruiter Evidence Companion** on the public résumé. It translates the locked
visual direction and the merged Grounded Ask Pete backend contract into one
bounded runtime design. It does not create a competing visual direction.

The Grounded Ask Pete backend merged through Azure PR 315 as `ebb6276`, but it
remains dormant while `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` is false. This
runtime lane may implement and verify the flag-gated interface, but it stops at
an independently reviewed Azure PR. It does not merge, deploy, enable the
feature flag, change a provider, or make the experience live.

The product moment to prove remains deliberately small:

1. A recruiter explicitly selects **Give me Pete's 60-second recruiter brief**.
2. Ask Pete returns a concise professional through-line.
3. Consequential claims expose inspectable, claim-level evidence.
4. The answer distinguishes support, interpretation, limitations, and what is
   not established in approved public information.
5. It proposes useful interview questions.
6. It offers Pete's current contact options when the human answer matters,
   without claiming that a message was sent.

The résumé remains understandable without AI. Pete and his evidence remain the
subject and authority; Ask Pete is the navigator.

## 2. Locked visual authority

The following files under the external 2026-08-06 Ask Pete visual round are
the exact implementation references. The SHA-256 values are part of this lock:

| State | File | SHA-256 |
|---|---|---|
| Desktop recruiter-brief master | `concept-h-aligned-master-answer-v2.png` | `AB1B2882A605BE414E46BBDCD0633D0AA3B07579CDA2F49660434952901FCAC2` |
| Desktop exact-source open | `concept-h-state-01-source-open-aligned-v2.png` | `5AD62C65A04BB95835650BA30B8AAE3B5928895FFA3359ED2AEDDCA64C87EF6D` |
| Desktop contextual MBSE pre-submit | `concept-h-state-02-contextual-mbse-aligned-v2.png` | `30197018CAA018A2D3B414642EA1A49E24666059A2D5585A1BBF1F9DED96C1D7` |
| Narrow-desktop side sheet | `concept-h-state-03-narrow-side-sheet-aligned-v2.png` | `AF2023BCD01A1BE23564ABF2A18AA119F4D7EC060CB5D8913509C6A6144F80C0` |
| Mobile bottom sheet | `concept-h-state-04-mobile-bottom-sheet-aligned-v2.png` | `24977354DFBEDAA8BC3E1965183380B986A61DFD25CD5505F3924848810CAB70` |
| Loading, partial, unknown, ambiguous, unavailable, handoff, focus board | critical-state board | `D06A015AF418DA3CCEF0ABD7383DC6506DDFD1AABCFFE5FF730F6E4731590DF1` |

Implementation must preserve the recognizable eucalyptus field, warm ivory
planes, deep forest interaction color, aged-gold evidence accents, restrained
cobalt AI cues, editorial headings, selective deep shadows, shared baselines,
and consistent rail/sheet insets. Elevation belongs to the résumé plane, Ask
Pete companion, selected evidence, primary action, and true floating layer—not
every row or section.

Rasterized mockup copy is not canonical data. Runtime copy and evidence come
from the approved structured résumé and Grounded Ask Pete response.

## 3. Fixed product and trust boundaries

- Product name: **Ask Pete AI**.
- Ask Pete speaks about Pete, never as Pete.
- Public résumé visibility and approval for Ask Pete use remain distinct.
- Retrieval remains limited to the server-side public-AI manifest.
- No browser-provided profile, subject, or context value grants authority.
- The interface never implies private Slate, Journal, Workshop, Opportunity,
  upload, voice, OCR, or job-description access.
- AI synthesis is not canonical truth and cannot save, publish, send, delete,
  contact, update knowledge, or make an employment decision.
- No fit score, hiring probability, protected-trait judgment, or unsupported
  inference appears.
- The human handoff opens Pete's existing contact options. Nothing is sent
  automatically; on-platform private messaging is not live.
- No question, prompt, source body, excerpt, answer, contact data, or exception
  payload is added to logs or diagnostics.

## 4. One canonical component

The page renders one `AskPeteEvidenceCompanion` DOM instance. It must not
render separate desktop, side-sheet, mobile, hero-chat, and global-chat copies.
CSS reflows the same component and JavaScript preserves one state object.

Recommended template boundary:

- `templates/partials/ask_pete_evidence_companion.html`
- one labelled `<aside>` root with `data-ask-pete-companion`;
- a header and responsive close control;
- capability/context region;
- starter actions;
- one visible composer;
- one status live region;
- one structured answer region; and
- one current-contact handoff region.

The companion exposes stable hooks rather than style-dependent selectors:

- `data-ask-pete-open`
- `data-ask-pete-close`
- `data-ask-pete-starter`
- `data-ask-pete-context-action`
- `data-ask-pete-context-label`
- `data-ask-pete-context-count`
- `data-ask-pete-form`
- `data-ask-pete-input`
- `data-ask-pete-submit`
- `data-ask-pete-cancel`
- `data-ask-pete-status`
- `data-ask-pete-answer`
- `data-ask-pete-source`
- `data-ask-pete-show-all`

Resume-specific entry points open this component. They do not open or submit to
the legacy global chat panel. When the grounded flag is enabled on the résumé,
the duplicate global launcher/panel and old compact sub-header form are omitted
or replaced with one compact opener into this component. Other pages retain
their current legacy assistant unchanged.

## 5. In-memory state machine

The controller owns one page-memory state object:

```text
layout: wide_rail | narrow_sheet | mobile_sheet
open: boolean
phase: idle | context_ready | loading | slow | answered |
       validation_error | unavailable
draft: string
requestedAction: recruiter_brief | evidence_finder |
                 interview_preparation | null
explicitContext: { key, label, evidenceItemCount, origin } | null
viewingSection: overview | impact | skills | experience | credentials
answer: structured response | null
lastInvoker: Element | null
requestSequence: integer
abortController: AbortController | null
highlightedTargets: Set<Element>
```

No state is stored in `localStorage`, a cookie, a database, or an analytics
payload. Refreshing the page starts a new unsaved public session. A follow-up
is independently grounded; prior answer text is not silently sent as model
context. The current answer and draft remain in the DOM while the visitor
scrolls the résumé or opens evidence.

Allowed transitions:

- `idle -> loading` after an explicit starter or form submission;
- `idle -> context_ready` after a contextual Ask action;
- `context_ready -> loading` only after the recruiter submits;
- `loading -> slow` after the slow threshold without changing the request;
- `loading|slow -> answered` after a valid structured response;
- `loading|slow -> validation_error` for bounded client/server failures;
- `loading|slow -> unavailable` for a structured unavailable answer or safe
  provider/network fallback;
- `answered|validation_error|unavailable -> loading` on a later explicit ask;
- any open sheet state may close without deleting its draft or answer;
- a new request aborts the previous request and increments `requestSequence`.

Responses whose sequence is no longer current are ignored even if the network
delivers them after a newer response.

## 6. Request contract

Use the existing same-origin `POST /api/chat` endpoint:

```json
{
  "message": "Show evidence of Pete's MBSE work.",
  "action": "evidence_finder",
  "context_key": "skill:mbse"
}
```

- `message` is required trimmed text, maximum 1,000 characters.
- The new composer uses `maxlength="1000"`; client validation is convenience,
  not authority.
- `action` is an optional bounded hint. Only `recruiter_brief`,
  `evidence_finder`, and `interview_preparation` are emitted.
- `context_key` is included only for a known manifest-backed object.
- Context prioritizes an approved record and never expands retrieval.
- The server must return `400` for a non-object body, missing/non-string
  `message`, empty message, invalid context, or oversized input before provider
  work. In particular, type validation occurs before `.strip()`.
- Existing same-origin and rate-limit enforcement remains authoritative.

Starter behavior is explicit:

- selecting the flagship recruiter brief is itself the submit action;
- selecting another starter submits that starter;
- a contextual `Ask Pete About This` action opens/focuses the companion, sets
  the approved context, and prefills editable wording but never auto-submits.

Context count language must distinguish data levels. Before submit, a skill
may say **3 approved evidence items**, derived from the résumé presentation.
After an answer, `source_summary.used_count` says **N public records**, derived
from the public-AI source versions. Do not label those as the same count.

## 7. Response mapping

The enabled path expects `schema_version: ask-pete-public-answer.v1`:

- `answer_id` remains an opaque identifier;
- `purpose` labels the bounded recruiter job;
- `state` and `support_label` drive the overall state heading;
- `summary` is the concise answer-first synthesis;
- `claims[]` render independently;
- `follow_up_questions[]` render as useful next questions, not answers Pete is
  presumed to have given;
- `handoff` renders only when present;
- `sources_used[]` support the aggregate source action;
- `source_summary` supplies its truthful count and label;
- `context.context_key` confirms the server-accepted context; and
- `response` remains legacy compatibility and is not the structured renderer's
  primary field.

For each claim:

- show `text` and its explicit `support_label`;
- distinguish `evidence`, `interpretation`, and `boundary`;
- show `limitation` next to the exact partially supported or boundary claim;
- render its citations directly beneath or beside that claim;
- never use one overall label to hide mixed claim states; and
- communicate state through icon, text, and structure—not color alone.

State presentation:

- `supported`: direct answer plus inspectable evidence;
- `partially_supported`: supported portions and exact limitations are separate;
- `not_established`: absence of approved evidence is not presented as “no”;
- `ambiguous`: ask the recruiter to clarify or rewrite before a blended answer;
- `refused`: state the public boundary without revealing hidden-source clues;
- `unavailable`: keep the résumé, PDF, and current contact path usable;
- malformed, unverifiable, or wrong-schema output: render a validation failure,
  never a plausible normal answer.

All dynamic text is assigned using `textContent` or equivalent safe DOM APIs.
Model output is never inserted with `innerHTML`.

## 8. Exact source coordination

Each citation's server-provided locator contains `section`, `anchor`,
`record_kind`, `record_id`, `highlight_key`, and `href`. The controller validates
the locator shape, resolves only a matching element inside the résumé root, and
never treats a locator as arbitrary script or selector text.

Opening one source:

1. Preserve the answer and companion state.
2. Open the relevant résumé detail when required.
3. Scroll the target below fixed/sticky chrome.
4. Move keyboard focus to the evidence target or its labelled detail region.
5. Announce the opened record in the existing/new status region.
6. Apply a restrained temporary highlight plus a persistent textual selected
   marker for the focused record.
7. Remove the temporary emphasis after a bounded interval; under reduced
   motion, scroll and highlight without animation.

Record mapping:

- `profile`: open/focus the public Overview record;
- `career_role`: dispatch the existing résumé experience-open behavior for the
  exact `record_id`, then target `r2-exp-card-{record_id}`;
- `skill`: open the exact skill evidence panel for `record_id`, then target
  `r2-skill-panel-{record_id}`;
- `achievement`: open the Recognition & Achievements credential panel and
  target a stable per-record ID.

Achievement locators currently collapse to the shared `resume-achievements`
anchor. This lane must add stable DOM IDs such as
`r2-credential-record-achievement-{record_id}` to the rendered recognition
records and update `data/ai_sources/ask_pete_public_v1.json` so every approved
achievement locator opens its exact record. Do not create a second fact body.

`Show all on résumé` marks all used records without forcing mutually exclusive
skill or experience detail panels open at once. It scrolls to the first used
record and lets the recruiter continue through the résumé. Visible
representatives may be the skill toggle/card when its detail is not the active
panel. The result must not become a permanent heat map.

## 9. Resume event integration

`static/js/living-resume-v2.js` remains owner of résumé section, skill,
experience, and credential opening. Add only small explicit custom-event seams
needed by the companion, for example:

- section-change notification with the canonical section ID/label;
- open-skill by approved record ID;
- existing open-experience by approved role ID;
- existing open-credential for the recognition category.

The companion owns API requests, answer rendering, sheet state, source intent,
and its own focus return. It must not duplicate the résumé's chapter/panel
logic or invoke hidden internal functions by fragile CSS traversal.

## 10. Responsive composition

The same component reflows at implementation-calibrated breakpoints that match
the accepted references:

### Wide desktop

- persistent 380–420 px evidence rail;
- the left navigation remains on the eucalyptus field;
- résumé and companion share a deliberate top baseline;
- rail content uses one consistent horizontal inset;
- the résumé retains a readable center width;
- the rail may be sticky, but its initial document-flow alignment must not
  depend on a transform or negative margin;
- no close control is needed while it is a persistent rail.

### Narrow desktop/tablet

- the companion becomes one dismissible side sheet below the compact header;
- it does not intrude into the header zone;
- it preserves the same answer and draft;
- the résumé remains readable and interactive;
- no duplicate sheet DOM is created.

### Mobile

- the companion becomes a bottom sheet with explicit close control;
- the header, résumé card, sheet, heading, source rows, and composer share one
  coherent inset system;
- use dynamic viewport units with a safe fallback and safe-area padding;
- keep enough résumé context visible to preserve orientation;
- prevent the fixed layer from hiding a newly focused underlying element;
- the compact persistent Ask Pete trigger opens the same component.

The side/bottom sheet is non-modal because the résumé must remain available
while Ask Pete works. When closed it is both visually hidden and inert. When
open it is a labelled complementary region, not falsely marked `aria-modal`.
Do not create competing nested page/sheet scroll traps.

## 11. Feature flag and legacy compatibility

`PEERSLATE_ASK_PETE_GROUNDED_ENABLED` gates both the structured backend and new
resume companion. When false:

- the established résumé markup, assistant, global launcher/panel, JavaScript,
  and `POST /api/chat` response behavior remain unchanged;
- no Concept H capability preview promises structured citations that the
  legacy response cannot provide; and
- the new stylesheet/controller has no observable behavior.

When true on the résumé:

- render the one structured companion;
- route resume-specific Ask entry points into it;
- omit/suppress the duplicate legacy resume widget and old compact form; and
- retain legacy compatibility for other pages through the response's existing
  `response` field.

Do not add a second feature flag or change the current default. Feature
enablement remains a later owner/release decision after PR integration,
homepage-parity assessment, provider verification, and live-release authority.

## 12. Accessibility and focus contract

- Every input has a persistent programmatic label.
- Every opener exposes its expanded state when applicable.
- Starter, source, close, cancel, handoff, and submit controls have at least a
  44 by 44 CSS-pixel target where layout permits.
- Visible focus uses the accepted high-contrast treatment and remains visible
  against eucalyptus, ivory, forest, gold, and focused evidence states.
- Opening a sheet records the exact invoker and focuses the composer or the
  prefilled context question.
- Escape closes only the dismissible narrow/mobile sheet and restores focus to
  the invoker. It must not close the persistent wide rail or conflict with an
  open résumé skill/experience/credential panel.
- Closing through the explicit control also restores focus.
- Loading and newly available answers are announced through a concise polite
  live region; validation errors receive an appropriate alert/status without
  repeating the full answer.
- Source navigation moves focus to the exact evidence target and announces it.
- Sticky/fixed layers and scroll margins keep that focused target visible.
- Reading order follows header, summary, claims/evidence, limitations,
  follow-ups, handoff, and composer.
- At 200% zoom the experience reflows without clipped text, horizontal page
  overflow, inaccessible actions, or dual scroll traps.
- `prefers-reduced-motion: reduce` disables smooth scrolling, animated
  elevation, and animated temporary highlighting.
- `forced-colors: active` retains borders, focus, selection, support labels,
  and operable controls without relying on background images or shadows.
- Text and interactive contrast must meet WCAG 2.2 AA; support state is never
  color-only.

## 13. Loading, slow, timeout, stale request, and error behavior

On submit:

- trim and validate the draft;
- abort any earlier request;
- increment the request sequence;
- disable only controls that would create a competing submission;
- keep the résumé interactive;
- announce **Reviewing Pete's approved public information…**; and
- show bounded activity language without a fake percentage or countdown.

After a short slow threshold, change the presentation to **This is taking
longer than expected. You can keep reviewing Pete's résumé while the answer
finishes.** Preserve actions to keep waiting or cancel.

Use an abortable overall request timeout consistent with the existing public
experience (45 seconds unless implementation evidence supports a smaller safe
bound). Timeout, network failure, structured `unavailable`, `429`, `400`,
grounding/validation failure, and unexpected server failure remain distinct
internal categories but expose only safe visitor copy.

- `400`: show the bounded correction and preserve the editable draft.
- `429`: ask the visitor to wait; do not pretend the provider failed.
- structured `unavailable`: use the accepted unavailable state and keep public
  résumé/contact paths.
- `502` or wrong/malformed schema: say the answer could not be verified; never
  render partial unvalidated content.
- network/timeout: say the assistant could not be reached/completed; allow a
  retry.
- canceled request: return to the prior stable state without an error alert.
- late response from an older sequence: ignore it completely.

Re-enable the composer after every terminal path. No exception detail, request
body, generated text, email, source excerpt, or private clue enters telemetry.

## 14. Exact implementation surfaces

The activated implementation lane may write only:

- `app.py`
- `templates/base.html`
- `templates/resume2.html`
- `templates/partials/profile_tabs.html`
- `templates/partials/ask_pete_evidence_companion.html`
- `static/css/ask-pete-resume-evidence.css`
- `static/js/ask-pete-evidence-companion.js`
- `static/js/living-resume-v2.js`
- `docs/initiatives/PS-ASK-PETE-AI-001/`
- `data/ai_sources/ask_pete_public_v1.json`
- `tests/ask_pete/`
- `tests/test_resume2.py`
- `tests/test_living_resume_preview.py`
- `tests/test_navigation.py`

Use the new additive, resume-specific stylesheet, controller, and partial.
Do not extend the shared `static/js/chatbot.js` or
`static/css/chatbot.css`, and do not append another large override section to
`static/css/resume2.css`. The new CSS is fully scoped to the flag-on résumé
body/root and loads with enough route specificity to coexist with the shared
public navigation without editing that stylesheet.

## 15. Explicit exclusions

- No new route or endpoint.
- No edit to `services/ai_foundation/`, shared `chatbot.js`/`chatbot.css`,
  provider configuration, secret, dependency, pipeline, or environment.
- No feature-flag setting change.
- No SQL, persistence, inbox, notification, private reply, message sending,
  automatic knowledge update, publication, deletion, or canonical mutation.
- No edit to Opportunity Slate, Workshop, Community, Journal, Interview
  Studio, homepage, `services/database_service.py`, or
  `services/knowledge_service.py`.
- No voice, uploads, OCR, job-description matching, fit score, hiring judgment,
  or private Slate retrieval.
- No résumé information-architecture or canonical-content rewrite.
- No pull-request merge, deployment, production enablement, provider change,
  or claim that this implementation is live.
- No write to another writer's branch, worktree, checkpoint, or unlisted
  surface.
- No cleanup of unrelated branches, worktrees, artifacts, stashes, dirty
  files, or user-owned material.

## 16. Vertical implementation slices

Terra Max implements sequentially in the dedicated runtime worktree:

1. **Flag-gated shell and visual system** — one partial, route-scoped
   stylesheet, persistent desktop rail, flag-off regression, and no API
   enablement.
2. **Structured renderer** — request validation, abort/sequence handling,
   summary, claim-level state, citations, follow-ups, handoff, and every
   supported/error fixture.
3. **Context and evidence coordination** — editable contextual prefill without
   auto-submit, résumé event seams, exact per-record source opening, source
   summary, and Show all on résumé.
4. **Responsive behavior** — narrow side sheet, mobile bottom sheet, one state
   across reflow, consistent alignment/insets, and no scroll traps.
5. **Accessibility and defensive hardening** — input-type `400`, focus return,
   Escape, live announcements, 200% zoom, reduced motion, forced colors,
   contrast, stale requests, slow/timeout, and safe failure recovery.
6. **Evidence and self-review** — focused/regression tests, screenshot
   comparison, changed-path audit, and removal of task-created cache or
   temporary capture debris.

Each slice should be a coherent reviewable commit, but the branch remains one
implementation lane and one writer. Do not create extra implementation
worktrees or stacked product branches.

## 17. Verification and visual evidence

Automated verification must cover:

- default-off HTML and `/api/chat` compatibility;
- flag-on render contains one companion and no duplicate resume assistant;
- non-string, empty, oversized, malformed, and invalid-context input fails
  before provider work;
- recruiter brief, evidence finder, interview preparation, supported,
  partially supported, not established, ambiguous, refused, unavailable,
  `400`, `429`, validation failure, network failure, timeout, cancel, and stale
  response behavior;
- all model strings use safe text rendering;
- exact profile, role, skill, and individual achievement locators;
- contextual prefill remains editable and never auto-submits;
- starter selection submits exactly once;
- Escape/focus return and source-focus behavior;
- no private-source or payload-bearing diagnostic fields; and
- relevant résumé/navigation regressions.

Browser verification uses deterministic intercepted structured fixtures and
representative dimensions including the locked-reference sizes:

- 1536 × 1024 desktop master and source/context states;
- 1435 × 1096 narrow-desktop side sheet;
- 853 × 1844 mobile reference;
- common 1366 px desktop, 1024 px narrow/tablet, and 390 px phone widths;
- 200% zoom/reflow; and
- reduced-motion and forced-colors checks where browser support permits.

Capture side-by-side implementation/reference screenshots for the master,
source-open, contextual pre-submit, narrow, mobile, and critical states. Check
alignment, center/rail baseline, insets, clipping, focus visibility, hit
targets, source highlight, sticky boundaries, long answers, overflow, and
scroll ownership. Record only intentional narrow adaptations and unresolved
differences; do not call approximate output accepted without Pete or explicit
delegated visual authority.

## 18. Model handoff and completion

The owner-selected sequence is mandatory:

1. **Sol Extra High** writes and commits this architecture record only.
2. Sol explicitly relinquishes the implementation worktree.
3. **Terra Max** becomes the sole writer, implements the vertical slices,
   validates, cleans task debris, and self-reviews the complete diff once.
4. **Fresh Sol Max** reviews the exact candidate SHA read-only against this
   contract, the accepted visual hashes, the backend contract, and changed
   paths.
5. Terra resolves every finding or records a truthful accepted limitation.
6. The coordinator verifies review closure and opens an Azure PR.
7. Stop before PR merge, deployment, configuration/provider change, feature
   enablement, or any statement that the new experience is live.

Clean-kitchen closeout occurs only after later verified merge authority: create
a recovery ref, prove the branch is merged and the worktree clean, then remove
only this lane's clean worktree/local branch/remote task branch and temporary
captures. Preserve every unrelated, dirty, unverified, or user-owned artifact.
