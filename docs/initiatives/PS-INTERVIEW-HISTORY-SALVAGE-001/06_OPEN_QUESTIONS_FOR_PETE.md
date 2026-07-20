# 06 — Open questions for Pete

These must be answered before a manager activates a package or names a writer.
Questions 1, 2, and 6 are blocking; the rest can be settled during package
definition. Nothing has been implemented, and no answer is assumed.

---

## Q1 — BLOCKING. Is an interview story its own record, or a view of a Moment?

**The situation.** PS-MOMENT-001 released a private, owner-scoped, versioned,
member-confirmed canonical record with exact source pinning and deleted-source
tombstones. PS-PLACEMENT-001 then released a reference from one exact confirmed
Moment version to a destination, copying no text. The old branch was designed
before either existed and proposes a *second* private, versioned,
member-confirmed aggregate — `dbo.interview_stories` — for the same kind of
lived experience.

**The risk of two.** A member captures "the contract renegotiation" as a
Moment, then answers an interview question about it and creates an interview
story. Now there are two canonical records of one experience, each versioned,
each independently confirmable, capable of disagreeing. Which one is the truth?

**The risk of one.** The shapes really are different. A Moment has
`moment_kind` / `title` / `occurred_on` / `narrative` / `why_it_matters`. An
interview story needs situation, responsibility, personal actions, reasoning,
results, reflection, competencies, source question, and per-field capture
progress. Forcing that into `narrative` overloads the canonical record — the
same objection the old branch's own audit raised against reusing
`career_chapters` and `career_achievements`.

**Options.**

- **(a) Separate aggregate** — closest to the branch. Six tables. Independent,
  self-contained, heavier, and creates the two-truths problem.
- **(b) Moment elaboration** — an interview story is a STAR decomposition
  attached by reference to one exact confirmed Moment version, inheriting its
  canonical facts. Four tables. One truth per experience. Reuses a proven
  contract. But a story cannot exist until the experience is a Moment, which
  makes "capture a story mid-practice" a longer journey.
- **(c) Defer** — implement nothing until the Projects/Story system boundaries
  from PS-PROJECTS-001 and PS-STORY-COMPOSER-001 are settled, since all three
  are competing to represent "things that happened to a member."

`04_SCHEMA_AND_MIGRATION_PLAN.md` sketches shapes for (a) and (b).

---

## Q2 — BLOCKING. Does private history belong on the public Studio, or under `/app`?

`/interview-studio` is fully public and unauthenticated — that is what
PS-INTERVIEW-PUBLIC-GATE-001 released and what `CURRENT_STATE.md` describes as
"a public browser-local practice experience… not an authenticated private
history system." Every other private surface lives under `/app`.

**Options.**

- **(a) Private mode inside the public Studio.** One page, signed-in members see
  more. Matches the old branch. Means the public page carries sign-in
  affordances and the public route reads private data.
- **(b) A separate private Studio under `/app`.** Clean boundary, matches every
  released private surface, but duplicates the practice experience and splits
  the product in two.
- **(c) Public Studio stays exactly as released; private history attaches to a
  future authenticated Story or Moment surface instead**, and interview practice
  simply *reads* it.

A sub-question if (a): the old branch returns HTTP `200` with
`sufficiency.status = 'PERMISSION_REQUIRED'` for anonymous callers rather than
`401`. That is defensible — the page can explain the gate instead of erroring,
and it does not distinguish "not signed in" from "no permitted stories" — but it
should be your deliberate choice, not an inherited one.

---

## Q3 — Where should the private story API live?

- **(a)** Extend the existing authenticated `owner` blueprint in
  `owner_routes.py`, under `/app/...`. Matches Capture, Voice, Photo, Moment,
  and Owner Home precedent. Recommended in `03_…`.
- **(b)** A new authenticated blueprint at `/api/interview/stories`, closest to
  the branch. Keeps interview concerns together, but places an authenticated
  blueprint under a prefix currently owned by three unauthenticated routes.

---

## Q4 — May confirming an interview story write an "approved" approval event?

`usp_ConfirmInterviewStory` flips the linked `slate_entities` row to
`approval_status='approved'` and inserts a `content_approval_events` row with
`action_type='approved'`. The row stays private and unpublished.

Every released package keeps confirmation, approval, and publication strictly
separate — `CURRENT_STATE.md` states plainly that Moment confirmation "does not
publish or place content."

- **(a)** Keep it, documented explicitly as "approved for the member's own
  private use, never for an audience."
- **(b)** Drop the approval-event write; record confirmation in the story's own
  audit trail only.

---

## Q5 — What consent wording does AI grounding require?

`allowed_for_ai_grounding` is the best idea on the branch, but grounding sends
confirmed private member text to an external model provider. That is a real
privacy expansion beyond anything released.

The branch's checkbox reads: "Allow this confirmed story to ground future
Interview AI answers." It does not mention transmission to a provider.

Should the consent be explicit about that? Should it be per-story only, or also
a global default? Should it expire or require periodic re-confirmation?

---

## Q6 — BLOCKING for sequencing. Does this compete with lanes already in flight?

Three lanes are already assigned in `CURRENT_BASELINE.yaml`:
`PS-CAPTURE-MEDIA-001` (Photo enablement, writer unassigned),
`PS-HOME-INTERVIEW-PARITY-001` (Claude Code sole writer, architecture checkpoint
awaiting manager review), and `PS-HOME-FRONTEND-001` (Codex writer, branch
pending). `NEXT_TASK_BOARD.md` lists four more open tasks.

This package would touch `app.py`, `services/database_service.py`, and
`scripts/apply_sql_migrations.py` — all files other lanes plausibly need. Is
member-history salvage a priority now, or does it wait behind Photo dark-launch,
Bible v2.7, and the two homepage lanes?

---

## Q7 — Should the illustrative-answer validation fix be pulled out separately?

`app.py::validate_interview_model_answer` raises when `evidenceIds` is empty,
but the released `best_practice` grounding mode calls it with an empty evidence
map and instructs the model to return an empty list. Read from source, that path
cannot validate and would surface as a `502`.

The old branch fixed it with a two-line `allow_illustrative` parameter and a
focused test. It is independent of every other question here.

**This has not been reproduced against a running request and has not been
fixed.** Should it get its own small lane now, or wait?

---

## Q8 — Retention and deletion of generated answers

`dbo.interview_answer_attempts` would store the generated answer text — private
member content derived from private stories — in an audit table.

What happens to prior answer attempts when a member deletes the story they were
derived from? Options: cascade-delete, tombstone the source link and keep the
text, or tombstone both. PS-MOMENT-001 already established a body-free
source-tombstone pattern that could apply.

Also: does answer text belong in the per-owner export path that Capture already
has?

---

## Q9 — Disposition of the old branch

`origin/work/2026-07-17-member-history-completion` at `b439afb` is listed in
`NEXT_TASK_BOARD.md` Task 7 as one of six stale remote branches awaiting a
disposition record.

Now that its content is inventoried here, options are: archive-tag and delete
the remote branch; keep it until a package is actually written; or keep it
indefinitely as a reference. Per `docs/AI_WORKFLOW.md`, a recovery reference
must exist before any deletion.

**Nothing has been deleted, tagged, or changed on that branch.** Its tip is
recorded in this package so the work can always be recovered:
`b439afb2c94b527f68d6d31ba7a9e34e3f49387d`.
