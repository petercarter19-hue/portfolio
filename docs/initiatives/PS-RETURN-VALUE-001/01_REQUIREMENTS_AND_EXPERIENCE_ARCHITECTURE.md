# PS-RETURN-VALUE-001 — Requirements and Experience Architecture

## Shared return-value requirements

- **PS-RV-COM-001:** Every return item shall state what it is, why it appeared,
  and which permitted records or member settings support it.
- **PS-RV-COM-002:** Return items shall be finite, optional, dismissible, and
  subordinate to the member's current task.
- **PS-RV-COM-003:** A focused room shall receive no more than one primary
  return/bridge and two secondary paths in its default state.
- **PS-RV-COM-004:** Authorization, lifecycle, suppression, and source validity
  shall be evaluated before retrieval and again before delivery.
- **PS-RV-COM-005:** Private content, source text, transcripts, embeddings, and
  insight payloads shall not enter product analytics or logs.
- **PS-RV-COM-006:** A member shall be able to pause all proactive return value
  without losing Journal access or existing Moments.
- **PS-RV-COM-007:** No service shall publish, send, broaden an audience, create
  a canonical fact, or apply a downstream action without explicit approval.
- **PS-RV-COM-008:** Empty history, insufficient evidence, conflicting history,
  removed sources, provider failure, and no useful result shall produce an
  honest quiet state rather than fabricated value.
- **PS-RV-COM-009:** Feedback and suppression shall affect future delivery
  predictably without deleting canonical history.
- **PS-RV-COM-010:** Every service shall support keyboard, screen reader,
  mobile, touch, 200% zoom, reduced motion, long content, and understandable
  failure/recovery behavior.

## Replay and resurfacing

Replay is a finite editorial synthesis. Resurfacing is the controlled selection
of one or a few prior items that may be relevant now. Neither is an infinite
memory feed.

- **PS-RV-RSF-001:** Resurfacing shall select only authorized, active, valid
  Moments or projections and shall preserve exact source/version links.
- **PS-RV-RSF-002:** Eligibility shall be determined by application rules before
  any generative ranking or explanation.
- **PS-RV-RSF-003:** Eligible reasons may include anniversary/time relation,
  unfinished thread, selected Focus Theme, current room relevance, member-
  chosen revisit, related current Moment, or previously saved Keepsake.
- **PS-RV-RSF-004:** Sensitive, recently dismissed, too-personal, deleted,
  revoked, unresolved, or frequency-capped material shall be excluded.
- **PS-RV-RSF-005:** The interface shall explain the selection in plain
  language and provide Inspect, Useful, Not useful, Too personal, Show less
  like this, Remind me later, and Dismiss as appropriate.
- **PS-RV-RSF-006:** Dismissal shall not delete the underlying Moment.
- **PS-RV-RSF-007:** A member may create a deliberate revisit date/condition;
  the system shall distinguish that request from algorithmic resurfacing.
- **PS-RV-RSF-008:** Another viewer shall never receive resurfacing computed
  from Moments hidden from that viewer.
- **PS-RV-RSF-009:** Resurfacing shall not infer that an old plan, relationship,
  role, health state, or goal is still current without confirmation.
- **PS-RV-RSF-010:** Frequency and recency caps shall prevent repetitive or
  intrusive returns.
- **PS-RV-RSF-011:** The service shall be silent when no item clears relevance,
  safety, and evidence thresholds.
- **PS-RV-RSF-012:** Resurfaced content shall never masquerade as newly created
  activity.
- **PS-RV-RSF-013:** The core first slice may show one recent and one resurfaced
  Moment; broader personalization is later.
- **PS-RV-RSF-014:** Deleted/revoked source propagation shall invalidate cached
  candidates and generated explanations.
- **PS-RV-RSF-015:** Member feedback shall tune ranking within transparent
  boundaries and shall not create psychological profiling.
- **PS-RV-RSF-016:** Telemetry shall measure useful continuation, suppression,
  and task completion—not time-on-site or compulsive return.

- **PS-RV-RPL-001:** Replay shall support finite member-selected or product-
  offered periods such as week, month, quarter, year, project, transition, or
  theme; no daily requirement is implied.
- **PS-RV-RPL-002:** Replay shall include a small number of significant Moments,
  truthful movement, one or two source-linked observations, missing context,
  and at most one primary next action.
- **PS-RV-RPL-003:** The member shall be able to inspect every source used.
- **PS-RV-RPL-004:** AI-generated synthesis shall remain a private proposal that
  the member can correct, regenerate with changed scope, or dismiss.
- **PS-RV-RPL-005:** Replay shall not equate capture volume with growth or
  generate praise unsupported by records.
- **PS-RV-RPL-006:** A quiet or difficult period may be represented without
  calling it failure or inventing a positive arc.
- **PS-RV-RPL-007:** The member may pin an item as a Keepsake; this stores a
  reference and owner meaning, not a duplicate or system trophy.
- **PS-RV-RPL-008:** Sharing a Replay requires a separate projection, exact
  audience preview, and explicit publication/share action.
- **PS-RV-RPL-009:** Public Replay, if ever considered, computes solely from
  independently public-permitted records and requires a new package.
- **PS-RV-RPL-010:** Replay shall remain accessible as structured content even
  when its visual treatment is cinematic.
- **PS-RV-RPL-011:** A failed Replay job shall not block Journal or hide the
  source Moments.
- **PS-RV-RPL-012:** The system shall not notify merely because a period ended;
  notification requires the member's settings and a worthwhile result.
- **PS-RV-RPL-013:** Replay version, scope, source set, model/rules, and feedback
  state shall be auditable and deletable.
- **PS-RV-RPL-014:** Exact names such as Weekly Debrief, Echo Back, or Growth
  Reel remain product-copy decisions; Replay is the governed capability family.

## Momentum

Momentum answers “What meaningful thread is continuing?” It is not a count of
consecutive logins.

- **PS-RV-MOM-001:** Momentum may use member-chosen or context-appropriate
  periods including day, week, month, project, chapter, transition, season, or
  practice sequence. A daily rhythm is optional and member-chosen; it is never
  a default obligation or loss/reset mechanism.
- **PS-RV-MOM-002:** Momentum shall be based on meaningful governed events such
  as saving/reviewing a Moment, returning to a chosen thread, completing a
  reflection, applying a Moment, correcting a record, practicing, or finishing
  a member-chosen step—not raw clicks or session length.
- **PS-RV-MOM-003:** No missed day, week, or period shall reset the member to
  zero, erase prior continuity, trigger loss copy, or require recovery labor.
- **PS-RV-MOM-004:** Returning after absence shall be recognized as continuation
  when recognition is useful; the product shall not call it a comeback from
  failure.
- **PS-RV-MOM-005:** Momentum shall be private by default and shall not create
  public counts, rankings, comparison, or social pressure.
- **PS-RV-MOM-006:** The member may hide, pause, or disable Momentum while
  retaining all underlying records.
- **PS-RV-MOM-007:** Purposeful acknowledgements/badges may recognize a clear,
  truthful criterion such as completing a chosen project reflection or
  revisiting a thread across a member-selected period.
- **PS-RV-MOM-008:** Every acknowledgement shall disclose its criterion and
  shall not assert mastery, skill verification, employability, identity, or
  superior performance.
- **PS-RV-MOM-009:** Acknowledgements shall be sparse, private, dismissible, and
  free of artificial scarcity or collectible pressure.
- **PS-RV-MOM-010:** Progress Keepsakes remain member-selected references and
  are not interchangeable with system acknowledgements.
- **PS-RV-MOM-011:** Momentum language shall be factual and proportionate;
  volume does not equal growth and inactivity does not equal decline.
- **PS-RV-MOM-012:** A member shall be able to inspect which events contributed
  to a Momentum summary and correct an incorrect relationship.
- **PS-RV-MOM-013:** Deleted/revoked events shall be removed or recomputed
  without exposing private historical counts.
- **PS-RV-MOM-014:** The product shall not optimize notifications, prompts, or
  recommendations to preserve a Momentum number.
- **PS-RV-MOM-015:** Visual continuity may use paths, chapters, threads, or calm
  summaries; it shall not use anxiety-inducing countdowns or broken chains.
- **PS-RV-MOM-016:** Exact formulae and acknowledgement names require user
  testing and a documented anti-pressure review before implementation.

## Prompt and Ritual Service

A prompt is a momentary optional question. A ritual is a member-chosen pattern
for reflection or preparation. Neither is a required chore.

- **PS-RV-PRM-001:** Prompts shall be private, specific, optional, source-aware
  when applicable, and useful without requiring AI.
- **PS-RV-PRM-002:** The member shall control cadence, delivery surface,
  notification permission, quiet hours, timezone, pause, snooze, dismiss, and
  stop-all state.
- **PS-RV-PRM-003:** A prompt shall never claim urgency, threatened loss,
  missed-day failure, popularity, or a moral obligation to contribute.
- **PS-RV-PRM-004:** The service shall cap frequency and avoid near-duplicate
  wording, repetitive themes, and recently dismissed subjects.
- **PS-RV-PRM-005:** Prompt personalization may use permitted history, Focus
  Themes, prior feedback, chosen rituals, current room, and explicit goals; it
  shall not infer sensitive traits or diagnoses.
- **PS-RV-PRM-006:** Prompt DNA is an internal personalization concept, not an
  immutable profile of the member. The member can inspect/reset relevant
  preferences.
- **PS-RV-PRM-007:** A ritual shall state its purpose, expected duration,
  cadence, data use, completion condition, and how to pause/end it.
- **PS-RV-PRM-008:** Ritual completion is an owner event; it shall not publish,
  create a public badge, or broaden audience.
- **PS-RV-PRM-009:** The member may answer by Type or Speak where Capture is
  available; saving follows the same Save Moment contract.
- **PS-RV-PRM-010:** “Not now” and dismissal complete the interaction without a
  penalty or repeated immediate request.
- **PS-RV-PRM-011:** Prompts may invite Release/Reframe, reflection, preparation,
  future-self messages, or selected journeys only after the specific content
  and safety review passes.
- **PS-RV-PRM-012:** The service shall be silent when personalization confidence
  is low or the only candidate is sensitive/repetitive.
- **PS-RV-PRM-013:** Notification content shall reveal no private Moment detail
  on a lock screen unless the member explicitly permits an appropriate preview.
- **PS-RV-PRM-014:** Delivery and response telemetry shall use safe identifiers
  and state only; prompt/answer content is excluded from analytics logs.
- **PS-RV-PRM-015:** Provider failure shall fall back to deterministic prompt
  sets or no prompt; fabricated personalization is prohibited.
- **PS-RV-PRM-016:** A prompt response may become a Moment only after explicit
  Save Moment; dismissing or typing transient text does not silently save.
- **PS-RV-PRM-017:** Ritual history shall be exportable/deletable and shall not
  survive source/member deletion beyond disclosed policy.
- **PS-RV-PRM-018:** Exact ritual names and schedules remain open; the service
  contract is locked.

## What PeerSlate Noticed and Slate Mirror

Slate Mirror is the governed observation capability. **What PeerSlate
Noticed** is its primary everyday surface. It is not a persona, diagnosis, or
claim to know the member better than they know themselves.

- **PS-RV-OBS-001:** An observation shall use only authorized, active,
  sufficiently supported sources and shall list the exact records behind it.
- **PS-RV-OBS-002:** Eligible observation types are limited initially to
  recurrence, change over time, unfinished thread, cross-context reuse,
  member-chosen theme movement, missing context, and clearly evidenced
  progress/decision patterns.
- **PS-RV-OBS-003:** Observations shall use calibrated language such as “may,”
  “appears in these Moments,” or “you have mentioned,” and shall disclose
  material uncertainty or conflicting records.
- **PS-RV-OBS-004:** The system shall not diagnose mood, mental/physical health,
  personality, motivation, competence, identity, relationship quality, or
  future outcome.
- **PS-RV-OBS-005:** Voice prosody, tone, pace, pauses, or inferred emotion shall
  not be used for diagnosis or hidden scoring. Any later voice cue requires a
  separate opt-in, validation, disclosure, and safety decision.
- **PS-RV-OBS-006:** The member shall be able to Confirm, Correct, Dismiss, Mark
  too personal, Show less like this, Inspect sources, and optionally activate a
  next step.
- **PS-RV-OBS-007:** Confirming an observation confirms only the interpretation
  record; it shall not silently rewrite canonical Moments or identity facts.
- **PS-RV-OBS-008:** Correction shall preserve the member's explanation and
  influence future observations without deleting source history.
- **PS-RV-OBS-009:** “Too personal” shall suppress the item and related
  proactive use according to an understandable rule.
- **PS-RV-OBS-010:** Observations shall expire or be invalidated when their
  source set, lifecycle, audience, or contradictory history changes.
- **PS-RV-OBS-011:** The surface shall be quiet or absent when evidence is
  insufficient; generic encouragement is not a substitute.
- **PS-RV-OBS-012:** The service shall not optimize for surprise, emotional
  intensity, confession, or shareability.
- **PS-RV-OBS-013:** An observation may propose one question or next action, but
  the member decides whether to save, place, schedule, share, or do anything.
- **PS-RV-OBS-014:** Owner observations are not exposed to selected-person,
  Connection, member, Public, public Ask [Name] AI, or public analytics by
  default.
- **PS-RV-OBS-015:** Viewer-facing observations, if ever authorized, require a
  separate projection computed only from viewer-permitted records.
- **PS-RV-OBS-016:** The generation record shall include owner, scope, source
  versions, rule/model version, prompt/template version where applicable,
  uncertainty, lifecycle, and feedback state.
- **PS-RV-OBS-017:** A deterministic rules path shall support basic observations
  and safety checks; a model shall not be the sole authority on eligibility.
- **PS-RV-OBS-018:** The interface shall visibly distinguish source facts,
  PeerSlate's interpretation, the member's correction, and an optional action.
- **PS-RV-OBS-019:** Evaluation shall measure source support, usefulness,
  correction/dismiss/too-personal rates, repeated-error suppression, and member
  trust—not engagement volume.
- **PS-RV-OBS-020:** This capability shall begin with an internal/two-member
  trust pilot after sufficient real history, not with fabricated fixtures
  presented as actual insight.

## Keepsakes and Focus Themes

- A **Progress Keepsake** is a member-selected reference to a quote, recording
  clip, comparison, Replay item, projection, or Moment that matters to them.
- A **Focus Theme** is a private, optional, time-bounded lens that can gently
  tune prompts, resurfacing, Replay, and preparation.
- Neither is a destination, canonical fact, public trophy, or popularity
  object.
- Selection/removal, source invalidation, audience, export, and deletion must
  be explicit.
